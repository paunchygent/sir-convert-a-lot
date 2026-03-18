"""Focused tests for the T241 Story 31 layer-15 output split assessment.

Purpose:
    Lock the post-T240 layer-15 split contract so the converged fp32-output-cap
    winner can only open one truthful follow-on branch.

Relationships:
    - Exercises `story31_post_t240_layer15_output_split_assessment.py`.
    - Reuses `story31_stability_lab_contracts.py` for compact matrix rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training import (
    story31_post_t240_layer15_output_split_assessment as t241_layer15_output_split_assessment,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T240_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    PostT240Layer15OutputSplitComparisonRow,
    StabilityLabMatrixRow,
    Story31PostT240Layer15OutputSplitAssessment,
    Story31StabilityLabSettings,
)

_T241_VARIANT = (
    "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_"
    "layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3"
)
_BUILD_ASSESSMENT = (
    t241_layer15_output_split_assessment.build_post_t240_layer15_output_split_assessment
)


def test_validate_post_t240_layer15_output_split_contract_rejects_wrong_family() -> None:
    """The T241 split probe should accept only the fixed T237/T240 winner."""
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
        hook_profile=TALKER_CORE_POST_T240_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE,
        stabilization_variants=(_T241_VARIANT, "off"),
        build_image=False,
    )

    with pytest.raises(SystemExit, match="supports only the fixed T237/T240 winner"):
        t241_layer15_output_split_assessment.validate_post_t240_layer15_output_split_contract(
            settings
        )


def test_build_post_t240_layer15_output_split_assessment_marks_gated_product() -> None:
    """All-three agreement at gated-product should open the narrowest follow-on split."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.mlp.gated_product",
            first_row="talker_core.layer_15.mlp.gated_product",
            second_row="talker_core.layer_15.mlp.gated_product",
        ),
    )

    assert assessment == Story31PostT240Layer15OutputSplitAssessment(
        stabilization_variant=_T241_VARIANT,
        target_loss_kind="sub_talker_loss",
        target_corridor_surfaces=(
            "talker_core.layer_15.mlp.gated_product",
            "talker_core.layer_15.mlp.down_proj",
            "talker_core.layer_15.output",
            "talker_core.layer_16.input",
        ),
        comparison_rows=(
            PostT240Layer15OutputSplitComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.mlp.gated_product",
                matched_corridor_surface="talker_core.layer_15.mlp.gated_product",
            ),
            PostT240Layer15OutputSplitComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.mlp.gated_product",
                matched_corridor_surface="talker_core.layer_15.mlp.gated_product",
            ),
            PostT240Layer15OutputSplitComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.mlp.gated_product",
                matched_corridor_surface="talker_core.layer_15.mlp.gated_product",
            ),
        ),
        convergence_classification="converged_mlp_gated_product",
        dominant_surface="talker_core.layer_15.mlp.gated_product",
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_task_rule=(
            "Open a diagnosis-only follow-on to split layer-15 gated-product "
            "formation under "
            "`layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3` "
            "at `talker_core.layer_15.mlp.gated_product`."
        ),
    )


def test_build_post_t240_layer15_output_split_assessment_marks_mlp_down_proj() -> None:
    """All-three agreement at down-proj should keep the seam there."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.mlp.down_proj",
            first_row="talker_core.layer_15.mlp.down_proj",
            second_row="talker_core.layer_15.mlp.down_proj",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "converged_mlp_down_proj"
    assert assessment.dominant_surface == "talker_core.layer_15.mlp.down_proj"


def test_build_post_t240_layer15_output_split_assessment_marks_layer15_output() -> None:
    """All-three agreement at layer-15 output should keep residual/output truth."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_15.output",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "converged_layer15_output_residual"
    assert assessment.dominant_surface == "talker_core.layer_15.output"


def test_build_post_t240_layer15_output_split_assessment_marks_downstream_disagreement() -> None:
    """Mixed layer-15 rows should remain disagreement evidence."""
    assessment = _BUILD_ASSESSMENT(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.mlp.gated_product",
            first_row="talker_core.layer_15.mlp.down_proj",
            second_row="talker_core.layer_15.output",
        ),
    )

    assert assessment is not None
    assert assessment.convergence_classification == "downstream_disagreement"
    assert assessment.dominant_surface is None


def test_build_post_t240_layer15_output_split_assessment_marks_regression() -> None:
    """Rows outside the committed corridor should close T241 as regression evidence."""
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
        hook_profile=TALKER_CORE_POST_T240_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE,
        stabilization_variants=(_T241_VARIANT,),
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
        stabilization_variant=_T241_VARIANT,
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
