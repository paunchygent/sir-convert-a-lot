"""Resources zip extraction helpers for service API v2.

Purpose:
    Provide safe, deterministic extraction of uploaded resources bundles (zip)
    for v2 conversion jobs.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` when v2 jobs include a
      `resources` upload.
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

RESOURCES_ZIP_INVALID = "resources_zip_invalid"
RESOURCES_ZIP_PATH_TRAVERSAL = "resources_zip_path_traversal"
RESOURCES_ZIP_TOO_MANY_MEMBERS = "resources_zip_too_many_members"
RESOURCES_ZIP_MEMBER_TOO_LARGE = "resources_zip_member_too_large"
RESOURCES_ZIP_TOTAL_TOO_LARGE = "resources_zip_total_too_large"
RESOURCES_ZIP_EXTRACT_FAILED = "resources_zip_extract_failed"

DEFAULT_MAX_ZIP_MEMBERS = 500
DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_MEMBER_UNCOMPRESSED_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class ResourcesZipError(Exception):
    """Typed error for resources zip extraction failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


def _is_within_directory(*, directory: Path, target: Path) -> bool:
    directory_resolved = directory.resolve()
    target_resolved = target.resolve()
    return directory_resolved == target_resolved or directory_resolved in target_resolved.parents


def extract_resources_zip(
    *,
    zip_path: Path,
    output_dir: Path,
    max_members: int = DEFAULT_MAX_ZIP_MEMBERS,
    max_total_uncompressed_bytes: int = DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
    max_member_uncompressed_bytes: int = DEFAULT_MAX_MEMBER_UNCOMPRESSED_BYTES,
) -> None:
    """Extract a resources zip to output_dir with path traversal + size limits."""
    try:
        zip_file = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise ResourcesZipError(
            code=RESOURCES_ZIP_INVALID,
            message="Uploaded resources bundle is not a valid zip file.",
        ) from exc

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        members = list(zip_file.infolist())
        if len(members) > max_members:
            raise ResourcesZipError(
                code=RESOURCES_ZIP_TOO_MANY_MEMBERS,
                message=(
                    "Uploaded resources bundle contains too many zip members "
                    f"({len(members)} > {max_members})."
                ),
            )

        total_uncompressed_bytes = 0
        validated_members: list[tuple[zipfile.ZipInfo, Path]] = []
        for member in members:
            name = member.filename
            if name.startswith("/") or name.startswith("\\"):
                raise ResourcesZipError(
                    code=RESOURCES_ZIP_PATH_TRAVERSAL,
                    message=f"Zip member uses an absolute path: {name}",
                )

            destination = output_dir / name
            if not _is_within_directory(directory=output_dir, target=destination):
                raise ResourcesZipError(
                    code=RESOURCES_ZIP_PATH_TRAVERSAL,
                    message=f"Zip member escapes target directory: {name}",
                )

            member_size = int(member.file_size)
            if member_size > max_member_uncompressed_bytes:
                raise ResourcesZipError(
                    code=RESOURCES_ZIP_MEMBER_TOO_LARGE,
                    message=(
                        "Zip member exceeds the configured uncompressed size limit: "
                        f"{name} ({member_size} bytes > {max_member_uncompressed_bytes})."
                    ),
                )

            total_uncompressed_bytes += member_size
            if total_uncompressed_bytes > max_total_uncompressed_bytes:
                raise ResourcesZipError(
                    code=RESOURCES_ZIP_TOTAL_TOO_LARGE,
                    message=(
                        "Uploaded resources bundle exceeds the configured total uncompressed size "
                        f"limit ({total_uncompressed_bytes} bytes > "
                        f"{max_total_uncompressed_bytes})."
                    ),
                )

            validated_members.append((member, destination))

        for member, destination in validated_members:
            if member.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                continue

            destination.parent.mkdir(parents=True, exist_ok=True)
            with zip_file.open(member) as input_stream, destination.open("wb") as output_stream:
                shutil.copyfileobj(input_stream, output_stream)
    except ResourcesZipError:
        raise
    except Exception as exc:
        raise ResourcesZipError(
            code=RESOURCES_ZIP_EXTRACT_FAILED,
            message=f"Failed to extract resources zip: {type(exc).__name__}: {exc}",
        ) from exc
    finally:
        zip_file.close()


def reset_directory(path: Path) -> None:
    """Remove and recreate a directory (best-effort) for deterministic workspaces."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
