"""In-container training entrypoint for Qwen fine-tuning.

Purpose:
    Execute one bounded Swedish Qwen3-TTS fine-tuning run inside the training
    image, persist machine-readable status/report artifacts, and keep the
    detached outer orchestrator independent from the inner training loop.

Relationships:
    - Executed inside the shared Qwen runtime image by the host orchestrator.
    - Delegates core training to the patched `sft_12hz.py`.
    - Uses the `ml.qwen.training.reporting` package for live heartbeat and
      terminal reports.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict

import sft_12hz
import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_diagnostic_capture import (
    diagnostic_capture_config_from_args,
    write_diagnostic_capture_artifact,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import load_optional_training_bundle_summary
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostic_artifacts import (
    build_diagnostic_replay_bundle,
    diagnostic_replay_bundle_path,
    diagnostic_window_artifact_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting import (
    StatusReporter,
    StatusReporterConfig,
    build_failed_training_report,
    build_training_report,
    write_json,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
    resolve_text_embedding_assembly_mode,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    resolve_text_embedding_mask_policy,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)
from scripts.sir_convert_a_lot.ml.qwen.training.trainer_cli import parse_trainer_args
from scripts.sir_convert_a_lot.ml.qwen.training.trainer_runtime_support import (
    count_jsonl_rows,
    load_completed_status_payload,
)


def _parse_args() -> argparse.Namespace:
    """Return CLI arguments for compatibility with trainer-focused tests."""
    return parse_trainer_args()


def main() -> int:
    """Run the in-container training trainer and persist report artifacts."""
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "status.json"
    report_path = output_dir / "report.json"
    failure_path = output_dir / "failure.txt"
    training_summary_path = output_dir / "training_summary.json"
    talker_runtime_path = output_dir / "talker_runtime.json"
    train_row_count = count_jsonl_rows(args.train_jsonl)
    eval_row_count = count_jsonl_rows(args.eval_jsonl)
    bundle_summary = (
        None
        if args.pilot_bundle_root is None
        else load_optional_training_bundle_summary(args.pilot_bundle_root)
    )
    bundle_precomputed_reference_input = (
        None
        if bundle_summary is None
        else {
            "kind": bundle_summary.precomputed_reference_input.kind,
            "version": bundle_summary.precomputed_reference_input.version,
            "source_field": bundle_summary.precomputed_reference_input.source_field,
            "artifact_root": bundle_summary.precomputed_reference_input.artifact_root,
            "artifact_count": bundle_summary.precomputed_reference_input.artifact_count,
        }
    )
    throughput_policy = resolve_throughput_batch_policy(
        profile_label=str(args.throughput_profile_label),
        max_batch_size=int(args.batch_size),
    )
    gradient_accumulation_steps = resolve_gradient_accumulation_steps(
        getattr(args, "gradient_accumulation_steps", None),
        default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    )

    tracking_plan = {
        "tracker_backends": ["mlflow", "tensorboard"],
        "project_name": str(args.tracker_project_name),
        "run_name": str(args.tracker_run_name or output_dir.name),
        "mlflow_experiment_name": str(args.mlflow_experiment_name),
        "mlflow_tracking_uri": args.mlflow_tracking_uri,
        "mlflow_artifact_root": args.mlflow_artifact_root,
        "tensorboard_logging_dir": args.tensorboard_logging_dir,
    }
    diagnostic = (
        None
        if getattr(args, "diagnostic_kind", None) is None
        else {
            "kind": str(getattr(args, "diagnostic_kind")),
            "source_launch_root": (
                None
                if getattr(args, "diagnostic_source_launch_root", None) is None
                else getattr(args, "diagnostic_source_launch_root").as_posix()
            ),
            "source_checkpoint_path": (
                None
                if getattr(args, "diagnostic_source_checkpoint_path", None) is None
                else getattr(args, "diagnostic_source_checkpoint_path").as_posix()
            ),
            "target_optimizer_step": (
                None
                if getattr(args, "diagnostic_target_optimizer_step", None) is None
                else int(getattr(args, "diagnostic_target_optimizer_step"))
            ),
            "start_optimizer_step": (
                None
                if getattr(args, "diagnostic_start_optimizer_step", None) is None
                else int(getattr(args, "diagnostic_start_optimizer_step"))
            ),
            "end_optimizer_step": (
                None
                if getattr(args, "diagnostic_end_optimizer_step", None) is None
                else int(getattr(args, "diagnostic_end_optimizer_step"))
            ),
            "window_artifact_dir": diagnostic_window_artifact_dir(output_dir).as_posix(),
            "replay_bundle_path": diagnostic_replay_bundle_path(output_dir).as_posix(),
        }
    )

    status_reporter = StatusReporter(
        StatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=args.launch_metadata_path,
            talker_runtime_path=talker_runtime_path,
            train_jsonl=args.train_jsonl,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            train_row_count=train_row_count,
            eval_row_count=eval_row_count,
            gradient_accumulation_steps=gradient_accumulation_steps,
            dataloader_tuning={
                "num_workers": int(args.dataloader_num_workers),
                "pin_memory": bool(args.dataloader_pin_memory),
                "persistent_workers": bool(args.dataloader_persistent_workers),
                "prefetch_factor": int(args.dataloader_prefetch_factor),
                "non_blocking_transfer": bool(args.non_blocking_transfer),
            },
            heartbeat_policy={
                "interval_optimizer_steps": int(args.heartbeat_interval_optimizer_steps),
            },
            eval_interval_steps=int(args.eval_interval_steps),
            finite_loss_guard_config={
                "enabled": True,
                "max_consecutive_non_finite_steps": int(args.finite_loss_max_consecutive_steps),
            },
            ref_mel_cache_config={
                "enabled": bool(args.ref_mel_cache_enabled),
                "max_items": int(args.ref_mel_cache_max_items),
            },
            bundle_precomputed_reference_input=bundle_precomputed_reference_input,
            throughput_profile=throughput_policy_payload(throughput_policy),
            profiling_plan={
                "torch_profiler_enabled": bool(args.torch_profiler_enabled),
                "torch_profiler_trace_dir": args.torch_profiler_trace_dir,
                "torch_profiler_wait_steps": int(args.torch_profiler_wait_steps),
                "torch_profiler_warmup_steps": int(args.torch_profiler_warmup_steps),
                "torch_profiler_active_steps": int(args.torch_profiler_active_steps),
                "torch_profiler_repeat": int(args.torch_profiler_repeat),
            },
            checkpoint_interval_steps=int(args.checkpoint_interval_steps),
            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
            durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
            resume_from_checkpoint=args.resume_from_checkpoint,
            tracking_plan=tracking_plan,
            diagnostic=diagnostic,
        )
    )
    status_reporter.write_startup()

    try:
        if not torch.cuda.is_available():
            raise SystemExit("Trainer expected GPU-visible torch inside the container.")
        if torch.version.hip is None:
            raise SystemExit("Trainer expected ROCm-enabled torch inside the container.")
        text_embedding_mask_policy = resolve_text_embedding_mask_policy(
            getattr(args, "text_embedding_mask_policy", None),
            default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
        )
        text_embedding_assembly_mode = resolve_text_embedding_assembly_mode(
            getattr(args, "text_embedding_assembly_mode", None),
            default=DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
        )

        training_args = argparse.Namespace(
            init_model_path=str(args.model_id),
            output_model_path=(output_dir / "checkpoints").as_posix(),
            train_jsonl=args.train_jsonl.as_posix(),
            eval_jsonl=args.eval_jsonl.as_posix(),
            batch_size=int(args.batch_size),
            throughput_profile_label=str(args.throughput_profile_label),
            lr=float(args.lr),
            num_epochs=int(args.num_epochs),
            max_steps=int(args.max_steps),
            gradient_accumulation_steps=gradient_accumulation_steps,
            checkpoint_interval_steps=int(args.checkpoint_interval_steps),
            eval_interval_steps=int(args.eval_interval_steps),
            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
            durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
            dataloader_num_workers=int(args.dataloader_num_workers),
            dataloader_pin_memory=bool(args.dataloader_pin_memory),
            dataloader_persistent_workers=bool(args.dataloader_persistent_workers),
            dataloader_prefetch_factor=int(args.dataloader_prefetch_factor),
            non_blocking_transfer=bool(args.non_blocking_transfer),
            data_path_proof_mode=bool(args.data_path_proof_mode),
            heartbeat_interval_optimizer_steps=int(args.heartbeat_interval_optimizer_steps),
            finite_loss_max_consecutive_steps=int(args.finite_loss_max_consecutive_steps),
            ref_mel_cache_enabled=bool(args.ref_mel_cache_enabled),
            ref_mel_cache_max_items=int(args.ref_mel_cache_max_items),
            torch_profiler_enabled=bool(args.torch_profiler_enabled),
            torch_profiler_wait_steps=int(args.torch_profiler_wait_steps),
            torch_profiler_warmup_steps=int(args.torch_profiler_warmup_steps),
            torch_profiler_active_steps=int(args.torch_profiler_active_steps),
            torch_profiler_repeat=int(args.torch_profiler_repeat),
            torch_profiler_record_shapes=bool(args.torch_profiler_record_shapes),
            torch_profiler_profile_memory=bool(args.torch_profiler_profile_memory),
            torch_profiler_with_stack=bool(args.torch_profiler_with_stack),
            torch_profiler_trace_dir=args.torch_profiler_trace_dir,
            resume_from_checkpoint=(
                None
                if args.resume_from_checkpoint is None
                else args.resume_from_checkpoint.as_posix()
            ),
            metrics_output_json=training_summary_path.as_posix(),
            tracker_project_name=args.tracker_project_name,
            mlflow_experiment_name=args.mlflow_experiment_name,
            mlflow_tracking_uri=args.mlflow_tracking_uri,
            mlflow_artifact_root=args.mlflow_artifact_root,
            tensorboard_logging_dir=args.tensorboard_logging_dir,
            tracker_run_name=args.tracker_run_name,
            pilot_bundle_root=(
                None if args.pilot_bundle_root is None else args.pilot_bundle_root.as_posix()
            ),
            train_manifest_family=args.train_manifest_family,
            eval_manifest_family=args.eval_manifest_family,
            text_embedding_assembly_mode=text_embedding_assembly_mode,
            text_embedding_mask_policy=text_embedding_mask_policy,
            diagnostic_kind=getattr(args, "diagnostic_kind", None),
            diagnostic_source_launch_root=(
                None
                if getattr(args, "diagnostic_source_launch_root", None) is None
                else getattr(args, "diagnostic_source_launch_root").as_posix()
            ),
            diagnostic_source_checkpoint_path=(
                None
                if getattr(args, "diagnostic_source_checkpoint_path", None) is None
                else getattr(args, "diagnostic_source_checkpoint_path").as_posix()
            ),
            diagnostic_target_optimizer_step=getattr(
                args, "diagnostic_target_optimizer_step", None
            ),
            diagnostic_capture_artifact_path=(
                None
                if getattr(args, "diagnostic_capture_artifact_path", None) is None
                else getattr(args, "diagnostic_capture_artifact_path").as_posix()
            ),
            diagnostic_capture_launch_root_host_path=(
                None
                if getattr(args, "diagnostic_capture_launch_root_host_path", None) is None
                else getattr(args, "diagnostic_capture_launch_root_host_path").as_posix()
            ),
            diagnostic_capture_checkpoint_path=(
                None
                if getattr(args, "diagnostic_capture_checkpoint_path", None) is None
                else getattr(args, "diagnostic_capture_checkpoint_path").as_posix()
            ),
            diagnostic_start_optimizer_step=getattr(args, "diagnostic_start_optimizer_step", None),
            diagnostic_end_optimizer_step=getattr(args, "diagnostic_end_optimizer_step", None),
        )

        training_summary = sft_12hz.train_with_args(
            training_args,
            progress_callback=status_reporter.heartbeat,
            tracker_ready_callback=lambda tracking: status_reporter.tracking_ready(
                asdict(tracking)
            ),
            runtime_ready_callback=lambda talker_runtime: status_reporter.runtime_ready(
                dict(talker_runtime)
            ),
        )
        capture_config = diagnostic_capture_config_from_args(training_args)
        status_reporter.write_completed(training_summary)
        completed_status = load_completed_status_payload(
            status_path=status_path,
            training_summary=training_summary,
        )
        if capture_config.enabled:
            if (
                training_summary.latest_durable_checkpoint_step
                != capture_config.target_optimizer_step
            ):
                raise SystemExit(
                    "Capture run completed without minting the exact requested durable checkpoint "
                    f"(target={capture_config.target_optimizer_step}, "
                    f"actual={training_summary.latest_durable_checkpoint_step})."
                )
            write_diagnostic_capture_artifact(
                capture_config,
                final_status=completed_status,
            )

        report = build_training_report(
            model_id=str(args.model_id),
            train_jsonl=args.train_jsonl,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            train_row_count=train_row_count,
            eval_row_count=eval_row_count,
            bundle_precomputed_reference_input=bundle_precomputed_reference_input,
            throughput_profile=throughput_policy_payload(throughput_policy),
            diagnostic=diagnostic,
            training_summary=training_summary,
        )
        write_json(report_path, asdict(report))
        if diagnostic is not None:
            write_json(
                diagnostic_replay_bundle_path(output_dir),
                build_diagnostic_replay_bundle(
                    diagnostic=diagnostic,
                    report=asdict(report),
                    status=completed_status,
                ),
            )
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
        return 0
    except BaseException as exc:
        failure_path.write_text(traceback.format_exc(), encoding="utf-8")
        failed_status = status_reporter.write_failed(exc)
        failed_report = build_failed_training_report(
            model_id=str(args.model_id),
            train_jsonl=args.train_jsonl,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            train_row_count=train_row_count,
            eval_row_count=eval_row_count,
            bundle_precomputed_reference_input=bundle_precomputed_reference_input,
            throughput_profile=throughput_policy_payload(throughput_policy),
            tracking=status_reporter.tracking,
            diagnostic=diagnostic,
            failed_status=failed_status,
        )
        write_json(report_path, asdict(failed_report))
        if diagnostic is not None:
            write_json(
                diagnostic_replay_bundle_path(output_dir),
                build_diagnostic_replay_bundle(
                    diagnostic=diagnostic,
                    report=asdict(failed_report),
                    status=failed_status,
                ),
            )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
