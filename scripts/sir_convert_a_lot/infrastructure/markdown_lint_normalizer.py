"""Markdown lint normalization for Sir Convert-a-Lot conversions.

Purpose:
    Apply deterministic lint-rule fixes to markdown output in strict normalization
    mode, addressing common markdownlint complaints while respecting code fences,
    math blocks, and existing link syntax.

Relationships:
    - Used by `infrastructure.markdown_normalizer` in strict mode.
    - Lint rules follow davidanson/markdownlint specifications.

Lint Rules Implemented:
    - MD034 (no-bare-urls): Wrap bare URLs in angle brackets.
    - MD040 (fenced-code-language): Add default language to bare fences.
    - MD004 (ul-style): Normalize unordered list markers to dash.
    - MD060 (table-column-style): Normalize via mdformat-gfm.

References:
    - https://github.com/davidanson/markdownlint
    - https://github.com/hukkin/mdformat
    - docs/backlog/tasks/task-21-structural-markdown-quality-gate-and-hard-case-normalization.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

import mdformat


class _BlockState(Enum):
    """State machine states for markdown block context."""

    NORMAL = auto()
    CODE_FENCE = auto()
    MATH_BLOCK = auto()


@dataclass
class _ParserState:
    """Mutable parser state for tracking block context."""

    block_state: _BlockState = _BlockState.NORMAL
    fence_char: str = ""
    fence_length: int = 0


@dataclass(frozen=True)
class _FenceOpening:
    """Parsed fenced-code opening line details."""

    indent: str
    marker: str
    suffix: str


_FENCE_OPEN_RE = re.compile(r"^(\s*)(`{3,}|~{3,})([^\r\n]*)$")
_FENCE_CLOSE_RE = re.compile(r"^\s*([`~]{3,})\s*$")

_UL_MARKER_RE = re.compile(r"^(\s*)([*+])(\s+)(.*)$")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")

_BARE_URL_RE = re.compile(
    r"(?<![(<\[`])"  # not preceded by ( < [ or backtick
    r"(https?://[^\s<>)\]`]+)"  # capture URL
    r"(?![>)\]`])"  # not followed by > ) ] or backtick
)
_TRAILING_URL_PUNCTUATION = ".,;:!?"

_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
_AUTOLINK_RE = re.compile(r"<https?://[^>]+>")
_REFERENCE_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*")

DEFAULT_FENCE_LANGUAGE = "text"
_MDFORMAT_EXTENSIONS = {"gfm"}
_MDFORMAT_OPTIONS = {
    "wrap": "keep",
    "number": False,
    "compact_tables": True,
}


def normalize_lint_rules(markdown_content: str) -> str:
    """Apply lint normalization rules to markdown content.

    This function applies the following markdownlint fixes:
    - MD040: Add default language to bare fenced code blocks.
    - MD034: Wrap bare URLs in angle brackets.
    - MD004: Normalize unordered list markers to dash.

    Code fences and math blocks are preserved without internal modification.

    Args:
        markdown_content: Raw markdown content.

    Returns:
        Lint-normalized markdown content.
    """
    if not markdown_content:
        return markdown_content

    lines = markdown_content.split("\n")
    state = _ParserState()
    output_lines: list[str] = []

    for line in lines:
        normalized_line = _process_line(line, state)
        output_lines.append(normalized_line)

    return _normalize_table_blocks("\n".join(output_lines))


def _process_line(line: str, state: _ParserState) -> str:
    """Process a single line with state tracking."""
    if state.block_state == _BlockState.CODE_FENCE:
        if _is_fence_close(line, state):
            state.block_state = _BlockState.NORMAL
            state.fence_char = ""
            state.fence_length = 0
        return line

    if state.block_state == _BlockState.MATH_BLOCK:
        if _is_math_block_close(line):
            state.block_state = _BlockState.NORMAL
        return line

    fence_opening = _parse_fence_opening(line)
    if fence_opening is not None:
        state.block_state = _BlockState.CODE_FENCE
        state.fence_char = fence_opening.marker[0]
        state.fence_length = len(fence_opening.marker)
        return _normalize_fence_opening(line, fence_opening)

    if _is_math_block_open(line):
        state.block_state = _BlockState.MATH_BLOCK
        return line

    line = _normalize_ul_marker(line)
    line = _normalize_bare_urls(line)

    return line


def _parse_fence_opening(line: str) -> _FenceOpening | None:
    """Parse a fenced-code opening line."""
    match = _FENCE_OPEN_RE.match(line)
    if match is None:
        return None
    return _FenceOpening(
        indent=match.group(1),
        marker=match.group(2),
        suffix=match.group(3),
    )


def _is_fence_close(line: str, state: _ParserState) -> bool:
    """Check if line closes current fenced code block."""
    match = _FENCE_CLOSE_RE.match(line)
    if match is None:
        return False
    marker = match.group(1)
    if state.fence_char == "":
        return False
    return marker[0] == state.fence_char and len(marker) >= state.fence_length


def _is_math_block_open(line: str) -> bool:
    """Check if line opens a display math block."""
    stripped = line.strip()
    return stripped == "$$" or stripped == r"\["


def _is_math_block_close(line: str) -> bool:
    """Check if line closes a display math block."""
    stripped = line.strip()
    return stripped == "$$" or stripped == r"\]"


def _normalize_fence_opening(line: str, opening: _FenceOpening) -> str:
    """Add default language specifier to bare fence openings (MD040).

    Only modifies fences that have no language specifier.
    Preserves existing language specifiers.
    """
    if opening.suffix.strip() == "":
        return f"{opening.indent}{opening.marker}{DEFAULT_FENCE_LANGUAGE}"

    return line


def _normalize_ul_marker(line: str) -> str:
    """Normalize unordered list markers to dash (MD004).

    Converts * and + list markers to - while preserving indentation.
    Only matches line-start list markers to avoid affecting inline content.
    """
    match = _UL_MARKER_RE.match(line)
    if match is not None:
        indent = match.group(1)
        spacing = match.group(3)
        content = match.group(4)
        return f"{indent}-{spacing}{content}"
    return line


def _normalize_bare_urls(line: str) -> str:
    """Wrap bare URLs in angle brackets (MD034).

    Excludes:
    - URLs inside inline code spans
    - URLs inside markdown links [text](url)
    - URLs already wrapped in angle brackets <url>
    - URLs in reference definitions [ref]: url
    """
    if "http" not in line:
        return line

    if _REFERENCE_DEF_RE.match(line) is not None:
        return line

    protected_ranges = _get_protected_ranges(line)

    def replace_if_not_protected(match: re.Match[str]) -> str:
        start, end = match.span()
        for prot_start, prot_end in protected_ranges:
            if start >= prot_start and end <= prot_end:
                return match.group(0)
        url = match.group(1)
        trimmed_url, trailing_punctuation = _split_trailing_url_punctuation(url)
        if trimmed_url == "":
            return match.group(0)
        return f"<{trimmed_url}>{trailing_punctuation}"

    return _BARE_URL_RE.sub(replace_if_not_protected, line)


def _split_trailing_url_punctuation(url: str) -> tuple[str, str]:
    """Split trailing sentence punctuation from a URL candidate."""
    trimmed_url = url
    punctuation = ""
    while trimmed_url and trimmed_url[-1] in _TRAILING_URL_PUNCTUATION:
        punctuation = trimmed_url[-1] + punctuation
        trimmed_url = trimmed_url[:-1]
    return trimmed_url, punctuation


def _get_protected_ranges(line: str) -> list[tuple[int, int]]:
    """Get character ranges that should not be modified (code, links, etc.)."""
    ranges: list[tuple[int, int]] = []

    for match in _INLINE_CODE_RE.finditer(line):
        ranges.append(match.span())

    for match in _MARKDOWN_LINK_RE.finditer(line):
        ranges.append(match.span())

    for match in _AUTOLINK_RE.finditer(line):
        ranges.append(match.span())

    return ranges


def _normalize_table_blocks(markdown_content: str) -> str:
    """Normalize markdown tables with mdformat-gfm when available (MD060)."""
    lines = markdown_content.split("\n")
    output_lines: list[str] = []
    state = _ParserState()
    index = 0

    while index < len(lines):
        line = lines[index]

        if state.block_state == _BlockState.CODE_FENCE:
            output_lines.append(line)
            if _is_fence_close(line, state):
                state.block_state = _BlockState.NORMAL
                state.fence_char = ""
                state.fence_length = 0
            index += 1
            continue

        if state.block_state == _BlockState.MATH_BLOCK:
            output_lines.append(line)
            if _is_math_block_close(line):
                state.block_state = _BlockState.NORMAL
            index += 1
            continue

        fence_opening = _parse_fence_opening(line)
        if fence_opening is not None:
            output_lines.append(line)
            state.block_state = _BlockState.CODE_FENCE
            state.fence_char = fence_opening.marker[0]
            state.fence_length = len(fence_opening.marker)
            index += 1
            continue

        if _is_math_block_open(line):
            output_lines.append(line)
            state.block_state = _BlockState.MATH_BLOCK
            index += 1
            continue

        if _starts_table_block(lines, index):
            table_block, next_index = _collect_table_block(lines, index)
            output_lines.extend(_format_table_block(table_block))
            index = next_index
            continue

        output_lines.append(line)
        index += 1

    return "\n".join(output_lines)


def _starts_table_block(lines: list[str], index: int) -> bool:
    """Return True when index starts a markdown table header + separator pair."""
    if index + 1 >= len(lines):
        return False
    header = lines[index].strip()
    separator = lines[index + 1].strip()
    if header == "" or "|" not in header:
        return False
    if _TABLE_SEPARATOR_RE.match(separator) is None:
        return False
    return True


def _collect_table_block(lines: list[str], start: int) -> tuple[list[str], int]:
    """Collect contiguous markdown table lines."""
    block: list[str] = [lines[start], lines[start + 1]]
    index = start + 2
    while index < len(lines):
        line = lines[index]
        if line.strip() == "":
            break
        if "|" not in line:
            break
        block.append(line)
        index += 1
    return block, index


def _format_table_block(table_lines: list[str]) -> list[str]:
    """Format one markdown table block with mdformat-gfm."""
    table_content = "\n".join(table_lines).rstrip("\n") + "\n"
    try:
        formatted = mdformat.text(
            table_content,
            extensions=_MDFORMAT_EXTENSIONS,
            options=_MDFORMAT_OPTIONS,
        )
    except Exception:  # pragma: no cover - defensive guard around third-party formatter.
        return table_lines
    formatted_lines = formatted.rstrip("\n").split("\n")
    if not formatted_lines:
        return table_lines
    return formatted_lines
