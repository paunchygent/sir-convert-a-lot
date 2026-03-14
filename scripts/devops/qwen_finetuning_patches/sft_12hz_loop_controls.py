"""Loop-control helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Keep heartbeat cadence and finite-loss guard logic out of `sft_12hz.py`
    so the training loop can stay focused on model orchestration while still
    enforcing truthful bounded observability and fast failure on persistent
    non-finite loss.

Relationships:
    - Imported by `sft_12hz.py` to decide when train-phase updates should be
      emitted and when a run must fail closed for acceptance purposes.
    - Its payloads are persisted into status and report artifacts by the
      training domain entrypoints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch

DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS = 20
DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS = 3


@dataclass(frozen=True)
class TrainingHeartbeatPolicy:
    """Bounded cadence for train-phase logs and heartbeats."""

    interval_optimizer_steps: int = DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS

    def __post_init__(self) -> None:
        if self.interval_optimizer_steps <= 0:
            raise ValueError("`heartbeat_interval_optimizer_steps` must be positive.")

    def should_emit_train_update(self, optimizer_steps_completed: int) -> bool:
        """Return whether this optimizer step should emit train-phase updates."""
        if optimizer_steps_completed <= 0:
            return False
        return optimizer_steps_completed % self.interval_optimizer_steps == 0

    def payload(self) -> dict[str, int]:
        """Return a JSON-safe heartbeat-policy payload."""
        return {"interval_optimizer_steps": self.interval_optimizer_steps}


@dataclass(frozen=True)
class LossObservation:
    """One synchronized scalar loss observation for guard/logging decisions."""

    loss_value: float
    is_finite: bool


def observe_loss(loss: torch.Tensor) -> LossObservation:
    """Synchronize one scalar loss value and classify its finiteness."""
    loss_value = float(loss.detach())
    return LossObservation(loss_value=loss_value, is_finite=math.isfinite(loss_value))


class NonFiniteLossError(RuntimeError):
    """Raised when the non-finite loss streak reaches the configured threshold."""

    def __init__(
        self,
        *,
        optimizer_step: int,
        consecutive_non_finite_steps: int,
        max_consecutive_non_finite_steps: int,
        loss_value: float,
    ) -> None:
        self.optimizer_step = optimizer_step
        self.consecutive_non_finite_steps = consecutive_non_finite_steps
        self.max_consecutive_non_finite_steps = max_consecutive_non_finite_steps
        self.loss_value = loss_value
        super().__init__(
            "Non-finite loss guard triggered after "
            f"{consecutive_non_finite_steps} consecutive optimizer steps "
            f"(threshold={max_consecutive_non_finite_steps}, "
            f"optimizer_step={optimizer_step}, loss={loss_value})."
        )

    def payload(self) -> dict[str, bool | float | int | str]:
        """Return a JSON-safe failure payload for status/report artifacts."""
        return {
            "enabled": True,
            "triggered": True,
            "trigger_reason": "non-finite-loss",
            "optimizer_step": self.optimizer_step,
            "consecutive_non_finite_steps": self.consecutive_non_finite_steps,
            "max_consecutive_non_finite_steps": self.max_consecutive_non_finite_steps,
            "loss_value": self.loss_value,
            "acceptance_measurement_valid": False,
        }


@dataclass(frozen=True)
class FiniteLossGuardConfig:
    """Configuration for the persistent non-finite loss guard."""

    max_consecutive_non_finite_steps: int = DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS

    def __post_init__(self) -> None:
        if self.max_consecutive_non_finite_steps <= 0:
            raise ValueError("`finite_loss_max_consecutive_steps` must be positive.")

    def payload(self) -> dict[str, bool | int]:
        """Return a JSON-safe guard-configuration payload."""
        return {
            "enabled": True,
            "max_consecutive_non_finite_steps": self.max_consecutive_non_finite_steps,
        }


@dataclass
class FiniteLossGuardState:
    """Track one bounded streak of consecutive non-finite optimizer losses."""

    config: FiniteLossGuardConfig
    consecutive_non_finite_steps: int = 0
    last_non_finite_optimizer_step: int | None = None
    last_non_finite_loss_value: float | None = None

    def observe(self, observation: LossObservation, *, optimizer_step: int) -> None:
        """Record one optimizer-step loss observation and fail when the streak holds."""
        if observation.is_finite:
            self.consecutive_non_finite_steps = 0
            self.last_non_finite_optimizer_step = None
            self.last_non_finite_loss_value = None
            return

        self.consecutive_non_finite_steps += 1
        self.last_non_finite_optimizer_step = optimizer_step
        self.last_non_finite_loss_value = observation.loss_value
        if self.consecutive_non_finite_steps >= self.config.max_consecutive_non_finite_steps:
            raise NonFiniteLossError(
                optimizer_step=optimizer_step,
                consecutive_non_finite_steps=self.consecutive_non_finite_steps,
                max_consecutive_non_finite_steps=self.config.max_consecutive_non_finite_steps,
                loss_value=observation.loss_value,
            )

    def payload(self) -> dict[str, bool | float | int | None]:
        """Return a JSON-safe guard-state payload."""
        return {
            "enabled": True,
            "triggered": False,
            "max_consecutive_non_finite_steps": self.config.max_consecutive_non_finite_steps,
            "consecutive_non_finite_steps": self.consecutive_non_finite_steps,
            "last_non_finite_optimizer_step": self.last_non_finite_optimizer_step,
            "last_non_finite_loss_value": self.last_non_finite_loss_value,
        }
