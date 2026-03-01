"""Pandoc-backed DOCX to HTML conversion.

Purpose:
    Provide a deterministic DOCX -> standalone HTML converter used as an
    intermediary stage for v2 PDF outputs (`docx -> html -> pdf`).

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for the v2 `docx -> pdf`
      route.
    - Uses the local `pandoc` binary and maps failures to stable error codes.
    - Must run Pandoc in sandboxed mode (`--sandbox`).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.pandoc_subprocess import run_pandoc_command

PANDOC_NOT_INSTALLED = "pandoc_not_installed"
DOCX_TO_HTML_FAILED = "docx_to_html_failed"
DOCX_TO_HTML_EMPTY = "docx_to_html_empty"
DOCX_TO_HTML_UNREADABLE = "docx_to_html_unreadable"
DOCX_TO_HTML_TIMEOUT = "docx_to_html_timeout"
PANDOC_DEFAULT_TIMEOUT_SECONDS = 300


@dataclass(frozen=True)
class DocxToHtmlConversionError(Exception):
    """Typed, deterministic error for local DOCX->HTML conversion failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


def _looks_like_unreadable_docx(stderr: str) -> bool:
    lowered = stderr.lower()
    unreadable_markers = (
        "couldn't unpack docx container",
        "not a valid zip",
        "not a zip archive",
        "zip end of central directory",
        "docx container",
        "corrupt",
        "damaged",
    )
    return any(marker in lowered for marker in unreadable_markers)


def convert_docx_to_html(
    *,
    docx_path: Path,
    output_html_path: Path,
    extract_media_dir: Path,
    timeout_seconds: int = PANDOC_DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Convert DOCX to standalone HTML using the local `pandoc` binary."""

    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        raise DocxToHtmlConversionError(
            code=PANDOC_NOT_INSTALLED,
            message="Pandoc is not installed. Install the `pandoc` binary.",
        )

    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    extract_media_dir.mkdir(parents=True, exist_ok=True)

    command = [
        pandoc_bin,
        "--sandbox",
        docx_path.as_posix(),
        "--standalone",
        "--from=docx",
        "--to=html5",
        f"--extract-media={extract_media_dir.as_posix()}",
        "-o",
        output_html_path.as_posix(),
    ]

    try:
        return_code, stderr = run_pandoc_command(
            command=command,
            timeout_seconds=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise DocxToHtmlConversionError(
            code=DOCX_TO_HTML_TIMEOUT,
            message=f"Pandoc timed out after {timeout_seconds} seconds.",
        ) from exc
    except OSError as exc:
        raise DocxToHtmlConversionError(
            code=DOCX_TO_HTML_FAILED,
            message=f"Failed to run pandoc: {exc}",
        ) from exc

    if return_code != 0:
        detail = f": {stderr}" if stderr else ""
        code = (
            DOCX_TO_HTML_UNREADABLE if _looks_like_unreadable_docx(stderr) else DOCX_TO_HTML_FAILED
        )
        raise DocxToHtmlConversionError(
            code=code,
            message=f"Pandoc failed with exit code {return_code}{detail}",
        )

    if not output_html_path.exists() or output_html_path.stat().st_size == 0:
        raise DocxToHtmlConversionError(
            code=DOCX_TO_HTML_EMPTY,
            message=f"Pandoc produced an empty HTML file: {output_html_path}",
        )
