"""Semantic-only text-embedding assembly helpers for patched Qwen fine-tuning.

Purpose:
    Build the full-sequence text-embedding tensor from semantic-only text ids
    and collated semantic positions so scaffold tokens never traverse the
    trainable text-embedding lookup path in the active no-projection lane.

Relationships:
    - Imported by `sft_12hz_train_step.py` and `sft_12hz_eval.py`.
    - Consumes the semantic-only batch fields emitted by `dataset.py`.
    - Preserves the downstream full-sequence `inputs_embeds` shape expected by
      the patched Qwen talker runtime.
"""

from __future__ import annotations

from collections.abc import Callable

import torch


def assemble_semantic_text_embedding(
    *,
    text_embedding: Callable[[torch.Tensor], torch.Tensor],
    semantic_text_ids: torch.Tensor,
    semantic_text_positions: torch.Tensor,
    semantic_text_mask: torch.Tensor,
    sequence_length: int,
) -> torch.Tensor:
    """Return one full-sequence text-embedding tensor from semantic-only ids."""
    _validate_semantic_text_inputs(
        semantic_text_ids=semantic_text_ids,
        semantic_text_positions=semantic_text_positions,
        semantic_text_mask=semantic_text_mask,
        sequence_length=sequence_length,
    )
    semantic_embeddings = text_embedding(semantic_text_ids)
    if semantic_embeddings.ndim != 3:
        raise ValueError("Semantic text embedding surface must return `[batch, tokens, hidden]`.")
    batch_size, _, hidden_size = semantic_embeddings.shape
    full_sequence_embedding = semantic_embeddings.new_zeros(
        (batch_size, sequence_length, hidden_size)
    )
    if semantic_text_ids.shape[1] == 0:
        return full_sequence_embedding
    semantic_mask = semantic_text_mask.unsqueeze(-1).to(dtype=semantic_embeddings.dtype)
    safe_positions = semantic_text_positions.to(device=semantic_embeddings.device).unsqueeze(-1)
    safe_positions = safe_positions.expand_as(semantic_embeddings)
    safe_positions = safe_positions.masked_fill(~semantic_text_mask.unsqueeze(-1), 0)
    full_sequence_embedding.scatter_add_(
        1,
        safe_positions,
        semantic_embeddings * semantic_mask,
    )
    return full_sequence_embedding


def _validate_semantic_text_inputs(
    *,
    semantic_text_ids: torch.Tensor,
    semantic_text_positions: torch.Tensor,
    semantic_text_mask: torch.Tensor,
    sequence_length: int,
) -> None:
    """Validate the semantic-only batch fields before embedding assembly."""
    if semantic_text_ids.ndim != 2:
        raise ValueError("`semantic_text_ids` must have shape `[batch, semantic_tokens]`.")
    if semantic_text_positions.shape != semantic_text_ids.shape:
        raise ValueError("`semantic_text_positions` must match `semantic_text_ids` shape.")
    if semantic_text_mask.shape != semantic_text_ids.shape:
        raise ValueError("`semantic_text_mask` must match `semantic_text_ids` shape.")
    if semantic_text_mask.dtype != torch.bool:
        raise ValueError("`semantic_text_mask` must be boolean.")
    if sequence_length <= 0:
        raise ValueError("`sequence_length` must be positive.")
    if semantic_text_ids.shape[0] == 0:
        raise ValueError("Semantic text embedding assembly requires at least one batch item.")
    if semantic_text_positions.numel() == 0:
        return
    valid_positions = semantic_text_positions[semantic_text_mask]
    if valid_positions.numel() == 0:
        return
    if int(valid_positions.min().item()) < 0:
        raise ValueError("`semantic_text_positions` cannot contain negative positions.")
    if int(valid_positions.max().item()) >= sequence_length:
        raise ValueError("`semantic_text_positions` must stay within the collated sequence.")
