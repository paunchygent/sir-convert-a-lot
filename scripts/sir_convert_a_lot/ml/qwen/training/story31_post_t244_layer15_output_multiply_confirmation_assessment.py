"""Focused T245 multiply-site confirmation assessment for the Story 31 lab.

Purpose:
    Classify whether the smallest post-T244 seam remains at the emitted
    `layer_15.output` tensor when the fixed winner performs its layer-15
    `output_scale=0.5` multiply in fp32, so Story 31 can decide whether that
    multiply is a real causal candidate.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses the narrowed T244 corridor and the shared Story 31 lab contracts.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_post_t243_layer15_output_return_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    PostT244Layer15OutputMultiplyConfirmationComparisonRow,
    StabilityLabMatrixRow,
    Story31PostT244Layer15OutputMultiplyConfirmationAssessment,
    Story31StabilityLabSettings,
)

T245_TARGET_LOSS_KIND = "sub_talker_loss"
T245_REQUIRED_VARIANT = LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3_LAYER15_OUTPUT_SCALE_FP32
T245_TARGET_CORRIDOR_SURFACES = talker_core_post_t243_layer15_output_return_trace_names()
_OUTPUT_RETURN_SURFACE = "talker_core.layer_15.output"
_CAUSAL_CANDIDATE_CONFIRMED = "causal_candidate_confirmed"
_MULTIPLY_NOT_CAUSAL = "multiply_not_causal"
_NONLOCAL_REGRESSION = "nonlocal_regression"


def validate_post_t244_layer15_output_multiply_confirmation_contract(
    settings: Story31StabilityLabSettings,
) -> None:
    """Reject unsupported T245 settings before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (T245_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Story 31 T245 supports only the exact fp32 layer-15 output "
        f"multiply confirmation `{T245_REQUIRED_VARIANT}`."
    )


def build_post_t244_layer15_output_multiply_confirmation_assessment(
    *,
    settings: Story31StabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> Story31PostT244Layer15OutputMultiplyConfirmationAssessment | None:
    """Build the focused T245 assessment when the confirmation variant is active."""
    if settings.hook_profile != TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (T245_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_multiply_confirmation(
        matrix_rows=matrix_rows,
        stabilization_variant=T245_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface = _classify_multiply_confirmation(comparison_rows)
    return Story31PostT244Layer15OutputMultiplyConfirmationAssessment(
        stabilization_variant=T245_REQUIRED_VARIANT,
        target_loss_kind=T245_TARGET_LOSS_KIND,
        target_corridor_surfaces=T245_TARGET_CORRIDOR_SURFACES,
        comparison_rows=comparison_rows,
        confirmation_classification=classification,
        dominant_surface=dominant_surface,
        evidence_is_ambiguous=False,
        ambiguity_reason=None,
        next_task_rule=_next_task_rule(
            classification=classification,
            dominant_surface=dominant_surface,
        ),
    )


def _comparison_rows_for_multiply_confirmation(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostT244Layer15OutputMultiplyConfirmationComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_multiply_confirmation_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_multiply_confirmation_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostT244Layer15OutputMultiplyConfirmationComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor in T245_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostT244Layer15OutputMultiplyConfirmationComparisonRow(
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
        "Story 31 stability lab could not resolve the required matrix row "
        f"`{stabilization_variant}:{case_id}` for the T245 assessment."
    )


def _classify_multiply_confirmation(
    comparison_rows: tuple[PostT244Layer15OutputMultiplyConfirmationComparisonRow, ...],
) -> tuple[str, str | None]:
    if all(not row.case_has_non_finite for row in comparison_rows):
        return _CAUSAL_CANDIDATE_CONFIRMED, None
    if all(row.matched_corridor_surface == _OUTPUT_RETURN_SURFACE for row in comparison_rows):
        return _MULTIPLY_NOT_CAUSAL, _OUTPUT_RETURN_SURFACE
    return _NONLOCAL_REGRESSION, None


def _next_task_rule(
    *,
    classification: str,
    dominant_surface: str | None,
) -> str:
    if classification == _CAUSAL_CANDIDATE_CONFIRMED:
        return (
            "Open a diagnosis-only T246 downstream verification slice before any "
            "promotion discussion; the fp32 layer-15 output multiply is now a "
            "confirmed causal candidate."
        )
    if classification == _MULTIPLY_NOT_CAUSAL and dominant_surface is not None:
        return (
            "Open a diagnosis-only T246 branch to split the fp32-scaled "
            f"layer-15 output result from the final emitted tensor under "
            f"`{T245_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    return (
        "Close T245 as non-promotable causal-confirmation evidence and return "
        "Story 31 to the previous verified localized seam."
    )
