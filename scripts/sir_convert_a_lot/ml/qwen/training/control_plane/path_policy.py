"""Path-governance helpers for Qwen training control-plane commands.

Purpose:
    Enforce scratch-root and existence requirements on operator-supplied or
    launch-derived paths before detached execution begins.

Relationships:
    - Used by eval, schedule, diagnose, and resume use cases.
    - Consumes `TrainingSettings` scratch-root policy.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings


def require_under_scratch_root(settings: TrainingSettings, path: Path, *, label: str) -> Path:
    """Fail closed when one eval-related path escapes the mounted scratch root."""
    resolved_path = path.resolve()
    try:
        resolved_path.relative_to(settings.scratch_build_root.resolve())
    except ValueError as exc:
        raise SystemExit(
            f"`{label}` must live under `{settings.scratch_build_root.as_posix()}`."
        ) from exc
    return resolved_path


def require_existing_path(path: Path, *, label: str) -> Path:
    """Fail closed when one operator-supplied path does not exist."""
    resolved_path = path.resolve()
    if not resolved_path.exists():
        raise SystemExit(f"`{label}` did not exist: {resolved_path.as_posix()}")
    return resolved_path
