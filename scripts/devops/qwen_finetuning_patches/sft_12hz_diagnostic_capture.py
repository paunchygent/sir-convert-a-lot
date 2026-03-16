"""Trainer-native exact diagnostic-capture helpers for Qwen fine-tuning.

Purpose:
    Define the typed capture-mode contract used to mint one exact durable
    checkpoint at a target optimizer step without relying on host-side stop
    timing or delayed heartbeat visibility.

Relationships:
    - Imported by `sft_12hz_loop.py` and `trainer.py`.
    - Reuses the canonical diagnostic artifact builder from the detached
      Qwen training domain package.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.diagnostic_artifacts import (
    build_diagnostic_state_capture,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting import write_json


@dataclass(frozen=True)
class DiagnosticCaptureConfig:
    """Resolved in-trainer capture contract for one exact target step."""

    enabled: bool
    target_optimizer_step: int | None = None
    artifact_path: Path | None = None
    launch_root_host_path: Path | None = None
    checkpoint_path: Path | None = None
    source_launch_root: str | None = None
    source_checkpoint_path: str | None = None


def diagnostic_capture_config_from_args(args: argparse.Namespace) -> DiagnosticCaptureConfig:
    """Resolve one validated exact-capture config from trainer args."""
    diagnostic_kind = getattr(args, "diagnostic_kind", None)
    if diagnostic_kind != "capture-diagnostic-state":
        return DiagnosticCaptureConfig(enabled=False)
    target_optimizer_step = _optional_int(getattr(args, "diagnostic_target_optimizer_step", None))
    artifact_path = _optional_path(getattr(args, "diagnostic_capture_artifact_path", None))
    launch_root_host_path = _optional_path(
        getattr(args, "diagnostic_capture_launch_root_host_path", None)
    )
    checkpoint_path = _optional_path(getattr(args, "diagnostic_capture_checkpoint_path", None))
    source_launch_root = _optional_str(getattr(args, "diagnostic_source_launch_root", None))
    source_checkpoint_path = _optional_str(getattr(args, "diagnostic_source_checkpoint_path", None))
    missing_fields: list[str] = []
    if target_optimizer_step is None or target_optimizer_step <= 0:
        missing_fields.append("diagnostic_target_optimizer_step")
    if artifact_path is None:
        missing_fields.append("diagnostic_capture_artifact_path")
    if launch_root_host_path is None:
        missing_fields.append("diagnostic_capture_launch_root_host_path")
    if checkpoint_path is None:
        missing_fields.append("diagnostic_capture_checkpoint_path")
    if source_launch_root is None:
        missing_fields.append("diagnostic_source_launch_root")
    if source_checkpoint_path is None:
        missing_fields.append("diagnostic_source_checkpoint_path")
    if missing_fields:
        joined_fields = ", ".join(missing_fields)
        raise ValueError(
            "Capture-diagnostic-state runs require the full exact-capture contract. "
            f"Missing: {joined_fields}."
        )
    return DiagnosticCaptureConfig(
        enabled=True,
        target_optimizer_step=target_optimizer_step,
        artifact_path=artifact_path,
        launch_root_host_path=launch_root_host_path,
        checkpoint_path=checkpoint_path,
        source_launch_root=source_launch_root,
        source_checkpoint_path=source_checkpoint_path,
    )


def write_diagnostic_capture_artifact(
    config: DiagnosticCaptureConfig,
    *,
    final_status: Mapping[str, object],
) -> None:
    """Persist one machine-readable exact-capture artifact from trainer truth."""
    if not config.enabled:
        return
    if (
        config.target_optimizer_step is None
        or config.artifact_path is None
        or config.launch_root_host_path is None
        or config.checkpoint_path is None
        or config.source_launch_root is None
        or config.source_checkpoint_path is None
    ):
        raise ValueError("Capture artifact write expected a fully resolved capture config.")
    write_json(
        config.artifact_path,
        build_diagnostic_state_capture(
            source_launch_root=Path(config.source_launch_root),
            source_checkpoint_path=Path(config.source_checkpoint_path),
            target_optimizer_step=config.target_optimizer_step,
            launch_root=config.launch_root_host_path,
            run_root=config.checkpoint_path.parent.parent,
            checkpoint_path=config.checkpoint_path,
            checkpoint_step=config.target_optimizer_step,
            final_status=final_status,
        ),
    )


def _optional_int(value: object) -> int | None:
    """Return one optional integer from a trainer arg payload."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"Expected one integer-compatible value, got `{type(value).__name__}`.")


def _optional_path(value: object) -> Path | None:
    """Return one optional path from a trainer arg payload."""
    if value is None:
        return None
    return Path(str(value))


def _optional_str(value: object) -> str | None:
    """Return one optional string from a trainer arg payload."""
    if value is None:
        return None
    return str(value)
