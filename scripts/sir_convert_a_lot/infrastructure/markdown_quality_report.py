"""Markdown quality reporting utilities for Sir Convert-a-Lot.

Purpose:
    Provide deterministic, lightweight quality signals derived from markdown
    output so callers can surface warnings and prefer higher-quality backend
    candidates without introducing brittle ad hoc replacements.

Relationships:
    - Used by `infrastructure.runtime_conversion` to emit result warnings.
    - Used by `infrastructure.docling_backend` quality scoring to select
      between formula-enrichment candidates.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_CONTROL_SENTINEL_LINE_RE = re.compile(r"^/[a-z_]+slash$", re.IGNORECASE)
_FORMULA_TAG_FRAGMENT_RE = re.compile(r"</?formula\b", re.IGNORECASE)
_LOC_TOKEN_RE = re.compile(r"<loc_\d+>", re.IGNORECASE)
_END_OF_UTTERANCE_RE = re.compile(r"<end_of_utterance", re.IGNORECASE)


@dataclass(frozen=True)
class MarkdownQualityReport:
    """Deterministic markdown quality counters."""

    control_sentinel_lines: int
    formula_tag_fragments: int
    loc_tokens: int
    end_of_utterance_fragments: int
    lines_gt_1000: int
    max_line_length: int

    @property
    def reserved_token_count(self) -> int:
        """Return a combined count of reserved protocol/control token occurrences."""
        return (
            self.control_sentinel_lines
            + self.formula_tag_fragments
            + self.loc_tokens
            + self.end_of_utterance_fragments
        )


def build_markdown_quality_report(markdown_content: str) -> MarkdownQualityReport:
    """Return a deterministic quality report for markdown content."""
    if markdown_content == "":
        return MarkdownQualityReport(
            control_sentinel_lines=0,
            formula_tag_fragments=0,
            loc_tokens=0,
            end_of_utterance_fragments=0,
            lines_gt_1000=0,
            max_line_length=0,
        )
    lines = markdown_content.splitlines()
    control_sentinel_lines = sum(
        1 for line in lines if _CONTROL_SENTINEL_LINE_RE.match(line.strip()) is not None
    )
    formula_tag_fragments = sum(
        1 for line in lines if _FORMULA_TAG_FRAGMENT_RE.search(line) is not None
    )
    loc_tokens = sum(len(_LOC_TOKEN_RE.findall(line)) for line in lines)
    end_of_utterance_fragments = sum(
        1 for line in lines if _END_OF_UTTERANCE_RE.search(line) is not None
    )
    lengths = [len(line) for line in lines]
    lines_gt_1000 = sum(1 for length in lengths if length > 1000)
    max_line_length = max(lengths) if lengths else 0
    return MarkdownQualityReport(
        control_sentinel_lines=control_sentinel_lines,
        formula_tag_fragments=formula_tag_fragments,
        loc_tokens=loc_tokens,
        end_of_utterance_fragments=end_of_utterance_fragments,
        lines_gt_1000=lines_gt_1000,
        max_line_length=max_line_length,
    )


def format_reserved_token_warning(*, label: str, report: MarkdownQualityReport) -> str:
    """Return a compact warning string for reserved token presence."""
    return (
        f"markdown_quality_{label}_reserved_tokens:"
        f"control_sentinel_lines={report.control_sentinel_lines},"
        f"formula_tag_fragments={report.formula_tag_fragments},"
        f"loc_tokens={report.loc_tokens},"
        f"end_of_utterance_fragments={report.end_of_utterance_fragments}"
    )


def format_extreme_line_warning(*, label: str, report: MarkdownQualityReport) -> str:
    """Return a compact warning string for extreme line lengths."""
    return (
        f"markdown_quality_{label}_extreme_lines:"
        f"lines_gt_1000={report.lines_gt_1000},"
        f"max_len={report.max_line_length}"
    )
