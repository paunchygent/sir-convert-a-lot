"""Deterministic markdown normalization facade for Sir Convert-a-Lot.

Purpose:
    Expose the stable `normalize_markdown` contract used by conversion runtime
    while delegating strict-mode internals to focused modules.

Relationships:
    - Used by `infrastructure.runtime_conversion` after backend conversion.
    - Strict-mode logic lives in `infrastructure.markdown_normalization`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs import NormalizeMode
from scripts.sir_convert_a_lot.infrastructure.markdown_lint_normalizer import (
    normalize_lint_rules,
)
from scripts.sir_convert_a_lot.infrastructure.markdown_normalization import (
    normalize_common,
    strict_reflow,
)


def normalize_markdown(markdown_content: str, mode: NormalizeMode) -> str:
    """Normalize markdown content based on v1 `conversion.normalize` semantics."""
    if mode == NormalizeMode.NONE:
        return markdown_content
    normalized = normalize_common(markdown_content)
    if mode == NormalizeMode.STANDARD:
        return normalized
    if mode == NormalizeMode.STRICT:
        reflowed = strict_reflow(normalized)
        return normalize_lint_rules(reflowed)
    return normalized
