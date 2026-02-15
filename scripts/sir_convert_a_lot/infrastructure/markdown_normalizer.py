"""Deterministic markdown normalization for Sir Convert-a-Lot conversions.

Purpose:
    Provide stable markdown normalization modes (`none`, `standard`, `strict`)
    aligned with the v1 conversion contract.

Relationships:
    - Used by `infrastructure.runtime_engine` after backend conversion.
    - Normalization semantics are documented in `docs/converters/pdf_to_md_service_api_v1.md`.
"""

from __future__ import annotations

import re
import textwrap

from scripts.sir_convert_a_lot.domain.specs import NormalizeMode

_BLANKS_RE = re.compile(r"\n{3,}")
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
_STANDALONE_PAGE_NUMBER_RE = re.compile(r"^\s*\d{1,6}\s*$")
_MATH_CONTROL_SENTINEL_RE = re.compile(r"^/[a-z_]+slash$", re.IGNORECASE)
_HEAVY_MATH_PADDING_LINE_RE = re.compile(r"^\s*\\(?:\s+\\){15,}\s*$")
_HEAVY_MATH_PADDING_WITH_CLOSER_RE = re.compile(r"^\s*\\(?:\s+\\){15,}\s*\$\$\s*$")
_HEAVY_MATH_PADDING_SUFFIX_RE = re.compile(r"(?:\s+\\){15,}\s*$")
_HEAVY_MATH_TRAIL_BEFORE_CLOSER_RE = re.compile(r"(?:\s+\\){15,}\s*\\?\s*\$\$\s*$")
_MATH_CLOSER_WITH_LEADING_SLASHES_RE = re.compile(r"^\s*(?:\\\s*)+\$\$\s*$")
_PAGINATION_NUMERIC_LINES_THRESHOLD = 20


def normalize_markdown(markdown_content: str, mode: NormalizeMode) -> str:
    """Normalize markdown content based on v1 `conversion.normalize` semantics."""
    if mode == NormalizeMode.NONE:
        return markdown_content
    normalized = _normalize_common(markdown_content)
    if mode == NormalizeMode.STANDARD:
        return normalized
    if mode == NormalizeMode.STRICT:
        return _strict_reflow(normalized)
    return normalized


def _normalize_common(markdown_content: str) -> str:
    text = markdown_content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANKS_RE.sub("\n\n", text)
    stripped = text.strip("\n")
    if stripped == "":
        return ""
    return stripped + "\n"


def _strict_reflow(markdown_content: str) -> str:
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

        if _MATH_CONTROL_SENTINEL_RE.match(stripped) is not None and _is_math_adjacent(
            previous_nonempty_line=previous_nonempty_line,
            next_nonempty_line=_next_nonempty_line(lines, index + 1),
        ):
            flush_paragraph()
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
            output_lines.append(lines[index + 1])
            previous_nonempty_line = lines[index + 1]
            index += 2
            while index < len(lines):
                table_line = lines[index]
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

    output_lines = _strip_pagination_noise(output_lines)

    collapsed: list[str] = []
    for line in output_lines:
        if line == "" and collapsed and collapsed[-1] == "":
            continue
        collapsed.append(line)

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


def _is_math_adjacent(*, previous_nonempty_line: str, next_nonempty_line: str | None) -> bool:
    if _contains_math_expression_marker(previous_nonempty_line, previous_nonempty_line.strip()):
        return True
    if next_nonempty_line is None:
        return False
    return _contains_math_expression_marker(next_nonempty_line, next_nonempty_line.strip())


def _next_nonempty_line(lines: list[str], start_index: int) -> str | None:
    index = start_index
    while index < len(lines):
        candidate = lines[index]
        if candidate.strip() != "":
            return candidate
        index += 1
    return None


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


def _strip_pagination_noise(lines: list[str]) -> list[str]:
    """Drop long standalone page-number blocks from strict-normalized output."""
    if not lines:
        return lines
    cleaned: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not _STANDALONE_PAGE_NUMBER_RE.match(line):
            cleaned.append(line)
            index += 1
            continue

        block_start = index
        numeric_line_count = 0
        while index < len(lines):
            block_line = lines[index]
            if _STANDALONE_PAGE_NUMBER_RE.match(block_line):
                numeric_line_count += 1
                index += 1
                continue
            if block_line.strip() == "":
                index += 1
                continue
            break

        if numeric_line_count >= _PAGINATION_NUMERIC_LINES_THRESHOLD:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue

        cleaned.extend(lines[block_start:index])
    return cleaned
