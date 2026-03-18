"""Focused T241 layer-15 output split assessment for the Story 31 lab.

Purpose:
    Classify the post-T240 converged `layer_15.output` seam one level deeper
    so the next Story 31 slice follows one verified layer-15 sub-boundary
    instead of widening into a new stabilizer family.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical T241 corridor
      and `story31_stability_lab_contracts.py` for the typed report payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_post_t240_layer15_output_split_trace_names,
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

T241_TARGET_LOSS_KIND = "sub_talker_loss"
T241_REQUIRED_VARIANT = LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3
T241_TARGET_CORRIDOR_SURFACES = talker_core_post_t240_layer15_output_split_trace_names()
_GATED_PRODUCT_SURFACE = "talker_core.layer_15.mlp.gated_product"
_MLP_DOWN_PROJ_SURFACE = "talker_core.layer_15.mlp.down_proj"
_LAYER15_OUTPUT_SURFACE = "talker_core.layer_15.output"
_LAYER16_INPUT_SURFACE = "talker_core.layer_16.input"
_CONVERGED_GATED_PRODUCT = "converged_mlp_gated_product"
_CONVERGED_MLP_DOWN_PROJ = "converged_mlp_down_proj"
_CONVERGED_LAYER15_OUTPUT = "converged_layer15_output_residual"
_DOWNSTREAM_DISAGREEMENT = "downstream_disagreement"
_NONLOCAL_REGRESSION = "nonlocal_regression"


def validate_post_t240_layer15_output_split_contract(
    settings: Story31StabilityLabSettings,
) -> None:
    """Reject unsupported T241 settings before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_POST_T240_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (T241_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        f"Story 31 T241 supports only the fixed T237/T240 winner `{T241_REQUIRED_VARIANT}`."
    )


def build_post_t240_layer15_output_split_assessment(
    *,
    settings: Story31StabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> Story31PostT240Layer15OutputSplitAssessment | None:
    """Build the focused T241 assessment when the layer-15 split profile is active."""
    if settings.hook_profile != TALKER_CORE_POST_T240_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (T241_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_post_t240_layer15_output_split(
        matrix_rows=matrix_rows,
        stabilization_variant=T241_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_layer15_output_split(
        comparison_rows
    )
    return Story31PostT240Layer15OutputSplitAssessment(
        stabilization_variant=T241_REQUIRED_VARIANT,
        target_loss_kind=T241_TARGET_LOSS_KIND,
        target_corridor_surfaces=T241_TARGET_CORRIDOR_SURFACES,
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


def _comparison_rows_for_post_t240_layer15_output_split(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostT240Layer15OutputSplitComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_post_t240_layer15_output_split_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_post_t240_layer15_output_split_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostT240Layer15OutputSplitComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor in T241_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostT240Layer15OutputSplitComparisonRow(
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
        f"`{stabilization_variant}:{case_id}` for the T241 assessment."
    )


def _classify_layer15_output_split(
    comparison_rows: tuple[PostT240Layer15OutputSplitComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if len(comparison_rows) != 3:
        return (
            None,
            None,
            "Story 31 T241 could not resolve the full pair-versus-single case set.",
        )
    matched_surfaces = tuple(row.matched_corridor_surface for row in comparison_rows)
    if any(not row.case_has_non_finite for row in comparison_rows):
        return _NONLOCAL_REGRESSION, None, None
    if any(surface is None for surface in matched_surfaces):
        return _NONLOCAL_REGRESSION, None, None
    if all(surface == _GATED_PRODUCT_SURFACE for surface in matched_surfaces):
        return _CONVERGED_GATED_PRODUCT, _GATED_PRODUCT_SURFACE, None
    if all(surface == _MLP_DOWN_PROJ_SURFACE for surface in matched_surfaces):
        return _CONVERGED_MLP_DOWN_PROJ, _MLP_DOWN_PROJ_SURFACE, None
    if all(surface == _LAYER15_OUTPUT_SURFACE for surface in matched_surfaces):
        return _CONVERGED_LAYER15_OUTPUT, _LAYER15_OUTPUT_SURFACE, None
    if all(surface in T241_TARGET_CORRIDOR_SURFACES for surface in matched_surfaces):
        return _DOWNSTREAM_DISAGREEMENT, None, None
    return _NONLOCAL_REGRESSION, None, None


def _next_task_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _CONVERGED_GATED_PRODUCT and dominant_surface is not None:
        return (
            "Open a diagnosis-only follow-on to split layer-15 gated-product "
            f"formation under `{T241_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_MLP_DOWN_PROJ and dominant_surface is not None:
        return (
            "Open a diagnosis-only follow-on to split layer-15 down-proj output "
            f"formation under `{T241_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_LAYER15_OUTPUT and dominant_surface is not None:
        return (
            "Open a diagnosis-only follow-on to split layer-15 residual/output "
            f"formation under `{T241_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _DOWNSTREAM_DISAGREEMENT:
        return (
            "Open a row-local downstream outlier task under "
            f"`{T241_REQUIRED_VARIANT}` instead of claiming a generic layer-15 seam."
        )
    if classification == _NONLOCAL_REGRESSION:
        return (
            "Close T241 as non-promotable mechanism evidence and return Story 31 "
            "to upstream diagnosis."
        )
    return "The next Story 31 task remains blocked until the T241 layer-15 split resolves."
