"""Focused sub-talker disagreement assessment for the Qwen stability lab.

Purpose:
    Derive the mixed post-input-layernorm output `sub_talker_loss` conclusion from the compact
    Qwen stability lab matrix rows so the runner can keep orchestration separate from
    the disagreement-resolution decision.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `qwen_stability_lab_contracts.py` for the typed sub-talker disagreement payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_INPUT_LAYERNORM_OUTPUT_DISAGREEMENT_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow,
    QwenStabilityLabSettings,
    QwenSubTalkerDisagreementAssessment,
    StabilityLabMatrixRow,
)

SUB_TALKER_DISAGREEMENT_TARGET_LOSS_KIND = "sub_talker_loss"
SUB_TALKER_DISAGREEMENT_REQUIRED_VARIANT = (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5
)
SUB_TALKER_DISAGREEMENT_TARGET_CORRIDOR_SURFACES = (
    "talker_core.layer_15.output",
    "talker_core.layer_16.input",
    "talker_core.layer_16.input_layernorm",
)


def validate_sub_talker_disagreement_contract(settings: QwenStabilityLabSettings) -> None:
    """Reject unsupported sub-talker disagreement settings before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_POST_INPUT_LAYERNORM_OUTPUT_DISAGREEMENT_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (SUB_TALKER_DISAGREEMENT_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Qwen stability lab post-INPUT_LAYERNORM_OUTPUT disagreement probing "
        "supports only the strongest INPUT_LAYERNORM_OUTPUT "
        f"member `{SUB_TALKER_DISAGREEMENT_REQUIRED_VARIANT}`."
    )


def build_sub_talker_disagreement_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenSubTalkerDisagreementAssessment | None:
    """Build the sub-talker assessment when the disagreement profile is active."""
    if settings.hook_profile != TALKER_CORE_POST_INPUT_LAYERNORM_OUTPUT_DISAGREEMENT_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (SUB_TALKER_DISAGREEMENT_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_sub_talker_disagreement(
        matrix_rows=matrix_rows,
        stabilization_variant=SUB_TALKER_DISAGREEMENT_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    matched_surfaces = {
        row.matched_corridor_surface
        for row in comparison_rows
        if row.matched_corridor_surface is not None
    }
    earliest_corridor_surface: str | None = None
    ambiguity_reason: str | None = None
    if len(comparison_rows) != 3:
        ambiguity_reason = (
            "Qwen stability lab SUB_TALKER_DISAGREEMENT could not resolve the "
            "full pair-versus-single case set."
        )
    elif len(matched_surfaces) == 1:
        earliest_corridor_surface = next(iter(matched_surfaces))
    elif any(not row.case_has_non_finite for row in comparison_rows):
        ambiguity_reason = (
            "One or more required SUB_TALKER_DISAGREEMENT cases stayed finite "
            "under the disagreement probe."
        )
    elif any(row.matched_corridor_surface is None for row in comparison_rows):
        ambiguity_reason = (
            "One or more required SUB_TALKER_DISAGREEMENT cases failed outside "
            "the committed disagreement corridor."
        )
    elif _is_second_row_outlier(comparison_rows):
        ambiguity_reason = (
            "Pair and first-row cases moved downstream to `layer_15.output`, "
            "but the second row stayed upstream."
        )
    else:
        ambiguity_reason = (
            "Pair and single-row sub-talker cases disagreed across the committed "
            "post-INPUT_LAYERNORM_OUTPUT corridor."
        )
    return QwenSubTalkerDisagreementAssessment(
        stabilization_variant=SUB_TALKER_DISAGREEMENT_REQUIRED_VARIANT,
        target_loss_kind=SUB_TALKER_DISAGREEMENT_TARGET_LOSS_KIND,
        target_corridor_surfaces=SUB_TALKER_DISAGREEMENT_TARGET_CORRIDOR_SURFACES,
        comparison_rows=comparison_rows,
        earliest_corridor_surface=earliest_corridor_surface,
        evidence_is_ambiguous=earliest_corridor_surface is None,
        ambiguity_reason=ambiguity_reason,
        next_micro_family_rule=_next_micro_family_rule(
            earliest_corridor_surface=earliest_corridor_surface,
            comparison_rows=comparison_rows,
        ),
    )


def _comparison_rows_for_sub_talker_disagreement(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_sub_talker_disagreement_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_sub_talker_disagreement_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor
        in SUB_TALKER_DISAGREEMENT_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow(
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
        f"`{stabilization_variant}:{case_id}` for the SUB_TALKER_DISAGREEMENT assessment."
    )


def _is_second_row_outlier(
    comparison_rows: tuple[PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow, ...],
) -> bool:
    if len(comparison_rows) != 3:
        return False
    pair_row, first_row, second_row = comparison_rows
    return (
        pair_row.matched_corridor_surface == "talker_core.layer_15.output"
        and first_row.matched_corridor_surface == "talker_core.layer_15.output"
        and second_row.matched_corridor_surface
        in ("talker_core.layer_16.input", "talker_core.layer_16.input_layernorm")
    )


def _next_micro_family_rule(
    *,
    earliest_corridor_surface: str | None,
    comparison_rows: tuple[PostINPUT_LAYERNORM_OUTPUTDisagreementComparisonRow, ...],
) -> str:
    if earliest_corridor_surface == "talker_core.layer_15.output":
        return "ROW_LOCAL_OUTLIER may split the downstream layer_15.output seam only."
    if earliest_corridor_surface == "talker_core.layer_16.input":
        return "ROW_LOCAL_OUTLIER may split the layer_16 input handoff seam only."
    if earliest_corridor_surface == "talker_core.layer_16.input_layernorm":
        return (
            "ROW_LOCAL_OUTLIER must treat the INPUT_LAYERNORM_OUTPUT "
            "relocation signal as non-repeatable and "
            "close the output-scale family."
        )
    if _is_second_row_outlier(comparison_rows):
        return (
            "ROW_LOCAL_OUTLIER must resolve the row-local second-row outlier before claiming "
            "a generic layer_15.output seam."
        )
    return (
        "ROW_LOCAL_OUTLIER remains blocked until the SUB_TALKER_DISAGREEMENT "
        "disagreement is resolved cleanly."
    )
