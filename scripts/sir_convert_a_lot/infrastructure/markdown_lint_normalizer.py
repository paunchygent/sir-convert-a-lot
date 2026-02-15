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


class _BlockState(Enum):
    """State machine states for markdown block context."""

    NORMAL = auto()
    CODE_FENCE = auto()
    MATH_BLOCK = auto()


@dataclass
class _ParserState:
    """Mutable parser state for tracking block context."""

    block_state: _BlockState = _BlockState.NORMAL
    fence_marker: str = ""


_FENCE_OPEN_RE = re.compile(r"^(\s*)(```|~~~)(\s*)$")
_FENCE_OPEN_WITH_LANG_RE = re.compile(r"^(\s*)(```|~~~)(\S+.*)?$")
_FENCE_CLOSE_RE = re.compile(r"^(\s*)(```|~~~)\s*$")

_MATH_BLOCK_OPEN_RE = re.compile(r"^\s*\$\$\s*$")
_MATH_BLOCK_CLOSE_RE = re.compile(r"^\s*\$\$\s*$")
_MATH_BACKSLASH_OPEN_RE = re.compile(r"^\s*\\\[\s*$")
_MATH_BACKSLASH_CLOSE_RE = re.compile(r"^\s*\\\]\s*$")

_UL_MARKER_RE = re.compile(r"^(\s*)([*+])(\s+)(.*)$")

_BARE_URL_RE = re.compile(
    r"(?<![(<\[`])"  # not preceded by ( < [ or backtick
    r"(https?://[^\s>)\]`]+)"  # capture URL
    r"(?![>)\]`])"  # not followed by > ) ] or backtick
)

_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]*\]\([^)]*\)")
_AUTOLINK_RE = re.compile(r"<https?://[^>]+>")
_REFERENCE_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*")

DEFAULT_FENCE_LANGUAGE = "text"


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

    return "\n".join(output_lines)


def _process_line(line: str, state: _ParserState) -> str:
    """Process a single line with state tracking."""
    if state.block_state == _BlockState.CODE_FENCE:
        if _is_fence_close(line, state.fence_marker):
            state.block_state = _BlockState.NORMAL
            state.fence_marker = ""
        return line

    if state.block_state == _BlockState.MATH_BLOCK:
        if _is_math_block_close(line):
            state.block_state = _BlockState.NORMAL
        return line

    if _is_fence_open(line):
        fence_marker = _get_fence_marker(line)
        state.block_state = _BlockState.CODE_FENCE
        state.fence_marker = fence_marker
        return _normalize_fence_opening(line)

    if _is_math_block_open(line):
        state.block_state = _BlockState.MATH_BLOCK
        return line

    line = _normalize_ul_marker(line)
    line = _normalize_bare_urls(line)

    return line


def _is_fence_open(line: str) -> bool:
    """Check if line opens a fenced code block."""
    stripped = line.lstrip()
    return stripped.startswith("```") or stripped.startswith("~~~")


def _is_fence_close(line: str, fence_marker: str) -> bool:
    """Check if line closes a fenced code block with matching marker."""
    stripped = line.strip()
    return stripped == fence_marker


def _get_fence_marker(line: str) -> str:
    """Extract the fence marker (``` or ~~~) from a fence line."""
    stripped = line.lstrip()
    if stripped.startswith("```"):
        return "```"
    if stripped.startswith("~~~"):
        return "~~~"
    return "```"


def _is_math_block_open(line: str) -> bool:
    """Check if line opens a display math block."""
    stripped = line.strip()
    return stripped == "$$" or stripped == r"\["


def _is_math_block_close(line: str) -> bool:
    """Check if line closes a display math block."""
    stripped = line.strip()
    return stripped == "$$" or stripped == r"\]"


def _normalize_fence_opening(line: str) -> str:
    """Add default language specifier to bare fence openings (MD040).

    Only modifies fences that have no language specifier.
    Preserves existing language specifiers.
    """
    match = _FENCE_OPEN_RE.match(line)
    if match is not None:
        indent = match.group(1)
        fence = match.group(2)
        return f"{indent}{fence}{DEFAULT_FENCE_LANGUAGE}"

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
        return f"<{match.group(1)}>"

    return _BARE_URL_RE.sub(replace_if_not_protected, line)


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
