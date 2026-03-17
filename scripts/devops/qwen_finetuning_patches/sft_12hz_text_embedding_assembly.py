"""Shared text-embedding assembly helpers for patched Qwen fine-tuning.

Purpose:
    Build the trainable text contribution for one collated batch while keeping
    the active assembly contract explicit: either the Story 30 semantic-only
    lookup path or the original masked full-channel lookup path used by the
    exact T220 control lane.

Relationships:
    - Imported by `sft_12hz_forward_surfaces.py`.
    - Reuses `sft_12hz_semantic_text_embeddings.py` for the semantic-only path.
    - Consumes the domain assembly-mode contract from
      `ml.qwen.training.text_embedding_assembly_mode`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_semantic_text_embeddings import (
    build_semantic_text_embedding_assembly,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
    FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE,
    TextEmbeddingAssemblyMode,
)


@dataclass(frozen=True)
class TextEmbeddingAssembly:
    """Lookup embeddings plus the assembled full-sequence text contribution."""

    lookup_embeddings: torch.Tensor
    full_sequence_embedding: torch.Tensor


def build_text_embedding_assembly(
    *,
    text_embedding: Callable[[torch.Tensor], torch.Tensor],
    input_text_ids: torch.Tensor,
    text_embedding_mask: torch.Tensor,
    semantic_text_ids: torch.Tensor,
    semantic_text_positions: torch.Tensor,
    semantic_text_mask: torch.Tensor,
    sequence_length: int,
    assembly_mode: TextEmbeddingAssemblyMode = DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
) -> TextEmbeddingAssembly:
    """Return the active text-embedding lookup and full-sequence assembly."""
    if assembly_mode == FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE:
        return _build_masked_full_channel_text_embedding_assembly(
            text_embedding=text_embedding,
            input_text_ids=input_text_ids,
            text_embedding_mask=text_embedding_mask,
            sequence_length=sequence_length,
        )
    semantic_assembly = build_semantic_text_embedding_assembly(
        text_embedding=text_embedding,
        semantic_text_ids=semantic_text_ids,
        semantic_text_positions=semantic_text_positions,
        semantic_text_mask=semantic_text_mask,
        sequence_length=sequence_length,
    )
    return TextEmbeddingAssembly(
        lookup_embeddings=semantic_assembly.semantic_embeddings,
        full_sequence_embedding=semantic_assembly.full_sequence_embedding,
    )


def _build_masked_full_channel_text_embedding_assembly(
    *,
    text_embedding: Callable[[torch.Tensor], torch.Tensor],
    input_text_ids: torch.Tensor,
    text_embedding_mask: torch.Tensor,
    sequence_length: int,
) -> TextEmbeddingAssembly:
    """Return the original masked full-channel text-embedding assembly."""
    _validate_full_channel_text_inputs(
        input_text_ids=input_text_ids,
        text_embedding_mask=text_embedding_mask,
        sequence_length=sequence_length,
    )
    lookup_embeddings = text_embedding(input_text_ids)
    if lookup_embeddings.ndim != 3:
        raise ValueError("Text embedding surface must return `[batch, sequence, hidden]`.")
    embedding_mask = text_embedding_mask.to(device=lookup_embeddings.device)
    if embedding_mask.ndim == 2:
        embedding_mask = embedding_mask.unsqueeze(-1)
    if embedding_mask.shape[:2] != lookup_embeddings.shape[:2]:
        raise ValueError(
            "`text_embedding_mask` must match the first two dimensions of the text embedding."
        )
    masked_full_sequence_embedding = lookup_embeddings * embedding_mask.to(
        dtype=lookup_embeddings.dtype,
    )
    return TextEmbeddingAssembly(
        lookup_embeddings=lookup_embeddings,
        full_sequence_embedding=masked_full_sequence_embedding,
    )


def _validate_full_channel_text_inputs(
    *,
    input_text_ids: torch.Tensor,
    text_embedding_mask: torch.Tensor,
    sequence_length: int,
) -> None:
    """Validate the masked full-channel text-embedding assembly inputs."""
    if input_text_ids.ndim != 2:
        raise ValueError("`input_text_ids` must have shape `[batch, sequence]`.")
    if input_text_ids.shape[0] == 0:
        raise ValueError("Text embedding assembly requires at least one batch item.")
    if input_text_ids.shape[1] != sequence_length:
        raise ValueError("`input_text_ids` sequence length must match the collated sequence.")
    if text_embedding_mask.ndim not in (2, 3):
        raise ValueError(
            "`text_embedding_mask` must have shape `[batch, sequence]` or `[batch, sequence, 1]`."
        )
    if text_embedding_mask.shape[0] != input_text_ids.shape[0]:
        raise ValueError("`text_embedding_mask` batch size must match `input_text_ids`.")
    if text_embedding_mask.shape[1] != input_text_ids.shape[1]:
        raise ValueError("`text_embedding_mask` sequence length must match `input_text_ids`.")
