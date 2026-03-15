"""Machine-readable artifacts for detached Qwen diagnostic and RCA runs.

Purpose:
    Persist a compact replay bundle for `diagnose-non-finite` runs so bounded
    root-cause investigations can reuse one captured failure window instead of
    depending on repeated long-running live reruns.

Relationships:
    - Used by the in-container trainer when running diagnostic mode.
    - Used by the detached diagnostic orchestration and tests as the canonical
      reader/writer for replay-bundle artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


def diagnostic_replay_bundle_path(output_dir: Path) -> Path:
    """Return the canonical replay-bundle path for one diagnostic run root."""
    return output_dir / "diagnostic_replay_bundle.json"


def diagnostic_state_capture_path(launch_root: Path) -> Path:
    """Return the capture artifact path for one reusable near-boundary state."""
    return launch_root / "diagnostic_state_capture.json"


def diagnostic_window_artifact_dir(output_dir: Path) -> Path:
    """Return the artifact directory for per-step diagnostic window payloads."""
    return output_dir / "diagnostic-window"


def diagnostic_window_artifact_path(output_dir: Path, *, optimizer_step: int) -> Path:
    """Return the per-step diagnostic-window artifact path."""
    return diagnostic_window_artifact_dir(output_dir) / (
        f"optimizer-step-{optimizer_step:08d}.json"
    )


def build_diagnostic_replay_bundle(
    *,
    diagnostic: Mapping[str, object],
    report: Mapping[str, object],
    status: Mapping[str, object],
) -> dict[str, object]:
    """Build one machine-readable replay bundle from status/report truth."""
    failure = report.get("failure")
    return {
        "diagnostic": dict(diagnostic),
        "failure": dict(failure) if isinstance(failure, Mapping) else None,
        "status": dict(status),
    }


def build_diagnostic_state_capture(
    *,
    source_launch_root: Path,
    source_checkpoint_path: Path,
    target_optimizer_step: int,
    launch_root: Path,
    run_root: Path,
    checkpoint_path: Path,
    checkpoint_step: int,
    final_status: Mapping[str, object],
) -> dict[str, object]:
    """Build one machine-readable reusable-state capture payload."""
    return {
        "kind": "capture-diagnostic-state",
        "source_launch_root": source_launch_root.as_posix(),
        "source_checkpoint_path": source_checkpoint_path.as_posix(),
        "target_optimizer_step": target_optimizer_step,
        "launch_root": launch_root.as_posix(),
        "run_root": run_root.as_posix(),
        "captured_checkpoint_path": checkpoint_path.as_posix(),
        "captured_checkpoint_step": checkpoint_step,
        "final_status": dict(final_status),
    }
