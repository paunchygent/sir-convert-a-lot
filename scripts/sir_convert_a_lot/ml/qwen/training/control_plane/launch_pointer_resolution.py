"""Launch-pointer and checkpoint-resolution helpers for control-plane flows.

Purpose:
    Own latest-launch and latest-checkpoint pointer resolution plus resume
    checkpoint ownership validation for detached Qwen training workflows.

Relationships:
    - Used by status/stop/eval/resume/diagnose/schedule use cases.
    - Consumes canonical path helpers from `launch_artifact_paths`.
"""

from __future__ import annotations

import json
from pathlib import Path

from .launch_artifact_paths import latest_pointer_path


def load_latest_checkpoint(run_root: Path) -> Path:
    """Resolve the latest durable checkpoint pointer for one training run root."""
    pointer_path = run_root / "latest_checkpoint.json"
    if not pointer_path.exists():
        raise SystemExit("Resume latest requires a run-root `latest_checkpoint.json` pointer.")
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Latest-checkpoint metadata was malformed.")
    return Path(_required_str(payload, "checkpoint_path"))


def validate_resume_checkpoint_path(run_root: Path, checkpoint_path: Path) -> Path:
    """Reject explicit resume checkpoints that do not belong to the source run root."""
    resolved_run_root = run_root.resolve()
    resolved_checkpoint_path = checkpoint_path.resolve()
    if not resolved_checkpoint_path.exists():
        raise SystemExit(
            f"Resume checkpoint `{resolved_checkpoint_path.as_posix()}` does not exist."
        )
    try:
        resolved_checkpoint_path.relative_to(resolved_run_root)
    except ValueError as exc:
        raise SystemExit(
            "Resume --checkpoint-path must belong to the selected source launch run root."
        ) from exc
    return resolved_checkpoint_path


def resolve_launch_root(output_root: Path, launch_root_arg: Path | None) -> Path:
    """Resolve the launch root for status inspection."""
    if launch_root_arg is not None:
        return launch_root_arg
    pointer_path = latest_pointer_path(output_root)
    if not pointer_path.exists():
        raise SystemExit(
            "Status requires `--launch-root` until a launch has recorded "
            "the latest detached pilot pointer."
        )
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Latest-launch metadata was malformed.")
    return Path(_required_str(payload, "launch_root"))


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Metadata returned malformed `{key}`.")
    return value
