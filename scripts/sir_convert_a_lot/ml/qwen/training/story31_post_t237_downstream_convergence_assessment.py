"""Focused T240 downstream convergence assessment for the Story 31 lab.

Purpose:
    Classify the post-T237 downstream seam beneath `layer_15.output` so the
    next Story 31 slice follows one verified downstream boundary instead of
    widening into another stabilizer family or promotion attempt.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical T240 corridor
      and `story31_stability_lab_contracts.py` for the typed report payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_post_t237_downstream_convergence_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T237_DOWNSTREAM_CONVERGENCE_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    PostT237DownstreamConvergenceComparisonRow,
    StabilityLabMatrixRow,
    Story31PostT237DownstreamConvergenceAssessment,
    Story31StabilityLabSettings,
)

T240_TARGET_LOSS_KIND = "sub_talker_loss"
T240_REQUIRED_VARIANT = LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3
T240_TARGET_CORRIDOR_SURFACES = talker_core_post_t237_downstream_convergence_trace_names()
_MLP_DOWN_PROJ_SURFACE = "talker_core.layer_15.mlp.down_proj"
_LAYER15_OUTPUT_SURFACE = "talker_core.layer_15.output"
_LAYER16_INPUT_HANDOFF_SURFACE = "talker_core.layer_16.input"
_UPSTREAM_GUARD_SURFACE = "talker_core.layer_16.input_layernorm.output"
_CONVERGED_MLP_DOWN_PROJ = "converged_mlp_down_proj"
_CONVERGED_LAYER15_OUTPUT = "converged_layer15_output"
_CONVERGED_LAYER16_INPUT_HANDOFF = "converged_layer16_input_handoff"
_DOWNSTREAM_DISAGREEMENT = "downstream_disagreement"
_UPSTREAM_OR_NONLOCAL_REGRESSION = "upstream_or_nonlocal_regression"


def validate_post_t237_downstream_convergence_contract(
    settings: Story31StabilityLabSettings,
) -> None:
    """Reject unsupported T240 settings before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_POST_T237_DOWNSTREAM_CONVERGENCE_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (T240_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        f"Story 31 T240 supports only the fixed T237 winner `{T240_REQUIRED_VARIANT}`."
    )


def build_post_t237_downstream_convergence_assessment(
    *,
    settings: Story31StabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> Story31PostT237DownstreamConvergenceAssessment | None:
    """Build the focused T240 assessment when the downstream profile is active."""
    if settings.hook_profile != TALKER_CORE_POST_T237_DOWNSTREAM_CONVERGENCE_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (T240_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_post_t237_downstream_convergence(
        matrix_rows=matrix_rows,
        stabilization_variant=T240_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_downstream_convergence(
        comparison_rows
    )
    return Story31PostT237DownstreamConvergenceAssessment(
        stabilization_variant=T240_REQUIRED_VARIANT,
        target_loss_kind=T240_TARGET_LOSS_KIND,
        target_corridor_surfaces=T240_TARGET_CORRIDOR_SURFACES,
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


def _comparison_rows_for_post_t237_downstream_convergence(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostT237DownstreamConvergenceComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_post_t237_downstream_convergence_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_post_t237_downstream_convergence_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostT237DownstreamConvergenceComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor in T240_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostT237DownstreamConvergenceComparisonRow(
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
        f"`{stabilization_variant}:{case_id}` for the T240 assessment."
    )


def _classify_downstream_convergence(
    comparison_rows: tuple[PostT237DownstreamConvergenceComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if len(comparison_rows) != 3:
        return (
            None,
            None,
            "Story 31 T240 could not resolve the full pair-versus-single case set.",
        )
    matched_surfaces = tuple(row.matched_corridor_surface for row in comparison_rows)
    if any(not row.case_has_non_finite for row in comparison_rows):
        return _UPSTREAM_OR_NONLOCAL_REGRESSION, None, None
    if any(surface is None for surface in matched_surfaces):
        return _UPSTREAM_OR_NONLOCAL_REGRESSION, None, None
    if any(surface == _UPSTREAM_GUARD_SURFACE for surface in matched_surfaces):
        return _UPSTREAM_OR_NONLOCAL_REGRESSION, _UPSTREAM_GUARD_SURFACE, None
    if all(surface == _MLP_DOWN_PROJ_SURFACE for surface in matched_surfaces):
        return _CONVERGED_MLP_DOWN_PROJ, _MLP_DOWN_PROJ_SURFACE, None
    if all(surface == _LAYER15_OUTPUT_SURFACE for surface in matched_surfaces):
        return _CONVERGED_LAYER15_OUTPUT, _LAYER15_OUTPUT_SURFACE, None
    if all(surface == _LAYER16_INPUT_HANDOFF_SURFACE for surface in matched_surfaces):
        return _CONVERGED_LAYER16_INPUT_HANDOFF, _LAYER16_INPUT_HANDOFF_SURFACE, None
    if all(surface in T240_TARGET_CORRIDOR_SURFACES[:-1] for surface in matched_surfaces):
        return _DOWNSTREAM_DISAGREEMENT, None, None
    return _UPSTREAM_OR_NONLOCAL_REGRESSION, None, None


def _next_task_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _CONVERGED_MLP_DOWN_PROJ and dominant_surface is not None:
        return (
            "Open diagnosis-only T241 to split "
            "`talker_core.layer_15.mlp.gated_product` versus "
            f"`{dominant_surface}` under `{T240_REQUIRED_VARIANT}`."
        )
    if classification == _CONVERGED_LAYER15_OUTPUT and dominant_surface is not None:
        return (
            "Open diagnosis-only T241 to split layer-15 residual/output formation "
            f"under `{T240_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_LAYER16_INPUT_HANDOFF and dominant_surface is not None:
        return (
            "Open diagnosis-only T241 to split the layer-15 to layer-16 handoff "
            f"under `{T240_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _DOWNSTREAM_DISAGREEMENT:
        return (
            "Open a row-local downstream outlier task under "
            f"`{T240_REQUIRED_VARIANT}` instead of claiming a generic seam."
        )
    if classification == _UPSTREAM_OR_NONLOCAL_REGRESSION:
        return (
            "Close T240 as non-promotable mechanism evidence and return Story 31 "
            "to upstream diagnosis."
        )
    return "The next Story 31 task remains blocked until the T240 downstream split resolves."
