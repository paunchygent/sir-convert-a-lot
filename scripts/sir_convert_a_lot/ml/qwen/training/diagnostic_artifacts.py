"""Machine-readable artifacts for detached Qwen diagnostic replay runs.

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
