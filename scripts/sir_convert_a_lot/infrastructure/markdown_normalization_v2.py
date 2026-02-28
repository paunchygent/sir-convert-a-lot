"""Markdown normalization helpers for service API v2 routes.

Purpose:
    Provide deterministic markdown normalization and warning generation for v2
    routes that emit Markdown artifacts from non-Markdown source formats.

Relationships:
    - Used by `infrastructure.v2_conversion_executor` for `docx -> md` and
      future markdown-ingress route branches.
    - Reuses canonical normalization and quality-report modules.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs import NormalizeMode
from scripts.sir_convert_a_lot.infrastructure.markdown_normalizer import normalize_markdown
from scripts.sir_convert_a_lot.infrastructure.markdown_quality_report import (
    build_markdown_quality_report,
    format_extreme_line_warning,
    format_reserved_token_warning,
)


def normalize_markdown_for_v2_md_output(
    *,
    markdown_content: str,
    mode: NormalizeMode = NormalizeMode.STRICT,
) -> tuple[str, list[str]]:
    """Normalize markdown and return deterministic warning messages."""

    raw_quality = build_markdown_quality_report(markdown_content)
    normalized = normalize_markdown(markdown_content, mode)
    normalized_quality = build_markdown_quality_report(normalized)

    warnings: list[str] = []
    if mode == NormalizeMode.STRICT:
        if raw_quality.reserved_token_count > 0 and normalized_quality.reserved_token_count == 0:
            warnings.append(format_reserved_token_warning(label="sanitized", report=raw_quality))
        elif normalized_quality.reserved_token_count > 0:
            warnings.append(
                format_reserved_token_warning(label="normalized", report=normalized_quality)
            )
        elif raw_quality.reserved_token_count > 0:
            warnings.append(format_reserved_token_warning(label="raw", report=raw_quality))
    elif raw_quality.reserved_token_count > 0:
        warnings.append(format_reserved_token_warning(label="raw", report=raw_quality))

    if normalized_quality.lines_gt_1000 > 0:
        warnings.append(format_extreme_line_warning(label="normalized", report=normalized_quality))

    return normalized, warnings
