"""Unit tests for Pandoc DOCX to Markdown conversion wrapper.

Purpose:
    Validate deterministic error mapping and success-path behavior for the
    local `docx -> markdown` converter wrapper.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_markdown`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_markdown import (
    DOCX_TO_MARKDOWN_EMPTY,
    DOCX_TO_MARKDOWN_FAILED,
    DOCX_TO_MARKDOWN_TIMEOUT,
    DOCX_TO_MARKDOWN_UNREADABLE,
    DocxToMarkdownConversionError,
    convert_docx_to_markdown,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED


class _Completed:
    def __init__(self, *, returncode: int, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr


def test_convert_docx_to_markdown_rejects_missing_pandoc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(
            docx_path=tmp_path / "input.docx",
            output_markdown_path=tmp_path / "output.md",
        )

    error = exc_info.value
    assert error.code == PANDOC_NOT_INSTALLED


def test_convert_docx_to_markdown_maps_unreadable_pandoc_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(
            returncode=2,
            stderr="couldn't unpack docx container: not a valid zip",
        ),
    )

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_UNREADABLE


def test_convert_docx_to_markdown_maps_generic_pandoc_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(returncode=2, stderr="unexpected conversion error"),
    )

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_FAILED


def test_convert_docx_to_markdown_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _raise_timeout(*args: object, **kwargs: object) -> _Completed:
        del args, kwargs
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=5)

    monkeypatch.setattr(subprocess, "run", _raise_timeout)

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_TIMEOUT


def test_convert_docx_to_markdown_rejects_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: _Completed(returncode=0, stderr=""),
    )

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_EMPTY


def test_convert_docx_to_markdown_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _fake_run(*args, **kwargs) -> _Completed:
        del args, kwargs
        output_md.write_text("# Converted\n\nBody\n", encoding="utf-8")
        return _Completed(returncode=0, stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    assert output_md.exists()
    assert output_md.read_text(encoding="utf-8").startswith("# Converted")
