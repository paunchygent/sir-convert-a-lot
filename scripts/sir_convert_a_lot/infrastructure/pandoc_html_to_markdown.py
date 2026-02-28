"""Pandoc-backed HTML to Markdown conversion.

Purpose:
    Provide a local HTML -> Markdown converter used by the v2 `html -> md`
    route after deterministic local-resource validation.

Relationships:
    - Called by `infrastructure.v2_conversion_executor` for HTML-source
      markdown-ingress routes.
    - Uses the local `pandoc` binary and maps failures to stable error codes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED

HTML_TO_MARKDOWN_FAILED = "html_to_markdown_failed"
HTML_TO_MARKDOWN_EMPTY = "html_to_markdown_empty"


@dataclass(frozen=True)
class HtmlToMarkdownConversionError(Exception):
    """Typed, deterministic error for local HTML->Markdown conversion failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


def convert_html_to_markdown(
    *,
    html_path: Path,
    output_markdown_path: Path,
    resource_root: Path,
) -> None:
    """Convert HTML to Markdown using the local `pandoc` binary."""

    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        raise HtmlToMarkdownConversionError(
            code=PANDOC_NOT_INSTALLED,
            message="Pandoc is not installed. Install the `pandoc` binary.",
        )

    output_markdown_path.parent.mkdir(parents=True, exist_ok=True)

    resource_paths: list[str] = []
    for candidate in (resource_root.resolve(), html_path.parent.resolve()):
        candidate_str = candidate.as_posix()
        if candidate_str not in resource_paths:
            resource_paths.append(candidate_str)

    command = [
        pandoc_bin,
        html_path.as_posix(),
        "--from=html",
        "--to=gfm",
        "--resource-path",
        os.pathsep.join(resource_paths),
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
        raise HtmlToMarkdownConversionError(
            code=HTML_TO_MARKDOWN_FAILED,
            message=f"Failed to run pandoc: {exc}",
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise HtmlToMarkdownConversionError(
            code=HTML_TO_MARKDOWN_FAILED,
            message=f"Pandoc failed with exit code {completed.returncode}{detail}",
        )

    if not output_markdown_path.exists() or output_markdown_path.stat().st_size == 0:
        raise HtmlToMarkdownConversionError(
            code=HTML_TO_MARKDOWN_EMPTY,
            message=f"Pandoc produced an empty Markdown file: {output_markdown_path}",
        )
