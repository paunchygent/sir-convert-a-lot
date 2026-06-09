"""Focused sub-boundary sub-boundary assessment for the Qwen stability lab stability lab.

Purpose:
    Derive the narrowed post-layer-16 handoff pair-versus-single-row comparison from the
    compact Qwen stability lab matrix rows so the runner can keep orchestration separate
    from the sub-boundary diagnostic conclusion.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `qwen_stability_lab_contracts.py` for the typed sub-boundary payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_HANDOFF_SUB_BOUNDARY_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    QwenStabilityLabSettings,
    QwenSubBoundaryAssessment,
    StabilityLabMatrixRow,
    SubBoundaryComparisonRow,
)

SUB_BOUNDARY_TARGET_LOSS_KIND = "sub_talker_loss"
SUB_BOUNDARY_REQUIRED_VARIANT = LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5
SUB_BOUNDARY_SUB_BOUNDARY_TARGETS = (
    "talker_core.layer_16.mlp.down_proj",
    "talker_core.layer_16.output",
    "talker_core.layer_16.residual_handoff",
    "talker_core.layer_16.input_layernorm",
)
NORMALIZATION_ENTRY_ALLOWED_VARIANTS = (
    SUB_BOUNDARY_REQUIRED_VARIANT,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E3,
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_PRE_INPUT_LN_RESCALE_1E2,
)


def validate_hook_profile_variant_contract(settings: QwenStabilityLabSettings) -> None:
    """Reject unsupported narrowed-profile variant families before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_HANDOFF_SUB_BOUNDARY_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (SUB_BOUNDARY_REQUIRED_VARIANT,):
        return
    if (
        2 <= len(settings.stabilization_variants) <= len(NORMALIZATION_ENTRY_ALLOWED_VARIANTS)
        and settings.stabilization_variants[0] == SUB_BOUNDARY_REQUIRED_VARIANT
        and len(set(settings.stabilization_variants)) == len(settings.stabilization_variants)
        and all(
            variant in NORMALIZATION_ENTRY_ALLOWED_VARIANTS
            for variant in settings.stabilization_variants
        )
    ):
        return
    if len(settings.stabilization_variants) == 1:
        raise SystemExit(
            "Qwen stability lab handoff sub-boundary probing requires the ranked "
            "layer-16 handoff winner "
            f"`{SUB_BOUNDARY_REQUIRED_VARIANT}`."
        )
    raise SystemExit(
        "Qwen stability lab handoff sub-boundary probing supports only the ranked "
        "layer-16 handoff winner plus the bounded normalization-entry micro-family."
    )


def build_sub_boundary_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenSubBoundaryAssessment | None:
    """Build the focused sub-boundary assessment when the narrowed hook profile is active."""
    if settings.hook_profile != TALKER_CORE_HANDOFF_SUB_BOUNDARY_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (SUB_BOUNDARY_REQUIRED_VARIANT,):
        return None
    variant = settings.stabilization_variants[0]
    comparison_rows = _comparison_rows_for_sub_boundary_assessment(
        matrix_rows=matrix_rows,
        stabilization_variant=variant,
        source_lines=settings.source_lines,
    )
    matched_boundaries = {
        row.matched_sub_boundary for row in comparison_rows if row.matched_sub_boundary is not None
    }
    ambiguity_reason: str | None = None
    earliest_sub_boundary: str | None = None
    if len(matched_boundaries) == 1 and len(comparison_rows) == 3:
        earliest_sub_boundary = next(iter(matched_boundaries))
    elif any(not row.case_has_non_finite for row in comparison_rows):
        ambiguity_reason = (
            "One or more required SUB_BOUNDARY cases stayed finite under the narrowed probe."
        )
    elif any(row.matched_sub_boundary is None for row in comparison_rows):
        ambiguity_reason = (
            "One or more required SUB_BOUNDARY cases failed outside the "
            "committed sub-boundary chain."
        )
    else:
        ambiguity_reason = (
            "Pair and single-row sub-talker cases disagreed on the earliest sub-boundary."
        )
    return QwenSubBoundaryAssessment(
        stabilization_variant=variant,
        target_loss_kind=SUB_BOUNDARY_TARGET_LOSS_KIND,
        target_sub_boundaries=SUB_BOUNDARY_SUB_BOUNDARY_TARGETS,
        comparison_rows=comparison_rows,
        earliest_sub_boundary=earliest_sub_boundary,
        evidence_is_ambiguous=earliest_sub_boundary is None,
        ambiguity_reason=ambiguity_reason,
        next_micro_family_rule=_next_micro_family_rule(earliest_sub_boundary),
    )


def _comparison_rows_for_sub_boundary_assessment(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[SubBoundaryComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_sub_boundary_comparison_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_sub_boundary_comparison_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> SubBoundaryComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_sub_boundary = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor in SUB_BOUNDARY_SUB_BOUNDARY_TARGETS
        else None
    )
    return SubBoundaryComparisonRow(
        case_id=row.case_id,
        source_line_numbers=row.source_line_numbers,
        batch_size=row.batch_size,
        role=role,
        case_has_non_finite=row.case_has_non_finite,
        first_non_finite_talker_core_hook_tensor=row.first_non_finite_talker_core_hook_tensor,
        matched_sub_boundary=matched_sub_boundary,
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
        f"`{stabilization_variant}:{case_id}` for the SUB_BOUNDARY assessment."
    )


def _next_micro_family_rule(earliest_sub_boundary: str | None) -> str:
    if earliest_sub_boundary == "talker_core.layer_16.mlp.down_proj":
        return "NORMALIZATION_ENTRY may test one late-MLP/down-projection micro-family only."
    if earliest_sub_boundary in (
        "talker_core.layer_16.output",
        "talker_core.layer_16.residual_handoff",
    ):
        return "NORMALIZATION_ENTRY may test one residual-side handoff micro-family only."
    if earliest_sub_boundary == "talker_core.layer_16.input_layernorm":
        return (
            "NORMALIZATION_ENTRY may test one pre-input-layernorm "
            "normalization-entry micro-family only."
        )
    return (
        "NORMALIZATION_ENTRY must stay blocked until the SUB_BOUNDARY "
        "sub-boundary ambiguity is resolved."
    )
