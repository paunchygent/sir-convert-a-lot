"""Focused tests for Qwen reporting failure projection helpers.

Purpose:
    Verify the bounded failure-projection logic that normalizes live progress
    and exception-derived counters for failed status/report artifacts.

Relationships:
    - Exercises `reporting.failure_projection`.
    - Complements reporter integration tests with direct failure-contract checks.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard import (
    OptimizerBoundaryCorruptionError,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.failure_projection import (
    resolve_failed_progress,
)


def test_resolve_failed_progress_prefers_optimizer_boundary_error_counters() -> None:
    """Failure projection should override stale live counters with exception truth."""
    exc = OptimizerBoundaryCorruptionError(
        trigger_reason="pre_step_non_finite_grad_norm",
        optimizer_step=1405,
        current_epoch=5,
        current_train_iteration=804,
        loss_value=3.8,
        main_loss_value=1.5,
        sub_talker_loss_value=7.3,
        grad_norm_value=float("nan"),
        optimizer_step_attempted=False,
        optimizer_step_completed=False,
        targeted_parameter_names=["text_embedding.weight"],
        first_non_finite_surface="grad_norm",
        pre_step_parameter_probes={},
        pre_step_gradient_probes={},
        pre_step_optimizer_state_probes={},
        post_step_parameter_probes=None,
        post_step_optimizer_state_probes=None,
        step_forensics=None,
    )

    payload = resolve_failed_progress(
        live_progress={
            "current_epoch": 1,
            "current_optimizer_step": 1300,
            "current_train_iteration": 384,
            "latest_eval_loss": 6.57,
            "best_eval_loss": 6.57,
            "best_eval_step": 1300,
            "eval_runs_completed": 1,
        },
        exc=exc,
    )

    assert payload is not None
    assert payload["current_epoch"] == 5
    assert payload["current_optimizer_step"] == 1405
    assert payload["current_train_iteration"] == 804
    assert payload["best_eval_step"] == 1300
