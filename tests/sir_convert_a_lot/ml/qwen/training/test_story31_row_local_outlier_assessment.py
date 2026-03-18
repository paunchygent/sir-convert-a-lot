"""Focused tests for the T236 Story 31 row-local outlier assessment.

Purpose:
    Lock the post-T235 row-local classification contract so the strongest
    output-scale member can only open one truthful T237 branch.

Relationships:
    - Exercises `story31_row_local_outlier_assessment.py`.
    - Reuses `story31_stability_lab_contracts.py` for compact matrix rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_row_local_outlier_assessment import (
    build_post_t235_row_local_outlier_assessment,
    validate_post_t235_row_local_outlier_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    PostT235RowLocalOutlierComparisonRow,
    StabilityLabMatrixRow,
    Story31PostT235RowLocalOutlierAssessment,
    Story31StabilityLabSettings,
)


def test_validate_post_t235_row_local_outlier_contract_rejects_multi_variant_family() -> None:
    """The T236 row-local probe should accept only the strongest T234 member."""
    settings = Story31StabilityLabSettings(
        output_root=Path("/tmp/story31"),
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
        hook_profile=TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
        stabilization_variants=(
            "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5",
            "off",
        ),
        build_image=False,
    )

    with pytest.raises(SystemExit, match="supports only the strongest T234 member"):
        validate_post_t235_row_local_outlier_contract(settings)


def test_build_post_t235_row_local_outlier_assessment_marks_row_local_difference() -> None:
    """Pair plus row 13 agreement with line 4 upstream should stay row-local."""
    assessment = build_post_t235_row_local_outlier_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_16.input_layernorm.output",
        ),
    )

    assert assessment == Story31PostT235RowLocalOutlierAssessment(
        stabilization_variant="layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5",
        target_loss_kind="sub_talker_loss",
        target_outlier_surfaces=(
            "talker_core.layer_15.output",
            "talker_core.layer_16.input",
            "talker_core.layer_16.input_layernorm.output",
        ),
        comparison_rows=(
            PostT235RowLocalOutlierComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output",
                matched_outlier_surface="talker_core.layer_15.output",
            ),
            PostT235RowLocalOutlierComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output",
                matched_outlier_surface="talker_core.layer_15.output",
            ),
            PostT235RowLocalOutlierComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_16.input_layernorm.output",
                matched_outlier_surface="talker_core.layer_16.input_layernorm.output",
            ),
        ),
        outlier_classification="genuine_row_local_seam_difference",
        dominant_surface="talker_core.layer_16.input_layernorm.output",
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_micro_family_rule=(
            "T237 may test one upstream row-local micro-family only against "
            "`talker_core.layer_16.input_layernorm.output`."
        ),
    )


def test_build_post_t235_row_local_outlier_assessment_marks_pair_masking() -> None:
    """A pair-only divergence from both singles should stay pair-interaction truth."""
    assessment = build_post_t235_row_local_outlier_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_16.input_layernorm.output",
            second_row="talker_core.layer_16.input_layernorm.output",
        ),
    )

    assert assessment is not None
    assert assessment.outlier_classification == "pair_interaction_masking_effect"
    assert assessment.dominant_surface == "talker_core.layer_15.output"


def test_build_post_t235_row_local_outlier_assessment_marks_non_repeatable_outlier() -> None:
    """All-three agreement should close the old line-4 outlier as non-repeatable."""
    assessment = build_post_t235_row_local_outlier_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_15.output",
        ),
    )

    assert assessment is not None
    assert assessment.outlier_classification == "non_repeatable_one_row_instability"
    assert assessment.dominant_surface == "talker_core.layer_15.output"


def _settings() -> Story31StabilityLabSettings:
    return Story31StabilityLabSettings(
        output_root=Path("/tmp/story31"),
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
        hook_profile=TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
        stabilization_variants=(
            "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5",
        ),
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
        stabilization_variant=(
            "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5"
        ),
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
