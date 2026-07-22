"""Focused tests for the fp32-scaled output Qwen stability lab fp32-scaled-output assessment.

Purpose:
    Lock the post-multiply-site confirmation seam split contract so Qwen stability lab can
    truthfully decide
    whether the first reproducible break is born in the fp32-scaled layer-15
    output result or only in the final emitted tensor.

Relationships:
    - Exercises `qwen_fp32_scaled_layer15_output_assessment.py`.
    - Reuses `qwen_stability_lab_contracts.py` for compact matrix rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_fp32_scaled_layer15_output_assessment as fp32_scaled_output_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_LAYER15_OUTPUT_MULTIPLY_FP32_SCALED_OUTPUT_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow,
    QwenFp32ScaledLayer15OutputAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

_FP32_SCALED_LAYER15_OUTPUT_VARIANT = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3_"
    "layer15_output_scale_fp32"
)
_BUILD_ASSESSMENT = fp32_scaled_output_assessment.build_fp32_scaled_layer15_output_assessment


def test_validate_fp32_scaled_layer15_output_contract_rejects_wrong_family() -> None:
    """The fp32-scaled output split probe should accept only the fixed multiply-site confirmation
    confirmation variant.
    """
    settings = QwenStabilityLabSettings(
        output_root=Path("/tmp/qwen_stability"),
        dockerfile_path=Path("Dockerfile"),
        image="test-image",
        model_id="test-model",
        hf_cache_dir=Path("/tmp/hf"),
        hf_cache_home_mount=Path("/tmp/hf-home"),
        output_root_home_mount_base=Path("/tmp/output-home"),
        source_bundle_root=Path("/tmp/bundle"),
        manifest_family="swedish_pilot_train",
        source_lines=(13, 4),
        text_embedding_mask_policy="text_span_only",
        hook_profile=TALKER_CORE_POST_LAYER15_OUTPUT_MULTIPLY_FP32_SCALED_OUTPUT_HOOK_PROFILE,
        stabilization_variants=(_FP32_SCALED_LAYER15_OUTPUT_VARIANT, "off"),
        build_image=False,
    )

    with pytest.raises(
        SystemExit,
        match="supports only the exact fixed LAYER15_OUTPUT_MULTIPLY confirmation variant",
    ):
        fp32_scaled_output_assessment.validate_fp32_scaled_layer15_output_contract(settings)


def test_build_fp32_scaled_layer15_output_assessment_marks_fp32_scaled_output() -> None:
    """All-three agreement on the fp32-scaled seam should keep drilling there."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output.fp32_scaled_output",
            first_row="talker_core.layer_15.output.fp32_scaled_output",
            second_row="talker_core.layer_15.output.fp32_scaled_output",
        ),
    )

    assert assessment == QwenFp32ScaledLayer15OutputAssessment(
        stabilization_variant=_FP32_SCALED_LAYER15_OUTPUT_VARIANT,
        target_loss_kind="sub_talker_loss",
        target_corridor_surfaces=(
            "talker_core.layer_15.output.fp32_scaled_output",
            "talker_core.layer_15.output",
            "talker_core.layer_16.input",
        ),
        comparison_rows=(
            PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output.fp32_scaled_output",
                matched_corridor_surface="talker_core.layer_15.output.fp32_scaled_output",
            ),
            PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output.fp32_scaled_output",
                matched_corridor_surface="talker_core.layer_15.output.fp32_scaled_output",
            ),
            PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output.fp32_scaled_output",
                matched_corridor_surface="talker_core.layer_15.output.fp32_scaled_output",
            ),
        ),
        convergence_classification="converged_fp32_scaled_output",
        dominant_surface="talker_core.layer_15.output.fp32_scaled_output",
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_task_rule=(
            "Open a diagnosis-only NEXT_DIAGNOSIS branch to split the fp32-scaled layer-15 "
            "output arithmetic before any new stabilizer family."
        ),
    )


def test_build_fp32_scaled_layer15_output_assessment_marks_output_return() -> None:
    """All-three agreement on the emitted tensor should keep the seam there."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_15.output",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "converged_output_return"
    assert assessment.dominant_surface == "talker_core.layer_15.output"


def test_build_fp32_scaled_layer15_output_assessment_marks_disagreement() -> None:
    """Mixed downstream corridor rows should stay disagreement evidence."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output.fp32_scaled_output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_16.input",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "downstream_disagreement"
    assert assessment.dominant_surface is None


def test_build_fp32_scaled_layer15_output_assessment_marks_regression() -> None:
    """Rows that escape the corridor or stay finite should remain regression evidence."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output.fp32_scaled_output",
            first_row=None,
            second_row="talker_core.layer_15.output",
            first_row_has_non_finite=False,
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "nonlocal_regression"
    assert assessment.dominant_surface is None


def _settings() -> QwenStabilityLabSettings:
    return QwenStabilityLabSettings(
        output_root=Path("/tmp/qwen_stability"),
        dockerfile_path=Path("Dockerfile"),
        image="test-image",
        model_id="test-model",
        hf_cache_dir=Path("/tmp/hf"),
        hf_cache_home_mount=Path("/tmp/hf-home"),
        output_root_home_mount_base=Path("/tmp/output-home"),
        source_bundle_root=Path("/tmp/bundle"),
        manifest_family="swedish_pilot_train",
        source_lines=(13, 4),
        text_embedding_mask_policy="text_span_only",
        hook_profile=TALKER_CORE_POST_LAYER15_OUTPUT_MULTIPLY_FP32_SCALED_OUTPUT_HOOK_PROFILE,
        stabilization_variants=(_FP32_SCALED_LAYER15_OUTPUT_VARIANT,),
        build_image=False,
    )


def _matrix_rows(
    *,
    pair: str | None,
    first_row: str | None,
    second_row: str | None,
    pair_has_non_finite: bool = True,
    first_row_has_non_finite: bool = True,
    second_row_has_non_finite: bool = True,
) -> tuple[StabilityLabMatrixRow, ...]:
    return (
        _row("pair-sub-talker-loss", (13, 4), 2, pair, pair_has_non_finite),
        _row("line-13-sub-talker-loss", (13,), 1, first_row, first_row_has_non_finite),
        _row("line-4-sub-talker-loss", (4,), 1, second_row, second_row_has_non_finite),
    )


def _row(
    case_id: str,
    source_line_numbers: tuple[int, ...],
    batch_size: int,
    talker_hook: str | None,
    case_has_non_finite: bool,
) -> StabilityLabMatrixRow:
    return StabilityLabMatrixRow(
        stabilization_variant=_FP32_SCALED_LAYER15_OUTPUT_VARIANT,
        case_id=case_id,
        loss_kind="sub_talker_loss",
        source_line_numbers=source_line_numbers,
        batch_size=batch_size,
        interaction_mode="both_rows",
        case_has_non_finite=case_has_non_finite,
        first_non_finite_hook_tensor=talker_hook,
        first_non_finite_talker_core_hook_tensor=talker_hook,
        gradient_rca_first_non_finite_surface="input_text_embedding.grad",
        parameter_first_non_finite_surface="text_embedding.weight.grad",
        anomaly_operator=None,
    )
