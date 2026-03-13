"""Detached in-container probe for the Task 101 Qwen pilot fine-tune lane.

Purpose:
    Execute one bounded Swedish Qwen3-TTS pilot fine-tuning run inside the
    Task 100 training image, persist machine-readable status/report artifacts,
    and keep the detached outer Hemma runner independent from the inner
    training loop.

Relationships:
    - Executed inside the shared Qwen runtime image by the detached Task 101
      Hemma runner.
    - Reuses the patched `sft_12hz.py` training entrypoint from
      `scripts/devops/qwen_finetuning_patches/`.
    - Reuses `task101_qwen_pilot_probe_reporting.py` for report/status payload
      assembly and deterministic JSON artifact writing.
"""

from __future__ import annotations

import argparse
import json
import traceback
from dataclasses import asdict
from pathlib import Path

import sft_12hz
import torch

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_probe_reporting import (
    _build_probe_report,
    _count_jsonl_rows,
    _write_json,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_status_reporter import (
    Task101PilotStatusReporter,
    Task101PilotStatusReporterConfig,
)


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the detached Task 101 training probe."""
    parser = argparse.ArgumentParser(description="Run the detached Task 101 Qwen pilot probe.")
    parser.add_argument("--launch-id", default=None)
    parser.add_argument("--launch-metadata-path", type=Path, default=None)
    parser.add_argument("--model-id", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument("--eval-jsonl", type=Path, required=True)
    parser.add_argument("--pilot-bundle-root", type=Path, default=None)
    parser.add_argument("--train-manifest-family", default=None)
    parser.add_argument("--eval-manifest-family", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tracker-project-name", default=None)
    parser.add_argument("--mlflow-experiment-name", default=None)
    parser.add_argument("--mlflow-tracking-uri", default=None)
    parser.add_argument("--mlflow-artifact-root", default=None)
    parser.add_argument("--tensorboard-logging-dir", default=None)
    parser.add_argument("--tracker-run-name", default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num-epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--checkpoint-interval-steps", type=int, default=2)
    parser.add_argument("--durable-checkpoint-retention", type=int, default=2)
    parser.add_argument("--durable-checkpoint-min-free-bytes", type=int, default=16 * 1024**3)
    parser.add_argument("--resume-from-checkpoint", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    """Run the detached Task 101 pilot probe and persist report artifacts."""
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "status.json"
    report_path = output_dir / "report.json"
    failure_path = output_dir / "failure.txt"
    training_summary_path = output_dir / "training_summary.json"
    train_row_count = _count_jsonl_rows(args.train_jsonl)
    eval_row_count = _count_jsonl_rows(args.eval_jsonl)
    tracking_plan = {
        "tracker_backends": ["mlflow", "tensorboard"],
        "project_name": None
        if args.tracker_project_name is None
        else str(args.tracker_project_name),
        "run_name": str(args.tracker_run_name or output_dir.name),
        "mlflow_experiment_name": None
        if args.mlflow_experiment_name is None
        else str(args.mlflow_experiment_name),
        "mlflow_tracking_uri": None
        if args.mlflow_tracking_uri is None
        else str(args.mlflow_tracking_uri),
        "mlflow_artifact_root": None
        if args.mlflow_artifact_root is None
        else str(args.mlflow_artifact_root),
        "tensorboard_logging_dir": None
        if args.tensorboard_logging_dir is None
        else str(args.tensorboard_logging_dir),
    }
    status_reporter = Task101PilotStatusReporter(
        Task101PilotStatusReporterConfig(
            status_path=status_path,
            launch_metadata_path=args.launch_metadata_path,
            train_jsonl=args.train_jsonl,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            train_row_count=train_row_count,
            eval_row_count=eval_row_count,
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
            raise SystemExit(
                "Task 101 pilot probe expected GPU-visible torch inside the container."
            )
        if torch.version.hip is None:
            raise SystemExit(
                "Task 101 pilot probe expected ROCm-enabled torch inside the container."
            )
        training_args = argparse.Namespace(
            init_model_path=str(args.model_id),
            output_model_path=(output_dir / "checkpoints").as_posix(),
            train_jsonl=args.train_jsonl.as_posix(),
            batch_size=int(args.batch_size),
            lr=float(args.lr),
            num_epochs=int(args.num_epochs),
            max_steps=int(args.max_steps),
            checkpoint_interval_steps=int(args.checkpoint_interval_steps),
            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
            durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
            resume_from_checkpoint=(
                None
                if args.resume_from_checkpoint is None
                else args.resume_from_checkpoint.as_posix()
            ),
            metrics_output_json=training_summary_path.as_posix(),
            tracker_project_name=(
                None if args.tracker_project_name is None else str(args.tracker_project_name)
            ),
            mlflow_experiment_name=(
                None if args.mlflow_experiment_name is None else str(args.mlflow_experiment_name)
            ),
            mlflow_tracking_uri=(
                None if args.mlflow_tracking_uri is None else str(args.mlflow_tracking_uri)
            ),
            mlflow_artifact_root=(
                None if args.mlflow_artifact_root is None else str(args.mlflow_artifact_root)
            ),
            tensorboard_logging_dir=(
                None if args.tensorboard_logging_dir is None else str(args.tensorboard_logging_dir)
            ),
            tracker_run_name=(
                None if args.tracker_run_name is None else str(args.tracker_run_name)
            ),
            pilot_bundle_root=(
                None if args.pilot_bundle_root is None else args.pilot_bundle_root.as_posix()
            ),
            train_manifest_family=(
                None if args.train_manifest_family is None else str(args.train_manifest_family)
            ),
            eval_manifest_family=(
                None if args.eval_manifest_family is None else str(args.eval_manifest_family)
            ),
            speaker_name="pilot_multi_speaker",
        )
        training_summary = sft_12hz.train_with_args(
            training_args,
            progress_callback=status_reporter.heartbeat,
            tracker_ready_callback=lambda tracking: status_reporter.tracking_ready(
                asdict(tracking)
            ),
        )
        report = _build_probe_report(
            model_id=str(args.model_id),
            train_jsonl=args.train_jsonl,
            eval_jsonl=args.eval_jsonl,
            output_dir=output_dir,
            train_row_count=train_row_count,
            eval_row_count=eval_row_count,
            training_summary=training_summary,
        )
        _write_json(report_path, asdict(report))
        status_reporter.write_completed(training_summary)
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure_path.write_text(traceback.format_exc(), encoding="utf-8")
        status_reporter.write_failed(exc)
        raise


if __name__ == "__main__":
    raise SystemExit(main())
