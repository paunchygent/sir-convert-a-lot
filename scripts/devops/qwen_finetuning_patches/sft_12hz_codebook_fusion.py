"""Codebook-fusion helpers for the patched Qwen trainer.

Purpose:
    Keep the Task 101 auxiliary-codebook fusion logic out of the hot training
    loop while reducing repeated tensor-add fragmentation there.

Relationships:
    - Imported by `sft_12hz_loop.py` during forward/backward execution.
    - Consumes the code predictor input-embedding modules from the upstream
      Qwen talker model.
"""

from __future__ import annotations

from collections.abc import Sequence

import torch


def _embedding_weight(embedding: torch.nn.Module) -> torch.Tensor:
    """Return the weight tensor for one auxiliary codebook embedding module."""
    if hasattr(embedding, "weight"):
        weight = getattr(embedding, "weight")
        if isinstance(weight, torch.Tensor):
            return weight
    nested_embedding = getattr(embedding, "embedding", None)
    if isinstance(nested_embedding, torch.nn.Embedding):
        return nested_embedding.weight
    raise TypeError("Auxiliary codebook embedding module must expose an embedding weight tensor.")


def _stack_codebook_weights(codebook_embeddings: Sequence[torch.nn.Module]) -> torch.Tensor:
    """Return one stacked `[codebook, vocab, dim]` weight tensor."""
    if len(codebook_embeddings) == 0:
        raise ValueError("Expected at least one auxiliary codebook embedding module.")
    weights = [_embedding_weight(embedding) for embedding in codebook_embeddings]
    return torch.stack(weights, dim=0)


def fuse_auxiliary_codebook_embeddings(
    *,
    codebook_embeddings: Sequence[torch.nn.Module],
    codec_ids: torch.Tensor,
    codec_mask: torch.Tensor,
) -> torch.Tensor:
    """Return the summed auxiliary codebook embeddings for groups 1..15."""
    auxiliary_codec_ids = codec_ids[:, :, 1:]
    if auxiliary_codec_ids.shape[2] != len(codebook_embeddings):
        raise ValueError("Auxiliary codec-id count did not match the codebook-embedding count.")
    stacked_weights = _stack_codebook_weights(codebook_embeddings).to(device=codec_ids.device)
    codebook_indices = torch.arange(
        len(codebook_embeddings),
        device=codec_ids.device,
        dtype=torch.long,
    ).view(1, 1, -1)
    fused_embeddings = stacked_weights[codebook_indices, auxiliary_codec_ids]
    mask = codec_mask.unsqueeze(-1).unsqueeze(-1).to(dtype=fused_embeddings.dtype)
    return (fused_embeddings * mask).sum(dim=2)
