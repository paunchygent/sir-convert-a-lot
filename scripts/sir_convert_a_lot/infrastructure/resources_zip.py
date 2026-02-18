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
RESOURCES_ZIP_EXTRACT_FAILED = "resources_zip_extract_failed"


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


def extract_resources_zip(*, zip_path: Path, output_dir: Path) -> None:
    """Extract a resources zip to output_dir with path traversal protection."""
    try:
        zip_file = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile as exc:
        raise ResourcesZipError(
            code=RESOURCES_ZIP_INVALID,
            message="Uploaded resources bundle is not a valid zip file.",
        ) from exc

    try:
        output_dir.mkdir(parents=True, exist_ok=True)

        for member in zip_file.infolist():
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

        zip_file.extractall(output_dir)
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
