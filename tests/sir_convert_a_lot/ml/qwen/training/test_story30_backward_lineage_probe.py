"""Focused tests for the Story 30 backward-lineage probe helpers.

Purpose:
    Keep the T212 probe honest by locking the requested branch order and the
    pair-versus-row interaction classification before any Hemma run.

Relationships:
    - Exercises pure helper functions in `backward_lineage_probe.py`.
    - Complements the proof-surface tests with the smallest local signal.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.backward_lineage_probe import (
    BranchInteractionSummary,
    ProbeCaseResult,
    TensorGradientObservation,
    _branch_summaries,
    _case_specs,
)


def test_case_specs_follow_requested_loss_order_before_row_isolation() -> None:
    """T212 must probe pair branches before any row-isolation cases."""
    cases = _case_specs((13, 4))

    assert [case.case_id for case in cases[:3]] == [
        "pair-main-loss",
        "pair-sub-talker-loss",
        "pair-combined-loss",
    ]
    assert [case.case_id for case in cases[3:]] == [
        "line-13-main-loss",
        "line-4-main-loss",
        "line-13-sub-talker-loss",
        "line-4-sub-talker-loss",
        "line-13-combined-loss",
        "line-4-combined-loss",
    ]


def test_branch_summaries_classify_pair_only_vs_row_local_behavior() -> None:
    """Branch summaries should tell us whether failure is pair-only or row-local."""
    cases = [
        _case_result("pair-main-loss", "main_loss", (13, 4), non_finite=True),
        _case_result("pair-sub-talker-loss", "sub_talker_loss", (13, 4), non_finite=False),
        _case_result("pair-combined-loss", "combined_loss", (13, 4), non_finite=True),
        _case_result("line-13-main-loss", "main_loss", (13,), non_finite=False),
        _case_result("line-4-main-loss", "main_loss", (4,), non_finite=False),
        _case_result("line-13-sub-talker-loss", "sub_talker_loss", (13,), non_finite=False),
        _case_result("line-4-sub-talker-loss", "sub_talker_loss", (4,), non_finite=False),
        _case_result("line-13-combined-loss", "combined_loss", (13,), non_finite=True),
        _case_result("line-4-combined-loss", "combined_loss", (4,), non_finite=False),
    ]

    summaries = _branch_summaries(cases, (13, 4))

    assert summaries == (
        BranchInteractionSummary(
            loss_kind="main_loss",
            pair_has_non_finite=True,
            first_row_has_non_finite=False,
            second_row_has_non_finite=False,
            interaction_mode="pair_only",
        ),
        BranchInteractionSummary(
            loss_kind="sub_talker_loss",
            pair_has_non_finite=False,
            first_row_has_non_finite=False,
            second_row_has_non_finite=False,
            interaction_mode="none",
        ),
        BranchInteractionSummary(
            loss_kind="combined_loss",
            pair_has_non_finite=True,
            first_row_has_non_finite=True,
            second_row_has_non_finite=False,
            interaction_mode="first_row_only",
        ),
    )


def _case_result(
    case_id: str,
    loss_kind: str,
    source_line_numbers: tuple[int, ...],
    *,
    non_finite: bool,
) -> ProbeCaseResult:
    return ProbeCaseResult(
        case_id=case_id,
        loss_kind=loss_kind,
        source_line_numbers=source_line_numbers,
        batch_size=len(source_line_numbers),
        loss_value=1.0,
        main_loss_value=1.0,
        sub_talker_loss_value=1.0,
        first_non_finite_hook_tensor=("input_embeddings" if non_finite else None),
        first_non_finite_hook_order=(1 if non_finite else None),
        first_non_finite_talker_core_hook_tensor=None,
        first_non_finite_talker_core_hook_order=None,
        hooked_tensor_gradients=(
            ()
            if not non_finite
            else (
                TensorGradientObservation(
                    tensor_name="input_embeddings",
                    hook_order=1,
                    is_finite=False,
                    nan_count=1,
                    inf_count=0,
                    max_abs=None,
                ),
            )
        ),
        gradient_rca={"first_non_finite_surface": None},
        parameter_gradient_probes={"first_non_finite_surface": None},
        anomaly_trace=None,
        batch_provenance=(),
    )
