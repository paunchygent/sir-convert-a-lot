"""Pandoc-backed Markdown to HTML conversion.

Purpose:
    Provide a local Markdown -> standalone HTML converter used as an
    intermediary stage for layout-controlled PDF/DOCX routes.

Relationships:
    - Called by `scripts.sir_convert_a_lot.interfaces.cli_app` for the
      `md -> pdf` route (Task 28).
    - Intended for reuse by later routes such as `md -> docx` and hybrid
      `pdf -> docx` (service pdf->md + local md->html->docx).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

PANDOC_NOT_INSTALLED = "pandoc_not_installed"
MARKDOWN_TO_HTML_FAILED = "markdown_to_html_failed"
MARKDOWN_TO_HTML_EMPTY = "markdown_to_html_empty"


@dataclass(frozen=True)
class MarkdownToHtmlConversionError(Exception):
    """Typed, deterministic error for local Markdown->HTML conversion failures."""

    code: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial and stable
        return f"{self.code}: {self.message}"


def _extract_title_from_markdown(markdown_path: Path) -> str:
    text = markdown_path.read_text(encoding="utf-8")

    if text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            raw_yaml = parts[0].removeprefix("---\n")
            try:
                payload = yaml.safe_load(raw_yaml)
            except yaml.YAMLError:
                payload = None
            if isinstance(payload, dict):
                title = payload.get("title")
                if isinstance(title, str) and title.strip():
                    return title.strip()

    match = re.search(r"^#\s+(.+?)\s*$", text, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()

    return markdown_path.stem


def convert_markdown_to_html(
    *,
    markdown_path: Path,
    output_html_path: Path,
) -> None:
    """Convert Markdown to standalone HTML using the local `pandoc` binary."""

    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        raise MarkdownToHtmlConversionError(
            code=PANDOC_NOT_INSTALLED,
            message="Pandoc is not installed. Install the `pandoc` binary.",
        )

    title = _extract_title_from_markdown(markdown_path)
    output_html_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        pandoc_bin,
        markdown_path.as_posix(),
        "--standalone",
        "--from=markdown+smart",
        "--to=html5",
        "--metadata",
        f"title={title}",
        "-o",
        output_html_path.as_posix(),
    ]

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise MarkdownToHtmlConversionError(
            code=MARKDOWN_TO_HTML_FAILED,
            message=f"Failed to run pandoc: {exc}",
        ) from exc

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise MarkdownToHtmlConversionError(
            code=MARKDOWN_TO_HTML_FAILED,
            message=f"Pandoc failed with exit code {completed.returncode}{detail}",
        )

    if not output_html_path.exists() or output_html_path.stat().st_size == 0:
        raise MarkdownToHtmlConversionError(
            code=MARKDOWN_TO_HTML_EMPTY,
            message=f"Pandoc produced an empty HTML file: {output_html_path}",
        )
