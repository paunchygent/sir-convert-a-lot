"""Strict markdown reflow and syntax-preserving guards.

Purpose:
    Reflow plain prose to deterministic width while preserving fenced blocks,
    lists, headings, tables, references, and math constructs.

Relationships:
    - Called by `infrastructure.markdown_normalizer.normalize_markdown`.
    - Delegates structural cleanup to `strict_structure.normalize_structural_blocks`.
"""

from __future__ import annotations

import re
import textwrap

from scripts.sir_convert_a_lot.infrastructure.markdown_normalization.strict_structure import (
    normalize_structural_blocks,
)

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s")
_LIST_RE = re.compile(r"^\s{0,3}([-*+]\s+|\d+[.)]\s+)")
_BLOCKQUOTE_RE = re.compile(r"^\s{0,3}>")
_HR_RE = re.compile(r"^\s{0,3}((\*\s*){3,}|(-\s*){3,}|(_\s*){3,})$")
_SETEXT_UNDERLINE_RE = re.compile(r"^\s{0,3}(=+|-{2,})\s*$")
_TABLE_RULE_RE = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]*$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
_REFERENCE_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
_FOOTNOTE_DEF_RE = re.compile(r"^\s{0,3}\[\^[^\]]+\]:\s*")
_INDENTED_RE = re.compile(r"^( {2,}|\t)")

_MATH_CONTROL_SENTINEL_RE = re.compile(r"^/[a-z_]+slash$", re.IGNORECASE)
_DOCLING_FORMULA_OPEN_TAG_RE = re.compile(r"<formula>", re.IGNORECASE)
_DOCLING_FORMULA_CLOSE_TAG_RE = re.compile(r"</formula\b>?", re.IGNORECASE)
_DOCLING_LOC_TOKEN_RE = re.compile(r"<loc_\d+>", re.IGNORECASE)
_HEAVY_MATH_PADDING_LINE_RE = re.compile(r"^\s*\\(?:\s+\\){15,}\s*$")
_HEAVY_MATH_PADDING_WITH_CLOSER_RE = re.compile(r"^\s*\\(?:\s+\\){15,}\s*\$\$\s*$")
_HEAVY_MATH_PADDING_SUFFIX_RE = re.compile(r"(?:\s+\\){15,}\s*$")
_HEAVY_MATH_TRAIL_BEFORE_CLOSER_RE = re.compile(r"(?:\s+\\){15,}\s*\\?\s*\$\$\s*$")
_MATH_CLOSER_WITH_LEADING_SLASHES_RE = re.compile(r"^\s*(?:\\\s*)+\$\$\s*$")


def strict_reflow(markdown_content: str) -> str:
    """Return strict-mode markdown normalization with syntax-aware reflow."""
    lines = markdown_content.split("\n")
    output_lines: list[str] = []
    paragraph_lines: list[str] = []
    in_fence = False
    in_display_math = False
    previous_nonempty_line = ""

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        joined = " ".join(part.strip() for part in paragraph_lines if part.strip() != "")
        paragraph_lines.clear()
        if joined == "":
            return
        wrapped = textwrap.fill(
            joined,
            width=100,
            break_long_words=False,
            break_on_hyphens=False,
        )
        output_lines.extend(wrapped.split("\n"))

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if _is_fence(line):
            flush_paragraph()
            output_lines.append(line)
            in_fence = not in_fence
            if stripped != "":
                previous_nonempty_line = line
            index += 1
            continue

        if in_fence:
            output_lines.append(line)
            if stripped != "":
                previous_nonempty_line = line
            index += 1
            continue

        if _MATH_CONTROL_SENTINEL_RE.match(stripped) is not None:
            flush_paragraph()
            index += 1
            continue

        line = _strip_reserved_protocol_tokens(line)
        stripped = line.strip()

        if in_display_math:
            flush_paragraph()
            normalized_math_line = _normalize_math_line(line)
            if _should_drop_math_padding_line(normalized_math_line):
                in_display_math = _next_math_block_state(
                    line=line,
                    stripped_line=stripped,
                    in_display_math=in_display_math,
                )
                index += 1
                continue
            output_lines.append(normalized_math_line)
            in_display_math = _next_math_block_state(
                line=line,
                stripped_line=stripped,
                in_display_math=in_display_math,
            )
            if normalized_math_line.strip() != "":
                previous_nonempty_line = normalized_math_line
            index += 1
            continue

        if _contains_math_expression_marker(line, stripped):
            flush_paragraph()
            normalized_marker_line = _normalize_math_line(line)
            normalized_marker_stripped = normalized_marker_line.strip()
            if _should_drop_math_padding_line(normalized_marker_line):
                index += 1
                continue
            output_lines.append(normalized_marker_line)
            in_display_math = _next_math_block_state(
                line=normalized_marker_line,
                stripped_line=normalized_marker_stripped,
                in_display_math=in_display_math,
            )
            previous_nonempty_line = normalized_marker_line
            index += 1
            continue

        if stripped == "":
            flush_paragraph()
            if output_lines and output_lines[-1] != "":
                output_lines.append("")
            index += 1
            continue

        if _starts_table_block(lines=lines, index=index):
            flush_paragraph()
            output_lines.append(line)
            separator_line = _strip_reserved_protocol_tokens(lines[index + 1])
            output_lines.append(separator_line)
            previous_nonempty_line = separator_line
            index += 2
            while index < len(lines):
                table_line = _strip_reserved_protocol_tokens(lines[index])
                if table_line.strip() == "":
                    break
                if not _is_table_row_line(table_line):
                    break
                output_lines.append(table_line)
                previous_nonempty_line = table_line
                index += 1
            continue

        if _is_protected_line(line, previous_nonempty_line):
            flush_paragraph()
            output_lines.append(line)
            previous_nonempty_line = line
            index += 1
            continue

        paragraph_lines.append(line)
        previous_nonempty_line = line
        index += 1

    flush_paragraph()

    collapsed = normalize_structural_blocks(output_lines)
    final_text = "\n".join(collapsed).strip("\n")
    if final_text == "":
        return ""
    return final_text + "\n"


def _is_fence(line: str) -> bool:
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _is_table_line(line: str) -> bool:
    stripped = line.strip()
    if stripped.startswith("|"):
        return True
    if "|" in stripped and (_TABLE_RULE_RE.match(stripped) is not None):
        return True
    return False


def _next_math_block_state(*, line: str, stripped_line: str, in_display_math: bool) -> bool:
    if stripped_line == r"\[":
        return True
    if stripped_line == r"\]":
        return False
    if line.count("$$") % 2 == 1:
        return not in_display_math
    return in_display_math


def _contains_math_expression_marker(line: str, stripped_line: str) -> bool:
    return "$$" in line or r"\[" in line or r"\]" in line or stripped_line in {r"\[", r"\]"}


def _strip_reserved_protocol_tokens(line: str) -> str:
    end_token_index = line.find("<end_of_utterance>")
    if end_token_index == -1:
        end_token_index = line.find("<end_of_utterance")
    if end_token_index != -1:
        line = line[:end_token_index]
    line = _DOCLING_LOC_TOKEN_RE.sub("", line)
    line = _DOCLING_FORMULA_OPEN_TAG_RE.sub("", line)
    line = _DOCLING_FORMULA_CLOSE_TAG_RE.sub("", line)
    line = line.replace("</code>", "")
    return line


def _normalize_math_line(line: str) -> str:
    if _HEAVY_MATH_TRAIL_BEFORE_CLOSER_RE.search(line) is not None:
        line = _HEAVY_MATH_TRAIL_BEFORE_CLOSER_RE.sub(" $$", line)
    if _MATH_CLOSER_WITH_LEADING_SLASHES_RE.match(line) is not None:
        return "$$"
    if _HEAVY_MATH_PADDING_WITH_CLOSER_RE.match(line) is not None:
        return "$$"
    return _HEAVY_MATH_PADDING_SUFFIX_RE.sub("", line).rstrip()


def _should_drop_math_padding_line(line: str) -> bool:
    return _HEAVY_MATH_PADDING_LINE_RE.match(line) is not None


def _is_table_row_line(line: str) -> bool:
    return "|" in line.strip()


def _starts_table_block(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    header_line = lines[index]
    separator_line = lines[index + 1]
    if header_line.strip() == "":
        return False
    if "|" not in header_line:
        return False
    if _TABLE_SEPARATOR_RE.match(separator_line.strip()) is None:
        return False
    return True


def _is_protected_line(line: str, previous_nonempty_line: str) -> bool:
    stripped = line.strip()
    if _is_table_line(line):
        return True
    if _REFERENCE_DEF_RE.match(line) is not None:
        return True
    if _FOOTNOTE_DEF_RE.match(line) is not None:
        return True
    if _INDENTED_RE.match(line) is not None:
        return True
    if _SETEXT_UNDERLINE_RE.match(stripped) is not None and previous_nonempty_line != "":
        return True
    if _HEADING_RE.match(line) is not None:
        return True
    if _LIST_RE.match(line) is not None:
        return True
    if _BLOCKQUOTE_RE.match(line) is not None:
        return True
    if _HR_RE.match(stripped) is not None:
        return True
    return False
