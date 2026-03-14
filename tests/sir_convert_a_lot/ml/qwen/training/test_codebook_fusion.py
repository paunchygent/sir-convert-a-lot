"""Focused tests for Task 101 codebook fusion.

Purpose:
    Validate that the auxiliary-codebook fusion helper preserves the summed
    embedding semantics expected by the patched Qwen training loop.

Relationships:
    - Exercises `sft_12hz_codebook_fusion.py`.
"""

from __future__ import annotations

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    fuse_auxiliary_codebook_embeddings,
)
from tests.sir_convert_a_lot.ml.qwen.training.test_support import _FakeEmbedding


def test_fuse_auxiliary_codebook_embeddings_matches_manual_sum() -> None:
    """The fusion helper should match the previous per-codebook accumulation."""
    embeddings = [_FakeEmbedding(4) for _ in range(15)]
    codec_ids = torch.randint(0, 16, (2, 5, 16), dtype=torch.long)
    codec_mask = torch.tensor(
        [
            [False, True, True, False, False],
            [False, True, False, True, False],
        ],
        dtype=torch.bool,
    )

    fused = fuse_auxiliary_codebook_embeddings(
        codebook_embeddings=embeddings,
        codec_ids=codec_ids,
        codec_mask=codec_mask,
    )

    manual = torch.zeros((2, 5, 4), dtype=fused.dtype)
    for codec_index in range(1, 16):
        manual = manual + (
            embeddings[codec_index - 1](codec_ids[:, :, codec_index]) * codec_mask.unsqueeze(-1)
        )

    assert torch.allclose(fused, manual)


def test_fuse_auxiliary_codebook_embeddings_accepts_plain_embedding_modules() -> None:
    """The fusion helper should work with direct `nn.Embedding` modules too."""
    embeddings = [torch.nn.Embedding(16, 4) for _ in range(15)]
    codec_ids = torch.randint(0, 16, (1, 3, 16), dtype=torch.long)
    codec_mask = torch.tensor([[True, False, True]], dtype=torch.bool)

    fused = fuse_auxiliary_codebook_embeddings(
        codebook_embeddings=embeddings,
        codec_ids=codec_ids,
        codec_mask=codec_mask,
    )

    manual = torch.zeros((1, 3, 4), dtype=fused.dtype)
    for codec_index in range(1, 16):
        manual = manual + (
            embeddings[codec_index - 1](codec_ids[:, :, codec_index]) * codec_mask.unsqueeze(-1)
        )

    assert torch.allclose(fused, manual)
