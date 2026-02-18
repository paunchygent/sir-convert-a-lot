"""Pandoc-backed HTML to DOCX conversion.

Purpose:
    Provide a local HTML -> DOCX converter used as the second stage of the
    default `md -> html -> docx` pipeline.

Relationships:
    - Called by `scripts.sir_convert_a_lot.interfaces.cli_app` for the
      `md -> docx` route (Task 30).
    - Depends on the local `pandoc` binary; missing Pandoc must be mapped to a
      deterministic error code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED

HTML_TO_DOCX_FAILED = "html_to_docx_failed"
HTML_TO_DOCX_EMPTY = "html_to_docx_empty"


@dataclass(frozen=True)
class HtmlToDocxConversionError(Exception):
    """Typed, deterministic error for local HTML->DOCX conversion failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


def convert_html_to_docx(
    *,
    html_path: Path,
    output_docx_path: Path,
    resource_root: Path,
    reference_docx_path: Path | None,
) -> None:
    """Convert HTML to DOCX using the local `pandoc` binary."""

    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        raise HtmlToDocxConversionError(
            code=PANDOC_NOT_INSTALLED,
            message="Pandoc is not installed. Install the `pandoc` binary.",
        )

    output_docx_path.parent.mkdir(parents=True, exist_ok=True)

    resource_paths = [
        resource_root.resolve().as_posix(),
        html_path.parent.resolve().as_posix(),
    ]
    resource_path_arg = os.pathsep.join(resource_paths)

    command = [
        pandoc_bin,
        html_path.as_posix(),
        "--from=html",
        "--to=docx",
        "--resource-path",
        resource_path_arg,
        "-o",
        output_docx_path.as_posix(),
    ]
    if reference_docx_path is not None:
        command.extend(["--reference-doc", reference_docx_path.as_posix()])

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise HtmlToDocxConversionError(
            code=HTML_TO_DOCX_FAILED,
            message=f"Failed to run pandoc: {exc}",
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise HtmlToDocxConversionError(
            code=HTML_TO_DOCX_FAILED,
            message=f"Pandoc failed with exit code {completed.returncode}{detail}",
        )

    if not output_docx_path.exists() or output_docx_path.stat().st_size == 0:
        raise HtmlToDocxConversionError(
            code=HTML_TO_DOCX_EMPTY,
            message=f"Pandoc produced an empty DOCX file: {output_docx_path}",
        )
