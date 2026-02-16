"""Docling formula enrichment quality heuristics.

Purpose:
    Provide deterministic fallback triggers for formula-enrichment presets based
    on unresolved placeholders and malformed markdown signals.

Relationships:
    - Used by `infrastructure.docling_backend` formula-guarded conversion flow.
    - Encapsulates regex/threshold heuristics so backend orchestration remains
      focused on control-flow decisions.
"""

from __future__ import annotations

import re

FORMULA_PLACEHOLDER_MARKER = "<!-- formula-not-decoded -->"
FORMULA_PRIMARY_PRESET = "codeformulav2"
FORMULA_FALLBACK_PRESET = "granite_docling"
FORMULA_RUNTIME_UNAVAILABLE_HINTS: tuple[str, ...] = (
    "codeformula",
    "formula",
    "vlm",
    "transformers",
    "huggingface",
    "snapshot",
    "tokenizer",
    "checkpoint",
    "weights",
)
_LEAKED_CONTROL_SENTINEL_RE = re.compile(r"^\s*/[a-z_]+slash\s*$", re.IGNORECASE)
_LEAKED_FORMULA_TAG_RE = re.compile(r"</?formula\b", re.IGNORECASE)
_LEAKED_LOC_TOKEN_RE = re.compile(r"<loc_\d+>", re.IGNORECASE)
_RUNAWAY_INLINE_MATH_BACKSLASH_RE = re.compile(r"(?:\s+\\){120,}\s*\$\$\s*$")
_INLINE_MATH_BACKSLASH_THRESHOLD = 240
_INLINE_MATH_LINE_LENGTH_THRESHOLD = 1200


def formula_placeholder_count(markdown_content: str) -> int:
    """Return count of unresolved Docling formula placeholders."""
    return markdown_content.count(FORMULA_PLACEHOLDER_MARKER)


def markdown_quality_penalty(markdown_content: str) -> int:
    """Compute structural markdown penalty for formula candidate selection."""
    lines = markdown_content.splitlines()
    leaked_control_sentinels = sum(
        1 for line in lines if _LEAKED_CONTROL_SENTINEL_RE.match(line) is not None
    )
    leaked_formula_tags = sum(
        1 for line in lines if _LEAKED_FORMULA_TAG_RE.search(line) is not None
    )
    leaked_loc_tokens = sum(1 for line in lines if _LEAKED_LOC_TOKEN_RE.search(line) is not None)
    malformed_inline_math_lines = sum(1 for line in lines if _is_malformed_inline_math_line(line))
    unbalanced_display_math_blocks = sum(line.count("$$") for line in lines) % 2
    return (
        leaked_control_sentinels * 20
        + leaked_formula_tags * 25
        + leaked_loc_tokens * 25
        + malformed_inline_math_lines * 20
        + unbalanced_display_math_blocks * 5
    )


def is_formula_runtime_unavailable(error_message: str) -> bool:
    """Return true when backend error hints formula runtime unavailability."""
    normalized_message = error_message.lower()
    return any(hint in normalized_message for hint in FORMULA_RUNTIME_UNAVAILABLE_HINTS)


def _is_malformed_inline_math_line(line: str) -> bool:
    stripped = line.strip()
    if "$$" not in stripped:
        return False
    if line.count("\\") < _INLINE_MATH_BACKSLASH_THRESHOLD:
        return False
    if len(line) < _INLINE_MATH_LINE_LENGTH_THRESHOLD:
        return False
    if _RUNAWAY_INLINE_MATH_BACKSLASH_RE.search(line) is not None:
        return True
    return line.count("$$") >= 1
