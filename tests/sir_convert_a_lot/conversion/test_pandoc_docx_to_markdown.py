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

from scripts.sir_convert_a_lot.infrastructure import pandoc_docx_to_markdown
from scripts.sir_convert_a_lot.infrastructure.markdown_normalization_v2 import (
    normalize_markdown_for_v2_md_output,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_docx_to_markdown import (
    DOCX_TO_MARKDOWN_EMPTY,
    DOCX_TO_MARKDOWN_FAILED,
    DOCX_TO_MARKDOWN_TIMEOUT,
    DOCX_TO_MARKDOWN_UNREADABLE,
    DocxToMarkdownConversionError,
    convert_docx_to_markdown,
    repair_exam_net_docx_markdown,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import PANDOC_NOT_INSTALLED


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

    monkeypatch.setattr(pandoc_docx_to_markdown, "run_pandoc_command", _fake_run_pandoc_command)

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_UNREADABLE
    assert "--sandbox" in seen_commands[0]


def test_convert_docx_to_markdown_maps_generic_pandoc_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

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
        return (2, "unexpected conversion error")

    monkeypatch.setattr(pandoc_docx_to_markdown, "run_pandoc_command", _fake_run_pandoc_command)

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_FAILED
    assert "--sandbox" in seen_commands[0]


def test_convert_docx_to_markdown_maps_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

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

    monkeypatch.setattr(pandoc_docx_to_markdown, "run_pandoc_command", _raise_timeout)

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
    seen_commands: list[list[str]] = []

    def _fake_run_pandoc_command(
        *,
        command: list[str],
        timeout_seconds: int,
        stderr_max_bytes: int = 65536,
    ) -> tuple[int, str]:
        del timeout_seconds, stderr_max_bytes
        seen_commands.append(command)
        return (0, "")

    monkeypatch.setattr(pandoc_docx_to_markdown, "run_pandoc_command", _fake_run_pandoc_command)

    with pytest.raises(DocxToMarkdownConversionError) as exc_info:
        convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    error = exc_info.value
    assert error.code == DOCX_TO_MARKDOWN_EMPTY
    assert "--sandbox" in seen_commands[0]


def test_convert_docx_to_markdown_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    input_docx = tmp_path / "input.docx"
    input_docx.write_bytes(b"PK\x03\x04fake")
    output_md = tmp_path / "out.md"

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
        output_md.write_text("# Converted\n\nBody\n", encoding="utf-8")
        return (0, "")

    monkeypatch.setattr(pandoc_docx_to_markdown, "run_pandoc_command", _fake_run_pandoc_command)

    convert_docx_to_markdown(docx_path=input_docx, output_markdown_path=output_md)

    assert output_md.exists()
    assert output_md.read_text(encoding="utf-8").startswith("# Converted")
    assert "--sandbox" in seen_commands[0]
    assert "--wrap=none" in seen_commands[0]


def test_repair_exam_net_docx_markdown_restores_paragraphs() -> None:
    raw = (
        "# Student\n\n"
        "### Antal ord: 449\n\n"
        "The power of curiosity\\\n"
        "\\\n"
        "What is curiosity? Why does it matter?\\\n"
        "\\\n"
        "\\\n"
        "Studies show that children ask more questions.\\\n"
        "Curiosity helps them learn faster.\\\n"
        "\\\n"
        "\\\n"
        "However, curiosity can also bring risk.\\\n"
    )

    repaired = repair_exam_net_docx_markdown(raw)

    assert "The power of curiosity\n\nWhat is curiosity? Why does it matter?\n\n" in repaired
    assert (
        "Studies show that children ask more questions. Curiosity helps them learn faster."
        in repaired
    )
    assert "However, curiosity can also bring risk." in repaired
    assert "\\\n" not in repaired


def test_repair_exam_net_docx_markdown_survives_strict_normalization() -> None:
    raw = (
        "# Student\n\n"
        "### Antal ord: 449\n\n"
        "The power of curiosity\\\n"
        "\\\n"
        "What is curiosity? Why does it matter?\\\n"
        "\\\n"
        "\\\n"
        "Studies show that children ask more questions.\\\n"
        "Curiosity helps them learn faster.\\\n"
        "\\\n"
        "\\\n"
        "However, curiosity can also bring risk.\\\n"
    )

    repaired = repair_exam_net_docx_markdown(raw)
    normalized, warnings = normalize_markdown_for_v2_md_output(markdown_content=repaired)

    assert "The power of curiosity\n\nWhat is curiosity? Why does it matter?" in normalized
    assert (
        "\n\nStudies show that children ask more questions. Curiosity helps them learn faster.\n\n"
        in normalized
    )
    assert "However, curiosity can also bring risk." in normalized
    assert "\\ \\" not in normalized
    assert warnings == []


def test_repair_exam_net_docx_markdown_leaves_normal_markdown_unchanged() -> None:
    raw = "# Student\n\nRegular paragraph one.\n\nRegular paragraph two.\n\n- list item\n"

    repaired = repair_exam_net_docx_markdown(raw)

    assert repaired == raw
