"""Focused tests for the output-return Qwen stability lab output-return assessment.

Purpose:
    Lock the post-residual/output return-path split contract so the converged fp32
    output-cap winner can only open one truthful follow-on branch.

Relationships:
    - Exercises `qwen_layer15_output_return_assessment.py`.
    - Reuses `qwen_stability_lab_contracts.py` for compact matrix rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_layer15_output_return_assessment as layer15_output_return_output_return_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_LAYER15_RESIDUAL_OUTPUT_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostLAYER15_RESIDUAL_OUTPUTLayer15OutputReturnComparisonRow,
    QwenLayer15OutputReturnAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

_LAYER15_OUTPUT_RETURN_VARIANT = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3"
)
_BUILD_ASSESSMENT = (
    layer15_output_return_output_return_assessment.build_layer15_output_return_assessment
)


def test_validate_layer15_output_return_contract_rejects_wrong_family() -> None:
    """The output-return split probe should accept only the fixed converged winner."""
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
        hook_profile=TALKER_CORE_POST_LAYER15_RESIDUAL_OUTPUT_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
        stabilization_variants=(_LAYER15_OUTPUT_RETURN_VARIANT, "off"),
        build_image=False,
    )

    with pytest.raises(
        SystemExit,
        match="supports only the fixed ROW_LOCAL_MICRO_FAMILY/LAYER15_RESIDUAL_OUTPUT winner",
    ):
        layer15_output_return_output_return_assessment.validate_layer15_output_return_contract(
            settings
        )


def test_build_layer15_output_return_assessment_marks_pre_scale_output() -> None:
    """All-three agreement before output scaling should keep drilling there."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output.pre_output_scale_return",
            first_row="talker_core.layer_15.output.pre_output_scale_return",
            second_row="talker_core.layer_15.output.pre_output_scale_return",
        ),
    )

    assert assessment == QwenLayer15OutputReturnAssessment(
        stabilization_variant=_LAYER15_OUTPUT_RETURN_VARIANT,
        target_loss_kind="sub_talker_loss",
        target_corridor_surfaces=(
            "talker_core.layer_15.output.pre_output_scale_return",
            "talker_core.layer_15.output",
            "talker_core.layer_16.input",
        ),
        comparison_rows=(
            PostLAYER15_RESIDUAL_OUTPUTLayer15OutputReturnComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output.pre_output_scale_return",
                matched_corridor_surface="talker_core.layer_15.output.pre_output_scale_return",
            ),
            PostLAYER15_RESIDUAL_OUTPUTLayer15OutputReturnComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output.pre_output_scale_return",
                matched_corridor_surface="talker_core.layer_15.output.pre_output_scale_return",
            ),
            PostLAYER15_RESIDUAL_OUTPUTLayer15OutputReturnComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output.pre_output_scale_return",
                matched_corridor_surface="talker_core.layer_15.output.pre_output_scale_return",
            ),
        ),
        convergence_classification="converged_pre_output_scale_return",
        dominant_surface="talker_core.layer_15.output.pre_output_scale_return",
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_task_rule=(
            "Open a diagnosis-only LAYER15_OUTPUT_MULTIPLY branch to split the raw pre-scale "
            "return tensor lineage and dtype regime under "
            f"`{_LAYER15_OUTPUT_RETURN_VARIANT}` "
            "at `talker_core.layer_15.output.pre_output_scale_return`."
        ),
    )


def test_build_layer15_output_return_assessment_marks_output_return() -> None:
    """All-three agreement at the emitted layer output should keep drilling there."""
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


def test_build_layer15_output_return_assessment_marks_layer16_input() -> None:
    """All-three agreement at the downstream guard should move the seam there."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_16.input",
            first_row="talker_core.layer_16.input",
            second_row="talker_core.layer_16.input",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "converged_layer16_input_handoff"
    assert assessment.dominant_surface == "talker_core.layer_16.input"


def test_build_layer15_output_return_assessment_marks_disagreement() -> None:
    """Mixed return-path rows should stay disagreement evidence."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output.pre_output_scale_return",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_16.input",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "downstream_disagreement"
    assert assessment.dominant_surface is None


def test_build_layer15_output_return_assessment_marks_regression() -> None:
    """Rows outside the committed corridor should close output-return as regression evidence."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_16.input_layernorm.output",
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
        hook_profile=TALKER_CORE_POST_LAYER15_RESIDUAL_OUTPUT_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
        stabilization_variants=(_LAYER15_OUTPUT_RETURN_VARIANT,),
        build_image=False,
    )


def _matrix_rows(
    *,
    pair: str,
    first_row: str,
    second_row: str,
) -> tuple[StabilityLabMatrixRow, ...]:
    return (
        _row("pair-sub-talker-loss", (13, 4), 2, pair),
        _row("line-13-sub-talker-loss", (13,), 1, first_row),
        _row("line-4-sub-talker-loss", (4,), 1, second_row),
    )


def _row(
    case_id: str,
    source_line_numbers: tuple[int, ...],
    batch_size: int,
    talker_hook: str,
) -> StabilityLabMatrixRow:
    return StabilityLabMatrixRow(
        stabilization_variant=_LAYER15_OUTPUT_RETURN_VARIANT,
        case_id=case_id,
        loss_kind="sub_talker_loss",
        source_line_numbers=source_line_numbers,
        batch_size=batch_size,
        interaction_mode="both_rows",
        case_has_non_finite=True,
        first_non_finite_hook_tensor=talker_hook,
        first_non_finite_talker_core_hook_tensor=talker_hook,
        gradient_rca_first_non_finite_surface="input_text_embedding.grad",
        parameter_first_non_finite_surface="text_embedding.weight.grad",
        anomaly_operator=None,
    )
