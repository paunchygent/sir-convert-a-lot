"""Common markdown normalization primitives.

Purpose:
    Provide newline canonicalization and blank-run collapsing that apply to
    both `standard` and `strict` normalization modes.

Relationships:
    - Called by `infrastructure.markdown_normalizer.normalize_markdown`.
    - Feeds preprocessed text into `strict_reflow` for strict mode.
"""

from __future__ import annotations

import re

_BLANKS_RE = re.compile(r"\n{3,}")


def normalize_common(markdown_content: str) -> str:
    """Return canonicalized markdown with stable newlines and blank spacing."""
    text = markdown_content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = _BLANKS_RE.sub("\n\n", text)
    stripped = text.strip("\n")
    if stripped == "":
        return ""
    return stripped + "\n"
