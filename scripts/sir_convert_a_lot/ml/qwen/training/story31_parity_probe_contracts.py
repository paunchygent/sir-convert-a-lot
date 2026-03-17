"""Contracts for the Story 31 deterministic parity probe.

Purpose:
    Keep the exact mechanism-lane settings, per-path artifacts, and
    comparison-report payloads in one small shared module so the public CLI and
    runner stay focused on orchestration rather than bookkeeping.

Relationships:
    - Imported by `story31_parity_probe.py` for the public command surface.
    - Imported by `story31_parity_probe_runner.py` and
      `story31_parity_probe_runtime.py` for typed artifact exchange.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    GradientAccumulationSteps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.t221_historical_control import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHECKPOINT_INTERVAL_STEPS,
    DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES,
    DEFAULT_DURABLE_CHECKPOINT_RETENTION,
    DEFAULT_EVAL_INTERVAL_STEPS,
    DEFAULT_HISTORICAL_BUNDLE_ROOT,
    DEFAULT_IMAGE,
    DEFAULT_LR,
    DEFAULT_MODEL_ID,
    DEFAULT_NUM_EPOCHS,
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
)
from scripts.sir_convert_a_lot.ml.qwen.training.t221_historical_control import (
    DEFAULT_EVAL_MANIFEST_FAMILY as DEFAULT_TASK101_EVAL_MANIFEST_FAMILY,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE,
    TextEmbeddingAssemblyMode,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    TextEmbeddingMaskPolicy,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/qwen-story31-parity-probe")
DEFAULT_MANIFEST_LINES = (6367, 6966, 4958, 623)
DEFAULT_PATH_LABEL_CURRENT = "current_patched_path"
DEFAULT_PATH_LABEL_INTENDED = "intended_upstream_compatible_reconstruction"
DEFAULT_EXECUTION_MODE_CURRENT = "current_train_step_window"
DEFAULT_EXECUTION_MODE_INTENDED = "reconstructed_shared_forward_window"


@dataclass(frozen=True)
class Story31ParityProbeSettings:
    """Configuration for one deterministic Story 31 parity-probe run."""

    output_root: Path
    source_bundle_root: Path = DEFAULT_HISTORICAL_BUNDLE_ROOT
    image: str = DEFAULT_IMAGE
    model_id: str = DEFAULT_MODEL_ID
    train_manifest_family: str = DEFAULT_TRAIN_MANIFEST_FAMILY
    eval_manifest_family: str = DEFAULT_TASK101_EVAL_MANIFEST_FAMILY
    manifest_lines: tuple[int, ...] = DEFAULT_MANIFEST_LINES
    batch_size: int = DEFAULT_BATCH_SIZE
    gradient_accumulation_steps: GradientAccumulationSteps = DEFAULT_GRADIENT_ACCUMULATION_STEPS
    text_embedding_assembly_mode: TextEmbeddingAssemblyMode = (
        FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE
    )
    text_embedding_mask_policy: TextEmbeddingMaskPolicy = TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY
    max_steps: int = 1
    lr: float = DEFAULT_LR
    num_epochs: int = DEFAULT_NUM_EPOCHS
    checkpoint_interval_steps: int = DEFAULT_CHECKPOINT_INTERVAL_STEPS
    eval_interval_steps: int = DEFAULT_EVAL_INTERVAL_STEPS
    durable_checkpoint_retention: int = DEFAULT_DURABLE_CHECKPOINT_RETENTION
    durable_checkpoint_min_free_bytes: int = DEFAULT_DURABLE_CHECKPOINT_MIN_FREE_BYTES
    throughput_profile_label: str = DEFAULT_THROUGHPUT_PROFILE_LABEL
    deterministic_seed: int = 0


@dataclass(frozen=True)
class Story31ParityPathReport:
    """Comparable artifact set for one parity-probe execution path."""

    path_label: str
    execution_mode: str
    output_model_path: str
    runtime_posture: dict[str, object]
    selected_rows: tuple[dict[str, object], ...]
    per_item_dataset_output: tuple[dict[str, object], ...]
    collated_batch_tensors: tuple[dict[str, object], ...]
    forward_entry_surfaces: tuple[dict[str, object], ...]
    loss_decomposition: tuple[dict[str, object], ...]
    backward_pre_clip: dict[str, object] | None
    clip_boundary: dict[str, object] | None
    optimizer_preconditions: dict[str, object] | None
    step_forensics: dict[str, object] | None
    execution_outcome: dict[str, object]


@dataclass(frozen=True)
class Story31ParityCheckpointComparison:
    """One checkpoint-by-checkpoint comparison between the two parity paths."""

    checkpoint_name: str
    matches: bool
    current_has_non_finite: bool
    intended_has_non_finite: bool


@dataclass(frozen=True)
class Story31ParityProbeReport:
    """Machine-readable report for one deterministic Story 31 parity run."""

    generated_at: str
    output_root: str
    source_bundle_root: str
    image: str
    model_id: str
    train_manifest_family: str
    eval_manifest_family: str
    manifest_lines: tuple[int, ...]
    batch_size: int
    gradient_accumulation_steps: GradientAccumulationSteps
    text_embedding_assembly_mode: TextEmbeddingAssemblyMode
    text_embedding_mask_policy: TextEmbeddingMaskPolicy
    max_steps: int
    current_path_report_path: str
    intended_path_report_path: str
    current_path: Story31ParityPathReport
    intended_path: Story31ParityPathReport
    checkpoint_comparisons: tuple[Story31ParityCheckpointComparison, ...]
    first_divergence_checkpoint: str | None
    first_divergence_classification: str
    recommended_next_step: str
    summary: str


DEFAULT_STORY31_PARITY_PROBE_SETTINGS = Story31ParityProbeSettings(output_root=DEFAULT_OUTPUT_ROOT)
