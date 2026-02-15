"""Tests for deterministic markdown normalization modes.

Purpose:
    Verify v1 normalization behavior and markdown safety guarantees for
    `none`, `standard`, and `strict` modes.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.markdown_normalizer`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs import NormalizeMode
from scripts.sir_convert_a_lot.infrastructure.markdown_normalizer import normalize_markdown


def test_none_mode_preserves_input_verbatim() -> None:
    raw = "Line A  \r\n\r\nLine B\r\n"
    assert normalize_markdown(raw, NormalizeMode.NONE) == raw


def test_standard_mode_is_deterministic_and_collapses_blank_runs() -> None:
    raw = "Line A  \r\n\r\n\r\nLine B\t  \n\n\nLine C\n"
    first = normalize_markdown(raw, NormalizeMode.STANDARD)
    second = normalize_markdown(raw, NormalizeMode.STANDARD)

    assert first == second
    assert first == "Line A\n\nLine B\n\nLine C\n"


def test_strict_reflow_wraps_only_prose_to_width_100() -> None:
    prose = " ".join(["prose"] * 45)
    raw = f"{prose}\n"
    normalized = normalize_markdown(raw, NormalizeMode.STRICT)
    lines = [line for line in normalized.splitlines() if line.strip() != ""]

    assert all(len(line) <= 100 for line in lines)
    assert "prose prose prose" in normalized


def test_strict_mode_preserves_fences_tables_headings_lists_and_quotes() -> None:
    raw = (
        "# Heading should stay one line\n"
        "\n"
        "- list item should not reflow even when verbose and intentionally long "
        "for this assertion\n"
        "> quote should remain untouched and should not be wrapped by strict reflow logic\n"
        "\n"
        "| col_a | col_b |\n"
        "| --- | --- |\n"
        "| value_a | value_b |\n"
        "\n"
        "```python\n"
        "print('code fence line')\n"
        "```\n"
        "\n"
        "---\n"
        "\n"
        " ".join(["paragraph"] * 40)
        + "\n"
    )

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    assert "# Heading should stay one line" in normalized
    assert "- list item should not reflow" in normalized
    assert "> quote should remain untouched" in normalized
    assert "| col_a | col_b |" in normalized
    assert "print('code fence line')" in normalized
    assert "\n---\n" in normalized

    paragraph_lines = [
        line
        for line in normalized.splitlines()
        if line.startswith("paragraph ") or line == "paragraph"
    ]
    assert paragraph_lines
    assert all(len(line) <= 100 for line in paragraph_lines)


def test_strict_mode_preserves_list_continuation_indentation() -> None:
    raw = (
        "- First list item heading\n"
        "  continuation line should remain nested under the same list item\n"
        "  second continuation line should also remain nested and not be merged into plain prose\n"
    )

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    assert "\n  continuation line should remain nested" in normalized
    assert (
        "\n  second continuation line should also remain nested and not be merged into plain prose"
        in normalized
    )


def test_strict_mode_preserves_reference_definitions() -> None:
    raw = (
        "[very_long_reference_identifier_that_should_not_wrap]: "
        "https://example.com/some/really/long/path/that/should/stay/on/one/line\n"
    )

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    assert (
        "[very_long_reference_identifier_that_should_not_wrap]: "
        "https://example.com/some/really/long/path/that/should/stay/on/one/line\n"
    ) == normalized


def test_strict_mode_preserves_pipe_table_without_leading_pipe() -> None:
    header = (
        "This Is A Very Long Header Column Name That Exceeds One Hundred Characters Significantly "
        "For Demonstration Purposes | Another Very Long Header Column Name Also Exceeding One "
        "Hundred Characters For This Check"
    )
    raw = f"{header}\n--- | ---\nvalue one | value two\n"

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    lines = normalized.splitlines()
    assert lines[0] == header
    assert lines[1] == "--- | ---"
    assert lines[2] == "value one | value two"


def test_strict_mode_removes_long_standalone_page_number_blocks() -> None:
    number_block = "\n".join(f"{index:03d}\n" for index in range(39, 69))
    raw = f"Intro paragraph.\n\n{number_block}\n\nNext paragraph.\n"

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    assert "039" not in normalized
    assert "068" not in normalized
    assert "Intro paragraph." in normalized
    assert "Next paragraph." in normalized


def test_strict_mode_removes_long_standalone_four_digit_number_blocks() -> None:
    number_block = "\n".join(f"{index}\n" for index in range(1001, 1036))
    raw = f"Before paragraph.\n\n{number_block}\n\nAfter paragraph.\n"

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    assert "1001" not in normalized
    assert "1035" not in normalized
    assert "Before paragraph." in normalized
    assert "After paragraph." in normalized


def test_strict_mode_preserves_short_numeric_lines() -> None:
    raw = "1\n\n2\n\n3\n\nkeep this paragraph intact\n"

    normalized = normalize_markdown(raw, NormalizeMode.STRICT)

    assert "1" in normalized
    assert "2" in normalized
    assert "3" in normalized
    assert "keep this paragraph intact" in normalized
