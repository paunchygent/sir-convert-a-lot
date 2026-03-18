"""Focused T244 layer-15 output-return assessment for the Story 31 lab.

Purpose:
    Classify the post-T243 converged `layer_15.output` seam one level deeper
    along the winner-specific output-scale return path so the next Story 31
    slice can keep drilling toward a causal candidate instead of reopening
    broad stabilizer exploration.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical T244 corridor
      and `story31_stability_lab_contracts.py` for the typed report payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_post_t243_layer15_output_return_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    PostT243Layer15OutputReturnComparisonRow,
    StabilityLabMatrixRow,
    Story31PostT243Layer15OutputReturnAssessment,
    Story31StabilityLabSettings,
)

T244_TARGET_LOSS_KIND = "sub_talker_loss"
T244_REQUIRED_VARIANT = LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3
T244_TARGET_CORRIDOR_SURFACES = talker_core_post_t243_layer15_output_return_trace_names()
_PRE_OUTPUT_SCALE_RETURN_SURFACE = "talker_core.layer_15.output.pre_output_scale_return"
_OUTPUT_RETURN_SURFACE = "talker_core.layer_15.output"
_LAYER16_INPUT_SURFACE = "talker_core.layer_16.input"
_CONVERGED_PRE_OUTPUT_SCALE_RETURN = "converged_pre_output_scale_return"
_CONVERGED_OUTPUT_RETURN = "converged_output_return"
_CONVERGED_LAYER16_INPUT_HANDOFF = "converged_layer16_input_handoff"
_DOWNSTREAM_DISAGREEMENT = "downstream_disagreement"
_NONLOCAL_REGRESSION = "nonlocal_regression"


def validate_post_t243_layer15_output_return_contract(
    settings: Story31StabilityLabSettings,
) -> None:
    """Reject unsupported T244 settings before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (T244_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        f"Story 31 T244 supports only the fixed T237/T243 winner `{T244_REQUIRED_VARIANT}`."
    )


def build_post_t243_layer15_output_return_assessment(
    *,
    settings: Story31StabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> Story31PostT243Layer15OutputReturnAssessment | None:
    """Build the focused T244 assessment when the return-path profile is active."""
    if settings.hook_profile != TALKER_CORE_POST_T243_LAYER15_OUTPUT_RETURN_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (T244_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_post_t243_layer15_output_return(
        matrix_rows=matrix_rows,
        stabilization_variant=T244_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_output_return_split(
        comparison_rows
    )
    return Story31PostT243Layer15OutputReturnAssessment(
        stabilization_variant=T244_REQUIRED_VARIANT,
        target_loss_kind=T244_TARGET_LOSS_KIND,
        target_corridor_surfaces=T244_TARGET_CORRIDOR_SURFACES,
        comparison_rows=comparison_rows,
        convergence_classification=classification,
        dominant_surface=dominant_surface,
        evidence_is_ambiguous=classification is None,
        ambiguity_reason=ambiguity_reason,
        next_task_rule=_next_task_rule(
            classification=classification,
            dominant_surface=dominant_surface,
        ),
    )


def _comparison_rows_for_post_t243_layer15_output_return(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostT243Layer15OutputReturnComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_post_t243_layer15_output_return_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_post_t243_layer15_output_return_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostT243Layer15OutputReturnComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor in T244_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostT243Layer15OutputReturnComparisonRow(
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
        f"`{stabilization_variant}:{case_id}` for the T244 assessment."
    )


def _classify_output_return_split(
    comparison_rows: tuple[PostT243Layer15OutputReturnComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if len(comparison_rows) != 3:
        return (
            None,
            None,
            "Story 31 T244 could not resolve the full pair-versus-single case set.",
        )
    matched_surfaces = tuple(row.matched_corridor_surface for row in comparison_rows)
    if any(not row.case_has_non_finite for row in comparison_rows):
        return _NONLOCAL_REGRESSION, None, None
    if any(surface is None for surface in matched_surfaces):
        return _NONLOCAL_REGRESSION, None, None
    if all(surface == _PRE_OUTPUT_SCALE_RETURN_SURFACE for surface in matched_surfaces):
        return (
            _CONVERGED_PRE_OUTPUT_SCALE_RETURN,
            _PRE_OUTPUT_SCALE_RETURN_SURFACE,
            None,
        )
    if all(surface == _OUTPUT_RETURN_SURFACE for surface in matched_surfaces):
        return _CONVERGED_OUTPUT_RETURN, _OUTPUT_RETURN_SURFACE, None
    if all(surface == _LAYER16_INPUT_SURFACE for surface in matched_surfaces):
        return _CONVERGED_LAYER16_INPUT_HANDOFF, _LAYER16_INPUT_SURFACE, None
    if all(surface in T244_TARGET_CORRIDOR_SURFACES for surface in matched_surfaces):
        return _DOWNSTREAM_DISAGREEMENT, None, None
    return _NONLOCAL_REGRESSION, None, None


def _next_task_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _CONVERGED_PRE_OUTPUT_SCALE_RETURN and dominant_surface is not None:
        return (
            "Open a diagnosis-only T245 branch to split the raw pre-scale "
            f"return tensor lineage and dtype regime under `{T244_REQUIRED_VARIANT}` "
            f"at `{dominant_surface}`."
        )
    if classification == _CONVERGED_OUTPUT_RETURN and dominant_surface is not None:
        return (
            "Open a diagnosis-only T245 branch to confirm or split the "
            f"winner-specific layer-15 output attenuation multiply under "
            f"`{T244_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_LAYER16_INPUT_HANDOFF and dominant_surface is not None:
        return (
            "Open a diagnosis-only T245 branch to split the layer-15 to "
            f"layer-16 handoff under `{T244_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _DOWNSTREAM_DISAGREEMENT:
        return (
            "Open one row-local downstream disagreement task under "
            f"`{T244_REQUIRED_VARIANT}` instead of claiming a generic return-path seam."
        )
    if classification == _NONLOCAL_REGRESSION:
        return (
            "Close T244 as non-promotable mechanism evidence and return Story 31 "
            "to the previous verified seam."
        )
    return "The next Story 31 task remains blocked until the T244 split resolves."
