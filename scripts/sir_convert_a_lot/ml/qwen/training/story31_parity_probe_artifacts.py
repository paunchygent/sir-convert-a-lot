"""Artifact and signature helpers for the Story 31 parity probe.

Purpose:
    Keep JSON-safe checkpoint extraction, tensor signatures, and comparable
    path-report payload shaping out of the execution module so the mechanism
    surface stays split between runtime work and artifact projection.

Relationships:
    - Imported by `story31_parity_probe_runtime.py` to build path reports.
    - Imported by `story31_parity_probe_execution.py` to project execution
      outcomes into checkpoint-comparison payloads.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import torch

from scripts.devops.qwen_finetuning_patches.dataset import (
    BatchTensors,
    DatasetItem,
    TrainingRow,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import PreparedTrainingRun

_FORWARD_ENTRY_PROBES = (
    "ref_mels",
    "speaker_embedding",
    "semantic_text_embeddings",
    "input_text_embedding",
    "input_codec_embedding",
    "fused_auxiliary_embedding",
    "input_embeddings",
    "talker_hidden_states",
)
_LOSS_PROBES = ("main_loss", "sub_talker_loss", "combined_loss", "grad_norm")


@dataclass(frozen=True)
class ExecutionArtifacts:
    """Internal checkpoint payloads extracted from one execution path."""

    execution_outcome: dict[str, object]
    step_forensics: dict[str, object] | None
    forward_entry_surfaces: tuple[dict[str, object], ...]
    loss_decomposition: tuple[dict[str, object], ...]
    backward_pre_clip: dict[str, object] | None
    clip_boundary: dict[str, object] | None
    optimizer_preconditions: dict[str, object] | None


@dataclass(frozen=True)
class SelectedRow:
    """One manifest row paired with its stable dataset index."""

    dataset_index: int
    row: TrainingRow


def execution_artifacts_from_failure_payload(
    *,
    status: str,
    payload: dict[str, object],
) -> ExecutionArtifacts:
    """Project one failure payload into comparable execution artifacts."""
    enriched_payload = {"status": status, **payload}
    return execution_artifacts_from_payload(payload=enriched_payload)


def execution_artifacts_from_payload(payload: dict[str, object]) -> ExecutionArtifacts:
    """Project one execution payload into comparable checkpoint artifacts."""
    step_forensics = optional_mapping(payload, "step_forensics")
    return ExecutionArtifacts(
        execution_outcome=payload,
        step_forensics=step_forensics,
        forward_entry_surfaces=_microbatch_surface_payloads(
            step_forensics=step_forensics,
            probe_names=_FORWARD_ENTRY_PROBES,
        ),
        loss_decomposition=_microbatch_surface_payloads(
            step_forensics=step_forensics,
            probe_names=_LOSS_PROBES,
        ),
        backward_pre_clip=_backward_pre_clip_payload(payload),
        clip_boundary=_clip_boundary_payload(payload),
        optimizer_preconditions=_optimizer_preconditions_payload(payload),
    )


def runtime_posture(prepared: PreparedTrainingRun) -> dict[str, object]:
    """Return the comparable runtime posture for one prepared parity path."""
    args = prepared.args
    return {
        "init_model_path": str(args.init_model_path),
        "train_jsonl": str(args.train_jsonl),
        "eval_jsonl": str(args.eval_jsonl),
        "batch_size": int(args.batch_size),
        "gradient_accumulation_steps": prepared.gradient_accumulation_steps,
        "text_embedding_assembly_mode": prepared.text_embedding_assembly_mode,
        "text_embedding_mask_policy": prepared.talker_runtime.get("text_embedding_mask_policy"),
        "throughput_profile": dict(prepared.throughput_profile_payload),
        "dataloader_tuning": {
            "num_workers": prepared.effective_dataloader_tuning.num_workers,
            "pin_memory": prepared.effective_dataloader_tuning.pin_memory,
            "persistent_workers": prepared.effective_dataloader_tuning.persistent_workers,
            "prefetch_factor": prepared.effective_dataloader_tuning.prefetch_factor,
            "non_blocking_transfer": prepared.effective_dataloader_tuning.non_blocking_transfer,
        },
        "accelerator_mixed_precision": getattr(prepared.accelerator, "mixed_precision", None),
        "talker_runtime": dict(prepared.talker_runtime),
    }


def selected_row_signature(*, row: TrainingRow, dataset_index: int) -> dict[str, object]:
    """Return one JSON-safe manifest-row signature for parity comparison."""
    audio_codes = row.get("audio_codes", [])
    return {
        "dataset_index": dataset_index,
        "row_id": row.get("row_id"),
        "manifest_path": row.get("manifest_path"),
        "manifest_line_number": row.get("manifest_line_number"),
        "speaker_id": row.get("speaker_id"),
        "text": row.get("text"),
        "ref_audio": row.get("ref_audio"),
        "audio_code_frame_count": len(audio_codes) if isinstance(audio_codes, list) else None,
        "audio_codes_sha256": _sha256_text(json.dumps(audio_codes, separators=(",", ":"))),
        "precomputed_ref_input_path": row.get("precomputed_ref_input_path"),
        "precomputed_ref_input_kind": row.get("precomputed_ref_input_kind"),
        "precomputed_ref_input_version": row.get("precomputed_ref_input_version"),
        "precomputed_ref_input_source_audio": row.get("precomputed_ref_input_source_audio"),
    }


def dataset_item_signature(item: DatasetItem) -> dict[str, object]:
    """Return one JSON-safe prepared dataset-item signature."""
    return {
        "batch_row_provenance": dict(item["batch_row_provenance"]),
        "speaker_id": int(item["speaker_id"]),
        "text_ids": _tensor_signature(item["text_ids"]),
        "audio_codes": _tensor_signature(item["audio_codes"]),
        "ref_mel": _tensor_signature(item["ref_mel"]),
    }


def collated_batch_signature(batch: BatchTensors) -> dict[str, object]:
    """Return one JSON-safe collated batch signature."""
    return {
        "input_ids": _tensor_signature(batch["input_ids"]),
        "semantic_text_ids": _tensor_signature(batch["semantic_text_ids"]),
        "semantic_text_positions": _tensor_signature(batch["semantic_text_positions"]),
        "semantic_text_mask": _tensor_signature(batch["semantic_text_mask"]),
        "ref_mels": _tensor_signature(batch["ref_mels"]),
        "attention_mask": _tensor_signature(batch["attention_mask"]),
        "text_embedding_mask": _tensor_signature(batch["text_embedding_mask"]),
        "codec_embedding_mask": _tensor_signature(batch["codec_embedding_mask"]),
        "codec_0_labels": _tensor_signature(batch["codec_0_labels"]),
        "codec_ids": _tensor_signature(batch["codec_ids"]),
        "codec_mask": _tensor_signature(batch["codec_mask"]),
        "speaker_ids": _tensor_signature(batch["speaker_ids"]),
        "batch_provenance": [dict(entry) for entry in batch["batch_provenance"]],
    }


def optional_mapping(payload: Mapping[str, object], key: str) -> dict[str, object] | None:
    """Return one optional mapping field as a plain dict when present."""
    value = payload.get(key)
    return dict(value) if isinstance(value, Mapping) else None


def _microbatch_surface_payloads(
    *,
    step_forensics: dict[str, object] | None,
    probe_names: Sequence[str],
) -> tuple[dict[str, object], ...]:
    if step_forensics is None:
        return ()
    raw_microbatches = step_forensics.get("microbatches")
    if not isinstance(raw_microbatches, list):
        return ()
    payloads: list[dict[str, object]] = []
    for microbatch in raw_microbatches:
        if not isinstance(microbatch, Mapping):
            continue
        tensor_finiteness = optional_mapping(microbatch, "tensor_finiteness")
        tensors = None if tensor_finiteness is None else tensor_finiteness.get("tensors")
        surfaces: dict[str, object] = {}
        if isinstance(tensors, Mapping):
            for probe_name in probe_names:
                probe_payload = tensors.get(probe_name)
                if isinstance(probe_payload, Mapping):
                    surfaces[probe_name] = dict(probe_payload)
        payloads.append(
            {
                "train_iteration": microbatch.get("train_iteration"),
                "microbatch_index_in_optimizer_step": microbatch.get(
                    "microbatch_index_in_optimizer_step"
                ),
                "first_non_finite_tensor": microbatch.get("first_non_finite_tensor"),
                "surfaces": surfaces,
            }
        )
    return tuple(payloads)


def _backward_pre_clip_payload(payload: Mapping[str, object]) -> dict[str, object] | None:
    pre_clip_gradient_probes = optional_mapping(payload, "pre_clip_gradient_probes")
    if pre_clip_gradient_probes is None:
        return None
    return {
        "trigger_reason": payload.get("trigger_reason"),
        "first_non_finite_stage": payload.get("first_non_finite_stage"),
        "first_non_finite_surface": payload.get("first_non_finite_surface"),
        "pre_clip_gradient_probes": pre_clip_gradient_probes,
    }


def _clip_boundary_payload(payload: Mapping[str, object]) -> dict[str, object] | None:
    post_clip_gradient_probes = optional_mapping(payload, "post_clip_gradient_probes")
    grad_norm_value = payload.get("grad_norm_value")
    if post_clip_gradient_probes is None and grad_norm_value is None:
        return None
    return {
        "trigger_reason": payload.get("trigger_reason"),
        "first_non_finite_stage": payload.get("first_non_finite_stage"),
        "first_non_finite_surface": payload.get("first_non_finite_surface"),
        "grad_norm_value": grad_norm_value,
        "grad_norm_is_finite": payload.get("grad_norm_is_finite"),
        "post_clip_gradient_probes": post_clip_gradient_probes,
    }


def _optimizer_preconditions_payload(payload: Mapping[str, object]) -> dict[str, object] | None:
    pre_step_parameter_probes = optional_mapping(payload, "pre_step_parameter_probes")
    pre_step_optimizer_state_probes = optional_mapping(payload, "pre_step_optimizer_state_probes")
    targeted_parameter_names = payload.get("targeted_parameter_names")
    if (
        pre_step_parameter_probes is None
        and pre_step_optimizer_state_probes is None
        and not isinstance(targeted_parameter_names, list)
    ):
        return None
    return {
        "targeted_parameter_names": (
            targeted_parameter_names if isinstance(targeted_parameter_names, list) else []
        ),
        "pre_step_parameter_probes": pre_step_parameter_probes,
        "pre_step_optimizer_state_probes": pre_step_optimizer_state_probes,
    }


def _tensor_signature(tensor: torch.Tensor) -> dict[str, object]:
    detached = tensor.detach().cpu().contiguous()
    byte_view = (
        detached.view(torch.uint8)
        if detached.numel() > 0
        else detached.new_zeros((0,), dtype=torch.uint8)
    )
    return {
        "dtype": str(detached.dtype),
        "shape": [int(dimension) for dimension in detached.shape],
        "element_count": int(detached.numel()),
        "sha256": hashlib.sha256(byte_view.numpy().tobytes()).hexdigest(),
        "preview": _tensor_preview(detached),
        "is_finite": _tensor_is_finite(detached),
    }


def _tensor_preview(tensor: torch.Tensor, *, max_items: int = 8) -> list[object]:
    if tensor.numel() == 0:
        return []
    flattened = tensor.reshape(-1)[:max_items]
    if flattened.dtype == torch.bool:
        return [bool(value.item()) for value in flattened]
    if torch.is_floating_point(flattened):
        return [float(value.item()) for value in flattened.to(dtype=torch.float32)]
    return [int(value.item()) for value in flattened]


def _tensor_is_finite(tensor: torch.Tensor) -> bool:
    if tensor.numel() == 0:
        return True
    if torch.is_floating_point(tensor):
        return bool(torch.isfinite(tensor.to(dtype=torch.float32)).all().item())
    return True


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
