"""Focused tests for Task 101 codebook fusion.

Purpose:
    Validate that the auxiliary-codebook fusion helper preserves the summed
    embedding semantics expected by the patched Qwen training loop.

Relationships:
    - Exercises `sft_12hz_codebook_fusion.py`.
"""

from __future__ import annotations

import pytest
import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    _reduce_masked_embeddings,
    fuse_auxiliary_codebook_embeddings,
)
from tests.sir_convert_a_lot.ml.qwen.training.training_test_support import _FakeEmbedding


def test_fuse_auxiliary_codebook_embeddings_matches_float32_accumulation_contract() -> None:
    """The fusion helper should match the native vectorized reduction contract."""
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

    stacked = torch.stack(
        [embeddings[codec_index](codec_ids[:, :, codec_index + 1]) for codec_index in range(15)],
        dim=2,
    )
    mask = codec_mask.unsqueeze(-1).unsqueeze(-1).to(dtype=stacked.dtype)
    manual = torch.sum(stacked * mask, dim=2)

    torch.testing.assert_close(fused, manual)


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

    stacked = torch.stack(
        [embeddings[codec_index](codec_ids[:, :, codec_index + 1]) for codec_index in range(15)],
        dim=2,
    )
    mask = codec_mask.unsqueeze(-1).unsqueeze(-1).to(dtype=stacked.dtype)
    manual = torch.sum(stacked * mask, dim=2)

    torch.testing.assert_close(fused, manual)


@pytest.mark.parametrize("dtype", [torch.float16, torch.bfloat16])
def test_reduce_masked_embeddings_matches_native_vectorized_sum(
    dtype: torch.dtype,
) -> None:
    """Low-precision reductions should match the native vectorized sum."""
    masked_embeddings = torch.randn((2, 3, 15, 8), dtype=torch.float32).to(dtype=dtype)

    reduced = _reduce_masked_embeddings(masked_embeddings)
    expected = torch.sum(masked_embeddings, dim=2)

    torch.testing.assert_close(reduced, expected)
