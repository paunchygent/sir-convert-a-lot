"""Shared forward-surface helpers for patched Qwen training and diagnostics.

Purpose:
    Build the semantic-only text path, codec path, fused auxiliary path, and
    talker losses in one reusable place so training, eval, and small-signal
    RCA probes all exercise the same assembly contract.

Relationships:
    - Imported by `sft_12hz_train_step.py` and `sft_12hz_eval.py`.
    - Imported by the Story 30 backward-lineage probe to inspect the same
      forward graph without duplicating train-step assembly code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    fuse_auxiliary_codebook_embeddings,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    to_device_with_optional_non_blocking,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_semantic_text_embeddings import (
    build_semantic_text_embedding_assembly,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    resolve_talker_codec_embedding,
    resolve_talker_text_embedding,
)


class TalkerOutputsProtocol(Protocol):
    """Minimal talker forward output surface reused by training helpers."""

    loss: torch.Tensor
    hidden_states: (
        list[list[torch.Tensor]]
        | tuple[list[torch.Tensor], ...]
        | tuple[tuple[torch.Tensor, ...], ...]
    )


@dataclass(frozen=True)
class TalkerForwardSurfaces:
    """Resolved forward-path tensors and losses for one collated batch."""

    ref_mels_on_device: torch.Tensor
    speaker_embedding: torch.Tensor
    semantic_text_embeddings: torch.Tensor
    input_text_embedding: torch.Tensor
    input_codec_embedding: torch.Tensor
    fused_auxiliary_embedding: torch.Tensor
    input_embeddings: torch.Tensor
    outputs: TalkerOutputsProtocol
    hidden_states: torch.Tensor
    talker_hidden_states: torch.Tensor
    talker_codec_ids: torch.Tensor
    main_loss: torch.Tensor
    sub_talker_loss: torch.Tensor
    combined_loss: torch.Tensor


@dataclass(frozen=True)
class ForwardBatchInputs:
    """Typed batch tensors required for one shared Qwen talker forward pass."""

    input_ids: torch.Tensor
    codec_ids: torch.Tensor
    semantic_text_ids: torch.Tensor
    semantic_text_positions: torch.Tensor
    semantic_text_mask: torch.Tensor
    ref_mels: torch.Tensor
    codec_embedding_mask: torch.Tensor
    attention_mask: torch.Tensor
    codec_0_labels: torch.Tensor
    codec_mask: torch.Tensor


def execute_talker_forward_pass(
    *,
    model,
    batch: ForwardBatchInputs,
    non_blocking_transfer: bool,
) -> TalkerForwardSurfaces:
    """Execute the shared no-projection talker forward pass for one batch."""
    ref_mels_on_device = to_device_with_optional_non_blocking(
        batch.ref_mels,
        device=model.device,
        dtype=model.dtype,
        non_blocking_transfer=non_blocking_transfer,
    )
    speaker_embedding = model.speaker_encoder(ref_mels_on_device).detach()
    text_embedding = resolve_talker_text_embedding(model)
    codec_embedding = resolve_talker_codec_embedding(model)
    input_codec_ids = batch.input_ids[:, :, 1]
    semantic_assembly = build_semantic_text_embedding_assembly(
        text_embedding=text_embedding,
        semantic_text_ids=batch.semantic_text_ids,
        semantic_text_positions=batch.semantic_text_positions,
        semantic_text_mask=batch.semantic_text_mask,
        sequence_length=batch.input_ids.shape[1],
    )
    input_codec_embedding = codec_embedding(input_codec_ids) * batch.codec_embedding_mask
    input_codec_embedding[:, 6, :] = speaker_embedding
    fused_auxiliary_embedding = fuse_auxiliary_codebook_embeddings(
        codebook_embeddings=model.talker.code_predictor.get_input_embeddings(),
        codec_ids=batch.codec_ids,
        codec_mask=batch.codec_mask,
    )
    input_embeddings = (
        semantic_assembly.full_sequence_embedding
        + input_codec_embedding
        + fused_auxiliary_embedding
    )
    outputs = model.talker(
        inputs_embeds=input_embeddings[:, :-1, :],
        attention_mask=batch.attention_mask[:, :-1],
        labels=batch.codec_0_labels[:, 1:],
        output_hidden_states=True,
    )
    hidden_states = outputs.hidden_states[0][-1]
    talker_hidden_states = hidden_states[batch.codec_mask[:, 1:]]
    talker_codec_ids = batch.codec_ids[batch.codec_mask]
    _, sub_talker_loss = model.talker.forward_sub_talker_finetune(
        talker_codec_ids,
        talker_hidden_states,
    )
    main_loss = outputs.loss
    combined_loss = outputs.loss + 0.3 * sub_talker_loss
    return TalkerForwardSurfaces(
        ref_mels_on_device=ref_mels_on_device,
        speaker_embedding=speaker_embedding,
        semantic_text_embeddings=semantic_assembly.semantic_embeddings,
        input_text_embedding=semantic_assembly.full_sequence_embedding,
        input_codec_embedding=input_codec_embedding,
        fused_auxiliary_embedding=fused_auxiliary_embedding,
        input_embeddings=input_embeddings,
        outputs=outputs,
        hidden_states=hidden_states,
        talker_hidden_states=talker_hidden_states,
        talker_codec_ids=talker_codec_ids,
        main_loss=main_loss,
        sub_talker_loss=sub_talker_loss,
        combined_loss=combined_loss,
    )
