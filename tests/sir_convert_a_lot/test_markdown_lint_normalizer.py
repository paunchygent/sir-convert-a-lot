"""Tests for markdown_lint_normalizer module.

Covers:
- MD034 (no-bare-urls): Bare URL wrapping
- MD040 (fenced-code-language): Fence language defaults
- MD004 (ul-style): List marker normalization
- MD060 (table-column-style): GFM table normalization
- State machine for code fence/math block exclusion
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.infrastructure.markdown_lint_normalizer import (
    DEFAULT_FENCE_LANGUAGE,
    normalize_lint_rules,
)


class TestMD040FencedCodeLanguage:
    """Tests for MD040: fenced-code-language rule."""

    def test_bare_backtick_fence_gets_default_language(self) -> None:
        input_md = "```\ncode here\n```"
        result = normalize_lint_rules(input_md)
        assert result == f"```{DEFAULT_FENCE_LANGUAGE}\ncode here\n```"

    def test_bare_tilde_fence_gets_default_language(self) -> None:
        input_md = "~~~\ncode here\n~~~"
        result = normalize_lint_rules(input_md)
        assert result == f"~~~{DEFAULT_FENCE_LANGUAGE}\ncode here\n~~~"

    def test_fence_with_language_preserved(self) -> None:
        input_md = "```python\nprint('hello')\n```"
        result = normalize_lint_rules(input_md)
        assert result == "```python\nprint('hello')\n```"

    def test_indented_bare_fence_gets_default_language(self) -> None:
        input_md = "  ```\ncode\n  ```"
        result = normalize_lint_rules(input_md)
        assert result == f"  ```{DEFAULT_FENCE_LANGUAGE}\ncode\n  ```"

    def test_fence_content_not_modified(self) -> None:
        input_md = "```python\nhttps://example.com\n* list item\n```"
        result = normalize_lint_rules(input_md)
        assert result == "```python\nhttps://example.com\n* list item\n```"


class TestMD034NoBareUrls:
    """Tests for MD034: no-bare-urls rule."""

    def test_bare_https_url_wrapped(self) -> None:
        input_md = "Visit https://example.com for more."
        result = normalize_lint_rules(input_md)
        assert result == "Visit <https://example.com> for more."

    def test_bare_http_url_wrapped(self) -> None:
        input_md = "Visit http://example.com for more."
        result = normalize_lint_rules(input_md)
        assert result == "Visit <http://example.com> for more."

    def test_already_wrapped_url_preserved(self) -> None:
        input_md = "Visit <https://example.com> for more."
        result = normalize_lint_rules(input_md)
        assert result == "Visit <https://example.com> for more."

    def test_markdown_link_url_preserved(self) -> None:
        input_md = "See [example](https://example.com) for more."
        result = normalize_lint_rules(input_md)
        assert result == "See [example](https://example.com) for more."

    def test_inline_code_url_preserved(self) -> None:
        input_md = "Use `https://example.com` as the URL."
        result = normalize_lint_rules(input_md)
        assert result == "Use `https://example.com` as the URL."

    def test_url_with_path_wrapped(self) -> None:
        input_md = "Check https://github.com/user/repo/issues/123 for details."
        result = normalize_lint_rules(input_md)
        assert result == "Check <https://github.com/user/repo/issues/123> for details."

    def test_multiple_bare_urls_wrapped(self) -> None:
        input_md = "Visit https://a.com and https://b.com today."
        result = normalize_lint_rules(input_md)
        assert result == "Visit <https://a.com> and <https://b.com> today."

    def test_url_in_code_fence_not_wrapped(self) -> None:
        input_md = "```python\nurl = 'https://example.com'\n```"
        result = normalize_lint_rules(input_md)
        assert "https://example.com" in result
        assert "<https://example.com>" not in result

    def test_trailing_url_punctuation_stays_outside_autolink(self) -> None:
        input_md = "Visit https://example.com, then continue."
        result = normalize_lint_rules(input_md)
        assert result == "Visit <https://example.com>, then continue."

    def test_space_after_protocol_is_repaired_then_wrapped(self) -> None:
        input_md = "URL https:// openreview.net/forum?id=Q9SKS5k8io ."
        result = normalize_lint_rules(input_md)
        assert result == "URL <https://openreview.net/forum?id=Q9SKS5k8io> ."

    def test_spaced_domain_dots_are_repaired_then_wrapped(self) -> None:
        input_md = "See https://vicuna. lmsys. org for details."
        result = normalize_lint_rules(input_md)
        assert result == "See <https://vicuna.lmsys.org> for details."


class TestMD004UlStyle:
    """Tests for MD004: ul-style rule."""

    def test_asterisk_marker_normalized_to_dash(self) -> None:
        input_md = "* item one\n* item two"
        result = normalize_lint_rules(input_md)
        assert result == "- item one\n- item two"

    def test_plus_marker_normalized_to_dash(self) -> None:
        input_md = "+ item one\n+ item two"
        result = normalize_lint_rules(input_md)
        assert result == "- item one\n- item two"

    def test_dash_marker_preserved(self) -> None:
        input_md = "- item one\n- item two"
        result = normalize_lint_rules(input_md)
        assert result == "- item one\n- item two"

    def test_indented_list_marker_normalized(self) -> None:
        input_md = "  * nested item\n    * deeper"
        result = normalize_lint_rules(input_md)
        assert result == "  - nested item\n    - deeper"

    def test_asterisk_in_text_not_affected(self) -> None:
        input_md = "This is *emphasized* text."
        result = normalize_lint_rules(input_md)
        assert result == "This is *emphasized* text."

    def test_list_marker_in_code_fence_preserved(self) -> None:
        input_md = "```\n* code comment\n```"
        result = normalize_lint_rules(input_md)
        assert "* code comment" in result


class TestMD060TableColumnStyle:
    """Tests for MD060: table-column-style rule."""

    def test_table_columns_normalized_with_compact_gfm_style(self) -> None:
        input_md = "| left|right |\n|:---|---:|\n|1|2|"
        result = normalize_lint_rules(input_md)
        assert result == "| left | right |\n| :- | -: |\n| 1 | 2 |"

    def test_table_inside_fence_not_modified(self) -> None:
        input_md = "```markdown\n|left|right|\n|---|---|\n|1|2|\n```"
        result = normalize_lint_rules(input_md)
        assert result == "```markdown\n|left|right|\n|---|---|\n|1|2|\n```"


class TestStateMachineCodeFence:
    """Tests for code fence state machine."""

    def test_nested_fence_markers_handled(self) -> None:
        input_md = "```\nSome ```nested``` content\n```"
        result = normalize_lint_rules(input_md)
        assert f"```{DEFAULT_FENCE_LANGUAGE}" in result

    def test_mismatched_fence_markers(self) -> None:
        input_md = "```python\ncode\n~~~"
        result = normalize_lint_rules(input_md)
        assert "```python" in result

    def test_content_after_fence_close_normalized(self) -> None:
        input_md = "```\ncode\n```\n* list after"
        result = normalize_lint_rules(input_md)
        assert "- list after" in result

    def test_long_backtick_fence_closes_and_normalizes_following_content(self) -> None:
        input_md = "````\ncode\n````\n* list after"
        result = normalize_lint_rules(input_md)
        assert result.startswith(f"````{DEFAULT_FENCE_LANGUAGE}\ncode\n````\n")
        assert result.endswith("- list after")


class TestStateMachineMathBlock:
    """Tests for math block state machine."""

    def test_content_in_math_block_preserved(self) -> None:
        input_md = "$$\nhttps://latex.com\n* not a list\n$$"
        result = normalize_lint_rules(input_md)
        assert "https://latex.com" in result
        assert "<https://latex.com>" not in result
        assert "* not a list" in result

    def test_backslash_math_block_preserved(self) -> None:
        input_md = "\\[\nhttps://math.com\n\\]"
        result = normalize_lint_rules(input_md)
        assert "https://math.com" in result
        assert "<https://math.com>" not in result

    def test_content_after_math_block_normalized(self) -> None:
        input_md = "$$\nmath\n$$\n* list after"
        result = normalize_lint_rules(input_md)
        assert "- list after" in result


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_string(self) -> None:
        assert normalize_lint_rules("") == ""

    def test_whitespace_only(self) -> None:
        assert normalize_lint_rules("   \n\n  ") == "   \n\n  "

    def test_no_modifications_needed(self) -> None:
        input_md = "# Heading\n\nParagraph text.\n\n- list item"
        result = normalize_lint_rules(input_md)
        assert result == input_md

    def test_complex_document(self) -> None:
        input_md = """# Title

Check https://example.com for info.

```
* code
```

* real list
+ another

$$
math block
$$

End of doc."""
        result = normalize_lint_rules(input_md)
        assert "<https://example.com>" in result
        assert "* code" in result  # preserved in fence
        assert "- real list" in result  # normalized
        assert "- another" in result  # normalized
