"""CLI and scalar-config helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Keep argparse and tracker-config payload shaping out of `sft_12hz.py` so
    the trainer facade can stay thin and SRP-aligned.

Relationships:
    - Imported by `sft_12hz.py` for the public CLI entrypoint.
    - Imported by the extracted training modules for consistent bool parsing
      and tracker-config payloads.
"""

from __future__ import annotations

import argparse

from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    DEFAULT_DURABLE_CHECKPOINT_RETENTION,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_NON_BLOCKING_TRANSFER,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_eval import (
    DEFAULT_EVAL_INTERVAL_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import (
    DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_profiling import (
    DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    DEFAULT_TORCH_PROFILER_ENABLED,
    DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    DEFAULT_TORCH_PROFILER_REPEAT,
    DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    DEFAULT_TORCH_PROFILER_WITH_STACK,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_mel_cache import (
    DEFAULT_REF_MEL_CACHE_ENABLED,
    DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import (
    DEFAULT_MLFLOW_EXPERIMENT_NAME,
    DEFAULT_TRACKER_PROJECT_NAME,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    resolve_throughput_batch_policy,
)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the patched Qwen trainer."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--init_model_path", type=str, default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--output_model_path", type=str, default="output")
    parser.add_argument("--train_jsonl", type=str, required=True)
    parser.add_argument("--eval_jsonl", type=str, required=True)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument(
        "--throughput_profile_label",
        type=str,
        default=DEFAULT_THROUGHPUT_PROFILE_LABEL,
    )
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num_epochs", type=int, default=3)
    parser.add_argument("--max_steps", type=int, default=None)
    parser.add_argument("--checkpoint_interval_steps", type=int, default=500)
    parser.add_argument("--eval_interval_steps", type=int, default=DEFAULT_EVAL_INTERVAL_STEPS)
    parser.add_argument(
        "--durable-checkpoint-retention",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    )
    parser.add_argument(
        "--durable-checkpoint-min-free-bytes",
        type=int,
        default=DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    )
    parser.add_argument("--resume_from_checkpoint", type=str, default=None)
    parser.add_argument(
        "--dataloader_num_workers",
        type=int,
        default=DEFAULT_DATALOADER_NUM_WORKERS,
    )
    _add_boolean_argument(
        parser,
        "--dataloader_pin_memory",
        default=DEFAULT_DATALOADER_PIN_MEMORY,
    )
    _add_boolean_argument(
        parser,
        "--dataloader_persistent_workers",
        default=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    )
    parser.add_argument(
        "--dataloader_prefetch_factor",
        type=int,
        default=DEFAULT_DATALOADER_PREFETCH_FACTOR,
    )
    _add_boolean_argument(
        parser,
        "--non_blocking_transfer",
        default=DEFAULT_NON_BLOCKING_TRANSFER,
    )
    _add_boolean_argument(
        parser,
        "--data_path_proof_mode",
        default=False,
    )
    parser.add_argument(
        "--heartbeat_interval_optimizer_steps",
        type=int,
        default=DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    )
    parser.add_argument(
        "--finite_loss_max_consecutive_steps",
        type=int,
        default=DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    )
    _add_boolean_argument(
        parser,
        "--ref_mel_cache_enabled",
        default=DEFAULT_REF_MEL_CACHE_ENABLED,
    )
    parser.add_argument(
        "--ref_mel_cache_max_items",
        type=int,
        default=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    )
    _add_boolean_argument(
        parser,
        "--torch_profiler_enabled",
        default=DEFAULT_TORCH_PROFILER_ENABLED,
    )
    parser.add_argument(
        "--torch_profiler_wait_steps",
        type=int,
        default=DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    )
    parser.add_argument(
        "--torch_profiler_warmup_steps",
        type=int,
        default=DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    )
    parser.add_argument(
        "--torch_profiler_active_steps",
        type=int,
        default=DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    )
    parser.add_argument(
        "--torch_profiler_repeat",
        type=int,
        default=DEFAULT_TORCH_PROFILER_REPEAT,
    )
    _add_boolean_argument(
        parser,
        "--torch_profiler_record_shapes",
        default=DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    )
    _add_boolean_argument(
        parser,
        "--torch_profiler_profile_memory",
        default=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    )
    _add_boolean_argument(
        parser,
        "--torch_profiler_with_stack",
        default=DEFAULT_TORCH_PROFILER_WITH_STACK,
    )
    parser.add_argument("--torch_profiler_trace_dir", type=str, default=None)
    parser.add_argument("--metrics_output_json", type=str, default=None)
    parser.add_argument(
        "--tracker_project_name",
        type=str,
        default=DEFAULT_TRACKER_PROJECT_NAME,
    )
    parser.add_argument(
        "--mlflow_experiment_name",
        type=str,
        default=DEFAULT_MLFLOW_EXPERIMENT_NAME,
    )
    parser.add_argument("--mlflow_tracking_uri", type=str, default=None)
    parser.add_argument("--mlflow_artifact_root", type=str, default=None)
    parser.add_argument("--tensorboard_logging_dir", type=str, default=None)
    parser.add_argument("--tracker_run_name", type=str, default=None)
    parser.add_argument("--pilot_bundle_root", type=str, default=None)
    parser.add_argument("--train_manifest_family", type=str, default=None)
    parser.add_argument("--eval_manifest_family", type=str, default=None)
    return parser.parse_args()


def _add_boolean_argument(
    parser: argparse.ArgumentParser,
    flag: str,
    *,
    default: bool,
) -> None:
    """Register one canonical boolean CLI option for the patched trainer."""
    parser.add_argument(
        flag,
        action=argparse.BooleanOptionalAction,
        default=default,
    )


def tracker_config_payload(
    args: argparse.Namespace,
) -> dict[str, bool | float | int | str | None]:
    """Build the canonical scalar tracker configuration for one training run."""
    tracker_project_name = getattr(args, "tracker_project_name", None)
    tracker_run_name = getattr(args, "tracker_run_name", None)
    mlflow_experiment_name = getattr(args, "mlflow_experiment_name", None)
    pilot_bundle_root = getattr(args, "pilot_bundle_root", None)
    train_manifest_family = getattr(args, "train_manifest_family", None)
    eval_manifest_family = getattr(args, "eval_manifest_family", None)
    dataloader_num_workers = int(
        getattr(args, "dataloader_num_workers", DEFAULT_DATALOADER_NUM_WORKERS)
    )
    dataloader_pin_memory = bool(
        getattr(args, "dataloader_pin_memory", DEFAULT_DATALOADER_PIN_MEMORY)
    )
    dataloader_persistent_workers = bool(
        getattr(args, "dataloader_persistent_workers", DEFAULT_DATALOADER_PERSISTENT_WORKERS)
    )
    dataloader_prefetch_factor = int(
        getattr(args, "dataloader_prefetch_factor", DEFAULT_DATALOADER_PREFETCH_FACTOR)
    )
    non_blocking_transfer = bool(
        getattr(args, "non_blocking_transfer", DEFAULT_NON_BLOCKING_TRANSFER)
    )
    ref_mel_cache_enabled = bool(
        getattr(args, "ref_mel_cache_enabled", DEFAULT_REF_MEL_CACHE_ENABLED)
    )
    ref_mel_cache_max_items = int(
        getattr(args, "ref_mel_cache_max_items", DEFAULT_REF_MEL_CACHE_MAX_ITEMS)
    )
    throughput_policy = resolve_throughput_batch_policy(
        profile_label=str(
            getattr(args, "throughput_profile_label", DEFAULT_THROUGHPUT_PROFILE_LABEL)
        ),
        max_batch_size=int(args.batch_size),
    )
    return {
        "model_id": str(args.init_model_path),
        "tracker_project_name": None if tracker_project_name is None else str(tracker_project_name),
        "tracker_run_name": None if tracker_run_name is None else str(tracker_run_name),
        "mlflow_experiment_name": (
            None if mlflow_experiment_name is None else str(mlflow_experiment_name)
        ),
        "pilot_bundle_root": None if pilot_bundle_root is None else str(pilot_bundle_root),
        "train_manifest_family": (
            None if train_manifest_family is None else str(train_manifest_family)
        ),
        "eval_manifest_family": None if eval_manifest_family is None else str(eval_manifest_family),
        "train_jsonl": str(args.train_jsonl),
        "eval_jsonl": str(args.eval_jsonl),
        "batch_size": int(args.batch_size),
        "throughput_profile_label": throughput_policy.profile_label,
        "throughput_policy_kind": throughput_policy.policy_kind,
        "throughput_max_batch_size": throughput_policy.max_batch_size,
        "throughput_max_tokens_per_batch": throughput_policy.max_tokens_per_batch,
        "throughput_max_codec_frames_per_batch": throughput_policy.max_codec_frames_per_batch,
        "throughput_length_bucket_boundaries": ",".join(
            str(boundary) for boundary in throughput_policy.length_bucket_boundaries
        ),
        "learning_rate": float(args.lr),
        "num_epochs": int(args.num_epochs),
        "max_steps": None if args.max_steps is None else int(args.max_steps),
        "gradient_accumulation_steps": GRADIENT_ACCUMULATION_STEPS,
        "checkpoint_interval_steps": int(args.checkpoint_interval_steps),
        "eval_interval_steps": int(
            getattr(args, "eval_interval_steps", DEFAULT_EVAL_INTERVAL_STEPS)
        ),
        "durable_checkpoint_retention": int(args.durable_checkpoint_retention),
        "durable_checkpoint_min_free_bytes": int(args.durable_checkpoint_min_free_bytes),
        "dataloader_num_workers": dataloader_num_workers,
        "dataloader_pin_memory": dataloader_pin_memory,
        "dataloader_persistent_workers": dataloader_persistent_workers,
        "dataloader_prefetch_factor": dataloader_prefetch_factor,
        "non_blocking_transfer": non_blocking_transfer,
        "heartbeat_interval_optimizer_steps": int(
            getattr(
                args,
                "heartbeat_interval_optimizer_steps",
                DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
            )
        ),
        "finite_loss_max_consecutive_steps": int(
            getattr(
                args,
                "finite_loss_max_consecutive_steps",
                DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
            )
        ),
        "ref_mel_cache_enabled": ref_mel_cache_enabled,
        "ref_mel_cache_max_items": ref_mel_cache_max_items,
        "torch_profiler_enabled": bool(
            getattr(args, "torch_profiler_enabled", DEFAULT_TORCH_PROFILER_ENABLED)
        ),
        "torch_profiler_wait_steps": int(
            getattr(args, "torch_profiler_wait_steps", DEFAULT_TORCH_PROFILER_WAIT_STEPS)
        ),
        "torch_profiler_warmup_steps": int(
            getattr(args, "torch_profiler_warmup_steps", DEFAULT_TORCH_PROFILER_WARMUP_STEPS)
        ),
        "torch_profiler_active_steps": int(
            getattr(args, "torch_profiler_active_steps", DEFAULT_TORCH_PROFILER_ACTIVE_STEPS)
        ),
        "torch_profiler_repeat": int(
            getattr(args, "torch_profiler_repeat", DEFAULT_TORCH_PROFILER_REPEAT)
        ),
        "torch_profiler_record_shapes": bool(
            getattr(args, "torch_profiler_record_shapes", DEFAULT_TORCH_PROFILER_RECORD_SHAPES)
        ),
        "torch_profiler_profile_memory": bool(
            getattr(args, "torch_profiler_profile_memory", DEFAULT_TORCH_PROFILER_PROFILE_MEMORY)
        ),
        "torch_profiler_with_stack": bool(
            getattr(args, "torch_profiler_with_stack", DEFAULT_TORCH_PROFILER_WITH_STACK)
        ),
        "torch_profiler_trace_dir": (
            None
            if getattr(args, "torch_profiler_trace_dir", None) in (None, "")
            else str(getattr(args, "torch_profiler_trace_dir"))
        ),
        "resumed_from_checkpoint": args.resume_from_checkpoint is not None,
    }
