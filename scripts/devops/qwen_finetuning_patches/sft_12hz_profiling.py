"""Profiling helpers for the patched Qwen Qwen pilot training trainer.

Purpose:
    Keep bounded PyTorch profiler setup and phase-marker helpers out of
    `sft_12hz.py` so the trainer remains focused on training orchestration.

Relationships:
    - Imported by `sft_12hz.py` to enable opt-in PyTorch profiling.
    - Writes profiler traces under the Qwen pilot training run root.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import ContextManager, Iterator

import torch
from torch.profiler import ProfilerActivity, profile, schedule, tensorboard_trace_handler

DEFAULT_TORCH_PROFILER_ENABLED = False
DEFAULT_TORCH_PROFILER_WAIT_STEPS = 1
DEFAULT_TORCH_PROFILER_WARMUP_STEPS = 1
DEFAULT_TORCH_PROFILER_ACTIVE_STEPS = 4
DEFAULT_TORCH_PROFILER_REPEAT = 1
DEFAULT_TORCH_PROFILER_RECORD_SHAPES = True
DEFAULT_TORCH_PROFILER_PROFILE_MEMORY = True
DEFAULT_TORCH_PROFILER_WITH_STACK = False


@dataclass(frozen=True)
class TorchProfilerConfig:
    """Normalized bounded profiler settings for one training run."""

    enabled: bool
    trace_dir: Path
    wait_steps: int
    warmup_steps: int
    active_steps: int
    repeat: int
    record_shapes: bool
    profile_memory: bool
    with_stack: bool


class TorchProfilerSession:
    """No-op compatible wrapper around one bounded PyTorch profiler."""

    def __init__(self, config: TorchProfilerConfig) -> None:
        self._config = config
        self._profiler: profile | None = None

    def start(self) -> None:
        """Start the profiler when profiling is enabled."""
        if not self._config.enabled:
            return
        self._config.trace_dir.mkdir(parents=True, exist_ok=True)
        activities: list[ProfilerActivity] = [ProfilerActivity.CPU]
        if torch.cuda.is_available():
            activities.append(ProfilerActivity.CUDA)
        self._profiler = profile(
            activities=activities,
            schedule=schedule(
                wait=self._config.wait_steps,
                warmup=self._config.warmup_steps,
                active=self._config.active_steps,
                repeat=self._config.repeat,
            ),
            on_trace_ready=tensorboard_trace_handler(self._config.trace_dir.as_posix()),
            record_shapes=self._config.record_shapes,
            profile_memory=self._config.profile_memory,
            with_stack=self._config.with_stack,
        )
        self._profiler.__enter__()

    def stop(self) -> None:
        """Stop the profiler when one is active."""
        if self._profiler is None:
            return
        self._profiler.__exit__(None, None, None)
        self._profiler = None

    def step(self) -> None:
        """Advance one profiler step when profiling is enabled."""
        if self._profiler is None:
            return
        self._profiler.step()

    def phase(self, name: str) -> ContextManager[None]:
        """Return one context manager that marks a profiling phase."""
        if self._profiler is None:
            return _null_phase_context()
        return torch.autograd.profiler.record_function(name)

    def payload(self) -> dict[str, bool | int | str | list[str]]:
        """Return a JSON-safe profiler configuration and trace manifest."""
        trace_files = sorted(
            path.as_posix()
            for path in self._config.trace_dir.glob("**/*.pt.trace.json")
            if path.is_file()
        )
        return {
            "enabled": self._config.enabled,
            "trace_dir": self._config.trace_dir.as_posix(),
            "wait_steps": self._config.wait_steps,
            "warmup_steps": self._config.warmup_steps,
            "active_steps": self._config.active_steps,
            "repeat": self._config.repeat,
            "record_shapes": self._config.record_shapes,
            "profile_memory": self._config.profile_memory,
            "with_stack": self._config.with_stack,
            "trace_files": trace_files,
        }


@contextmanager
def _null_phase_context() -> Iterator[None]:
    """Return one typed no-op phase context for disabled profiling."""
    with nullcontext():
        yield


def resolve_torch_profiler_config(
    *,
    enabled: bool,
    trace_dir: Path,
    wait_steps: int,
    warmup_steps: int,
    active_steps: int,
    repeat: int,
    record_shapes: bool,
    profile_memory: bool,
    with_stack: bool,
) -> TorchProfilerConfig:
    """Validate and return one normalized profiler config payload."""
    if wait_steps < 0:
        raise ValueError("`torch_profiler_wait_steps` cannot be negative.")
    if warmup_steps <= 0:
        raise ValueError("`torch_profiler_warmup_steps` must be positive.")
    if active_steps <= 0:
        raise ValueError("`torch_profiler_active_steps` must be positive.")
    if repeat <= 0:
        raise ValueError("`torch_profiler_repeat` must be positive.")
    return TorchProfilerConfig(
        enabled=enabled,
        trace_dir=trace_dir,
        wait_steps=wait_steps,
        warmup_steps=warmup_steps,
        active_steps=active_steps,
        repeat=repeat,
        record_shapes=record_shapes,
        profile_memory=profile_memory,
        with_stack=with_stack,
    )
