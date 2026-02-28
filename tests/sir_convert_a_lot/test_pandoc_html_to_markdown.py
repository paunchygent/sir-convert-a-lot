"""Unit tests for Pandoc HTML to Markdown conversion wrapper.

Purpose:
    Validate deterministic error mapping and success-path behavior for the
    local `html -> markdown` converter wrapper.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_markdown`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_markdown import (
    HTML_TO_MARKDOWN_EMPTY,
    HTML_TO_MARKDOWN_FAILED,
    HTML_TO_MARKDOWN_TIMEOUT,
    HtmlToMarkdownConversionError,
    convert_html_to_markdown,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED


class _Completed:
    def __init__(self, *, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr


def test_convert_html_to_markdown_rejects_missing_pandoc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    with pytest.raises(HtmlToMarkdownConversionError) as exc_info:
        convert_html_to_markdown(
            html_path=tmp_path / "input.html",
            output_markdown_path=tmp_path / "output.md",
            resource_root=tmp_path,
        )

    error = exc_info.value
    assert error.code == PANDOC_NOT_INSTALLED


def test_convert_html_to_markdown_maps_generic_pandoc_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_html = tmp_path / "input.html"
    input_html.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(returncode=2, stderr="unexpected conversion error"),
    )

    with pytest.raises(HtmlToMarkdownConversionError) as exc_info:
        convert_html_to_markdown(
            html_path=input_html,
            output_markdown_path=output_md,
            resource_root=tmp_path,
        )

    error = exc_info.value
    assert error.code == HTML_TO_MARKDOWN_FAILED


def test_convert_html_to_markdown_rejects_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_html = tmp_path / "input.html"
    input_html.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(returncode=0, stderr=""),
    )

    with pytest.raises(HtmlToMarkdownConversionError) as exc_info:
        convert_html_to_markdown(
            html_path=input_html,
            output_markdown_path=output_md,
            resource_root=tmp_path,
        )

    error = exc_info.value
    assert error.code == HTML_TO_MARKDOWN_EMPTY


def test_convert_html_to_markdown_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_html = tmp_path / "input.html"
    input_html.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _raise_timeout(*args: object, **kwargs: object) -> _Completed:
        del args, kwargs
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=5)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    with pytest.raises(HtmlToMarkdownConversionError) as exc_info:
        convert_html_to_markdown(
            html_path=input_html,
            output_markdown_path=output_md,
            resource_root=tmp_path,
        )

    error = exc_info.value
    assert error.code == HTML_TO_MARKDOWN_TIMEOUT


def test_convert_html_to_markdown_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_html = tmp_path / "input.html"
    input_html.write_text("<html><body>Hello</body></html>", encoding="utf-8")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _fake_run(*args, **kwargs) -> _Completed:
        del args, kwargs
        output_md.write_text("# Converted\n\nBody\n", encoding="utf-8")
        return _Completed(returncode=0, stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    convert_html_to_markdown(
        html_path=input_html,
        output_markdown_path=output_md,
        resource_root=tmp_path,
    )

    assert output_md.exists()
    assert output_md.read_text(encoding="utf-8").startswith("# Converted")
