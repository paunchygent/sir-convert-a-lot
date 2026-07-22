"""Focused tests for the sub-talker disagreement Qwen stability lab disagreement assessment.

Purpose:
    Lock the post-input-layernorm output disagreement contract so the strongest output-scale
    member either converges on one corridor surface or stays explicitly
    ambiguous for the next task.

Relationships:
    - Exercises `qwen_sub_talker_disagreement_assessment.py`.
    - Reuses `qwen_stability_lab_contracts.py` for compact matrix rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_INPUT_LAYERNORM_OUTPUT_DISAGREEMENT_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow,
    QwenStabilityLabSettings,
    QwenSubTalkerDisagreementAssessment,
    StabilityLabMatrixRow,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_sub_talker_disagreement_assessment import (
    build_sub_talker_disagreement_assessment,
    validate_sub_talker_disagreement_contract,
)


def test_validate_sub_talker_disagreement_contract_rejects_multi_variant_family() -> None:
    """
    The sub-talker disagreement probe should accept only the strongest input-layernorm
    output member.
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
        hook_profile=TALKER_CORE_POST_INPUT_LAYERNORM_OUTPUT_DISAGREEMENT_HOOK_PROFILE,
        stabilization_variants=(
            "layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5",
            "off",
        ),
        build_image=False,
    )

    with pytest.raises(
        SystemExit, match="supports only the strongest INPUT_LAYERNORM_OUTPUT member"
    ):
        validate_sub_talker_disagreement_contract(settings)


def test_build_sub_talker_disagreement_assessment_matches_downstream_family() -> None:
    """All-three downstream agreement should authorize only downstream seam splitting."""
    assessment = build_sub_talker_disagreement_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_15.output",
        ),
    )

    assert assessment == QwenSubTalkerDisagreementAssessment(
        stabilization_variant="layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5",
        target_loss_kind="sub_talker_loss",
        target_corridor_surfaces=(
            "talker_core.layer_15.output",
            "talker_core.layer_16.input",
            "talker_core.layer_16.input_layernorm",
        ),
        comparison_rows=(
            PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow(
                case_id="pair-sub-talker-loss",
                source_line_numbers=(13, 4),
                batch_size=2,
                role="pair",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output",
                matched_corridor_surface="talker_core.layer_15.output",
            ),
            PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow(
                case_id="line-13-sub-talker-loss",
                source_line_numbers=(13,),
                batch_size=1,
                role="first_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output",
                matched_corridor_surface="talker_core.layer_15.output",
            ),
            PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow(
                case_id="line-4-sub-talker-loss",
                source_line_numbers=(4,),
                batch_size=1,
                role="second_row",
                case_has_non_finite=True,
                first_non_finite_talker_core_hook_tensor="talker_core.layer_15.output",
                matched_corridor_surface="talker_core.layer_15.output",
            ),
        ),
        earliest_corridor_surface="talker_core.layer_15.output",
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_micro_family_rule=(
            "ROW_LOCAL_OUTLIER may split the downstream layer_15.output seam only."
        ),
    )


def test_build_sub_talker_disagreement_assessment_matches_non_repeatable_reversion() -> None:
    """All-three reversion to input-layernorm should close the input-layernorm output relocation
    signal.
    """
    assessment = build_sub_talker_disagreement_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_16.input_layernorm",
            first_row="talker_core.layer_16.input_layernorm",
            second_row="talker_core.layer_16.input_layernorm",
        ),
    )

    assert assessment is not None
    assert assessment.earliest_corridor_surface == "talker_core.layer_16.input_layernorm"
    assert assessment.evidence_is_ambiguous is False
    assert (
        assessment.next_micro_family_rule
        == "ROW_LOCAL_OUTLIER must treat the INPUT_LAYERNORM_OUTPUT "
        "relocation signal as non-repeatable and "
        "close the output-scale family."
    )


def test_build_sub_talker_disagreement_assessment_marks_second_row_outlier() -> None:
    """A surviving line-4 upstream seam should stay explicit as a row-local outlier."""
    assessment = build_sub_talker_disagreement_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            pair="talker_core.layer_15.output",
            first_row="talker_core.layer_15.output",
            second_row="talker_core.layer_16.input_layernorm",
        ),
    )

    assert assessment is not None
    assert assessment.earliest_corridor_surface is None
    assert assessment.evidence_is_ambiguous is True
    assert assessment.ambiguity_reason == (
        "Pair and first-row cases moved downstream to `layer_15.output`, "
        "but the second row stayed upstream."
    )
    assert (
        assessment.next_micro_family_rule
        == "ROW_LOCAL_OUTLIER must resolve the row-local second-row outlier before claiming "
        "a generic layer_15.output seam."
    )


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
        hook_profile=TALKER_CORE_POST_INPUT_LAYERNORM_OUTPUT_DISAGREEMENT_HOOK_PROFILE,
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
