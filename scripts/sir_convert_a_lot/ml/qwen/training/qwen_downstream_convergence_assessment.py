"""Focused downstream convergence downstream convergence assessment for the Qwen stability lab lab.

Purpose:
    Classify the post-row-local micro-family downstream seam beneath `layer_15.output` so the
    next Qwen stability lab slice follows one verified downstream boundary instead of
    widening into another stabilizer family or promotion attempt.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical downstream convergence corridor
      and `qwen_stability_lab_contracts.py` for the typed report payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_downstream_convergence_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_ROW_LOCAL_MICRO_FAMILY_DOWNSTREAM_CONVERGENCE_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostROW_LOCAL_MICRO_FAMILYDownstreamConvergenceComparisonRow,
    QwenDownstreamConvergenceAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

DOWNSTREAM_CONVERGENCE_TARGET_LOSS_KIND = "sub_talker_loss"
DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT = LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3
DOWNSTREAM_CONVERGENCE_TARGET_CORRIDOR_SURFACES = talker_core_downstream_convergence_trace_names()
_MLP_DOWN_PROJ_SURFACE = "talker_core.layer_15.mlp.down_proj"
_LAYER15_OUTPUT_SURFACE = "talker_core.layer_15.output"
_LAYER16_INPUT_HANDOFF_SURFACE = "talker_core.layer_16.input"
_UPSTREAM_GUARD_SURFACE = "talker_core.layer_16.input_layernorm.output"
_CONVERGED_MLP_DOWN_PROJ = "converged_mlp_down_proj"
_CONVERGED_LAYER15_OUTPUT = "converged_layer15_output"
_CONVERGED_LAYER16_INPUT_HANDOFF = "converged_layer16_input_handoff"
_DOWNSTREAM_DISAGREEMENT = "downstream_disagreement"
_UPSTREAM_OR_NONLOCAL_REGRESSION = "upstream_or_nonlocal_regression"


def validate_downstream_convergence_contract(
    settings: QwenStabilityLabSettings,
) -> None:
    """Reject unsupported downstream convergence settings before the Hemma probe starts."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_ROW_LOCAL_MICRO_FAMILY_DOWNSTREAM_CONVERGENCE_HOOK_PROFILE
    ):
        return
    if settings.stabilization_variants == (DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Qwen stability lab DOWNSTREAM_CONVERGENCE supports only the fixed "
        "ROW_LOCAL_MICRO_FAMILY winner "
        f"`{DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT}`."
    )


def build_downstream_convergence_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenDownstreamConvergenceAssessment | None:
    """Build the focused downstream convergence assessment when the downstream profile is active."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_ROW_LOCAL_MICRO_FAMILY_DOWNSTREAM_CONVERGENCE_HOOK_PROFILE
    ):
        return None
    if settings.stabilization_variants != (DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_downstream_convergence(
        matrix_rows=matrix_rows,
        stabilization_variant=DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_downstream_convergence(
        comparison_rows
    )
    return QwenDownstreamConvergenceAssessment(
        stabilization_variant=DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT,
        target_loss_kind=DOWNSTREAM_CONVERGENCE_TARGET_LOSS_KIND,
        target_corridor_surfaces=DOWNSTREAM_CONVERGENCE_TARGET_CORRIDOR_SURFACES,
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


def _comparison_rows_for_downstream_convergence(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostROW_LOCAL_MICRO_FAMILYDownstreamConvergenceComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_downstream_convergence_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_downstream_convergence_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostROW_LOCAL_MICRO_FAMILYDownstreamConvergenceComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor
        in DOWNSTREAM_CONVERGENCE_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostROW_LOCAL_MICRO_FAMILYDownstreamConvergenceComparisonRow(
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
        "Qwen stability lab stability lab could not resolve the required matrix row "
        f"`{stabilization_variant}:{case_id}` for the DOWNSTREAM_CONVERGENCE assessment."
    )


def _classify_downstream_convergence(
    comparison_rows: tuple[PostROW_LOCAL_MICRO_FAMILYDownstreamConvergenceComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if len(comparison_rows) != 3:
        return (
            None,
            None,
            "Qwen stability lab DOWNSTREAM_CONVERGENCE could not resolve the "
            "full pair-versus-single case set.",
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
    if all(
        surface in DOWNSTREAM_CONVERGENCE_TARGET_CORRIDOR_SURFACES[:-1]
        for surface in matched_surfaces
    ):
        return _DOWNSTREAM_DISAGREEMENT, None, None
    return _UPSTREAM_OR_NONLOCAL_REGRESSION, None, None


def _next_followup_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _CONVERGED_MLP_DOWN_PROJ and dominant_surface is not None:
        return (
            "Open diagnosis-only LAYER15_OUTPUT_SPLIT to split "
            "`talker_core.layer_15.mlp.gated_product` versus "
            f"`{dominant_surface}` under `{DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT}`."
        )
    if classification == _CONVERGED_LAYER15_OUTPUT and dominant_surface is not None:
        return (
            "Open diagnosis-only LAYER15_OUTPUT_SPLIT to split layer-15 residual/output formation "
            f"under `{DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_LAYER16_INPUT_HANDOFF and dominant_surface is not None:
        return (
            "Open diagnosis-only LAYER15_OUTPUT_SPLIT to split the layer-15 to layer-16 handoff "
            f"under `{DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _DOWNSTREAM_DISAGREEMENT:
        return (
            "Open a row-local downstream outlier task under "
            f"`{DOWNSTREAM_CONVERGENCE_REQUIRED_VARIANT}` instead of claiming a generic seam."
        )
    if classification == _UPSTREAM_OR_NONLOCAL_REGRESSION:
        return (
            "Close DOWNSTREAM_CONVERGENCE as non-promotable mechanism evidence "
            "and return Qwen stability lab "
            "to upstream diagnosis."
        )
    return (
        "The next Qwen stability lab task remains blocked until the "
        "DOWNSTREAM_CONVERGENCE downstream split resolves."
    )
