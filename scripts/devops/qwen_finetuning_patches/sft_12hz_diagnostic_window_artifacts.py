"""Artifact helpers for bounded Qwen diagnostic-window RCA output.

Purpose:
    Persist one machine-readable per-step RCA artifact during targeted
    diagnostic runs so operators can inspect the failing accumulation window
    without relying on ad hoc terminal scraping.

Relationships:
    - Imported by `sft_12hz_train_step.py`.
    - Shares canonical artifact paths with
      `ml.qwen.training.diagnostic_artifacts`.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.diagnostic_artifacts import (
    diagnostic_window_artifact_path,
)


def write_diagnostic_window_artifact(
    *,
    output_model_path: Path,
    optimizer_step: int,
    current_train_iteration: int,
    diagnostic_kind: str,
    start_optimizer_step: int,
    end_optimizer_step: int,
    step_forensics: dict[str, object],
) -> None:
    """Write one machine-readable RCA artifact for the active optimizer step."""
    artifact_path = diagnostic_window_artifact_path(
        output_model_path.parent,
        optimizer_step=optimizer_step,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(
        json.dumps(
            {
                "diagnostic_kind": diagnostic_kind,
                "start_optimizer_step": start_optimizer_step,
                "end_optimizer_step": end_optimizer_step,
                "optimizer_step": optimizer_step,
                "current_train_iteration": current_train_iteration,
                "step_forensics": step_forensics,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
