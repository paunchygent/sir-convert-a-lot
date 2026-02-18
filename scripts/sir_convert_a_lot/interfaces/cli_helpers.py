"""CLI helper functions for Sir Convert-a-Lot.

Purpose:
    Keep the Typer CLI entrypoint (`interfaces.cli_app`) focused on command
    definitions by isolating parsing, file discovery, deterministic zip
    assembly, and job-spec/idempotency helpers.

Relationships:
    - Used by `interfaces.cli_app` for `convert` route selection and payload
      preparation for both v1 and v2 job submissions.
    - Uses `interfaces.cli_routes` for route enumeration and type-safe formats.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path

import typer

from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.interfaces.cli_routes import (
    SourceFormat,
    TargetFormat,
    list_routes,
)


def parse_target_format(raw: str) -> TargetFormat:
    """Parse `--to` into a typed TargetFormat value."""
    try:
        return TargetFormat(raw.lower().strip())
    except ValueError as exc:
        raise typer.BadParameter(f"Unsupported --to value: {raw}") from exc


def parse_source_format(raw: str) -> SourceFormat:
    """Parse `--from` into a typed SourceFormat value."""
    try:
        return SourceFormat(raw.lower().strip())
    except ValueError as exc:
        raise typer.BadParameter(f"Unsupported --from value: {raw}") from exc


def discover_files_by_extension(
    source: Path, *, extensions: tuple[str, ...], recursive: bool
) -> list[Path]:
    """Return stable file listing for source directory/file with allowed extensions."""
    if source.is_file():
        return [source]

    results: list[Path] = []
    patterns = [f"**/*{ext}" if recursive else f"*{ext}" for ext in extensions]
    for pattern in patterns:
        results.extend(path for path in source.glob(pattern) if path.is_file())

    return sorted(set(results))


def discover_source_files(
    source: Path, *, source_format: SourceFormat, recursive: bool
) -> list[Path]:
    """Discover source files based on SourceFormat rules."""
    if source_format is SourceFormat.PDF:
        return discover_files_by_extension(source, extensions=(".pdf",), recursive=recursive)
    if source_format is SourceFormat.MD:
        return discover_files_by_extension(
            source, extensions=(".md", ".markdown"), recursive=recursive
        )
    if source_format is SourceFormat.HTML:
        return discover_files_by_extension(
            source, extensions=(".html", ".htm"), recursive=recursive
        )
    if source_format is SourceFormat.DOCX:
        return discover_files_by_extension(source, extensions=(".docx",), recursive=recursive)
    raise AssertionError(f"Unsupported source_format: {source_format}")


def detect_directory_source_format(
    *,
    source_dir: Path,
    target_format: TargetFormat,
    recursive: bool,
) -> SourceFormat:
    """Infer source format for directory conversions, rejecting ambiguous inputs."""
    if target_format is TargetFormat.MD:
        return SourceFormat.PDF

    candidates = sorted({route.source for route in list_routes() if route.target is target_format})
    present: list[SourceFormat] = []
    for candidate in candidates:
        if discover_source_files(source_dir, source_format=candidate, recursive=recursive):
            present.append(candidate)

    if not present:
        raise typer.BadParameter(
            f"No source files found in {source_dir} for target '{target_format.value}'. "
            "Provide --from to disambiguate."
        )

    if len(present) > 1:
        options = ", ".join(sorted(fmt.value for fmt in present))
        raise typer.BadParameter(
            f"Ambiguous input directory: found multiple source formats ({options}). "
            "Provide --from to disambiguate."
        )

    return present[0]


def default_job_spec_v1(
    *,
    filename: str,
    acceleration_policy: str,
    backend_strategy: str,
    ocr_mode: str,
    table_mode: str,
    normalize: str,
) -> dict[str, object]:
    """Return the default v1 job_spec payload."""
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": backend_strategy,
            "ocr_mode": ocr_mode,
            "table_mode": table_mode,
            "normalize": normalize,
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def idempotency_key_for_file(pdf_path: Path, job_spec: dict[str, object]) -> str:
    """Return a deterministic v1 Idempotency-Key based on filename + content + spec."""
    file_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    spec_sha = hashlib.sha256(
        json.dumps(job_spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    combined = hashlib.sha256(f"{pdf_path.name}:{file_sha}:{spec_sha}".encode("utf-8")).hexdigest()
    return f"idem_{combined[:48]}"


def default_job_spec_v2(
    *,
    filename: str,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
    css_filenames: list[str],
    reference_docx_filename: str | None,
    acceleration_policy: str,
    backend_strategy: str,
    ocr_mode: str,
    table_mode: str,
    normalize: str,
) -> dict[str, object]:
    """Return the default v2 job_spec payload for the selected route."""
    conversion: dict[str, object] = {
        "output_format": output_format.value,
        "css_filenames": css_filenames,
        "reference_docx_filename": reference_docx_filename,
    }

    payload: dict[str, object] = {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": source_format.value},
        "conversion": conversion,
        "retention": {"pin": False},
    }

    if source_format == SourceFormatV2.PDF:
        payload["pdf_options"] = {
            "backend_strategy": backend_strategy,
            "ocr_mode": ocr_mode,
            "table_mode": table_mode,
            "normalize": normalize,
        }
        payload["execution"] = {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        }

    return payload


def sha256_bytes(payload: bytes) -> str:
    """Return a hex SHA256 for bytes payloads."""
    return hashlib.sha256(payload).hexdigest()


def deterministic_zip_bytes(*, files: dict[str, bytes]) -> bytes:
    """Build deterministic zip bytes from an {arcname: bytes} mapping."""
    fixed_dt = (1980, 1, 1, 0, 0, 0)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zip_handle:
        for arcname in sorted(files):
            info = zipfile.ZipInfo(filename=arcname, date_time=fixed_dt)
            info.compress_type = zipfile.ZIP_DEFLATED
            zip_handle.writestr(info, files[arcname])
    return buffer.getvalue()


def build_resources_zip_payload(
    *, resources: Path | None, css_paths: tuple[Path, ...]
) -> tuple[bytes | None, list[str]]:
    """Build resources zip bytes (optional) and return CSS filenames for the v2 job spec."""
    files: dict[str, bytes] = {}

    if resources is not None:
        if resources.is_dir():
            root = resources.resolve()
            candidates = sorted(path for path in root.rglob("*") if path.is_file())
            for candidate in candidates:
                arcname = candidate.relative_to(root).as_posix()
                if arcname in files:
                    raise typer.BadParameter(f"Duplicate resources path in bundle: {arcname}")
                files[arcname] = candidate.read_bytes()
        else:
            if resources.suffix.lower() != ".zip":
                raise typer.BadParameter("--resources must be a directory or a .zip file.")
            with zipfile.ZipFile(resources) as zip_handle:
                for info in zip_handle.infolist():
                    if info.is_dir():
                        continue
                    arcname = info.filename
                    if arcname in files:
                        raise typer.BadParameter(f"Duplicate resources path in bundle: {arcname}")
                    files[arcname] = zip_handle.read(info)

    css_filenames: list[str] = []
    for css_path in css_paths:
        css_arcname: str
        if resources is not None and resources.is_dir():
            root = resources.resolve()
            resolved_css = css_path.resolve()
            if resolved_css.is_relative_to(root):
                css_arcname = resolved_css.relative_to(root).as_posix()
            else:
                css_arcname = css_path.name
        else:
            css_arcname = css_path.name

        css_bytes = css_path.read_bytes()
        if css_arcname in files:
            if files[css_arcname] != css_bytes:
                raise typer.BadParameter(
                    f"CSS file name collides with a different resources bundle entry: {css_arcname}"
                )
        else:
            files[css_arcname] = css_bytes
        css_filenames.append(css_arcname)

    if not files:
        return None, []

    return deterministic_zip_bytes(files=files), css_filenames


def idempotency_key_for_v2_request(
    *,
    filename: str,
    file_sha256: str,
    spec_payload: dict[str, object],
    resources_sha256: str | None,
    reference_docx_sha256: str | None,
) -> str:
    """Return a deterministic v2 Idempotency-Key based on the full request fingerprint."""
    spec_sha = hashlib.sha256(
        json.dumps(spec_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    resources_part = resources_sha256 or ""
    reference_part = reference_docx_sha256 or ""
    combined = hashlib.sha256(
        f"{filename}:{file_sha256}:{spec_sha}:{resources_part}:{reference_part}".encode("utf-8")
    ).hexdigest()
    return f"idemv2_{combined[:48]}"


def relative_source_label(source_root: Path, current_file: Path) -> str:
    """Return deterministic manifest labels relative to the input root."""
    if source_root.is_file():
        return current_file.name
    return current_file.relative_to(source_root).as_posix()
