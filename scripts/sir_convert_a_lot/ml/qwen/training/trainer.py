"""In-container training entrypoint for Qwen fine-tuning.

Purpose:
    Execute one bounded Swedish Qwen3-TTS fine-tuning run inside the training
    image, persist machine-readable status/report artifacts, and keep the
    detached outer orchestrator independent from the inner training loop.

Relationships:
    - Executed inside the shared Qwen runtime image by the host orchestrator.
    - Delegates core training to the patched `sft_12hz.py`.
    - Uses `ml.qwen.training.reporting` for live heartbeat and terminal reports.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict
from pathlib import Path

import sft_12hz
import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import load_optional_training_bundle_summary
from scripts.sir_convert_a_lot.ml.qwen.training.cli_flags import add_boolean_argument
from scripts.sir_convert_a_lot.ml.qwen.training.reporting import (
    StatusReporter,
    StatusReporterConfig,
    build_failed_training_report,
    build_training_report,
    write_json,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)


def _count_jsonl_rows(path: Path) -> int:
    """Return the number of JSONL rows in one file."""
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the in-container training entrypoint."""
    parser = argparse.ArgumentParser(description="Run the Qwen training trainer.")
    parser.add_argument("--launch-id", default=None)
    parser.add_argument("--launch-metadata-path", type=Path, default=None)
    parser.add_argument("--model-id", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument("--eval-jsonl", type=Path, required=True)
    parser.add_argument("--pilot-bundle-root", type=Path, default=None)
    parser.add_argument("--train-manifest-family", default=None)
    parser.add_argument("--eval-manifest-family", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tracker-project-name", default="qwen-training")
    parser.add_argument("--mlflow-experiment-name", default="qwen-training")
    parser.add_argument("--mlflow-tracking-uri", default=None)
    parser.add_argument("--mlflow-artifact-root", default=None)
    parser.add_argument("--tensorboard-logging-dir", default=None)
    parser.add_argument("--tracker-run-name", default=None)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument(
        "--throughput-profile-label",
        default=DEFAULT_THROUGHPUT_PROFILE_LABEL,
    )
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num-epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--checkpoint-interval-steps", type=int, default=100)
    parser.add_argument("--durable-checkpoint-retention", type=int, default=2)
    parser.add_argument("--durable-checkpoint-min-free-bytes", type=int, default=16 * 1024**3)
    parser.add_argument("--dataloader-num-workers", type=int, default=4)
    add_boolean_argument(parser, "--dataloader-pin-memory", default=True)
    add_boolean_argument(parser, "--dataloader-persistent-workers", default=True)
    parser.add_argument("--dataloader-prefetch-factor", type=int, default=4)
    add_boolean_argument(parser, "--non-blocking-transfer", default=True)
    add_boolean_argument(parser, "--data-path-proof-mode", default=False)
    parser.add_argument("--heartbeat-interval-optimizer-steps", type=int, default=20)
    parser.add_argument("--finite-loss-max-consecutive-steps", type=int, default=3)
    add_boolean_argument(parser, "--ref-mel-cache-enabled", default=True)
    parser.add_argument("--ref-mel-cache-max-items", type=int, default=2048)
    add_boolean_argument(parser, "--torch-profiler-enabled", default=False)
    parser.add_argument("--torch-profiler-wait-steps", type=int, default=1)
    parser.add_argument("--torch-profiler-warmup-steps", type=int, default=1)
    parser.add_argument("--torch-profiler-active-steps", type=int, default=4)
    parser.add_argument("--torch-profiler-repeat", type=int, default=1)
    add_boolean_argument(parser, "--torch-profiler-record-shapes", default=True)
    add_boolean_argument(parser, "--torch-profiler-profile-memory", default=True)
    add_boolean_argument(parser, "--torch-profiler-with-stack", default=False)
    parser.add_argument("--torch-profiler-trace-dir", default=None)
    parser.add_argument("--resume-from-checkpoint", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    """Run the in-container training trainer and persist report artifacts."""
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "status.json"
    report_path = output_dir / "report.json"
    failure_path = output_dir / "failure.txt"
    training_summary_path = output_dir / "training_summary.json"
    train_row_count = _count_jsonl_rows(args.train_jsonl)
    eval_row_count = _count_jsonl_rows(args.eval_jsonl)
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

    tracking_plan = {
        "tracker_backends": ["mlflow", "tensorboard"],
        "project_name": str(args.tracker_project_name),
        "run_name": str(args.tracker_run_name or output_dir.name),
        "mlflow_experiment_name": str(args.mlflow_experiment_name),
        "mlflow_tracking_uri": args.mlflow_tracking_uri,
        "mlflow_artifact_root": args.mlflow_artifact_root,
        "tensorboard_logging_dir": args.tensorboard_logging_dir,
    }

    status_reporter = StatusReporter(
        StatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=args.launch_metadata_path,
            train_jsonl=args.train_jsonl,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            train_row_count=train_row_count,
            eval_row_count=eval_row_count,
            gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
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
        )
    )
    status_reporter.write_startup()

    try:
        if not torch.cuda.is_available():
            raise SystemExit("Trainer expected GPU-visible torch inside the container.")
        if torch.version.hip is None:
            raise SystemExit("Trainer expected ROCm-enabled torch inside the container.")

        training_args = argparse.Namespace(
            init_model_path=str(args.model_id),
            output_model_path=(output_dir / "checkpoints").as_posix(),
            train_jsonl=args.train_jsonl.as_posix(),
            batch_size=int(args.batch_size),
            throughput_profile_label=str(args.throughput_profile_label),
            lr=float(args.lr),
            num_epochs=int(args.num_epochs),
            max_steps=int(args.max_steps),
            checkpoint_interval_steps=int(args.checkpoint_interval_steps),
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
        )

        training_summary = sft_12hz.train_with_args(
            training_args,
            progress_callback=status_reporter.heartbeat,
            tracker_ready_callback=lambda tracking: status_reporter.tracking_ready(
                asdict(tracking)
            ),
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
            training_summary=training_summary,
        )
        write_json(report_path, asdict(report))
        status_reporter.write_completed(training_summary)
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
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
            failed_status=failed_status,
        )
        write_json(report_path, asdict(failed_report))
        raise


if __name__ == "__main__":
    raise SystemExit(main())
