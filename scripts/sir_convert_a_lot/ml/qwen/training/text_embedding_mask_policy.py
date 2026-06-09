"""Text-embedding mask policy contracts for Qwen fine-tuning.

Purpose:
    Define the canonical Qwen pilot training text-embedding mask policies, keep launch
    defaults and retained codec-span defaults explicit, and provide the
    small helpers needed to compute the active positional text-embedding span
    during batch collation.

Relationships:
    - Imported by the detached Qwen control plane when constructing settings.
    - Imported by the patched Qwen dataset and runtime fingerprint helpers.
    - Consumed by metadata loading so retained launch artifacts resolve deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

TextEmbeddingMaskPolicy = Literal["legacy_codec_span", "text_span_only"]

LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY: TextEmbeddingMaskPolicy = "legacy_codec_span"
TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY: TextEmbeddingMaskPolicy = "text_span_only"
DEFAULT_TEXT_EMBEDDING_MASK_POLICY: TextEmbeddingMaskPolicy = (
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY
)
LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT: TextEmbeddingMaskPolicy = (
    LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY
)
TEXT_EMBEDDING_MASK_POLICY_CHOICES: tuple[str, ...] = get_args(TextEmbeddingMaskPolicy)
SEMANTIC_TEXT_START_INDEX = 8


@dataclass(frozen=True)
class TextEmbeddingSpan:
    """One contiguous positional span in the collated text channel."""

    start_index: int
    end_index_exclusive: int

    @property
    def length(self) -> int:
        """Return the number of active positions in the span."""
        return self.end_index_exclusive - self.start_index


def resolve_text_embedding_mask_policy(
    value: str | None,
    *,
    default: TextEmbeddingMaskPolicy,
) -> TextEmbeddingMaskPolicy:
    """Return one validated mask policy, falling back to the provided default."""
    if value is None:
        return default
    if value == LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY:
        return LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY
    if value == TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY:
        return TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY
    supported_values = ", ".join(TEXT_EMBEDDING_MASK_POLICY_CHOICES)
    raise ValueError(
        f"Unsupported text-embedding mask policy `{value}`. Expected one of: {supported_values}."
    )


def resolve_active_text_embedding_span(
    *,
    policy: TextEmbeddingMaskPolicy,
    text_ids_len: int,
    codec_ids_len: int,
) -> TextEmbeddingSpan:
    """Return the active positional text-embedding span for one collated row."""
    if text_ids_len <= 0:
        raise ValueError("`text_ids_len` must be positive to build the Qwen batch prefix.")
    if codec_ids_len < 0:
        raise ValueError("`codec_ids_len` must be non-negative.")
    if policy == LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY:
        return TextEmbeddingSpan(
            start_index=0,
            end_index_exclusive=SEMANTIC_TEXT_START_INDEX + text_ids_len + codec_ids_len,
        )
    if policy == TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY:
        return resolve_semantic_text_embedding_span(text_ids_len=text_ids_len)
    raise AssertionError(f"Unhandled text-embedding mask policy: {policy}")


def resolve_semantic_text_embedding_span(*, text_ids_len: int) -> TextEmbeddingSpan:
    """Return the canonical semantic-text span inside one collated row."""
    if text_ids_len <= 3:
        raise ValueError("`text_ids_len` must be greater than 3 to isolate the semantic text span.")
    return TextEmbeddingSpan(
        start_index=SEMANTIC_TEXT_START_INDEX,
        end_index_exclusive=SEMANTIC_TEXT_START_INDEX + text_ids_len - 3,
    )


def active_text_embedding_length(
    *,
    policy: TextEmbeddingMaskPolicy,
    text_ids_len: int,
    codec_ids_len: int,
) -> int:
    """Return the active text-embedding span length for one collated row."""
    return resolve_active_text_embedding_span(
        policy=policy,
        text_ids_len=text_ids_len,
        codec_ids_len=codec_ids_len,
    ).length
