"""Artifact helpers for the Story 29 bounded-proof surfaces.

Purpose:
    Own deterministic proof configuration, artifact paths, and operator-facing
    markdown for the bounded Story 29 proof lanes that start from the canonical
    `1406` RCA checkpoint.

Relationships:
    - Used by the task-specific proof entrypoints for `T197` and `T198`.
    - Used by `t197_proof_runtime.py` for remote launch-root resolution.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path

DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training"
)
DEFAULT_SOURCE_LAUNCH_ROOT = DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT / "task194-20260316t-1405-rca-a1"
DEFAULT_SOURCE_CHECKPOINT_PATH = (
    DEFAULT_SOURCE_LAUNCH_ROOT / "diagnostic-run/checkpoints/state-step-00001406"
)
DEFAULT_TEXT_EMBEDDING_MASK_POLICY = "text_span_only"
DEFAULT_WINDOW_START_OPTIMIZER_STEP = 1406
DEFAULT_WINDOW_END_OPTIMIZER_STEP = 1418
DEFAULT_GATE_MAX_STEPS = 1500
DEFAULT_GATE_CHECKPOINT_INTERVAL_STEPS = 500
DEFAULT_GATE_EVAL_INTERVAL_STEPS = 100
DEFAULT_REQUIRED_SCRATCH_FREE_BYTES = 64 * 1024**3


@dataclass(frozen=True)
class Story29ProofProfile:
    """Task-specific defaults for one Story 29 proof command surface."""

    task_label: str
    command_name: str
    local_proof_root: Path
    proof_id_prefix: str
    default_gradient_accumulation_steps: int


T197_PROOF_PROFILE = Story29ProofProfile(
    task_label="Task 197",
    command_name="qwen-t197-proof",
    local_proof_root=Path("build/verification/qwen-t197-proof"),
    proof_id_prefix="task197",
    default_gradient_accumulation_steps=4,
)

T198_PROOF_PROFILE = Story29ProofProfile(
    task_label="Task 198",
    command_name="qwen-t198-proof",
    local_proof_root=Path("build/verification/qwen-t198-proof"),
    proof_id_prefix="task198",
    default_gradient_accumulation_steps=2,
)


@dataclass(frozen=True)
class Story29ProofConfig:
    """Deterministic configuration for one Story 29 proof package."""

    task_label: str
    command_name: str
    prepared_at: str
    proof_id: str
    local_proof_root: str
    remote_training_output_root: str
    source_launch_root: str
    source_checkpoint_path: str
    text_embedding_mask_policy: str
    gradient_accumulation_steps: int
    window_start_optimizer_step: int
    window_end_optimizer_step: int
    gate_max_steps: int
    gate_checkpoint_interval_steps: int
    gate_eval_interval_steps: int
    required_scratch_free_bytes: int
    skip_build: bool
    window_launch_id: str
    gate_launch_id: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_proof_id(profile: Story29ProofProfile) -> str:
    """Return one deterministic Story 29 proof identifier for one task lane."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ").lower()
    return f"{profile.proof_id_prefix}-{timestamp}"


def proof_root(base_output_root: Path, proof_id: str) -> Path:
    """Return the immutable local verification root for one Story 29 proof."""
    return base_output_root / proof_id


def config_path(local_proof_root: Path) -> Path:
    """Return the canonical config artifact path for one Story 29 proof."""
    return local_proof_root / "proof-config.json"


def plan_path(local_proof_root: Path) -> Path:
    """Return the canonical plan artifact path for one Story 29 proof."""
    return local_proof_root / "plan.md"


def checklist_path(local_proof_root: Path) -> Path:
    """Return the canonical checklist artifact path for one Story 29 proof."""
    return local_proof_root / "checklist.md"


def latest_pointer_path(base_output_root: Path) -> Path:
    """Return the pointer path for the latest prepared Story 29 proof root."""
    return base_output_root / "latest-proof.json"


def window_launch_path(local_proof_root: Path) -> Path:
    """Return the launch artifact path for the bounded replay phase."""
    return local_proof_root / "window-launch.json"


def window_status_path(local_proof_root: Path) -> Path:
    """Return the status artifact path for the bounded replay phase."""
    return local_proof_root / "window-status.json"


def window_status_markdown_path(local_proof_root: Path) -> Path:
    """Return the markdown status artifact path for the bounded replay phase."""
    return local_proof_root / "window-status.md"


def gate_launch_path(local_proof_root: Path) -> Path:
    """Return the launch artifact path for the `1500` gate phase."""
    return local_proof_root / "gate1500-launch.json"


def gate_status_path(local_proof_root: Path) -> Path:
    """Return the status artifact path for the `1500` gate phase."""
    return local_proof_root / "gate1500-status.json"


def gate_status_markdown_path(local_proof_root: Path) -> Path:
    """Return the markdown status artifact path for the `1500` gate phase."""
    return local_proof_root / "gate1500-status.md"


def remote_window_launch_root(config: Story29ProofConfig) -> Path:
    """Return the remote launch root for the bounded replay phase."""
    return Path(config.remote_training_output_root) / config.window_launch_id


def remote_gate_launch_root(config: Story29ProofConfig) -> Path:
    """Return the remote launch root for the `1500` continuation phase."""
    return Path(config.remote_training_output_root) / config.gate_launch_id


def write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def build_prepare_config(
    profile: Story29ProofProfile,
    args: argparse.Namespace,
) -> Story29ProofConfig:
    """Build one normalized Story 29 proof configuration from parsed args."""
    proof_id = default_proof_id(profile) if args.proof_id is None else str(args.proof_id)
    local_root = proof_root(Path(args.output_root), proof_id)
    return Story29ProofConfig(
        task_label=profile.task_label,
        command_name=profile.command_name,
        prepared_at=utc_now_iso(),
        proof_id=proof_id,
        local_proof_root=local_root.as_posix(),
        remote_training_output_root=Path(args.remote_training_output_root).as_posix(),
        source_launch_root=Path(args.source_launch_root).as_posix(),
        source_checkpoint_path=Path(args.source_checkpoint_path).as_posix(),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        gradient_accumulation_steps=int(args.gradient_accumulation_steps),
        window_start_optimizer_step=int(args.window_start_optimizer_step),
        window_end_optimizer_step=int(args.window_end_optimizer_step),
        gate_max_steps=int(args.gate_max_steps),
        gate_checkpoint_interval_steps=int(args.gate_checkpoint_interval_steps),
        gate_eval_interval_steps=int(args.gate_eval_interval_steps),
        required_scratch_free_bytes=int(args.required_scratch_free_bytes),
        skip_build=bool(args.skip_build),
        window_launch_id=f"{proof_id}-window",
        gate_launch_id=f"{proof_id}-gate1500",
    )


def resolve_proof_root(
    *,
    base_output_root: Path,
    proof_root_arg: Path | None,
    proof_id_arg: str | None,
) -> Path:
    """Resolve one proof root from explicit args or the latest local pointer."""
    if proof_root_arg is not None:
        return Path(proof_root_arg)
    if proof_id_arg is not None:
        return proof_root(base_output_root, str(proof_id_arg))
    payload = json.loads(latest_pointer_path(base_output_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Latest Story 29 proof metadata was malformed.")
    return Path(_required_str(payload, "proof_root"))


def load_config(local_proof_root: Path) -> Story29ProofConfig:
    """Load one prepared Story 29 proof configuration."""
    payload = json.loads(config_path(local_proof_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Story 29 proof config was malformed.")
    return Story29ProofConfig(
        task_label=_required_str(payload, "task_label"),
        command_name=_required_str(payload, "command_name"),
        prepared_at=_required_str(payload, "prepared_at"),
        proof_id=_required_str(payload, "proof_id"),
        local_proof_root=_required_str(payload, "local_proof_root"),
        remote_training_output_root=_required_str(payload, "remote_training_output_root"),
        source_launch_root=_required_str(payload, "source_launch_root"),
        source_checkpoint_path=_required_str(payload, "source_checkpoint_path"),
        text_embedding_mask_policy=_required_str(payload, "text_embedding_mask_policy"),
        gradient_accumulation_steps=_required_int(payload, "gradient_accumulation_steps"),
        window_start_optimizer_step=_required_int(payload, "window_start_optimizer_step"),
        window_end_optimizer_step=_required_int(payload, "window_end_optimizer_step"),
        gate_max_steps=_required_int(payload, "gate_max_steps"),
        gate_checkpoint_interval_steps=_required_int(payload, "gate_checkpoint_interval_steps"),
        gate_eval_interval_steps=_required_int(payload, "gate_eval_interval_steps"),
        required_scratch_free_bytes=_required_int(payload, "required_scratch_free_bytes"),
        skip_build=_required_bool(payload, "skip_build"),
        window_launch_id=_required_str(payload, "window_launch_id"),
        gate_launch_id=_required_str(payload, "gate_launch_id"),
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Story 29 proof metadata expected string field `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Story 29 proof metadata expected integer field `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Story 29 proof metadata expected boolean field `{key}`.")
    return value
