"""Focused tests for the Qwen stability lab input-layernorm internal input-layernorm internal
assessment.

Purpose:
    Lock the input-layernorm internal validation and interpretation contract so the next mechanism
    family is derived from one consistent internal normalization surface rather
    than from mixed exploratory evidence.

Relationships:
    - Exercises `qwen_input_layernorm_internal_assessment.py`.
    - Reuses `qwen_stability_lab_contracts.py` for the compact matrix-row
      payloads consumed by the Qwen stability lab runner.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_input_layernorm_internal_assessment import (
    INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,
    build_input_layernorm_internal_assessment,
    validate_input_layernorm_internal_contract,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_runner import (
    DEFAULT_MANIFEST_FAMILY,
    DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
    DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
)


def test_validate_input_layernorm_internal_contract_rejects_multi_variant_family() -> None:
    """input-layernorm internal should stay baseline-only and reject any widened variant family."""
    with pytest.raises(
        SystemExit,
        match="supports only the ranked SUB_BOUNDARY/NORMALIZATION_ENTRY baseline variant",
    ):
        validate_input_layernorm_internal_contract(
            _settings(stabilization_variants=(INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT, "off"))
        )


def test_build_input_layernorm_internal_assessment_matches_upstream_residual_family() -> None:
    """Residual-input agreement should point the next task at the upstream family only."""
    assessment = build_input_layernorm_internal_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            "talker_core.layer_16.input_layernorm.residual_input",
            "talker_core.layer_16.input_layernorm.residual_input",
            "talker_core.layer_16.input_layernorm.residual_input",
        ),
    )

    assert assessment is not None
    assert (
        assessment.earliest_internal_surface
        == "talker_core.layer_16.input_layernorm.residual_input"
    )
    assert assessment.evidence_is_ambiguous is False
    assert (
        assessment.next_micro_family_rule
        == "The next task may test one upstream residual-amplitude micro-family only."
    )


def test_build_input_layernorm_internal_assessment_matches_numeric_safety_family() -> None:
    """Variance agreement should point the next task at the numeric-safety family only."""
    assessment = build_input_layernorm_internal_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            "talker_core.layer_16.input_layernorm.variance",
            "talker_core.layer_16.input_layernorm.variance",
            "talker_core.layer_16.input_layernorm.variance",
        ),
    )

    assert assessment is not None
    assert assessment.earliest_internal_surface == "talker_core.layer_16.input_layernorm.variance"
    assert (
        assessment.next_micro_family_rule
        == "The next task may test one normalization-internal numeric-safety micro-family only."
    )


def test_build_input_layernorm_internal_assessment_matches_output_scale_family() -> None:
    """Output agreement should point the next task at the post-normalization family only."""
    assessment = build_input_layernorm_internal_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            "talker_core.layer_16.input_layernorm.output",
            "talker_core.layer_16.input_layernorm.output",
            "talker_core.layer_16.input_layernorm.output",
        ),
    )

    assert assessment is not None
    assert assessment.earliest_internal_surface == "talker_core.layer_16.input_layernorm.output"
    assert (
        assessment.next_micro_family_rule
        == "The next task may test one post-normalization output-scale micro-family only."
    )


def test_build_input_layernorm_internal_assessment_marks_disagreement_ambiguous() -> None:
    """Disagreement across pair and single rows should keep the next task blocked."""
    assessment = build_input_layernorm_internal_assessment(
        settings=_settings(),
        matrix_rows=_matrix_rows(
            "talker_core.layer_16.input_layernorm.residual_input",
            "talker_core.layer_16.input_layernorm.variance",
            "talker_core.layer_16.input_layernorm.output",
        ),
    )

    assert assessment is not None
    assert assessment.earliest_internal_surface is None
    assert assessment.evidence_is_ambiguous is True
    assert assessment.ambiguity_reason == (
        "Pair and single-row sub-talker cases disagreed on the earliest "
        "input-layernorm internal surface."
    )
    assert (
        assessment.next_micro_family_rule
        == "The next task remains blocked until the INPUT_LAYERNORM_INTERNAL ambiguity is resolved."
    )


def _settings(
    *,
    stabilization_variants: tuple[str, ...] = (INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,),
) -> QwenStabilityLabSettings:
    return QwenStabilityLabSettings(
        output_root=Path("/tmp/qwen_stability"),
        dockerfile_path=Path("Dockerfile"),
        image="test-image",
        model_id="test-model",
        hf_cache_dir=Path("/tmp/hf"),
        hf_cache_home_mount=Path("/tmp/hf-home"),
        output_root_home_mount_base=DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
        source_bundle_root=Path("/tmp/bundle"),
        manifest_family=DEFAULT_MANIFEST_FAMILY,
        source_lines=(13, 4),
        text_embedding_mask_policy=DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
        hook_profile=TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE,
        stabilization_variants=stabilization_variants,
        build_image=False,
    )


def _matrix_rows(
    pair_surface: str,
    first_row_surface: str,
    second_row_surface: str,
) -> tuple[StabilityLabMatrixRow, ...]:
    return (
        _row(
            case_id="pair-sub-talker-loss",
            source_line_numbers=(13, 4),
            batch_size=2,
            matched_surface=pair_surface,
        ),
        _row(
            case_id="line-13-sub-talker-loss",
            source_line_numbers=(13,),
            batch_size=1,
            matched_surface=first_row_surface,
        ),
        _row(
            case_id="line-4-sub-talker-loss",
            source_line_numbers=(4,),
            batch_size=1,
            matched_surface=second_row_surface,
        ),
    )


def _row(
    *,
    case_id: str,
    source_line_numbers: tuple[int, ...],
    batch_size: int,
    matched_surface: str,
) -> StabilityLabMatrixRow:
    return StabilityLabMatrixRow(
        stabilization_variant=INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,
        case_id=case_id,
        loss_kind="sub_talker_loss",
        source_line_numbers=source_line_numbers,
        batch_size=batch_size,
        interaction_mode="both_rows",
        case_has_non_finite=True,
        first_non_finite_hook_tensor=matched_surface,
        first_non_finite_talker_core_hook_tensor=matched_surface,
        gradient_rca_first_non_finite_surface="input_text_embedding.grad",
        parameter_first_non_finite_surface="text_embedding.weight.grad",
        anomaly_operator=None,
    )
