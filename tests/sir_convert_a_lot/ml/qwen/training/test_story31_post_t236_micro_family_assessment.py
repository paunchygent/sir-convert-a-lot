"""Focused tests for the T237 Story 31 row-local micro-family assessment.

Purpose:
    Lock the post-T236 family-classification contract so the fp32-output-cap
    family opens only the next truthful mechanism branch.

Relationships:
    - Exercises `story31_post_t236_micro_family_assessment.py`.
    - Reuses `story31_stability_lab_contracts.py` for the compact matrix-row
      payloads consumed by the Story 31 runner.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_post_t236_micro_family_assessment import (
    T237_BASELINE_VARIANT,
    T237_CANDIDATE_VARIANTS,
    T237_REQUIRED_VARIANTS,
    build_post_t236_row_local_micro_family_assessment,
    validate_post_t236_row_local_micro_family_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    StabilityLabMatrixRow,
    Story31StabilityLabSettings,
)


def test_validate_post_t236_row_local_micro_family_contract_rejects_wrong_family() -> None:
    """The T237 probe should accept only the fixed fp32-output-cap family."""
    settings = _settings(stabilization_variants=(T237_BASELINE_VARIANT, "off"))

    with pytest.raises(SystemExit, match="supports only the fixed baseline plus the two fp32"):
        validate_post_t236_row_local_micro_family_contract(settings)


def test_build_post_t236_row_local_micro_family_assessment_marks_upstream_persistent() -> None:
    """Both cap variants keeping line 4 upstream should close the family as persistent."""
    assessment = build_post_t236_row_local_micro_family_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            baseline=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
            first_candidate=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
            second_candidate=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
        ),
    )

    assert assessment is not None
    assert assessment.family_classification == "upstream_persistent"
    assert assessment.winning_candidate_variant is None
    assert assessment.dominant_surface == "talker_core.layer_16.input_layernorm.output"


def test_build_post_t236_row_local_micro_family_assessment_marks_converged_downstream() -> None:
    """A clean line-4 downstream move should pick the least invasive winning cap."""
    assessment = build_post_t236_row_local_micro_family_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            baseline=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
            first_candidate=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
            ),
            second_candidate=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
        ),
    )

    assert assessment is not None
    assert assessment.family_classification == "converged_downstream"
    assert assessment.winning_candidate_variant == T237_CANDIDATE_VARIANTS[0]
    assert assessment.dominant_surface == "talker_core.layer_15.output"


def test_build_post_t236_row_local_micro_family_assessment_marks_non_local_regression() -> None:
    """A pair regression or out-of-corridor move should close the family negative."""
    assessment = build_post_t236_row_local_micro_family_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            baseline=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
            first_candidate=(
                "talker_core.layer_16.input",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
            second_candidate=(
                "talker_core.layer_15.output",
                "talker_core.layer_15.output",
                "talker_core.layer_16.input_layernorm.output",
            ),
        ),
    )

    assert assessment is not None
    assert assessment.family_classification == "non_local_regression"
    assert assessment.winning_candidate_variant == T237_CANDIDATE_VARIANTS[0]
    assert assessment.next_task_rule == (
        "Close T237 as negative mechanism evidence and keep Story 31 in mechanism."
    )


def _settings(
    *,
    stabilization_variants: tuple[str, ...] = T237_REQUIRED_VARIANTS,
) -> Story31StabilityLabSettings:
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
        stabilization_variants=stabilization_variants,
        build_image=False,
    )


def _matrix_rows(
    *,
    baseline: tuple[str, str, str],
    first_candidate: tuple[str, str, str],
    second_candidate: tuple[str, str, str],
) -> tuple[StabilityLabMatrixRow, ...]:
    family_rows = (baseline, first_candidate, second_candidate)
    return tuple(
        _row(
            variant=variant,
            case_id=case_id,
            source_line_numbers=source_line_numbers,
            batch_size=batch_size,
            talker_hook=talker_hook,
        )
        for variant, variant_rows in zip(T237_REQUIRED_VARIANTS, family_rows, strict=True)
        for case_id, source_line_numbers, batch_size, talker_hook in (
            ("pair-sub-talker-loss", (13, 4), 2, variant_rows[0]),
            ("line-13-sub-talker-loss", (13,), 1, variant_rows[1]),
            ("line-4-sub-talker-loss", (4,), 1, variant_rows[2]),
        )
    )


def _row(
    *,
    variant: str,
    case_id: str,
    source_line_numbers: tuple[int, ...],
    batch_size: int,
    talker_hook: str,
) -> StabilityLabMatrixRow:
    return StabilityLabMatrixRow(
        stabilization_variant=variant,
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
