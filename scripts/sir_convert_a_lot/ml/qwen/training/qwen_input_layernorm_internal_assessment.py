"""
Focused input-layernorm internal internal layernorm assessment for the Qwen stability lab stability
lab.

Purpose:
    Derive the normalization-internal pair-versus-single-row conclusion from
    the compact Qwen stability lab matrix rows so the runner can keep orchestration
    separate from the input-layernorm internal mechanism decision.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical input-layernorm internal internal
      trace order and `qwen_stability_lab_contracts.py` for the typed payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_input_layernorm_internal_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    InputLayernormInternalComparisonRow,
    QwenInputLayernormInternalAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

INPUT_LAYERNORM_INTERNAL_TARGET_LOSS_KIND = "sub_talker_loss"
INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT = (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5
)
INPUT_LAYERNORM_INTERNAL_TARGET_INTERNAL_SURFACES = (
    talker_core_input_layernorm_internal_trace_names()
)


def validate_input_layernorm_internal_contract(settings: QwenStabilityLabSettings) -> None:
    """Reject unsupported input-layernorm internal variants before the Hemma probe."""
    if settings.hook_profile != TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Qwen stability lab input-layernorm-internal probing supports only the "
        "ranked SUB_BOUNDARY/NORMALIZATION_ENTRY "
        f"baseline variant `{INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT}`."
    )


def build_input_layernorm_internal_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenInputLayernormInternalAssessment | None:
    """Build the focused input-layernorm internal assessment when the internal profile is active."""
    if settings.hook_profile != TALKER_CORE_INPUT_LAYERNORM_INTERNAL_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_input_layernorm_internal_assessment(
        matrix_rows=matrix_rows,
        stabilization_variant=INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    matched_surfaces = {
        row.matched_internal_surface
        for row in comparison_rows
        if row.matched_internal_surface is not None
    }
    earliest_internal_surface: str | None = None
    ambiguity_reason: str | None = None
    if len(comparison_rows) != 3:
        ambiguity_reason = (
            "Qwen stability lab INPUT_LAYERNORM_INTERNAL could not resolve the "
            "full pair-versus-single case set."
        )
    elif len(matched_surfaces) == 1:
        earliest_internal_surface = next(iter(matched_surfaces))
    elif any(not row.case_has_non_finite for row in comparison_rows):
        ambiguity_reason = (
            "One or more required INPUT_LAYERNORM_INTERNAL cases stayed finite "
            "under the internal probe."
        )
    elif any(row.matched_internal_surface is None for row in comparison_rows):
        ambiguity_reason = (
            "One or more required INPUT_LAYERNORM_INTERNAL cases failed outside the committed "
            "input-layernorm internal chain."
        )
    else:
        ambiguity_reason = (
            "Pair and single-row sub-talker cases disagreed on the earliest "
            "input-layernorm internal surface."
        )
    return QwenInputLayernormInternalAssessment(
        stabilization_variant=INPUT_LAYERNORM_INTERNAL_REQUIRED_VARIANT,
        target_loss_kind=INPUT_LAYERNORM_INTERNAL_TARGET_LOSS_KIND,
        target_internal_surfaces=INPUT_LAYERNORM_INTERNAL_TARGET_INTERNAL_SURFACES,
        comparison_rows=comparison_rows,
        earliest_internal_surface=earliest_internal_surface,
        evidence_is_ambiguous=earliest_internal_surface is None,
        ambiguity_reason=ambiguity_reason,
        next_micro_family_rule=_next_micro_family_rule(earliest_internal_surface),
    )


def _comparison_rows_for_input_layernorm_internal_assessment(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[InputLayernormInternalComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_input_layernorm_internal_comparison_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_input_layernorm_internal_comparison_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> InputLayernormInternalComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_internal_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor
        in INPUT_LAYERNORM_INTERNAL_TARGET_INTERNAL_SURFACES
        else None
    )
    return InputLayernormInternalComparisonRow(
        case_id=row.case_id,
        source_line_numbers=row.source_line_numbers,
        batch_size=row.batch_size,
        role=role,
        case_has_non_finite=row.case_has_non_finite,
        first_non_finite_talker_core_hook_tensor=row.first_non_finite_talker_core_hook_tensor,
        matched_internal_surface=matched_internal_surface,
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
        f"`{stabilization_variant}:{case_id}` for the INPUT_LAYERNORM_INTERNAL assessment."
    )


def _next_micro_family_rule(earliest_internal_surface: str | None) -> str:
    if earliest_internal_surface in (
        "talker_core.layer_16.input_layernorm.residual_input",
        "talker_core.layer_16.input_layernorm.fp32_input",
    ):
        return "The next task may test one upstream residual-amplitude micro-family only."
    if earliest_internal_surface in (
        "talker_core.layer_16.input_layernorm.variance",
        "talker_core.layer_16.input_layernorm.normalized_hidden_states",
    ):
        return "The next task may test one normalization-internal numeric-safety micro-family only."
    if earliest_internal_surface == "talker_core.layer_16.input_layernorm.output":
        return "The next task may test one post-normalization output-scale micro-family only."
    return "The next task remains blocked until the INPUT_LAYERNORM_INTERNAL ambiguity is resolved."
