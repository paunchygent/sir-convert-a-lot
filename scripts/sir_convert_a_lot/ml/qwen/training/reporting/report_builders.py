"""Terminal report builders for Qwen training artifacts.

Purpose:
    Assemble machine-readable completed and failed training reports while
    keeping runtime-environment discovery and failure parsing in separate
    modules.

Relationships:
    - Used by the in-container trainer entrypoint.
    - Consumes runtime version helpers and failure-projection helpers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    TrainingFailureSummary,
    TrainingReport,
)

from .artifact_io import utc_now_iso
from .failure_projection import (
    optional_mapping_bool,
    optional_mapping_dict,
    optional_mapping_float,
    optional_mapping_int,
    optional_mapping_string,
    required_string,
)
from .runtime_versions import runtime_environment_payload


def build_training_report(
    *,
    model_id: str,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    bundle_precomputed_reference_input: Mapping[str, object] | None,
    throughput_profile: Mapping[str, object] | None,
    diagnostic: Mapping[str, object] | None,
    training_summary: TrainingSummary,
) -> TrainingReport:
    """Build the machine-readable report from one completed training run."""
    runtime_payload = runtime_environment_payload()
    return TrainingReport(
        generated_at=utc_now_iso(),
        status="completed",
        model_id=model_id,
        train_jsonl=train_jsonl.as_posix(),
        eval_jsonl=eval_jsonl.as_posix(),
        output_dir=output_dir.as_posix(),
        train_row_count=train_row_count,
        eval_row_count=eval_row_count,
        upstream_trainer_uses_eval_manifest=True,
        torch_version=str(runtime_payload["torch_version"]),
        torchaudio_version=runtime_payload["torchaudio_version"],
        torch_cuda_available=bool(runtime_payload["torch_cuda_available"]),
        torch_cuda_device_count=int(runtime_payload["torch_cuda_device_count"]),
        torch_hip_version=str(runtime_payload["torch_hip_version"]),
        flash_attn_importable=bool(runtime_payload["flash_attn_importable"]),
        flash_attn_version=runtime_payload["flash_attn_version"],
        bundle_precomputed_reference_input=(
            None
            if bundle_precomputed_reference_input is None
            else dict(bundle_precomputed_reference_input)
        ),
        throughput_profile=None if throughput_profile is None else dict(throughput_profile),
        tracking=None if training_summary.tracking is None else asdict(training_summary.tracking),
        diagnostic=None if diagnostic is None else dict(diagnostic),
        training_summary=asdict(training_summary),
        failure=None,
    )


def build_failed_training_report(
    *,
    model_id: str,
    train_jsonl: Path,
    eval_jsonl: Path,
    output_dir: Path,
    train_row_count: int,
    eval_row_count: int,
    bundle_precomputed_reference_input: Mapping[str, object] | None,
    throughput_profile: Mapping[str, object] | None,
    tracking: Mapping[str, object] | None,
    diagnostic: Mapping[str, object] | None,
    failed_status: Mapping[str, object],
) -> TrainingReport:
    """Build the machine-readable report from one failed training run."""
    runtime_payload = runtime_environment_payload()
    return TrainingReport(
        generated_at=utc_now_iso(),
        status="failed",
        model_id=model_id,
        train_jsonl=train_jsonl.as_posix(),
        eval_jsonl=eval_jsonl.as_posix(),
        output_dir=output_dir.as_posix(),
        train_row_count=train_row_count,
        eval_row_count=eval_row_count,
        upstream_trainer_uses_eval_manifest=True,
        torch_version=str(runtime_payload["torch_version"]),
        torchaudio_version=runtime_payload["torchaudio_version"],
        torch_cuda_available=bool(runtime_payload["torch_cuda_available"]),
        torch_cuda_device_count=int(runtime_payload["torch_cuda_device_count"]),
        torch_hip_version=str(runtime_payload["torch_hip_version"]),
        flash_attn_importable=bool(runtime_payload["flash_attn_importable"]),
        flash_attn_version=runtime_payload["flash_attn_version"],
        bundle_precomputed_reference_input=(
            None
            if bundle_precomputed_reference_input is None
            else dict(bundle_precomputed_reference_input)
        ),
        throughput_profile=None if throughput_profile is None else dict(throughput_profile),
        tracking=None if tracking is None else dict(tracking),
        diagnostic=None if diagnostic is None else dict(diagnostic),
        training_summary=None,
        failure=TrainingFailureSummary(
            error=required_string(failed_status, "error"),
            current_phase=required_string(failed_status, "current_phase"),
            step_semantics=optional_mapping_dict(failed_status, "step_semantics"),
            current_epoch=optional_mapping_int(failed_status, "current_epoch"),
            current_step=optional_mapping_int(failed_status, "current_step"),
            current_optimizer_step=optional_mapping_int(failed_status, "current_optimizer_step"),
            current_train_iteration=optional_mapping_int(failed_status, "current_train_iteration"),
            latest_loss=optional_mapping_float(failed_status, "latest_loss"),
            smoothed_loss=optional_mapping_float(failed_status, "smoothed_loss"),
            latest_durable_checkpoint_path=optional_mapping_string(
                failed_status,
                "latest_durable_checkpoint_path",
            ),
            latest_durable_checkpoint_step=optional_mapping_int(
                failed_status,
                "latest_durable_checkpoint_step",
            ),
            latest_durable_checkpoint_saved_at=optional_mapping_string(
                failed_status,
                "latest_durable_checkpoint_saved_at",
            ),
            finite_loss_guard=optional_mapping_dict(failed_status, "finite_loss_guard"),
            optimizer_boundary_guard=optional_mapping_dict(
                failed_status,
                "optimizer_boundary_guard",
            ),
            acceptance_measurement_valid=optional_mapping_bool(
                failed_status,
                "acceptance_measurement_valid",
            ),
            latest_eval_loss=optional_mapping_float(failed_status, "latest_eval_loss"),
            best_eval_loss=optional_mapping_float(failed_status, "best_eval_loss"),
            best_eval_step=optional_mapping_int(failed_status, "best_eval_step"),
            eval_runs_completed=optional_mapping_int(failed_status, "eval_runs_completed"),
        ),
    )
