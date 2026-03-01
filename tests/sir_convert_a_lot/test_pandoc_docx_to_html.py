"""Unit tests for Pandoc DOCX to HTML conversion wrapper."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure import pandoc_docx_to_html
from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_html import (
    DOCX_TO_HTML_EMPTY,
    DOCX_TO_HTML_FAILED,
    DOCX_TO_HTML_TIMEOUT,
    DOCX_TO_HTML_UNREADABLE,
    PANDOC_NOT_INSTALLED,
    DocxToHtmlConversionError,
    convert_docx_to_html,
)


def test_convert_docx_to_html_rejects_missing_pandoc(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("shutil.which", lambda name: None)

    with pytest.raises(DocxToHtmlConversionError) as exc_info:
        convert_docx_to_html(
            docx_path=tmp_path / "input.docx",
            output_html_path=tmp_path / "output.html",
            extract_media_dir=tmp_path / "media",
        )

    error = exc_info.value
    assert error.code == PANDOC_NOT_INSTALLED


def test_convert_docx_to_html_maps_unreadable_pandoc_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_html = tmp_path / "out.html"
    media_dir = tmp_path / "media"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    seen_commands: list[list[str]] = []

    def _fake_run_pandoc_command(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        seen_commands.append(command)
        return (2, "couldn't unpack docx container: not a valid zip")

    monkeypatch.setattr(pandoc_docx_to_html, "run_pandoc_command", _fake_run_pandoc_command)

    with pytest.raises(DocxToHtmlConversionError) as exc_info:
        convert_docx_to_html(
            docx_path=input_docx,
            output_html_path=output_html,
            extract_media_dir=media_dir,
        )

    error = exc_info.value
    assert error.code == DOCX_TO_HTML_UNREADABLE
    assert "--sandbox" in seen_commands[0]
    assert any(arg.startswith("--extract-media=") for arg in seen_commands[0])


def test_convert_docx_to_html_maps_generic_pandoc_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_html = tmp_path / "out.html"
    media_dir = tmp_path / "media"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _fake_run_pandoc_command(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        assert "--sandbox" in command
        return (2, "unexpected conversion error")

    monkeypatch.setattr(pandoc_docx_to_html, "run_pandoc_command", _fake_run_pandoc_command)

    with pytest.raises(DocxToHtmlConversionError) as exc_info:
        convert_docx_to_html(
            docx_path=input_docx,
            output_html_path=output_html,
            extract_media_dir=media_dir,
        )

    error = exc_info.value
    assert error.code == DOCX_TO_HTML_FAILED


def test_convert_docx_to_html_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_html = tmp_path / "out.html"
    media_dir = tmp_path / "media"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _raise_timeout(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        assert "--sandbox" in command
        raise subprocess.TimeoutExpired(cmd=["pandoc"], timeout=5)

    monkeypatch.setattr(pandoc_docx_to_html, "run_pandoc_command", _raise_timeout)

    with pytest.raises(DocxToHtmlConversionError) as exc_info:
        convert_docx_to_html(
            docx_path=input_docx,
            output_html_path=output_html,
            extract_media_dir=media_dir,
        )

    error = exc_info.value
    assert error.code == DOCX_TO_HTML_TIMEOUT


def test_convert_docx_to_html_rejects_empty_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_html = tmp_path / "out.html"
    media_dir = tmp_path / "media"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")

    def _fake_run_pandoc_command(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        assert "--sandbox" in command
        return (0, "")

    monkeypatch.setattr(pandoc_docx_to_html, "run_pandoc_command", _fake_run_pandoc_command)

    with pytest.raises(DocxToHtmlConversionError) as exc_info:
        convert_docx_to_html(
            docx_path=input_docx,
            output_html_path=output_html,
            extract_media_dir=media_dir,
        )

    error = exc_info.value
    assert error.code == DOCX_TO_HTML_EMPTY


def test_convert_docx_to_html_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_html = tmp_path / "out.html"
    media_dir = tmp_path / "media"

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/pandoc")
    seen_commands: list[list[str]] = []

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

    monkeypatch.setattr(pandoc_docx_to_html, "run_pandoc_command", _fake_run_pandoc_command)

    convert_docx_to_html(
        docx_path=input_docx,
        output_html_path=output_html,
        extract_media_dir=media_dir,
    )

    assert output_html.exists()
    assert "--sandbox" in seen_commands[0]
    assert any(arg.startswith("--extract-media=") for arg in seen_commands[0])
