"""Text-embedding assembly-mode contracts for Qwen training.

Purpose:
    Define the canonical runtime choices for how collated text ids enter the
    trainable text-embedding lookup path so host-side launch metadata,
    detached-runtime snapshots, and patched train/eval surfaces can all agree
    on the exact assembly contract.

Relationships:
    - Imported by host control-plane settings and detached-runtime snapshots.
    - Imported by patched train/eval runtime helpers to select the active
      text-embedding assembly path.
"""

from __future__ import annotations

from typing import Literal, cast, get_args

TextEmbeddingAssemblyMode = Literal[
    "semantic_only",
    "full_channel_masked",
]

SEMANTIC_ONLY_TEXT_EMBEDDING_ASSEMBLY_MODE: TextEmbeddingAssemblyMode = "semantic_only"
FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE: TextEmbeddingAssemblyMode = "full_channel_masked"

DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE: TextEmbeddingAssemblyMode = cast(
    TextEmbeddingAssemblyMode,
    SEMANTIC_ONLY_TEXT_EMBEDDING_ASSEMBLY_MODE,
)
TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES = tuple(get_args(TextEmbeddingAssemblyMode))


def resolve_text_embedding_assembly_mode(
    value: str | None,
    *,
    default: TextEmbeddingAssemblyMode = DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
) -> TextEmbeddingAssemblyMode:
    """Return one validated text-embedding assembly mode."""
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized == "":
        return default
    if normalized not in TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES:
        choices = ", ".join(TEXT_EMBEDDING_ASSEMBLY_MODE_CHOICES)
        raise ValueError(
            f"Unsupported text-embedding assembly mode: `{value}`. Expected one of: {choices}."
        )
    return cast(TextEmbeddingAssemblyMode, normalized)
