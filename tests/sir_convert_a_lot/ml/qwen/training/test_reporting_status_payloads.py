"""Focused tests for Qwen reporting status-payload builders.

Purpose:
    Verify the bounded status-payload builders directly so status contract
    drift is caught outside the broader reporter integration tests.

Relationships:
    - Exercises `reporting.status_payloads`.
    - Complements `test_reporting.py` with module-owned unit checks.
"""

from __future__ import annotations

from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_contracts import TrainingSummary
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import TrainingTrackerSummary
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.status_payloads import (
    completed_status_payload,
    running_status_payload,
)


def _training_summary() -> TrainingSummary:
    """Build one compact training summary fixture for payload tests."""
    return TrainingSummary(
        init_model_path="/tmp/model",
        output_model_path="/tmp/run",
        train_jsonl="/tmp/train.jsonl",
        batch_size=8,
        lr=2e-5,
        num_epochs=1,
        max_steps=8,
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        dataloader_length=128,
        eval_dataloader_length=8,
        gradient_accumulation_steps=4,
        optimizer_steps_completed=8,
        train_iterations_completed=32,
        eval_runs_completed=1,
        eval_batches_completed=8,
        last_loss=1.1,
        smoothed_loss=1.2,
        latest_eval_loss=0.9,
        best_eval_loss=0.9,
        best_eval_step=8,
        peak_memory_allocated_bytes=None,
        peak_memory_reserved_bytes=None,
        resumed_from_checkpoint_path=None,
        latest_durable_checkpoint_path="/tmp/run/checkpoints/state-step-00000008",
        latest_durable_checkpoint_step=8,
        latest_durable_checkpoint_epoch=0,
        durable_checkpoint_paths=["/tmp/run/checkpoints/state-step-00000008"],
        checkpoint_paths=["/tmp/run/checkpoint-final"],
        stop_requested=False,
        stop_signal=None,
        stopped_early=False,
        throughput_profile={"profile_label": "hemma-throughput-balanced-v1"},
        batch_occupancy={"total_batches": 1},
        data_path_attribution=None,
        dataloader_tuning={"pin_memory": True},
        heartbeat_policy={"interval_optimizer_steps": 20},
        finite_loss_guard={"enabled": True, "max_consecutive_non_finite_steps": 3},
        acceptance_measurement_valid=True,
        ref_mel_cache={"enabled": True},
        talker_runtime={
            "text_embedding_assembly_mode": "semantic_only",
            "text_embedding_mask_policy": "text_span_only",
            "text_embedding": {
                "available": True,
                "resolved_path": "model.talker.get_text_embeddings()",
                "probeable_as_module": True,
            },
            "codec_embedding": {
                "available": True,
                "resolved_path": "model.talker.get_input_embeddings()",
                "probeable_as_module": True,
            },
            "text_projection": {
                "available": True,
                "resolved_path": "model.talker.text_projection",
                "probeable_as_module": True,
            },
        },
        profiling=None,
        tracking=TrainingTrackerSummary(
            tracker_backends=["mlflow"],
            project_name="qwen-training",
            run_name="run-a",
            mlflow_experiment_name="qwen-training",
            mlflow_tracking_uri="sqlite:////tmp/mlflow.db",
            mlflow_artifact_root="/tmp/mlflow/artifacts",
            mlflow_experiment_id="1",
            mlflow_run_id="run-id",
            mlflow_artifact_uri="/tmp/mlflow/artifacts/run-id/artifacts",
            mlflow_system_metrics_enabled=True,
            mlflow_system_metrics_interval_seconds=10,
            tensorboard_logging_dir="/tmp/tensorboard",
            tensorboard_run_dir="/tmp/tensorboard/qwen-training",
            tensorboard_event_files=["/tmp/tensorboard/event"],
        ),
    )


def _required_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return one nested mapping from a status payload."""
    resolved = payload[key]
    assert isinstance(resolved, dict)
    return resolved


def test_running_status_payload_preserves_diagnostic_and_step_truth() -> None:
    """Running payloads should expose the diagnostic contract and live counters."""
    payload = running_status_payload(
        train_jsonl=Path("/tmp/train.jsonl"),
        eval_jsonl=Path("/tmp/eval.jsonl"),
        output_dir=Path("/tmp/run"),
        train_row_count=128,
        eval_row_count=8,
        dataloader_length=128,
        eval_dataloader_length=8,
        checkpoint_interval_steps=500,
        eval_interval_steps=100,
        gradient_accumulation_steps=4,
        durable_checkpoint_retention=3,
        durable_checkpoint_min_free_bytes=16 * 1024**3,
        dataloader_tuning={"pin_memory": True},
        heartbeat_policy={"interval_optimizer_steps": 20},
        finite_loss_guard_config={"enabled": True, "max_consecutive_non_finite_steps": 3},
        ref_mel_cache_config={"enabled": True},
        bundle_precomputed_reference_input=None,
        throughput_profile={"profile_label": "hemma-throughput-balanced-v1"},
        profiling_plan=None,
        diagnostic={"kind": "diagnose-non-finite"},
        talker_runtime={
            "text_embedding_assembly_mode": "semantic_only",
            "text_embedding_mask_policy": "text_span_only",
            "text_projection": {
                "available": True,
                "resolved_path": "model.talker.text_projection",
                "probeable_as_module": True,
            },
        },
        resume_from_checkpoint=None,
        live_progress={
            "phase": "train",
            "current_epoch": 1,
            "current_optimizer_step": 1405,
            "current_train_iteration": 804,
            "latest_loss": 3.8,
        },
    )

    assert payload["diagnostic"] == {"kind": "diagnose-non-finite"}
    talker_runtime = _required_mapping(payload, "talker_runtime")
    assert talker_runtime["text_embedding_assembly_mode"] == "semantic_only"
    assert talker_runtime["text_embedding_mask_policy"] == "text_span_only"
    text_projection = _required_mapping(talker_runtime, "text_projection")
    assert text_projection["resolved_path"] == ("model.talker.text_projection")
    assert payload["current_phase"] == "train"
    assert payload["current_optimizer_step"] == 1405
    assert payload["current_train_iteration"] == 804


def test_completed_status_payload_serializes_tracking_summary() -> None:
    """Completed payloads should serialize the typed tracking summary via asdict."""
    payload = completed_status_payload(
        train_jsonl=Path("/tmp/train.jsonl"),
        eval_jsonl=Path("/tmp/eval.jsonl"),
        output_dir=Path("/tmp/run"),
        train_row_count=128,
        eval_row_count=8,
        bundle_precomputed_reference_input=None,
        throughput_profile={"profile_label": "hemma-throughput-balanced-v1"},
        training_summary=_training_summary(),
        live_progress={"current_epoch": 0, "current_step": 8},
    )

    tracking = payload["tracking"]
    assert isinstance(tracking, dict)
    assert tracking["mlflow_run_id"] == "run-id"
    talker_runtime = _required_mapping(payload, "talker_runtime")
    assert talker_runtime["text_embedding_assembly_mode"] == "semantic_only"
    assert talker_runtime["text_embedding_mask_policy"] == "text_span_only"
    text_projection = _required_mapping(talker_runtime, "text_projection")
    assert text_projection["resolved_path"] == ("model.talker.text_projection")
    assert payload["checkpoint_interval_steps"] == 500
    assert payload["durable_checkpoint_retention"] == 3
