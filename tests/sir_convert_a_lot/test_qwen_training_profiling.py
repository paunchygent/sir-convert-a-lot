"""Focused tests for Qwen training profiling helpers."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

SFT_PATCH_ROOT = Path(__file__).resolve().parents[2] / "scripts/devops/qwen_finetuning_patches"
if SFT_PATCH_ROOT.as_posix() not in sys.path:
    sys.path.insert(0, SFT_PATCH_ROOT.as_posix())

PROFILING = importlib.import_module("scripts.devops.qwen_finetuning_patches.sft_12hz_profiling")

TorchProfilerConfig = PROFILING.TorchProfilerConfig
TorchProfilerSession = PROFILING.TorchProfilerSession
resolve_torch_profiler_config = PROFILING.resolve_torch_profiler_config


def test_resolve_torch_profiler_config_rejects_invalid_step_values(tmp_path: Path) -> None:
    """Profiler config should fail fast on invalid bounded schedule values."""
    with pytest.raises(ValueError):
        resolve_torch_profiler_config(
            enabled=True,
            trace_dir=tmp_path / "trace",
            wait_steps=-1,
            warmup_steps=1,
            active_steps=1,
            repeat=1,
            record_shapes=True,
            profile_memory=True,
            with_stack=False,
        )


def test_torch_profiler_session_payload_reports_config_even_when_disabled(tmp_path: Path) -> None:
    """Disabled profiler sessions should still emit deterministic payload fields."""
    config = TorchProfilerConfig(
        enabled=False,
        trace_dir=tmp_path / "profiling/pytorch",
        wait_steps=1,
        warmup_steps=1,
        active_steps=2,
        repeat=1,
        record_shapes=True,
        profile_memory=True,
        with_stack=False,
    )
    session = TorchProfilerSession(config)

    payload = session.payload()
    assert payload["enabled"] is False
    assert payload["trace_dir"].endswith("/profiling/pytorch")
    assert payload["trace_files"] == []
