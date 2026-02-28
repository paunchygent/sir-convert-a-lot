"""Pandoc-backed DOCX to Markdown conversion.

Purpose:
    Provide a local DOCX -> Markdown converter used by the v2 `docx -> md`
    route as a deterministic conversion stage before markdown normalization.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for DOCX-source routes.
    - Uses the local `pandoc` binary and maps failures to stable error codes.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED

DOCX_TO_MARKDOWN_FAILED = "docx_to_markdown_failed"
DOCX_TO_MARKDOWN_EMPTY = "docx_to_markdown_empty"
DOCX_TO_MARKDOWN_UNREADABLE = "docx_to_markdown_unreadable"


@dataclass(frozen=True)
class DocxToMarkdownConversionError(Exception):
    """Typed, deterministic error for local DOCX->Markdown conversion failures."""

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


def convert_docx_to_markdown(
    *,
    docx_path: Path,
    output_markdown_path: Path,
) -> None:
    """Convert DOCX to Markdown using the local `pandoc` binary."""

    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        raise DocxToMarkdownConversionError(
            code=PANDOC_NOT_INSTALLED,
            message="Pandoc is not installed. Install the `pandoc` binary.",
        )

    output_markdown_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        pandoc_bin,
        docx_path.as_posix(),
        "--from=docx",
        "--to=gfm",
        "-o",
        output_markdown_path.as_posix(),
    ]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise DocxToMarkdownConversionError(
            code=DOCX_TO_MARKDOWN_FAILED,
            message=f"Failed to run pandoc: {exc}",
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        code = (
            DOCX_TO_MARKDOWN_UNREADABLE
            if _looks_like_unreadable_docx(stderr)
            else DOCX_TO_MARKDOWN_FAILED
        )
        raise DocxToMarkdownConversionError(
            code=code,
            message=f"Pandoc failed with exit code {completed.returncode}{detail}",
        )

    if not output_markdown_path.exists() or output_markdown_path.stat().st_size == 0:
        raise DocxToMarkdownConversionError(
            code=DOCX_TO_MARKDOWN_EMPTY,
            message=f"Pandoc produced an empty Markdown file: {output_markdown_path}",
        )
