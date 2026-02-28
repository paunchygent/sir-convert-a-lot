"""Timeout-path tests for Pandoc HTML/DOCX wrapper helpers.

Purpose:
    Verify deterministic timeout mapping for converter wrappers that previously
    lacked dedicated subprocess timeout coverage.

Relationships:
    - Exercises `pandoc_markdown_to_html` and `pandoc_html_to_docx`.
    - Supports Task 60 security/resilience hardening evidence.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HTML_TO_DOCX_TIMEOUT,
    HtmlToDocxConversionError,
    convert_html_to_docx,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MARKDOWN_TO_HTML_TIMEOUT,
    MarkdownToHtmlConversionError,
    convert_markdown_to_html,
)


def test_convert_markdown_to_html_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "note.md"
    markdown_path.write_text("# Title\n\nBody\n", encoding="utf-8")
    output_html = tmp_path / "note.html"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _raise_timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=10)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    with pytest.raises(MarkdownToHtmlConversionError) as exc_info:
        convert_markdown_to_html(
            markdown_path=markdown_path,
            output_html_path=output_html,
            timeout_seconds=10,
        )

    error = exc_info.value
    assert error.code == MARKDOWN_TO_HTML_TIMEOUT


def test_convert_html_to_docx_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_docx = tmp_path / "page.docx"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _raise_timeout(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=12)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    with pytest.raises(HtmlToDocxConversionError) as exc_info:
        convert_html_to_docx(
            html_path=html_path,
            output_docx_path=output_docx,
            resource_root=tmp_path,
            reference_docx_path=None,
            timeout_seconds=12,
        )

    error = exc_info.value
    assert error.code == HTML_TO_DOCX_TIMEOUT
