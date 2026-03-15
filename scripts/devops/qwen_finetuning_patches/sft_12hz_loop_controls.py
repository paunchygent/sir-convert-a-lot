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
from collections import deque
from dataclasses import dataclass, field
from typing import Deque

import torch

DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS = 20
DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS = 3
DEFAULT_FINITE_LOSS_RECENT_OBSERVATION_WINDOW = 8


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
    """One host-visible loss observation for guard/logging decisions."""

    optimizer_step: int
    current_epoch: int
    current_train_iteration: int
    loss_value: float
    main_loss_value: float
    sub_talker_loss_value: float
    grad_norm_value: float | None
    is_finite: bool
    main_loss_is_finite: bool
    sub_talker_loss_is_finite: bool
    grad_norm_is_finite: bool | None
    step_forensics: dict[str, object] | None = None

    def payload(self) -> dict[str, object]:
        """Return one JSON-safe payload for history and failure artifacts."""
        return {
            "optimizer_step": self.optimizer_step,
            "current_epoch": self.current_epoch,
            "current_train_iteration": self.current_train_iteration,
            "loss_value": self.loss_value,
            "combined_loss_value": self.loss_value,
            "main_loss_value": self.main_loss_value,
            "sub_talker_loss_value": self.sub_talker_loss_value,
            "grad_norm_value": self.grad_norm_value,
            "combined_loss_is_finite": self.is_finite,
            "main_loss_is_finite": self.main_loss_is_finite,
            "sub_talker_loss_is_finite": self.sub_talker_loss_is_finite,
            "grad_norm_is_finite": self.grad_norm_is_finite,
            "step_forensics": self.step_forensics,
        }


@dataclass(frozen=True)
class _PendingLossObservation:
    """One asynchronously staged loss scalar waiting for host consumption."""

    optimizer_step: int
    current_epoch: int
    current_train_iteration: int
    staged_loss_cpu: torch.Tensor
    staged_main_loss_cpu: torch.Tensor
    staged_sub_talker_loss_cpu: torch.Tensor
    staged_grad_norm_cpu: torch.Tensor | None
    ready_event: torch.cuda.Event | None
    step_forensics: dict[str, object] | None


@dataclass
class AsyncLossObserver:
    """Stage optimizer-step losses for later host inspection without blocking each step."""

    _pending: Deque[_PendingLossObservation]

    def __init__(self) -> None:
        self._pending = deque()

    def submit(
        self,
        *,
        loss: torch.Tensor,
        main_loss: torch.Tensor,
        sub_talker_loss: torch.Tensor,
        grad_norm: torch.Tensor | float | None,
        step_forensics: dict[str, object] | None,
        optimizer_step: int,
        current_epoch: int,
        current_train_iteration: int,
    ) -> None:
        """Stage one optimizer-step loss for later host-side inspection."""
        detached_loss = _detach_scalar(loss)
        detached_main_loss = _detach_scalar(main_loss)
        detached_sub_talker_loss = _detach_scalar(sub_talker_loss)
        detached_grad_norm = None if grad_norm is None else _detach_scalar(grad_norm)
        if (
            detached_loss.device.type != "cuda"
            and detached_main_loss.device.type != "cuda"
            and detached_sub_talker_loss.device.type != "cuda"
            and (detached_grad_norm is None or detached_grad_norm.device.type != "cuda")
        ):
            self._pending.append(
                _PendingLossObservation(
                    optimizer_step=optimizer_step,
                    current_epoch=current_epoch,
                    current_train_iteration=current_train_iteration,
                    staged_loss_cpu=detached_loss.to(device="cpu"),
                    staged_main_loss_cpu=detached_main_loss.to(device="cpu"),
                    staged_sub_talker_loss_cpu=detached_sub_talker_loss.to(device="cpu"),
                    staged_grad_norm_cpu=(
                        None if detached_grad_norm is None else detached_grad_norm.to(device="cpu")
                    ),
                    ready_event=None,
                    step_forensics=step_forensics,
                )
            )
            return

        staged_loss_cpu = _copy_scalar_to_cpu(detached_loss)
        staged_main_loss_cpu = _copy_scalar_to_cpu(detached_main_loss)
        staged_sub_talker_loss_cpu = _copy_scalar_to_cpu(detached_sub_talker_loss)
        staged_grad_norm_cpu = (
            None if detached_grad_norm is None else _copy_scalar_to_cpu(detached_grad_norm)
        )
        event_device = next(
            scalar.device
            for scalar in (
                detached_loss,
                detached_main_loss,
                detached_sub_talker_loss,
                detached_grad_norm,
            )
            if scalar is not None and scalar.device.type == "cuda"
        )
        with torch.cuda.device(event_device):
            ready_event = torch.cuda.Event()
            torch.cuda.current_stream().record_event(ready_event)
        self._pending.append(
            _PendingLossObservation(
                optimizer_step=optimizer_step,
                current_epoch=current_epoch,
                current_train_iteration=current_train_iteration,
                staged_loss_cpu=staged_loss_cpu,
                staged_main_loss_cpu=staged_main_loss_cpu,
                staged_sub_talker_loss_cpu=staged_sub_talker_loss_cpu,
                staged_grad_norm_cpu=staged_grad_norm_cpu,
                ready_event=ready_event,
                step_forensics=step_forensics,
            )
        )

    def drain_ready(self, *, force: bool) -> list[LossObservation]:
        """Return all ready staged losses, synchronizing only when explicitly requested."""
        observations: list[LossObservation] = []
        while self._pending:
            pending = self._pending[0]
            if pending.ready_event is not None:
                if force:
                    pending.ready_event.synchronize()
                elif not pending.ready_event.query():
                    break
            self._pending.popleft()
            loss_value = float(pending.staged_loss_cpu.item())
            main_loss_value = float(pending.staged_main_loss_cpu.item())
            sub_talker_loss_value = float(pending.staged_sub_talker_loss_cpu.item())
            grad_norm_value = (
                None
                if pending.staged_grad_norm_cpu is None
                else float(pending.staged_grad_norm_cpu.item())
            )
            observations.append(
                LossObservation(
                    optimizer_step=pending.optimizer_step,
                    current_epoch=pending.current_epoch,
                    current_train_iteration=pending.current_train_iteration,
                    loss_value=loss_value,
                    main_loss_value=main_loss_value,
                    sub_talker_loss_value=sub_talker_loss_value,
                    grad_norm_value=grad_norm_value,
                    is_finite=math.isfinite(loss_value),
                    main_loss_is_finite=math.isfinite(main_loss_value),
                    sub_talker_loss_is_finite=math.isfinite(sub_talker_loss_value),
                    grad_norm_is_finite=(
                        None if grad_norm_value is None else math.isfinite(grad_norm_value)
                    ),
                    step_forensics=pending.step_forensics,
                )
            )
        return observations


class NonFiniteLossError(RuntimeError):
    """Raised when the non-finite loss streak reaches the configured threshold."""

    def __init__(
        self,
        *,
        optimizer_step: int,
        current_epoch: int,
        current_train_iteration: int,
        consecutive_non_finite_steps: int,
        max_consecutive_non_finite_steps: int,
        loss_value: float,
        main_loss_value: float | None = None,
        sub_talker_loss_value: float | None = None,
        grad_norm_value: float | None = None,
        step_forensics: dict[str, object] | None = None,
        recent_observations: list[dict[str, object]] | None = None,
    ) -> None:
        self.optimizer_step = optimizer_step
        self.current_epoch = current_epoch
        self.current_train_iteration = current_train_iteration
        self.consecutive_non_finite_steps = consecutive_non_finite_steps
        self.max_consecutive_non_finite_steps = max_consecutive_non_finite_steps
        self.loss_value = loss_value
        self.main_loss_value = main_loss_value
        self.sub_talker_loss_value = sub_talker_loss_value
        self.grad_norm_value = grad_norm_value
        self.step_forensics = step_forensics
        self.recent_observations = recent_observations
        self.loss_is_finite = math.isfinite(loss_value)
        self.main_loss_is_finite = (
            None if main_loss_value is None else math.isfinite(main_loss_value)
        )
        self.sub_talker_loss_is_finite = (
            None if sub_talker_loss_value is None else math.isfinite(sub_talker_loss_value)
        )
        self.grad_norm_is_finite = (
            None if grad_norm_value is None else math.isfinite(grad_norm_value)
        )
        super().__init__(
            "Non-finite loss guard triggered after "
            f"{consecutive_non_finite_steps} consecutive optimizer steps "
            f"(threshold={max_consecutive_non_finite_steps}, "
            f"optimizer_step={optimizer_step}, loss={loss_value}, "
            f"main_loss={main_loss_value}, sub_talker_loss={sub_talker_loss_value}, "
            f"grad_norm={grad_norm_value})."
        )

    def payload(self) -> dict[str, object]:
        """Return a JSON-safe failure payload for status/report artifacts."""
        return {
            "enabled": True,
            "triggered": True,
            "trigger_reason": "non-finite-loss",
            "optimizer_step": self.optimizer_step,
            "current_epoch": self.current_epoch,
            "current_train_iteration": self.current_train_iteration,
            "consecutive_non_finite_steps": self.consecutive_non_finite_steps,
            "max_consecutive_non_finite_steps": self.max_consecutive_non_finite_steps,
            "loss_value": self.loss_value,
            "combined_loss_value": self.loss_value,
            "main_loss_value": self.main_loss_value,
            "sub_talker_loss_value": self.sub_talker_loss_value,
            "grad_norm_value": self.grad_norm_value,
            "combined_loss_is_finite": self.loss_is_finite,
            "main_loss_is_finite": self.main_loss_is_finite,
            "sub_talker_loss_is_finite": self.sub_talker_loss_is_finite,
            "grad_norm_is_finite": self.grad_norm_is_finite,
            "step_forensics": self.step_forensics,
            "recent_observations": self.recent_observations,
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
    recent_observations: Deque[dict[str, object]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the bounded recent-observation history."""
        self.recent_observations = deque(maxlen=DEFAULT_FINITE_LOSS_RECENT_OBSERVATION_WINDOW)

    def observe(self, observation: LossObservation) -> None:
        """Record one optimizer-step loss observation and fail when the streak holds."""
        self.recent_observations.append(observation.payload())
        if observation.is_finite:
            self.consecutive_non_finite_steps = 0
            self.last_non_finite_optimizer_step = None
            self.last_non_finite_loss_value = None
            return

        self.consecutive_non_finite_steps += 1
        self.last_non_finite_optimizer_step = observation.optimizer_step
        self.last_non_finite_loss_value = observation.loss_value
        if self.consecutive_non_finite_steps >= self.config.max_consecutive_non_finite_steps:
            raise NonFiniteLossError(
                optimizer_step=observation.optimizer_step,
                current_epoch=observation.current_epoch,
                current_train_iteration=observation.current_train_iteration,
                consecutive_non_finite_steps=self.consecutive_non_finite_steps,
                max_consecutive_non_finite_steps=self.config.max_consecutive_non_finite_steps,
                loss_value=observation.loss_value,
                main_loss_value=observation.main_loss_value,
                sub_talker_loss_value=observation.sub_talker_loss_value,
                grad_norm_value=observation.grad_norm_value,
                step_forensics=observation.step_forensics,
                recent_observations=list(self.recent_observations),
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


def _detach_scalar(value: torch.Tensor | float | int) -> torch.Tensor:
    """Detach one scalar-like value into a float32 rank-0 tensor."""
    if isinstance(value, torch.Tensor):
        return value.detach().to(dtype=torch.float32).view(())
    return torch.tensor(float(value), dtype=torch.float32)


def _copy_scalar_to_cpu(value: torch.Tensor) -> torch.Tensor:
    """Copy one detached scalar to CPU, using pinned memory for CUDA tensors."""
    if value.device.type != "cuda":
        return value.to(device="cpu")
    staged_value = torch.empty((), dtype=torch.float32, device="cpu", pin_memory=True)
    staged_value.copy_(value, non_blocking=True)
    return staged_value
