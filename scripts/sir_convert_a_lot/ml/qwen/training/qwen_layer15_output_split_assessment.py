"""Focused layer-15 split layer-15 output split assessment for the Qwen stability lab lab.

Purpose:
    Classify the post-downstream convergence converged `layer_15.output` seam one level deeper
    so the next Qwen stability lab slice follows one verified layer-15 sub-boundary
    instead of widening into a new stabilizer family.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical layer-15 split corridor
      and `qwen_stability_lab_contracts.py` for the typed report payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_layer15_output_split_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_DOWNSTREAM_CONVERGENCE_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostDOWNSTREAM_CONVERGENCELayer15OutputSplitComparisonRow,
    QwenLayer15OutputSplitAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

LAYER15_OUTPUT_SPLIT_TARGET_LOSS_KIND = "sub_talker_loss"
LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT = LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3
LAYER15_OUTPUT_SPLIT_TARGET_CORRIDOR_SURFACES = talker_core_layer15_output_split_trace_names()
_GATED_PRODUCT_SURFACE = "talker_core.layer_15.mlp.gated_product"
_MLP_DOWN_PROJ_SURFACE = "talker_core.layer_15.mlp.down_proj"
_LAYER15_OUTPUT_SURFACE = "talker_core.layer_15.output"
_LAYER16_INPUT_SURFACE = "talker_core.layer_16.input"
_CONVERGED_GATED_PRODUCT = "converged_mlp_gated_product"
_CONVERGED_MLP_DOWN_PROJ = "converged_mlp_down_proj"
_CONVERGED_LAYER15_OUTPUT = "converged_layer15_output_residual"
_DOWNSTREAM_DISAGREEMENT = "downstream_disagreement"
_NONLOCAL_REGRESSION = "nonlocal_regression"


def validate_layer15_output_split_contract(
    settings: QwenStabilityLabSettings,
) -> None:
    """Reject unsupported layer-15 split settings before the Hemma probe starts."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_DOWNSTREAM_CONVERGENCE_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE
    ):
        return
    if settings.stabilization_variants == (LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Qwen stability lab layer-15 output split supports only the fixed "
        "row-local micro-family/downstream-convergence winner "
        f"`{LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT}`."
    )


def build_layer15_output_split_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenLayer15OutputSplitAssessment | None:
    """Build the focused layer-15 split assessment when the layer-15 split profile is active."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_DOWNSTREAM_CONVERGENCE_LAYER15_OUTPUT_SPLIT_HOOK_PROFILE
    ):
        return None
    if settings.stabilization_variants != (LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_layer15_output_split(
        matrix_rows=matrix_rows,
        stabilization_variant=LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_layer15_output_split(
        comparison_rows
    )
    return QwenLayer15OutputSplitAssessment(
        stabilization_variant=LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT,
        target_loss_kind=LAYER15_OUTPUT_SPLIT_TARGET_LOSS_KIND,
        target_corridor_surfaces=LAYER15_OUTPUT_SPLIT_TARGET_CORRIDOR_SURFACES,
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


def _comparison_rows_for_layer15_output_split(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostDOWNSTREAM_CONVERGENCELayer15OutputSplitComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_layer15_output_split_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_layer15_output_split_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostDOWNSTREAM_CONVERGENCELayer15OutputSplitComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor
        in LAYER15_OUTPUT_SPLIT_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostDOWNSTREAM_CONVERGENCELayer15OutputSplitComparisonRow(
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
        f"`{stabilization_variant}:{case_id}` for the LAYER15_OUTPUT_SPLIT assessment."
    )


def _classify_layer15_output_split(
    comparison_rows: tuple[PostDOWNSTREAM_CONVERGENCELayer15OutputSplitComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if len(comparison_rows) != 3:
        return (
            None,
            None,
            "Qwen stability lab LAYER15_OUTPUT_SPLIT could not resolve the "
            "full pair-versus-single case set.",
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
    if all(
        surface in LAYER15_OUTPUT_SPLIT_TARGET_CORRIDOR_SURFACES for surface in matched_surfaces
    ):
        return _DOWNSTREAM_DISAGREEMENT, None, None
    return _NONLOCAL_REGRESSION, None, None


def _next_followup_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _CONVERGED_GATED_PRODUCT and dominant_surface is not None:
        return (
            "Open a diagnosis-only follow-on to split layer-15 gated-product "
            f"formation under `{LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_MLP_DOWN_PROJ and dominant_surface is not None:
        return (
            "Open a diagnosis-only follow-on to split layer-15 down-proj output "
            f"formation under `{LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _CONVERGED_LAYER15_OUTPUT and dominant_surface is not None:
        return (
            "Open a diagnosis-only follow-on to split layer-15 residual/output "
            f"formation under `{LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT}` at `{dominant_surface}`."
        )
    if classification == _DOWNSTREAM_DISAGREEMENT:
        return (
            "Open a row-local downstream outlier task under "
            f"`{LAYER15_OUTPUT_SPLIT_REQUIRED_VARIANT}` instead of claiming "
            "a generic layer-15 seam."
        )
    if classification == _NONLOCAL_REGRESSION:
        return (
            "Close LAYER15_OUTPUT_SPLIT as non-promotable mechanism evidence "
            "and return Qwen stability lab "
            "to upstream diagnosis."
        )
    return (
        "The next Qwen stability lab task remains blocked until the "
        "LAYER15_OUTPUT_SPLIT layer-15 split resolves."
    )
