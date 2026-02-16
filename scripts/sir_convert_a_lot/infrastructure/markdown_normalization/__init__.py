"""Markdown normalization internals for Sir Convert-a-Lot.

Purpose:
    Group focused strict-normalization helpers so the public normalization
    contract remains small, readable, and maintainable.

Relationships:
    - Used by `infrastructure.markdown_normalizer` as the canonical facade.
    - Split into `common`, `strict_reflow`, and `strict_structure` modules.
"""

from scripts.sir_convert_a_lot.infrastructure.markdown_normalization.common import (
    normalize_common,
)
from scripts.sir_convert_a_lot.infrastructure.markdown_normalization.strict_reflow import (
    strict_reflow,
)

__all__ = ["normalize_common", "strict_reflow"]
