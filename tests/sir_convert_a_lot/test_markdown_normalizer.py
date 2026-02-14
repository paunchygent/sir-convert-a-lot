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
