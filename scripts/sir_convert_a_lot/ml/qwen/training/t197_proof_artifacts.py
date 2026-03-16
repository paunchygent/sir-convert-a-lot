"""Artifact helpers for the Task 197 Hemma proof surface.

Purpose:
    Own deterministic proof configuration, artifact paths, and operator-facing
    markdown for the bounded `1406 -> 1418 -> 1500` Story 29 gate.

Relationships:
    - Used by `t197_proof.py` as the local artifact and config backing store.
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
DEFAULT_LOCAL_PROOF_ROOT = Path("build/verification/qwen-t197-proof")
DEFAULT_SOURCE_LAUNCH_ROOT = DEFAULT_REMOTE_TRAINING_OUTPUT_ROOT / "task194-20260316t-1405-rca-a1"
DEFAULT_SOURCE_CHECKPOINT_PATH = (
    DEFAULT_SOURCE_LAUNCH_ROOT / "diagnostic-run/checkpoints/state-step-00001406"
)
DEFAULT_TEXT_EMBEDDING_MASK_POLICY = "text_span_only"
DEFAULT_GRADIENT_ACCUMULATION_STEPS = 4
DEFAULT_WINDOW_START_OPTIMIZER_STEP = 1406
DEFAULT_WINDOW_END_OPTIMIZER_STEP = 1418
DEFAULT_GATE_MAX_STEPS = 1500
DEFAULT_GATE_CHECKPOINT_INTERVAL_STEPS = 500
DEFAULT_GATE_EVAL_INTERVAL_STEPS = 100


@dataclass(frozen=True)
class T197ProofConfig:
    """Deterministic configuration for one Task 197 proof package."""

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
    skip_build: bool
    window_launch_id: str
    gate_launch_id: str


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_proof_id() -> str:
    """Return one deterministic Task 197 proof identifier."""
    return f"task197-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ').lower()}"


def proof_root(base_output_root: Path, proof_id: str) -> Path:
    """Return the immutable local verification root for one Task 197 proof."""
    return base_output_root / proof_id


def config_path(local_proof_root: Path) -> Path:
    """Return the canonical config artifact path for one Task 197 proof."""
    return local_proof_root / "proof-config.json"


def plan_path(local_proof_root: Path) -> Path:
    """Return the canonical plan artifact path for one Task 197 proof."""
    return local_proof_root / "plan.md"


def checklist_path(local_proof_root: Path) -> Path:
    """Return the canonical checklist artifact path for one Task 197 proof."""
    return local_proof_root / "checklist.md"


def latest_pointer_path(base_output_root: Path) -> Path:
    """Return the pointer path for the latest prepared Task 197 proof root."""
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


def remote_window_launch_root(config: T197ProofConfig) -> Path:
    """Return the remote launch root for the bounded replay phase."""
    return Path(config.remote_training_output_root) / config.window_launch_id


def remote_gate_launch_root(config: T197ProofConfig) -> Path:
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


def build_prepare_config(args: argparse.Namespace) -> T197ProofConfig:
    """Build one normalized proof configuration from parsed prepare args."""
    proof_id = default_proof_id() if args.proof_id is None else str(args.proof_id)
    local_root = proof_root(Path(args.output_root), proof_id)
    return T197ProofConfig(
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
        raise SystemExit("Latest Task 197 proof metadata was malformed.")
    return Path(_required_str(payload, "proof_root"))


def load_config(local_proof_root: Path) -> T197ProofConfig:
    """Load one prepared Task 197 proof configuration."""
    payload = json.loads(config_path(local_proof_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Task 197 proof config was malformed.")
    return T197ProofConfig(
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
        skip_build=_required_bool(payload, "skip_build"),
        window_launch_id=_required_str(payload, "window_launch_id"),
        gate_launch_id=_required_str(payload, "gate_launch_id"),
    )


def render_plan_markdown(
    config: T197ProofConfig,
    *,
    window_command: list[str],
    status_window_command: list[str],
    gate_command: list[str],
    status_gate_command: list[str],
) -> str:
    """Render one concise markdown plan for the prepared Task 197 proof."""
    return "\n".join(
        [
            "# Task 197 Proof Plan",
            "",
            f"- proof_id: `{config.proof_id}`",
            f"- local_proof_root: `{config.local_proof_root}`",
            f"- remote_training_output_root: `{config.remote_training_output_root}`",
            f"- source_launch_root: `{config.source_launch_root}`",
            f"- source_checkpoint_path: `{config.source_checkpoint_path}`",
            f"- text_embedding_mask_policy: `{config.text_embedding_mask_policy}`",
            f"- gradient_accumulation_steps: `{config.gradient_accumulation_steps}`",
            (
                f"- bounded_window: `{config.window_start_optimizer_step} -> "
                f"{config.window_end_optimizer_step}`"
            ),
            f"- preferred_gate_step: `{config.gate_max_steps}`",
            f"- gate_checkpoint_interval_steps: `{config.gate_checkpoint_interval_steps}`",
            f"- gate_eval_interval_steps: `{config.gate_eval_interval_steps}`",
            "",
            "## Wrapper Commands",
            "",
            f"- prepare: `pdm run qwen-t197-proof prepare --proof-id {config.proof_id}`",
            (
                f"- launch-window: `pdm run qwen-t197-proof launch-window "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- status-window: `pdm run qwen-t197-proof status-window "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- launch-gate1500: `pdm run qwen-t197-proof launch-gate1500 "
                f"--proof-id {config.proof_id}`"
            ),
            (
                f"- status-gate1500: `pdm run qwen-t197-proof status-gate1500 "
                f"--proof-id {config.proof_id}`"
            ),
            "",
            "## Raw Remote Commands",
            "",
            f"- bounded replay: `{' '.join(window_command)}`",
            f"- replay status: `{' '.join(status_window_command)}`",
            f"- 1500 gate: `{' '.join(gate_command)}`",
            f"- 1500 status: `{' '.join(status_gate_command)}`",
        ]
    )


def render_checklist_markdown(config: T197ProofConfig) -> str:
    """Render the operator checklist for one prepared Task 197 proof."""
    window_launch_root = remote_window_launch_root(config)
    gate_launch_root = remote_gate_launch_root(config)
    return "\n".join(
        [
            "# Task 197 Proof Checklist",
            "",
            "## Preflight",
            "",
            "- [ ] Confirm Hemma repo `HEAD` matches the intended local revision before launch.",
            f"- [ ] Confirm the source launch root exists: `{config.source_launch_root}`",
            f"- [ ] Confirm the source checkpoint exists: `{config.source_checkpoint_path}`",
            (
                f"- [ ] Confirm `text_embedding_mask_policy={config.text_embedding_mask_policy}` "
                f"and `gradient_accumulation_steps={config.gradient_accumulation_steps}` "
                "are the active overrides."
            ),
            (
                f"- [ ] Confirm the bounded replay target is exactly optimizer steps "
                f"`{config.window_start_optimizer_step} -> {config.window_end_optimizer_step}`."
            ),
            "",
            "## Window Gate",
            "",
            (
                f"- [ ] Launch the bounded replay with `pdm run qwen-t197-proof "
                f"launch-window --proof-id {config.proof_id}`"
            ),
            (
                f"- [ ] Inspect status with `pdm run qwen-t197-proof status-window "
                f"--proof-id {config.proof_id}`"
            ),
            f"- [ ] Verify the replay launch root: `{window_launch_root}`",
            (
                f"- [ ] Pass condition: detached run exits `0`, replays optimizer steps "
                f"`{config.window_start_optimizer_step} -> {config.window_end_optimizer_step}`, "
                "and does not surface a non-finite trigger."
            ),
            (
                f"- [ ] Fail condition: the run fails before step "
                f"`{config.window_end_optimizer_step}` or surfaces a new first bad "
                "tensor/gradient path."
            ),
            "",
            "## 1500 Gate",
            "",
            (
                f"- [ ] Launch only after the window gate passes: "
                f"`pdm run qwen-t197-proof launch-gate1500 --proof-id {config.proof_id}`"
            ),
            (
                f"- [ ] Inspect status with `pdm run qwen-t197-proof status-gate1500 "
                f"--proof-id {config.proof_id}`"
            ),
            f"- [ ] Verify the continuation launch root: `{gate_launch_root}`",
            (
                f"- [ ] Pass condition: detached run exits `0`, reaches optimizer step "
                f"`{config.gate_max_steps}`, and records the scheduled eval there."
            ),
            (
                f"- [ ] Fail condition: the run fails before `{config.gate_max_steps}`; if so, "
                "`T198` becomes the next active task."
            ),
            "",
            "## Close-Out",
            "",
            "- [ ] Record the outcome in the training reference ledger and Story 29 docs.",
            (
                "- [ ] If the proof passes, treat `text_span_only` as the winning "
                "mitigation for the preferred gate."
            ),
            (
                "- [ ] If the proof fails, record the failure step and first bad "
                "surface before touching `T198`."
            ),
        ]
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Task 197 proof metadata expected string field `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Task 197 proof metadata expected integer field `{key}`.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Task 197 proof metadata expected boolean field `{key}`.")
    return value
