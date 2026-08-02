"""Timeout-path tests for Pandoc HTML/DOCX wrapper helpers.

Purpose:
    Verify deterministic timeout mapping for converter wrappers that previously
    lacked dedicated subprocess timeout coverage.

Relationships:
    - Exercises `pandoc_markdown_to_html` and `pandoc_html_to_docx`.
    - Supports resource sandboxing security/resilience hardening evidence.
    - Validates that DOCX-output wrappers do not use Pandoc `--sandbox`, since
      Pandoc's DOCX writer requires built-in data files that are unavailable
      under sandbox mode.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure import pandoc_html_to_docx, pandoc_markdown_to_html
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HTML_TO_DOCX_EMPTY,
    HTML_TO_DOCX_TIMEOUT,
    HtmlToDocxConversionError,
    convert_html_to_docx,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MARKDOWN_TO_HTML_EMPTY,
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

    def _raise_timeout(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        assert "--sandbox" not in command
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=10)

    monkeypatch.setattr(pandoc_markdown_to_html, "run_pandoc_command", _raise_timeout)

    with pytest.raises(MarkdownToHtmlConversionError) as exc_info:
        convert_markdown_to_html(
            markdown_path=markdown_path,
            output_html_path=output_html,
            timeout_seconds=10,
        )

    error = exc_info.value
    assert error.code == MARKDOWN_TO_HTML_TIMEOUT


def test_convert_markdown_to_html_does_not_use_sandbox_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "note.md"
    markdown_path.write_text("# Title\n\nBody\n", encoding="utf-8")
    output_html = tmp_path / "note.html"
    seen_commands: list[list[str]] = []

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _fake_run_pandoc_command(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        seen_commands.append(command)
        output_html.write_text("<html><body>ok</body></html>", encoding="utf-8")
        return (0, "")

    monkeypatch.setattr(pandoc_markdown_to_html, "run_pandoc_command", _fake_run_pandoc_command)

    convert_markdown_to_html(markdown_path=markdown_path, output_html_path=output_html)

    assert output_html.exists()
    assert "--sandbox" not in seen_commands[0]


def test_convert_markdown_to_html_reports_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    markdown_path = tmp_path / "note.md"
    markdown_path.write_text("# Title\n\nBody\n", encoding="utf-8")
    output_html = tmp_path / "note.html"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        pandoc_markdown_to_html,
        "run_pandoc_command",
        lambda **kwargs: (0, ""),
    )

    with pytest.raises(MarkdownToHtmlConversionError) as exc_info:
        convert_markdown_to_html(markdown_path=markdown_path, output_html_path=output_html)

    assert exc_info.value.code == MARKDOWN_TO_HTML_EMPTY


def test_convert_html_to_docx_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_docx = tmp_path / "page.docx"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _raise_timeout(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        assert "--sandbox" not in command
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=12)

    monkeypatch.setattr(pandoc_html_to_docx, "run_pandoc_command", _raise_timeout)

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


def test_convert_html_to_docx_does_not_use_sandbox_flag(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_docx = tmp_path / "page.docx"
    seen_commands: list[list[str]] = []

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _fake_run_pandoc_command(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        seen_commands.append(command)
        output_docx.write_bytes(b"docx")
        return (0, "")

    monkeypatch.setattr(pandoc_html_to_docx, "run_pandoc_command", _fake_run_pandoc_command)

    convert_html_to_docx(
        html_path=html_path,
        output_docx_path=output_docx,
        resource_root=tmp_path,
        reference_docx_path=None,
    )

    assert output_docx.exists()
    assert "--sandbox" not in seen_commands[0]


def test_convert_html_to_docx_reports_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "page.html"
    html_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_docx = tmp_path / "page.docx"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        pandoc_html_to_docx,
        "run_pandoc_command",
        lambda **kwargs: (0, ""),
    )

    with pytest.raises(HtmlToDocxConversionError) as exc_info:
        convert_html_to_docx(
            html_path=html_path,
            output_docx_path=output_docx,
            resource_root=tmp_path,
            reference_docx_path=None,
        )

    assert exc_info.value.code == HTML_TO_DOCX_EMPTY
