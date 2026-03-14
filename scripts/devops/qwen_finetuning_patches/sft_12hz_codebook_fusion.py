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


def fuse_auxiliary_codebook_embeddings(
    *,
    codebook_embeddings: Sequence[torch.nn.Module],
    codec_ids: torch.Tensor,
    codec_mask: torch.Tensor,
) -> torch.Tensor:
    """Return the summed auxiliary codebook embeddings for groups 1..15."""
    auxiliary_codec_ids = codec_ids[:, :, 1:]
    fused_embeddings = torch.stack(
        [
            embedding(auxiliary_codec_ids[:, :, index])
            for index, embedding in enumerate(codebook_embeddings)
        ],
        dim=0,
    )
    mask = codec_mask.unsqueeze(0).unsqueeze(-1).to(dtype=fused_embeddings.dtype)
    return (fused_embeddings * mask).sum(dim=0)
