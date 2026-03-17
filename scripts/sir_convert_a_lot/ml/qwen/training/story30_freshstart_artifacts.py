"""Artifact helpers for the Story 30 fresh-start discriminant proof.

Purpose:
    Own deterministic proof configuration, artifact paths, and config loading
    for the short fresh-start Candidate 1 Hemma proof lane.

Relationships:
    - Used by `story30_freshstart_proof.py` for local proof-package handling.
    - Used by `story30_freshstart_runtime.py` for remote command construction.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.defaults import (
    DEFAULT_PILOT_BUNDLE_ROOT,
)

DEFAULT_LOCAL_PROOF_ROOT = Path("build/verification/qwen-story30-freshstart-proof")
DEFAULT_REMOTE_PROOF_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen-story30-freshstart-proof"
)
DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training"
)
DEFAULT_TRAIN_SOURCE_BUNDLE_ROOT = DEFAULT_PILOT_BUNDLE_ROOT
DEFAULT_EVAL_SOURCE_BUNDLE_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/"
    "task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1"
)
DEFAULT_TRAIN_MANIFEST_FAMILY = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY = "swedish_checkpoint_dev"
DEFAULT_TEXT_EMBEDDING_MASK_POLICY = "text_span_only"
DEFAULT_THROUGHPUT_PROFILE_LABEL = "hemma-throughput-balanced-v1"
DEFAULT_TRAIN_LINE_START = 1
DEFAULT_TRAIN_LINE_END = 16
DEFAULT_EVAL_LINE_START = 1
DEFAULT_EVAL_LINE_END = 1
DEFAULT_BATCH_SIZE = 8
DEFAULT_MAX_STEPS = 2
DEFAULT_CHECKPOINT_INTERVAL_STEPS = 500
DEFAULT_EVAL_INTERVAL_STEPS = 1000
DEFAULT_GRADIENT_ACCUMULATION_STEPS = 1
DEFAULT_REQUIRED_SCRATCH_FREE_BYTES = 16 * 1024**3
DEFAULT_TASK_LABEL = "Task 211"
DEFAULT_COMMAND_NAME = "qwen-story30-freshstart-proof"
DEFAULT_PROOF_ID_PREFIX = "task211"


@dataclass(frozen=True)
class Story30FreshstartProofConfig:
    """Deterministic configuration for one fresh-start proof package."""

    task_label: str
    command_name: str
    prepared_at: str
    proof_id: str
    local_proof_root: str
    remote_proof_output_root: str
    remote_training_output_root: str
    train_source_bundle_root: str
    eval_source_bundle_root: str
    train_manifest_family: str
    eval_manifest_family: str
    text_embedding_mask_policy: str
    throughput_profile_label: str
    train_line_start: int
    train_line_end: int
    eval_line_start: int
    eval_line_end: int
    batch_size: int
    max_steps: int
    checkpoint_interval_steps: int
    eval_interval_steps: int
    gradient_accumulation_steps: int
    required_scratch_free_bytes: int
    skip_build: bool
    launch_id: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_proof_id() -> str:
    """Return one deterministic fresh-start proof identifier."""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ").lower()
    return f"{DEFAULT_PROOF_ID_PREFIX}-{timestamp}"


def proof_root(base_output_root: Path, proof_id: str) -> Path:
    """Return the immutable local proof root for one prepared proof id."""
    return base_output_root / proof_id


def remote_proof_root(config: Story30FreshstartProofConfig) -> Path:
    """Return the immutable remote proof root for one proof id."""
    return Path(config.remote_proof_output_root) / config.proof_id


def remote_bundle_root(config: Story30FreshstartProofConfig) -> Path:
    """Return the remote mini-bundle root for one fresh-start proof."""
    return remote_proof_root(config) / "mini-bundle"


def remote_launch_root(config: Story30FreshstartProofConfig) -> Path:
    """Return the detached training launch root for one fresh-start proof."""
    return Path(config.remote_training_output_root) / config.launch_id


def config_path(local_proof_root: Path) -> Path:
    """Return the canonical proof-config path."""
    return local_proof_root / "proof-config.json"


def plan_path(local_proof_root: Path) -> Path:
    """Return the canonical proof plan path."""
    return local_proof_root / "plan.md"


def checklist_path(local_proof_root: Path) -> Path:
    """Return the canonical proof checklist path."""
    return local_proof_root / "checklist.md"


def launch_path(local_proof_root: Path) -> Path:
    """Return the canonical launch artifact path."""
    return local_proof_root / "launch.json"


def status_path(local_proof_root: Path) -> Path:
    """Return the canonical status artifact path."""
    return local_proof_root / "status.json"


def status_markdown_path(local_proof_root: Path) -> Path:
    """Return the canonical markdown status artifact path."""
    return local_proof_root / "status.md"


def latest_pointer_path(base_output_root: Path) -> Path:
    """Return the pointer artifact for the latest prepared proof root."""
    return base_output_root / "latest-proof.json"


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


def build_prepare_config(args: argparse.Namespace) -> Story30FreshstartProofConfig:
    """Build one normalized fresh-start proof config from parsed args."""
    proof_id = default_proof_id() if args.proof_id is None else str(args.proof_id)
    local_root = proof_root(Path(args.output_root), proof_id)
    return Story30FreshstartProofConfig(
        task_label=DEFAULT_TASK_LABEL,
        command_name=DEFAULT_COMMAND_NAME,
        prepared_at=utc_now_iso(),
        proof_id=proof_id,
        local_proof_root=local_root.as_posix(),
        remote_proof_output_root=Path(args.remote_proof_output_root).as_posix(),
        remote_training_output_root=Path(args.remote_training_output_root).as_posix(),
        train_source_bundle_root=Path(args.train_source_bundle_root).as_posix(),
        eval_source_bundle_root=Path(args.eval_source_bundle_root).as_posix(),
        train_manifest_family=str(args.train_manifest_family),
        eval_manifest_family=str(args.eval_manifest_family),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        throughput_profile_label=str(args.throughput_profile_label),
        train_line_start=int(args.train_line_start),
        train_line_end=int(args.train_line_end),
        eval_line_start=int(args.eval_line_start),
        eval_line_end=int(args.eval_line_end),
        batch_size=int(args.batch_size),
        max_steps=int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        eval_interval_steps=int(args.eval_interval_steps),
        gradient_accumulation_steps=int(args.gradient_accumulation_steps),
        required_scratch_free_bytes=int(args.required_scratch_free_bytes),
        skip_build=bool(args.skip_build),
        launch_id=f"{proof_id}-freshstart",
    )


def load_config(local_proof_root: Path) -> Story30FreshstartProofConfig:
    """Load one prepared fresh-start proof config from disk."""
    payload = json.loads(config_path(local_proof_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Fresh-start proof config was not a JSON object.")
    return Story30FreshstartProofConfig(
        task_label=_required_str(payload, "task_label"),
        command_name=_required_str(payload, "command_name"),
        prepared_at=_required_str(payload, "prepared_at"),
        proof_id=_required_str(payload, "proof_id"),
        local_proof_root=_required_str(payload, "local_proof_root"),
        remote_proof_output_root=_required_str(payload, "remote_proof_output_root"),
        remote_training_output_root=_required_str(payload, "remote_training_output_root"),
        train_source_bundle_root=_required_str(payload, "train_source_bundle_root"),
        eval_source_bundle_root=_required_str(payload, "eval_source_bundle_root"),
        train_manifest_family=_required_str(payload, "train_manifest_family"),
        eval_manifest_family=_required_str(payload, "eval_manifest_family"),
        text_embedding_mask_policy=_required_str(payload, "text_embedding_mask_policy"),
        throughput_profile_label=_required_str(payload, "throughput_profile_label"),
        train_line_start=_required_int(payload, "train_line_start"),
        train_line_end=_required_int(payload, "train_line_end"),
        eval_line_start=_required_int(payload, "eval_line_start"),
        eval_line_end=_required_int(payload, "eval_line_end"),
        batch_size=_required_int(payload, "batch_size"),
        max_steps=_required_int(payload, "max_steps"),
        checkpoint_interval_steps=_required_int(payload, "checkpoint_interval_steps"),
        eval_interval_steps=_required_int(payload, "eval_interval_steps"),
        gradient_accumulation_steps=_required_int(payload, "gradient_accumulation_steps"),
        required_scratch_free_bytes=_required_int(payload, "required_scratch_free_bytes"),
        skip_build=_required_bool(payload, "skip_build"),
        launch_id=_required_str(payload, "launch_id"),
    )


def resolve_proof_root(
    *,
    base_output_root: Path,
    proof_root_arg: Path | None,
    proof_id_arg: str | None,
) -> Path:
    """Resolve one prepared proof root from explicit args or the latest pointer."""
    if proof_root_arg is not None:
        return proof_root_arg
    if proof_id_arg is not None:
        return proof_root(base_output_root, str(proof_id_arg))
    pointer = latest_pointer_path(base_output_root)
    if not pointer.exists():
        raise SystemExit("Fresh-start proof root was not provided and no latest pointer exists.")
    payload = json.loads(pointer.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Fresh-start latest-proof pointer was malformed.")
    return Path(_required_str(payload, "proof_root"))


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Fresh-start proof payload missing string `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Fresh-start proof payload missing integer `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Fresh-start proof payload missing boolean `{key}`.")
    return value
