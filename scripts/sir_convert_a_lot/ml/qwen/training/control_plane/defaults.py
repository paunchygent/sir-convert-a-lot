"""Default constants and helpers for the Qwen training control plane.

Purpose:
    Centralize CLI defaults and shared default-path helpers for detached Qwen
    training, eval, schedule, and diagnostic flows.

Relationships:
    - Used by the control-plane parser and use-case modules.
    - Keeps hard-coded defaults out of the CLI composition root.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from scripts.devops.qwen_finetuning_patches.sft_12hz_eval import DEFAULT_EVAL_INTERVAL_STEPS
from scripts.sir_convert_a_lot.ml.qwen.common.storage import DEFAULT_SCRATCH_BUILD_ROOT
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostics import (
    DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP as DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP_RUNTIME,
)
from scripts.sir_convert_a_lot.ml.qwen.training.diagnostics import (
    DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP as DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP_RUNTIME,
)
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import (
    DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS as DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS_RUNTIME,
)
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import (
    DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND as DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND_RUNTIME,
)

DEFAULT_OUTPUT_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "verification/qwen3-tts-swedish-hemma-training"
DEFAULT_RUNS_ROOT = DEFAULT_SCRATCH_BUILD_ROOT / "runs/qwen3-tts-swedish-finetune"
DEFAULT_SCRATCH_BUILD_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/build")
DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:latest"
DEFAULT_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"
DEFAULT_PILOT_BUNDLE_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "reference/qwen3-tts-swedish-task101-pilot-bundle"
)
DEFAULT_HEMMA_HF_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT"
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_TRAIN_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY = "swedish_checkpoint_dev"
DEFAULT_BATCH_SIZE = 8
DEFAULT_LR = 2e-5
DEFAULT_NUM_EPOCHS = 1
DEFAULT_MAX_STEPS = 8
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 500
DEFAULT_EVAL_INTERVAL_STEPS_CLI = DEFAULT_EVAL_INTERVAL_STEPS
DEFAULT_DURABLE_CHECKPOINT_RETENTION = 3
DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES = 16 * 1024**3
DEFAULT_DATALOADER_NUM_WORKERS = 4
DEFAULT_DATALOADER_PIN_MEMORY = True
DEFAULT_DATALOADER_PERSISTENT_WORKERS = True
DEFAULT_DATALOADER_PREFETCH_FACTOR = 4
DEFAULT_NON_BLOCKING_TRANSFER = True
DEFAULT_DATA_PATH_PROOF_MODE = False
DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS = 20
DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS = 3
DEFAULT_REF_MEL_CACHE_ENABLED = True
DEFAULT_REF_MEL_CACHE_MAX_ITEMS = 2048
DEFAULT_TORCH_PROFILER_ENABLED = False
DEFAULT_TORCH_PROFILER_WAIT_STEPS = 1
DEFAULT_TORCH_PROFILER_WARMUP_STEPS = 1
DEFAULT_TORCH_PROFILER_ACTIVE_STEPS = 4
DEFAULT_TORCH_PROFILER_REPEAT = 1
DEFAULT_TORCH_PROFILER_RECORD_SHAPES = True
DEFAULT_TORCH_PROFILER_PROFILE_MEMORY = True
DEFAULT_TORCH_PROFILER_WITH_STACK = False
DEFAULT_ROCM_PROFILER_ENABLED = False
DEFAULT_SCHEDULE_POLL_INTERVAL_SECONDS = 15.0
DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP = DEFAULT_DIAGNOSTIC_START_OPTIMIZER_STEP_RUNTIME
DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP = DEFAULT_DIAGNOSTIC_END_OPTIMIZER_STEP_RUNTIME
DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS = DEFAULT_RESOURCE_MONITOR_INTERVAL_SECONDS_RUNTIME
DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND = DEFAULT_RESOURCE_MONITOR_RUNTIME_KIND_RUNTIME
LEGACY_SMALL_BATCH_THROUGHPUT_PROFILE_LABEL = "hemma-throughput-balanced-v1"
DEFAULT_THROUGHPUT_PROFILE_LABEL = "hemma-throughput-balanced-v1"
TrainingCommand = Literal[
    "launch",
    "resume",
    "eval",
    "schedule",
    "diagnose-non-finite",
    "status",
    "stop",
]


def default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for training."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE
    return Path(configured_path.strip())


def default_hf_cache_home_mount() -> Path:
    """Resolve the fallback home-backed Hugging Face cache mount path."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE_HOME_MOUNT
    return Path(configured_path.strip())
