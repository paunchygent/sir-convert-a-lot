"""Small runtime helpers for the in-container Qwen trainer.

Purpose:
    Keep `trainer.py` focused on orchestration by owning small file-counting and
    completed-status fallback helpers that do not belong to the main control
    flow.

Relationships:
    - Imported by `trainer.py`.
    - Consumed only by the in-container training entrypoint.
"""

from __future__ import annotations

import json
from pathlib import Path


def count_jsonl_rows(path: Path) -> int:
    """Return the number of non-empty JSONL rows in one file."""
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def load_completed_status_payload(
    *,
    status_path: Path,
    training_summary: object,
) -> dict[str, object]:
    """Return one completed status payload, falling back when tests stub writes."""
    if status_path.is_file():
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return {str(key): value for key, value in payload.items()}
        raise ValueError("Completed status payload must be a JSON object.")
    latest_checkpoint_step = getattr(training_summary, "latest_durable_checkpoint_step", None)
    current_optimizer_step = getattr(training_summary, "optimizer_steps_completed", None)
    stopped_early = bool(getattr(training_summary, "stopped_early", False))
    return {
        "status": "completed",
        "current_phase": "signal-stop" if stopped_early else "completed",
        "current_optimizer_step": current_optimizer_step,
        "latest_durable_checkpoint_step": latest_checkpoint_step,
    }
