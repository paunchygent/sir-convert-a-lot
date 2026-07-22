"""Tests for the Qwen stability lab promotion gate.

Purpose:
    Prove the first local promotion rule evaluates the exact fresh-start
    failure family from Qwen stability lab results and does not require another bespoke
    harness.

Relationships:
    - Exercises `qwen_stability_lab_gate.py`.
    - Complements the Qwen stability lab lab runner tests by checking the promotion
      decision layer separately.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab import main
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_gate import (
    DEFAULT_BASELINE_VARIANT,
    DEFAULT_CANDIDATE_VARIANT,
    evaluate_promotion_gate,
)


def test_evaluate_promotion_gate_requires_baseline_failure_and_candidate_finiteness(
    tmp_path: Path,
) -> None:
    """The gate should pass only when baseline reproduces the family cleanly."""
    report = evaluate_promotion_gate(
        results_payload=_results_payload(
            candidate_main_hook=None,
            candidate_sub_hook=None,
            candidate_combined_hook=None,
            candidate_gradient_surface=None,
            candidate_parameter_surface=None,
        ),
        results_path=tmp_path / "results.json",
        baseline_variant=DEFAULT_BASELINE_VARIANT,
        candidate_variant=DEFAULT_CANDIDATE_VARIANT,
    )

    assert report.exact_family_reproduced_by_baseline is True
    assert report.candidate_exact_surfaces_finite is True
    assert report.promotion_passed is True


def test_evaluate_promotion_gate_rejects_candidate_when_exact_surfaces_still_fail(
    tmp_path: Path,
) -> None:
    """The gate should fail when the candidate still reproduces the fresh-start failure family."""
    report = evaluate_promotion_gate(
        results_payload=_results_payload(
            candidate_main_hook="talker_core.layer_16.mlp.gated_product",
            candidate_sub_hook="talker_core.layer_15.output",
            candidate_combined_hook="talker_core.layer_16.mlp.gated_product",
            candidate_gradient_surface="input_text_embedding.grad",
            candidate_parameter_surface="text_embedding.weight.grad",
        ),
        results_path=tmp_path / "results.json",
        baseline_variant=DEFAULT_BASELINE_VARIANT,
        candidate_variant=DEFAULT_CANDIDATE_VARIANT,
    )

    assert report.candidate_exact_surfaces_finite is False
    assert report.promotion_passed is False


def test_qwen_stability_lab_gate_cli_reads_existing_results_and_writes_gate_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public gate command should evaluate an existing matrix run without rerunning it."""
    results_path = tmp_path / "results.json"
    results_path.write_text(
        json.dumps(
            _results_payload(
                candidate_main_hook=None,
                candidate_sub_hook=None,
                candidate_combined_hook=None,
                candidate_gradient_surface=None,
                candidate_parameter_surface=None,
            ),
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    result = main(
        [
            "gate",
            "--output-root",
            tmp_path.as_posix(),
            "--results-path",
            results_path.as_posix(),
        ]
    )
    capsys.readouterr()

    assert result == 0
    gate_payload = json.loads((tmp_path / "gate.json").read_text(encoding="utf-8"))
    assert gate_payload["promotion_passed"] is True
    assert "# Qwen stability lab Promotion Gate" in (tmp_path / "gate.md").read_text(
        encoding="utf-8"
    )


def _results_payload(
    *,
    candidate_main_hook: str | None,
    candidate_sub_hook: str | None,
    candidate_combined_hook: str | None,
    candidate_gradient_surface: str | None,
    candidate_parameter_surface: str | None,
) -> dict[str, object]:
    return {
        "hook_profile": "talker_core_boundary",
        "text_embedding_mask_policy": "text_span_only",
        "matrix_rows": [
            _matrix_row(
                variant="off",
                case_id="pair-main-loss",
                loss_kind="main_loss",
                first_talker_hook="talker_core.layer_16.mlp.gated_product",
                gradient_surface="input_text_embedding.grad",
                parameter_surface="text_embedding.weight.grad",
            ),
            _matrix_row(
                variant="off",
                case_id="pair-sub-talker-loss",
                loss_kind="sub_talker_loss",
                first_talker_hook="talker_core.layer_15.output",
                gradient_surface="input_text_embedding.grad",
                parameter_surface="text_embedding.weight.grad",
            ),
            _matrix_row(
                variant="off",
                case_id="pair-combined-loss",
                loss_kind="combined_loss",
                first_talker_hook="talker_core.layer_16.mlp.gated_product",
                gradient_surface="input_text_embedding.grad",
                parameter_surface="text_embedding.weight.grad",
            ),
            _matrix_row(
                variant="layer16_gated_fp32",
                case_id="pair-main-loss",
                loss_kind="main_loss",
                first_talker_hook=candidate_main_hook,
                gradient_surface=candidate_gradient_surface,
                parameter_surface=candidate_parameter_surface,
            ),
            _matrix_row(
                variant="layer16_gated_fp32",
                case_id="pair-sub-talker-loss",
                loss_kind="sub_talker_loss",
                first_talker_hook=candidate_sub_hook,
                gradient_surface=candidate_gradient_surface,
                parameter_surface=candidate_parameter_surface,
            ),
            _matrix_row(
                variant="layer16_gated_fp32",
                case_id="pair-combined-loss",
                loss_kind="combined_loss",
                first_talker_hook=candidate_combined_hook,
                gradient_surface=candidate_gradient_surface,
                parameter_surface=candidate_parameter_surface,
            ),
        ],
    }


def _matrix_row(
    *,
    variant: str,
    case_id: str,
    loss_kind: str,
    first_talker_hook: str | None,
    gradient_surface: str | None,
    parameter_surface: str | None,
) -> dict[str, object]:
    return {
        "stabilization_variant": variant,
        "case_id": case_id,
        "loss_kind": loss_kind,
        "source_line_numbers": [13, 4],
        "batch_size": 2,
        "interaction_mode": "both_rows",
        "case_has_non_finite": first_talker_hook is not None,
        "first_non_finite_hook_tensor": first_talker_hook,
        "first_non_finite_talker_core_hook_tensor": first_talker_hook,
        "gradient_rca_first_non_finite_surface": gradient_surface,
        "parameter_first_non_finite_surface": parameter_surface,
        "anomaly_operator": ("MulBackward0" if first_talker_hook is not None else None),
    }
