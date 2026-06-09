"""Focused fp32-scaled output fp32-scaled-output assessment for the Qwen stability lab lab.

Purpose:
    Classify whether the post-multiply-site confirmation converged `layer_15.output` seam is born in
    the fp32-scaled output result or only in the final emitted tensor under the
    fixed multiply-site confirmation confirmation variant, so Qwen stability lab can keep narrowing
    the
    smallest truthful root-cause surface.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses the fp32-scaled output corridor trace names and the shared Qwen stability lab lab
      contracts.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_post_layer15_output_multiply_fp32_scaled_output_trace_names,
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

FP32_SCALED_LAYER15_OUTPUT_TARGET_LOSS_KIND = "sub_talker_loss"
FP32_SCALED_LAYER15_OUTPUT_REQUIRED_VARIANT = (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32
)
FP32_SCALED_LAYER15_OUTPUT_TARGET_CORRIDOR_SURFACES = (
    talker_core_post_layer15_output_multiply_fp32_scaled_output_trace_names()
)
_FP32_SCALED_OUTPUT_SURFACE = "talker_core.layer_15.output.fp32_scaled_output"
_OUTPUT_RETURN_SURFACE = "talker_core.layer_15.output"
_LAYER16_INPUT_SURFACE = "talker_core.layer_16.input"
_CONVERGED_FP32_SCALED_OUTPUT = "converged_fp32_scaled_output"
_CONVERGED_OUTPUT_RETURN = "converged_output_return"
_CONVERGED_LAYER16_INPUT_HANDOFF = "converged_layer16_input_handoff"
_DOWNSTREAM_DISAGREEMENT = "downstream_disagreement"
_NONLOCAL_REGRESSION = "nonlocal_regression"


def validate_fp32_scaled_layer15_output_contract(
    settings: QwenStabilityLabSettings,
) -> None:
    """Reject unsupported fp32-scaled output settings before the Hemma probe starts."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_LAYER15_OUTPUT_MULTIPLY_FP32_SCALED_OUTPUT_HOOK_PROFILE
    ):
        return
    if settings.stabilization_variants == (FP32_SCALED_LAYER15_OUTPUT_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Qwen stability lab FP32_SCALED_LAYER15_OUTPUT supports only the exact "
        "fixed LAYER15_OUTPUT_MULTIPLY confirmation variant "
        f"`{FP32_SCALED_LAYER15_OUTPUT_REQUIRED_VARIANT}`."
    )


def build_fp32_scaled_layer15_output_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenFp32ScaledLayer15OutputAssessment | None:
    """Build the focused fp32-scaled output assessment when the fp32-scaled corridor is active."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_LAYER15_OUTPUT_MULTIPLY_FP32_SCALED_OUTPUT_HOOK_PROFILE
    ):
        return None
    if settings.stabilization_variants != (FP32_SCALED_LAYER15_OUTPUT_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_fp32_scaled_output(
        matrix_rows=matrix_rows,
        stabilization_variant=FP32_SCALED_LAYER15_OUTPUT_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_fp32_scaled_output_split(
        comparison_rows
    )
    return QwenFp32ScaledLayer15OutputAssessment(
        stabilization_variant=FP32_SCALED_LAYER15_OUTPUT_REQUIRED_VARIANT,
        target_loss_kind=FP32_SCALED_LAYER15_OUTPUT_TARGET_LOSS_KIND,
        target_corridor_surfaces=FP32_SCALED_LAYER15_OUTPUT_TARGET_CORRIDOR_SURFACES,
        comparison_rows=comparison_rows,
        convergence_classification=classification,
        dominant_surface=dominant_surface,
        evidence_is_ambiguous=classification is None,
        ambiguity_reason=ambiguity_reason,
        next_task_rule=_next_followup_rule(
            classification=classification,
            dominant_surface=dominant_surface,
        ),
    )


def _comparison_rows_for_fp32_scaled_output(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_fp32_scaled_output_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_fp32_scaled_output_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor
        in FP32_SCALED_LAYER15_OUTPUT_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow(
        case_id=row.case_id,
        source_line_numbers=row.source_line_numbers,
        batch_size=row.batch_size,
        role=role,
        case_has_non_finite=row.case_has_non_finite,
        first_non_finite_talker_core_hook_tensor=row.first_non_finite_talker_core_hook_tensor,
        matched_corridor_surface=matched_corridor_surface,
    )


def _required_matrix_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
) -> StabilityLabMatrixRow:
    for row in matrix_rows:
        if row.stabilization_variant == stabilization_variant and row.case_id == case_id:
            return row
    raise SystemExit(
        "Qwen stability lab could not resolve the required matrix row "
        f"`{stabilization_variant}:{case_id}` for the FP32_SCALED_LAYER15_OUTPUT assessment."
    )


def _classify_fp32_scaled_output_split(
    comparison_rows: tuple[PostLAYER15_OUTPUT_MULTIPLYFp32ScaledLayer15OutputComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if any(not row.case_has_non_finite for row in comparison_rows):
        return _NONLOCAL_REGRESSION, None, None
    matched_surfaces = tuple(row.matched_corridor_surface for row in comparison_rows)
    if all(surface == _FP32_SCALED_OUTPUT_SURFACE for surface in matched_surfaces):
        return _CONVERGED_FP32_SCALED_OUTPUT, _FP32_SCALED_OUTPUT_SURFACE, None
    if all(surface == _OUTPUT_RETURN_SURFACE for surface in matched_surfaces):
        return _CONVERGED_OUTPUT_RETURN, _OUTPUT_RETURN_SURFACE, None
    if all(surface == _LAYER16_INPUT_SURFACE for surface in matched_surfaces):
        return _CONVERGED_LAYER16_INPUT_HANDOFF, _LAYER16_INPUT_SURFACE, None
    if all(
        surface in FP32_SCALED_LAYER15_OUTPUT_TARGET_CORRIDOR_SURFACES
        for surface in matched_surfaces
    ):
        return _DOWNSTREAM_DISAGREEMENT, None, None
    return _NONLOCAL_REGRESSION, None, None


def _next_followup_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _CONVERGED_FP32_SCALED_OUTPUT:
        return (
            "Open a diagnosis-only NEXT_DIAGNOSIS branch to split the fp32-scaled layer-15 "
            "output arithmetic before any new stabilizer family."
        )
    if classification == _CONVERGED_OUTPUT_RETURN and dominant_surface is not None:
        return (
            "Open a diagnosis-only NEXT_DIAGNOSIS branch to split the final emitted "
            f"layer-15 output tensor from the immediate downstream consumer at "
            f"`{dominant_surface}`."
        )
    if classification == _CONVERGED_LAYER16_INPUT_HANDOFF:
        return (
            "Open a diagnosis-only NEXT_DIAGNOSIS branch to split the layer-15 to layer-16 "
            "handoff beneath the fixed LAYER15_OUTPUT_MULTIPLY confirmation variant."
        )
    if classification == _DOWNSTREAM_DISAGREEMENT:
        return (
            "Open a diagnosis-only NEXT_DIAGNOSIS row-local downstream disagreement task "
            "before making a generic layer-15 output claim."
        )
    return (
        "Close FP32_SCALED_LAYER15_OUTPUT as non-promotable diagnosis evidence "
        "and return Qwen stability lab "
        "to the previous verified localized seam."
    )
