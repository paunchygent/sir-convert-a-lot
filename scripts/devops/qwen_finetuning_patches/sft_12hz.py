# coding=utf-8
# Copyright 2026 The Alibaba Qwen team.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Patched Qwen `sft_12hz.py` entrypoint for Swedish multi-speaker training.

This module keeps the upstream Qwen training loop shape but preserves the
speaker encoder, keeps exported checkpoints in base-model form, and applies the
text-projection fix needed by the repo's planned Swedish language-expansion
lane. It is paired with the speaker-aware `dataset.py` patch in the same
directory and is intended for the Task 100 runtime rather than the serving
sidecar lane.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import sft_12hz_checkpointing as checkpointing
import torch
from accelerate import Accelerator
from dataset import TTSDataset
from huggingface_hub import hf_hub_download, snapshot_download
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel
from safetensors.torch import save_file
from sft_12hz_checkpointing import DurableCheckpointMetadata
from sft_12hz_dataloader import (
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_NON_BLOCKING_TRANSFER,
    dataloader_kwargs,
    dataloader_tuning_payload,
    resolve_dataloader_tuning,
    to_device_with_optional_non_blocking,
)
from sft_12hz_profiling import (
    DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    DEFAULT_TORCH_PROFILER_ENABLED,
    DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    DEFAULT_TORCH_PROFILER_REPEAT,
    DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    DEFAULT_TORCH_PROFILER_WITH_STACK,
    TorchProfilerSession,
    resolve_torch_profiler_config,
)
from sft_12hz_progress import (
    TrainingProgressHeartbeat,
    build_training_progress_heartbeat,
)
from sft_12hz_ref_mel_cache import (
    DEFAULT_REF_MEL_CACHE_ENABLED,
    DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    RefMelCache,
)
from sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from sft_12hz_tracking import (
    DEFAULT_MLFLOW_EXPERIMENT_NAME,
    DEFAULT_TRACKER_PROJECT_NAME,
    TrainingTrackerSummary,
    build_training_tracker_config,
    initialize_training_trackers,
    log_training_metrics,
    refresh_training_tracker_summary,
    update_smoothed_loss,
)
from sft_12hz_training_rows import _load_training_rows
from torch.optim import AdamW
from torch.utils.data import DataLoader
from training_stop import TrainingStopState, install_training_stop_handlers
from transformers import AutoConfig

EXPORT_METADATA_PATTERNS = (
    "*.json",
    "*.model",
    "*.py",
    "*.tiktoken",
    "*.txt",
)
DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES = checkpointing.DEFAULT_DURABLE_CHECKPOINT_ESTIMATE_BYTES
DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES = checkpointing.DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES
DEFAULT_DURABLE_CHECKPOINT_RETENTION = checkpointing.DEFAULT_DURABLE_CHECKPOINT_RETENTION
_checkpoint_advanced_since_latest_save = checkpointing._checkpoint_advanced_since_latest_save
_checkpoint_resume_cursor = checkpointing._checkpoint_resume_cursor
_current_durable_checkpoint_paths = checkpointing._current_durable_checkpoint_paths
_durable_checkpoint_staging_dir = checkpointing._durable_checkpoint_staging_dir
_load_durable_checkpoint_metadata = checkpointing._load_durable_checkpoint_metadata
_save_durable_checkpoint = checkpointing._save_durable_checkpoint
_validate_saved_durable_checkpoint = checkpointing._validate_saved_durable_checkpoint


@dataclass(frozen=True)
class TrainingSummary:
    """Machine-readable summary for one bounded Qwen fine-tuning run."""

    init_model_path: str
    output_model_path: str
    train_jsonl: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int | None
    checkpoint_interval_steps: int
    durable_checkpoint_retention: int
    durable_checkpoint_min_free_bytes: int
    gradient_accumulation_steps: int
    optimizer_steps_completed: int
    train_iterations_completed: int
    last_loss: float | None
    smoothed_loss: float | None
    peak_memory_allocated_bytes: int | None
    peak_memory_reserved_bytes: int | None
    resumed_from_checkpoint_path: str | None
    latest_durable_checkpoint_path: str | None
    latest_durable_checkpoint_step: int | None
    latest_durable_checkpoint_epoch: int | None
    durable_checkpoint_paths: list[str]
    checkpoint_paths: list[str]
    stop_requested: bool
    stop_signal: str | None
    stopped_early: bool
    dataloader_tuning: dict[str, object]
    ref_mel_cache: dict[str, bool | float | int | None]
    profiling: dict[str, object] | None
    tracking: TrainingTrackerSummary | None = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init_model_path", type=str, default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--output_model_path", type=str, default="output")
    parser.add_argument("--train_jsonl", type=str, required=True)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num_epochs", type=int, default=3)
    parser.add_argument("--max_steps", type=int, default=None)
    parser.add_argument("--checkpoint_interval_steps", type=int, default=100)
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
    parser.add_argument(
        "--dataloader_pin_memory",
        choices=("true", "false"),
        default="true" if DEFAULT_DATALOADER_PIN_MEMORY else "false",
    )
    parser.add_argument(
        "--dataloader_persistent_workers",
        choices=("true", "false"),
        default="true" if DEFAULT_DATALOADER_PERSISTENT_WORKERS else "false",
    )
    parser.add_argument(
        "--dataloader_prefetch_factor",
        type=int,
        default=DEFAULT_DATALOADER_PREFETCH_FACTOR,
    )
    parser.add_argument(
        "--non_blocking_transfer",
        choices=("true", "false"),
        default="true" if DEFAULT_NON_BLOCKING_TRANSFER else "false",
    )
    parser.add_argument(
        "--ref_mel_cache_enabled",
        choices=("true", "false"),
        default="true" if DEFAULT_REF_MEL_CACHE_ENABLED else "false",
    )
    parser.add_argument(
        "--ref_mel_cache_max_items",
        type=int,
        default=DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    )
    parser.add_argument(
        "--torch_profiler_enabled",
        choices=("true", "false"),
        default="true" if DEFAULT_TORCH_PROFILER_ENABLED else "false",
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
    parser.add_argument(
        "--torch_profiler_record_shapes",
        choices=("true", "false"),
        default="true" if DEFAULT_TORCH_PROFILER_RECORD_SHAPES else "false",
    )
    parser.add_argument(
        "--torch_profiler_profile_memory",
        choices=("true", "false"),
        default="true" if DEFAULT_TORCH_PROFILER_PROFILE_MEMORY else "false",
    )
    parser.add_argument(
        "--torch_profiler_with_stack",
        choices=("true", "false"),
        default="true" if DEFAULT_TORCH_PROFILER_WITH_STACK else "false",
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
    parser.add_argument(
        "--speaker_name",
        type=str,
        default="speaker_test",
        help=(
            "Compatibility-only argument kept for existing runner surfaces. "
            "The multi-speaker patch set does not use it."
        ),
    )
    return parser.parse_args()


def _load_config_dict(model_path: str) -> dict[str, object]:
    config_path = _resolve_model_config_path(model_path)
    with config_path.open("r", encoding="utf-8") as handle:
        config_dict_raw = json.load(handle)
    if not isinstance(config_dict_raw, dict):
        raise ValueError("Expected config.json to contain a JSON object.")
    return {str(key): value for key, value in config_dict_raw.items()}


def _resolve_model_config_path(model_path: str) -> Path:
    local_model_path = Path(model_path)
    if local_model_path.is_dir():
        return local_model_path / "config.json"

    return Path(hf_hub_download(repo_id=model_path, filename="config.json"))


def _resolve_model_export_source_path(model_path: str) -> Path:
    local_model_path = Path(model_path)
    if local_model_path.is_dir():
        return local_model_path

    snapshot_path = snapshot_download(
        repo_id=model_path,
        allow_patterns=list(EXPORT_METADATA_PATTERNS),
    )
    return Path(snapshot_path)


def _save_checkpoint(
    *,
    accelerator: Accelerator,
    model: torch.nn.Module,
    model_path: str,
    output_dir: Path,
) -> str:
    """Export one checkpoint directory from the current training state."""
    resolved_model_path = _resolve_model_export_source_path(model_path)
    shutil.copytree(resolved_model_path, output_dir, dirs_exist_ok=True)

    config_dict = _load_config_dict(model_path)
    config_dict["tts_model_type"] = "base"

    output_config_path = output_dir / "config.json"
    with output_config_path.open("w", encoding="utf-8") as handle:
        json.dump(config_dict, handle, indent=2, ensure_ascii=False)

    unwrapped_model = accelerator.unwrap_model(model)
    state_dict = {
        key: value.detach().to("cpu") for key, value in unwrapped_model.state_dict().items()
    }
    save_file(state_dict, (output_dir / "model.safetensors").as_posix())
    return output_dir.as_posix()


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _tracker_config_payload(args: argparse.Namespace) -> dict[str, bool | float | int | str | None]:
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
    dataloader_pin_memory = _namespace_bool_arg(
        args,
        "dataloader_pin_memory",
        default=DEFAULT_DATALOADER_PIN_MEMORY,
    )
    dataloader_persistent_workers = _namespace_bool_arg(
        args,
        "dataloader_persistent_workers",
        default=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    )
    dataloader_prefetch_factor = int(
        getattr(args, "dataloader_prefetch_factor", DEFAULT_DATALOADER_PREFETCH_FACTOR)
    )
    non_blocking_transfer = _namespace_bool_arg(
        args,
        "non_blocking_transfer",
        default=DEFAULT_NON_BLOCKING_TRANSFER,
    )
    ref_mel_cache_enabled = _namespace_bool_arg(
        args,
        "ref_mel_cache_enabled",
        default=DEFAULT_REF_MEL_CACHE_ENABLED,
    )
    ref_mel_cache_max_items = int(
        getattr(args, "ref_mel_cache_max_items", DEFAULT_REF_MEL_CACHE_MAX_ITEMS)
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
        "batch_size": int(args.batch_size),
        "learning_rate": float(args.lr),
        "num_epochs": int(args.num_epochs),
        "max_steps": None if args.max_steps is None else int(args.max_steps),
        "gradient_accumulation_steps": GRADIENT_ACCUMULATION_STEPS,
        "checkpoint_interval_steps": int(args.checkpoint_interval_steps),
        "durable_checkpoint_retention": int(args.durable_checkpoint_retention),
        "durable_checkpoint_min_free_bytes": int(args.durable_checkpoint_min_free_bytes),
        "dataloader_num_workers": dataloader_num_workers,
        "dataloader_pin_memory": dataloader_pin_memory,
        "dataloader_persistent_workers": dataloader_persistent_workers,
        "dataloader_prefetch_factor": dataloader_prefetch_factor,
        "non_blocking_transfer": non_blocking_transfer,
        "ref_mel_cache_enabled": ref_mel_cache_enabled,
        "ref_mel_cache_max_items": ref_mel_cache_max_items,
        "torch_profiler_enabled": _namespace_bool_arg(
            args,
            "torch_profiler_enabled",
            default=DEFAULT_TORCH_PROFILER_ENABLED,
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
        "torch_profiler_record_shapes": _namespace_bool_arg(
            args,
            "torch_profiler_record_shapes",
            default=DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
        ),
        "torch_profiler_profile_memory": _namespace_bool_arg(
            args,
            "torch_profiler_profile_memory",
            default=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
        ),
        "torch_profiler_with_stack": _namespace_bool_arg(
            args,
            "torch_profiler_with_stack",
            default=DEFAULT_TORCH_PROFILER_WITH_STACK,
        ),
        "torch_profiler_trace_dir": (
            None
            if getattr(args, "torch_profiler_trace_dir", None) in (None, "")
            else str(getattr(args, "torch_profiler_trace_dir"))
        ),
        "resumed_from_checkpoint": args.resume_from_checkpoint is not None,
    }


def _namespace_bool_arg(args: argparse.Namespace, name: str, *, default: bool) -> bool:
    """Resolve one bool-like argparse namespace field with compatibility fallbacks."""
    raw_value = getattr(args, name, default)
    if isinstance(raw_value, bool):
        return raw_value
    return str(raw_value).lower() == "true"


def train_with_args(
    args: argparse.Namespace,
    *,
    progress_callback: Callable[[TrainingProgressHeartbeat], None] | None = None,
    tracker_ready_callback: Callable[[TrainingTrackerSummary], None] | None = None,
) -> TrainingSummary:
    """Run one bounded Qwen fine-tuning job and return machine-readable metrics."""
    if args.max_steps is not None and args.max_steps <= 0:
        raise ValueError("`--max_steps` must be positive when provided.")
    if int(args.checkpoint_interval_steps) <= 0:
        raise ValueError("`--checkpoint_interval_steps` must be positive.")
    if int(args.durable_checkpoint_retention) <= 0:
        raise ValueError("`--durable-checkpoint-retention` must be positive.")
    if int(args.durable_checkpoint_min_free_bytes) <= 0:
        raise ValueError("`--durable-checkpoint-min-free-bytes` must be positive.")
    dataloader_num_workers = int(
        getattr(args, "dataloader_num_workers", DEFAULT_DATALOADER_NUM_WORKERS)
    )
    dataloader_pin_memory = _namespace_bool_arg(
        args,
        "dataloader_pin_memory",
        default=DEFAULT_DATALOADER_PIN_MEMORY,
    )
    dataloader_persistent_workers = _namespace_bool_arg(
        args,
        "dataloader_persistent_workers",
        default=DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    )
    dataloader_prefetch_factor = int(
        getattr(args, "dataloader_prefetch_factor", DEFAULT_DATALOADER_PREFETCH_FACTOR)
    )
    non_blocking_transfer = _namespace_bool_arg(
        args,
        "non_blocking_transfer",
        default=DEFAULT_NON_BLOCKING_TRANSFER,
    )
    ref_mel_cache_enabled = _namespace_bool_arg(
        args,
        "ref_mel_cache_enabled",
        default=DEFAULT_REF_MEL_CACHE_ENABLED,
    )
    ref_mel_cache_max_items = int(
        getattr(args, "ref_mel_cache_max_items", DEFAULT_REF_MEL_CACHE_MAX_ITEMS)
    )
    if ref_mel_cache_max_items <= 0:
        raise ValueError("`--ref_mel_cache_max_items` must be positive.")
    effective_dataloader_tuning = resolve_dataloader_tuning(
        num_workers=dataloader_num_workers,
        pin_memory=dataloader_pin_memory,
        persistent_workers=dataloader_persistent_workers,
        prefetch_factor=dataloader_prefetch_factor,
        non_blocking_transfer=non_blocking_transfer,
    )
    ref_mel_cache = RefMelCache(
        enabled=ref_mel_cache_enabled,
        max_items=ref_mel_cache_max_items,
    )

    output_model_path = Path(args.output_model_path)
    torch_profiler_enabled = _namespace_bool_arg(
        args,
        "torch_profiler_enabled",
        default=DEFAULT_TORCH_PROFILER_ENABLED,
    )
    torch_profiler_wait_steps = int(
        getattr(args, "torch_profiler_wait_steps", DEFAULT_TORCH_PROFILER_WAIT_STEPS)
    )
    torch_profiler_warmup_steps = int(
        getattr(args, "torch_profiler_warmup_steps", DEFAULT_TORCH_PROFILER_WARMUP_STEPS)
    )
    torch_profiler_active_steps = int(
        getattr(args, "torch_profiler_active_steps", DEFAULT_TORCH_PROFILER_ACTIVE_STEPS)
    )
    torch_profiler_repeat = int(
        getattr(args, "torch_profiler_repeat", DEFAULT_TORCH_PROFILER_REPEAT)
    )
    torch_profiler_record_shapes = _namespace_bool_arg(
        args,
        "torch_profiler_record_shapes",
        default=DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    )
    torch_profiler_profile_memory = _namespace_bool_arg(
        args,
        "torch_profiler_profile_memory",
        default=DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    )
    torch_profiler_with_stack = _namespace_bool_arg(
        args,
        "torch_profiler_with_stack",
        default=DEFAULT_TORCH_PROFILER_WITH_STACK,
    )
    torch_profiler_trace_dir_raw = getattr(args, "torch_profiler_trace_dir", None)
    torch_profiler_trace_dir = (
        output_model_path.parent / "profiling" / "pytorch"
        if torch_profiler_trace_dir_raw in (None, "")
        else Path(str(torch_profiler_trace_dir_raw))
    )
    torch_profiler_config = resolve_torch_profiler_config(
        enabled=torch_profiler_enabled,
        trace_dir=torch_profiler_trace_dir,
        wait_steps=torch_profiler_wait_steps,
        warmup_steps=torch_profiler_warmup_steps,
        active_steps=torch_profiler_active_steps,
        repeat=torch_profiler_repeat,
        record_shapes=torch_profiler_record_shapes,
        profile_memory=torch_profiler_profile_memory,
        with_stack=torch_profiler_with_stack,
    )
    torch_profiler_session = TorchProfilerSession(torch_profiler_config)
    tracker_run_name = getattr(args, "tracker_run_name", None)
    tracker_project_name = getattr(args, "tracker_project_name", None)
    mlflow_experiment_name = getattr(args, "mlflow_experiment_name", None)
    mlflow_tracking_uri = getattr(args, "mlflow_tracking_uri", None)
    mlflow_artifact_root = getattr(args, "mlflow_artifact_root", None)
    tensorboard_logging_dir = getattr(args, "tensorboard_logging_dir", None)
    tracker_config = build_training_tracker_config(
        output_model_path=output_model_path,
        tracker_run_name=None if tracker_run_name in (None, "") else str(tracker_run_name),
        tracker_project_name=(
            None if tracker_project_name in (None, "") else str(tracker_project_name)
        ),
        mlflow_experiment_name=(
            None if mlflow_experiment_name in (None, "") else str(mlflow_experiment_name)
        ),
        mlflow_tracking_uri=(
            None if mlflow_tracking_uri in (None, "") else str(mlflow_tracking_uri)
        ),
        mlflow_artifact_root=(
            None if mlflow_artifact_root in (None, "") else str(mlflow_artifact_root)
        ),
        tensorboard_logging_dir=(
            None if tensorboard_logging_dir in (None, "") else str(tensorboard_logging_dir)
        ),
    )
    accelerator = Accelerator(
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        mixed_precision="bf16",
        log_with=list(tracker_config.tracker_backends),
        project_dir=tracker_config.tensorboard_logging_dir,
    )

    model_path = args.init_model_path
    qwen3tts = Qwen3TTSModel.from_pretrained(
        model_path,
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    config = AutoConfig.from_pretrained(model_path)

    train_data = _load_training_rows(Path(args.train_jsonl))
    dataset = TTSDataset(
        train_data,
        qwen3tts.processor,
        config,
        ref_mel_cache=ref_mel_cache,
    )
    train_dataloader = DataLoader(
        dataset,
        **dataloader_kwargs(
            tuning=effective_dataloader_tuning,
            batch_size=args.batch_size,
            collate_fn=dataset.collate_fn,
        ),
    )
    optimizer = AdamW(qwen3tts.model.parameters(), lr=args.lr, weight_decay=0.01)

    model, optimizer, train_dataloader = accelerator.prepare(
        qwen3tts.model,
        optimizer,
        train_dataloader,
    )

    dataloader_length = len(train_dataloader)
    durable_checkpoint_paths: list[str] = []
    latest_durable_checkpoint: DurableCheckpointMetadata | None = None
    resumed_from_checkpoint_path: str | None = None
    starting_epoch = 0
    resume_step_in_epoch = 0
    model.train()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    optimizer_steps_completed = 0
    train_iterations_completed = 0
    last_loss: float | None = None
    smoothed_loss: float | None = None
    checkpoint_paths: list[str] = []
    stop_state = TrainingStopState()
    install_training_stop_handlers(stop_state)
    trackers_initialized = False
    tracker_summary = initialize_training_trackers(
        accelerator,
        tracker_config=tracker_config,
        config=_tracker_config_payload(args),
        tags={
            "task": "task-101",
            "story": "story-26",
            "lane": "qwen-finetune",
            "run_name": tracker_config.run_name,
        },
    )
    trackers_initialized = True
    if tracker_ready_callback is not None:
        tracker_ready_callback(tracker_summary)
    if args.resume_from_checkpoint is not None:
        resume_checkpoint_path = Path(args.resume_from_checkpoint)
        latest_durable_checkpoint = _load_durable_checkpoint_metadata(resume_checkpoint_path)
        accelerator.load_state(resume_checkpoint_path.as_posix())
        resumed_from_checkpoint_path = resume_checkpoint_path.as_posix()
        optimizer_steps_completed = latest_durable_checkpoint.optimizer_steps_completed
        starting_epoch = latest_durable_checkpoint.next_epoch
        resume_step_in_epoch = latest_durable_checkpoint.next_step_in_epoch
        durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
        train_iterations_completed = (starting_epoch * dataloader_length) + resume_step_in_epoch
    if progress_callback is not None:
        progress_callback(
            build_training_progress_heartbeat(
                phase="startup",
                current_epoch=starting_epoch,
                current_optimizer_step=optimizer_steps_completed,
                current_train_iteration=train_iterations_completed,
                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                latest_loss=last_loss,
                smoothed_loss=smoothed_loss,
                latest_durable_checkpoint=latest_durable_checkpoint,
            )
        )
    reached_max_steps = False
    stop_requested_during_training = False
    epoch = starting_epoch
    step = 0
    torch_profiler_session.start()
    try:
        for epoch in range(starting_epoch, args.num_epochs):
            epoch_dataloader = train_dataloader
            epoch_start_step = 0
            if epoch == starting_epoch and resume_step_in_epoch > 0:
                epoch_dataloader = accelerator.skip_first_batches(
                    train_dataloader,
                    resume_step_in_epoch,
                )
                epoch_start_step = resume_step_in_epoch
            for step, batch in enumerate(epoch_dataloader, start=epoch_start_step):
                train_iterations_completed += 1
                with accelerator.accumulate(model):
                    with torch_profiler_session.phase("task101.batch-preparation"):
                        input_ids = batch["input_ids"]
                        codec_ids = batch["codec_ids"]
                        ref_mels = batch["ref_mels"]
                        text_embedding_mask = batch["text_embedding_mask"]
                        codec_embedding_mask = batch["codec_embedding_mask"]
                        attention_mask = batch["attention_mask"]
                        codec_0_labels = batch["codec_0_labels"]
                        codec_mask = batch["codec_mask"]

                        speaker_embedding = model.speaker_encoder(
                            to_device_with_optional_non_blocking(
                                ref_mels,
                                device=model.device,
                                dtype=model.dtype,
                                non_blocking_transfer=(
                                    effective_dataloader_tuning.non_blocking_transfer
                                ),
                            )
                        ).detach()

                    with torch_profiler_session.phase("task101.forward-backward"):
                        input_text_ids = input_ids[:, :, 0]
                        input_codec_ids = input_ids[:, :, 1]

                        input_text_embedding = (
                            model.talker.model.text_embedding(input_text_ids) * text_embedding_mask
                        )
                        if hasattr(model.talker.model, "text_projection"):
                            input_text_embedding = model.talker.model.text_projection(
                                input_text_embedding
                            )

                        input_codec_embedding = (
                            model.talker.model.codec_embedding(input_codec_ids)
                            * codec_embedding_mask
                        )
                        input_codec_embedding[:, 6, :] = speaker_embedding
                        input_embeddings = input_text_embedding + input_codec_embedding

                        for codec_index in range(1, 16):
                            codec_i_embedding = model.talker.code_predictor.get_input_embeddings()[
                                codec_index - 1
                            ](codec_ids[:, :, codec_index])
                            codec_i_embedding = codec_i_embedding * codec_mask.unsqueeze(-1)
                            input_embeddings = input_embeddings + codec_i_embedding

                        outputs = model.talker(
                            inputs_embeds=input_embeddings[:, :-1, :],
                            attention_mask=attention_mask[:, :-1],
                            labels=codec_0_labels[:, 1:],
                            output_hidden_states=True,
                        )

                        hidden_states = outputs.hidden_states[0][-1]
                        talker_hidden_states = hidden_states[codec_mask[:, 1:]]
                        talker_codec_ids = codec_ids[codec_mask]

                        _, sub_talker_loss = model.talker.forward_sub_talker_finetune(
                            talker_codec_ids,
                            talker_hidden_states,
                        )
                        loss = outputs.loss + 0.3 * sub_talker_loss

                        accelerator.backward(loss)
                        completed_optimizer_step = accelerator.sync_gradients
                        if completed_optimizer_step:
                            accelerator.clip_grad_norm_(model.parameters(), 1.0)

                    with torch_profiler_session.phase("task101.optimizer-step"):
                        optimizer.step()
                        optimizer.zero_grad()
                    if completed_optimizer_step:
                        optimizer_steps_completed += 1
                    last_loss = float(loss.item())
                    smoothed_loss = update_smoothed_loss(smoothed_loss, last_loss)
                    log_training_metrics(
                        accelerator,
                        raw_loss=last_loss,
                        smoothed_loss=smoothed_loss,
                        current_epoch=epoch,
                        current_optimizer_step=optimizer_steps_completed,
                        current_train_iteration=train_iterations_completed,
                        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
                        ref_mel_cache_metrics=ref_mel_cache.payload(),
                    )
                    if progress_callback is not None:
                        progress_callback(
                            build_training_progress_heartbeat(
                                phase="train",
                                current_epoch=epoch,
                                current_optimizer_step=optimizer_steps_completed,
                                current_train_iteration=train_iterations_completed,
                                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                                latest_loss=last_loss,
                                smoothed_loss=smoothed_loss,
                                latest_durable_checkpoint=latest_durable_checkpoint,
                            )
                        )

                if step % 10 == 0:
                    accelerator.print(f"Epoch {epoch} | Step {step} | Loss: {loss.item():.4f}")
                if (
                    completed_optimizer_step
                    and optimizer_steps_completed > 0
                    and optimizer_steps_completed % int(args.checkpoint_interval_steps) == 0
                ):
                    with torch_profiler_session.phase("task101.checkpoint-save"):
                        latest_durable_checkpoint = _save_durable_checkpoint(
                            accelerator=accelerator,
                            output_model_path=output_model_path,
                            optimizer_steps_completed=optimizer_steps_completed,
                            epoch=epoch,
                            step_in_epoch=step,
                            dataloader_length=dataloader_length,
                            reason="interval",
                            durable_checkpoint_retention=int(args.durable_checkpoint_retention),
                            durable_checkpoint_min_free_bytes=int(
                                args.durable_checkpoint_min_free_bytes
                            ),
                        )
                    durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
                    if progress_callback is not None:
                        progress_callback(
                            build_training_progress_heartbeat(
                                phase="checkpoint-save",
                                current_epoch=epoch,
                                current_optimizer_step=optimizer_steps_completed,
                                current_train_iteration=train_iterations_completed,
                                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                                latest_loss=last_loss,
                                smoothed_loss=smoothed_loss,
                                latest_durable_checkpoint=latest_durable_checkpoint,
                            )
                        )
                if stop_state.stop_requested:
                    stop_requested_during_training = True
                    if progress_callback is not None:
                        progress_callback(
                            build_training_progress_heartbeat(
                                phase="signal-stop",
                                current_epoch=epoch,
                                current_optimizer_step=optimizer_steps_completed,
                                current_train_iteration=train_iterations_completed,
                                gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                                latest_loss=last_loss,
                                smoothed_loss=smoothed_loss,
                                latest_durable_checkpoint=latest_durable_checkpoint,
                            )
                        )
                    accelerator.print(
                        "Received stop request; saving one final durable checkpoint before exit."
                    )
                    break
                if (
                    args.max_steps is not None
                    and completed_optimizer_step
                    and optimizer_steps_completed >= args.max_steps
                ):
                    reached_max_steps = True
                    break
                torch_profiler_session.step()

            if accelerator.is_main_process:
                output_dir = output_model_path / f"checkpoint-epoch-{epoch}"
                checkpoint_paths.append(
                    _save_checkpoint(
                        accelerator=accelerator,
                        model=model,
                        model_path=model_path,
                        output_dir=output_dir,
                    )
                )
            if reached_max_steps:
                break
            if stop_requested_during_training:
                break

        if _checkpoint_advanced_since_latest_save(
            latest_durable_checkpoint,
            optimizer_steps_completed=optimizer_steps_completed,
        ):
            with torch_profiler_session.phase("task101.checkpoint-save"):
                latest_durable_checkpoint = _save_durable_checkpoint(
                    accelerator=accelerator,
                    output_model_path=output_model_path,
                    optimizer_steps_completed=optimizer_steps_completed,
                    epoch=epoch,
                    step_in_epoch=step,
                    dataloader_length=dataloader_length,
                    reason="signal-stop" if stop_requested_during_training else "final-step",
                    durable_checkpoint_retention=int(args.durable_checkpoint_retention),
                    durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
                )
            durable_checkpoint_paths = _current_durable_checkpoint_paths(output_model_path)
            if progress_callback is not None:
                progress_callback(
                    build_training_progress_heartbeat(
                        phase="checkpoint-save",
                        current_epoch=epoch,
                        current_optimizer_step=optimizer_steps_completed,
                        current_train_iteration=train_iterations_completed,
                        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
                        latest_loss=last_loss,
                        smoothed_loss=smoothed_loss,
                        latest_durable_checkpoint=latest_durable_checkpoint,
                    )
                )

        if accelerator.is_main_process:
            final_output_dir = output_model_path / "checkpoint-final"
            checkpoint_paths.append(
                _save_checkpoint(
                    accelerator=accelerator,
                    model=model,
                    model_path=model_path,
                    output_dir=final_output_dir,
                )
            )

        peak_memory_allocated_bytes = (
            int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
        )
        peak_memory_reserved_bytes = (
            int(torch.cuda.max_memory_reserved()) if torch.cuda.is_available() else None
        )
    finally:
        torch_profiler_session.stop()
        if trackers_initialized:
            accelerator.end_training()
            tracker_summary = refresh_training_tracker_summary(
                accelerator,
                tracker_config=tracker_config,
                system_metrics_enabled=tracker_summary.mlflow_system_metrics_enabled,
            )
    return TrainingSummary(
        init_model_path=str(args.init_model_path),
        output_model_path=str(args.output_model_path),
        train_jsonl=str(args.train_jsonl),
        batch_size=int(args.batch_size),
        lr=float(args.lr),
        num_epochs=int(args.num_epochs),
        max_steps=None if args.max_steps is None else int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        durable_checkpoint_retention=int(args.durable_checkpoint_retention),
        durable_checkpoint_min_free_bytes=int(args.durable_checkpoint_min_free_bytes),
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        optimizer_steps_completed=optimizer_steps_completed,
        train_iterations_completed=train_iterations_completed,
        last_loss=last_loss,
        smoothed_loss=smoothed_loss,
        peak_memory_allocated_bytes=peak_memory_allocated_bytes,
        peak_memory_reserved_bytes=peak_memory_reserved_bytes,
        resumed_from_checkpoint_path=resumed_from_checkpoint_path,
        latest_durable_checkpoint_path=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.checkpoint_path
        ),
        latest_durable_checkpoint_step=(
            None
            if latest_durable_checkpoint is None
            else latest_durable_checkpoint.optimizer_steps_completed
        ),
        latest_durable_checkpoint_epoch=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.epoch
        ),
        durable_checkpoint_paths=durable_checkpoint_paths,
        checkpoint_paths=checkpoint_paths,
        stop_requested=stop_requested_during_training,
        stop_signal=stop_state.signal_name,
        stopped_early=stop_requested_during_training,
        dataloader_tuning=dataloader_tuning_payload(effective_dataloader_tuning),
        ref_mel_cache=ref_mel_cache.payload(),
        profiling=torch_profiler_session.payload(),
        tracking=tracker_summary,
    )


def train() -> None:
    args = _parse_args()
    summary = train_with_args(args)
    if args.metrics_output_json is not None:
        metrics_output_path = Path(args.metrics_output_json)
        metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_output_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(summary), handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    train()
