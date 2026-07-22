"""Focused tests for the multiply-site confirmation Qwen stability lab multiply-site confirmation
assessment.

Purpose:
    Lock the post-output-return causal-confirmation contract so Qwen stability lab can test the
    winner-specific layer-15 `output_scale=0.5` multiply without reopening a
    broad stabilizer family.

Relationships:
    - Exercises `qwen_layer15_output_multiply_confirmation_assessment.py`.
    - Reuses `qwen_stability_lab_contracts.py` for compact matrix rows.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training import (
    qwen_layer15_output_multiply_confirmation_assessment as layer15_output_multiply_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_LAYER15_RESIDUAL_OUTPUT_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostLAYER15_OUTPUT_RETURNLayer15OutputMultiplyConfirmationComparisonRow,
    QwenLayer15OutputMultiplyConfirmationAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

_LAYER15_OUTPUT_MULTIPLY_VARIANT = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3_"
    "layer15_output_scale_fp32"
)
_BUILD_ASSESSMENT = (
    layer15_output_multiply_assessment.build_layer15_output_multiply_confirmation_assessment
)


def test_build_layer15_output_multiply_confirmation_marks_confirmed() -> None:
    """Finite normative rows should mark the multiply site as a confirmed candidate."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair=(None, False),
            first_row=(None, False),
            second_row=(None, False),
        ),
    )

    assert assessment == QwenLayer15OutputMultiplyConfirmationAssessment(
        stabilization_variant=_LAYER15_OUTPUT_MULTIPLY_VARIANT,
        target_loss_kind="sub_talker_loss",
        target_corridor_surfaces=(
            "talker_core.layer_15.output.pre_output_scale_return",
            "talker_core.layer_15.output",
            "talker_core.layer_16.input",
        ),
        comparison_rows=(
            PostLAYER15_OUTPUT_RETURNLayer15OutputMultiplyConfirmationComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=False,
                first_non_finite_talker_core_hook_tensor=None,
                matched_corridor_surface=None,
            ),
            PostLAYER15_OUTPUT_RETURNLayer15OutputMultiplyConfirmationComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=False,
                first_non_finite_talker_core_hook_tensor=None,
                matched_corridor_surface=None,
            ),
            PostLAYER15_OUTPUT_RETURNLayer15OutputMultiplyConfirmationComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=False,
                first_non_finite_talker_core_hook_tensor=None,
                matched_corridor_surface=None,
            ),
        ),
        confirmation_classification="causal_candidate_confirmed",
        dominant_surface=None,
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_task_rule=(
            "Open a diagnosis-only FP32_SCALED_LAYER15_OUTPUT downstream "
            "verification slice before any "
            "promotion discussion; the fp32 layer-15 output multiply is now a "
            "confirmed causal candidate."
        ),
    )


def test_build_layer15_output_multiply_confirmation_marks_not_causal() -> None:
    """Rows that stay on the emitted output seam should reject the multiply candidate."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair=("talker_core.layer_15.output", True),
            first_row=("talker_core.layer_15.output", True),
            second_row=("talker_core.layer_15.output", True),
        ),
    )

    assert assessment is not None
    assert assessment.confirmation_classification == "multiply_not_causal"
    assert assessment.dominant_surface == "talker_core.layer_15.output"


def test_build_layer15_output_multiply_confirmation_marks_regression() -> None:
    """Rows that relocate into the corridor should stay regression evidence."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair=("talker_core.layer_16.input", True),
            first_row=("talker_core.layer_16.input", True),
            second_row=("talker_core.layer_16.input", True),
        ),
    )

    assert assessment is not None
    assert assessment.confirmation_classification == "nonlocal_regression"
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
        stabilization_variants=(_LAYER15_OUTPUT_MULTIPLY_VARIANT,),
        build_image=False,
    )


def _matrix_rows(
    *,
    pair: tuple[str | None, bool],
    first_row: tuple[str | None, bool],
    second_row: tuple[str | None, bool],
) -> tuple[StabilityLabMatrixRow, ...]:
    return (
        _row("pair-sub-talker-loss", (13, 4), 2, pair[0], pair[1]),
        _row("line-13-sub-talker-loss", (13,), 1, first_row[0], first_row[1]),
        _row("line-4-sub-talker-loss", (4,), 1, second_row[0], second_row[1]),
    )


def _row(
    case_id: str,
    source_line_numbers: tuple[int, ...],
    batch_size: int,
    talker_hook: str | None,
    case_has_non_finite: bool,
) -> StabilityLabMatrixRow:
    return StabilityLabMatrixRow(
        stabilization_variant=_LAYER15_OUTPUT_MULTIPLY_VARIANT,
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
