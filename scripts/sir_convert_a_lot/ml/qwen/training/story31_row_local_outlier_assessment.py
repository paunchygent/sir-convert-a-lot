"""Focused T236 row-local outlier assessment for the Story 31 stability lab.

Purpose:
    Derive the post-T235 row-local line-4 conclusion from the compact Story 31
    matrix rows so the runner can keep orchestration separate from the T236
    branching decision.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical T236 corridor
      and `story31_stability_lab_contracts.py` for the typed payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_post_t235_row_local_outlier_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    PostT235RowLocalOutlierComparisonRow,
    StabilityLabMatrixRow,
    Story31PostT235RowLocalOutlierAssessment,
    Story31StabilityLabSettings,
)

T236_TARGET_LOSS_KIND = "sub_talker_loss"
T236_REQUIRED_VARIANT = (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5
)
T236_TARGET_OUTLIER_SURFACES = talker_core_post_t235_row_local_outlier_trace_names()
_ROW_LOCAL_DIFFERENCE = "genuine_row_local_seam_difference"
_PAIR_MASKING = "pair_interaction_masking_effect"
_NON_REPEATABLE = "non_repeatable_one_row_instability"


def validate_post_t235_row_local_outlier_contract(
    settings: Story31StabilityLabSettings,
) -> None:
    """Reject unsupported T236 settings before the Hemma probe starts."""
    if settings.hook_profile != TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE:
        return
    if settings.stabilization_variants == (T236_REQUIRED_VARIANT,):
        return
    raise SystemExit(
        "Story 31 row-local outlier probing supports only the strongest T234 "
        f"member `{T236_REQUIRED_VARIANT}`."
    )


def build_post_t235_row_local_outlier_assessment(
    *,
    settings: Story31StabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> Story31PostT235RowLocalOutlierAssessment | None:
    """Build the focused T236 assessment when the row-local profile is active."""
    if settings.hook_profile != TALKER_CORE_POST_T235_ROW_LOCAL_OUTLIER_HOOK_PROFILE:
        return None
    if settings.stabilization_variants != (T236_REQUIRED_VARIANT,):
        return None
    comparison_rows = _comparison_rows_for_post_t235_row_local_outlier(
        matrix_rows=matrix_rows,
        stabilization_variant=T236_REQUIRED_VARIANT,
        source_lines=settings.source_lines,
    )
    classification, dominant_surface, ambiguity_reason = _classify_outlier(comparison_rows)
    return Story31PostT235RowLocalOutlierAssessment(
        stabilization_variant=T236_REQUIRED_VARIANT,
        target_loss_kind=T236_TARGET_LOSS_KIND,
        target_outlier_surfaces=T236_TARGET_OUTLIER_SURFACES,
        comparison_rows=comparison_rows,
        outlier_classification=classification,
        dominant_surface=dominant_surface,
        evidence_is_ambiguous=classification is None,
        ambiguity_reason=ambiguity_reason,
        next_micro_family_rule=_next_micro_family_rule(
            classification=classification,
            dominant_surface=dominant_surface,
        ),
    )


def _comparison_rows_for_post_t235_row_local_outlier(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    source_lines: tuple[int, int],
) -> tuple[PostT235RowLocalOutlierComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_post_t235_row_local_outlier_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for case_id, role in case_ids
    )


def _build_post_t235_row_local_outlier_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostT235RowLocalOutlierComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_outlier_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor in T236_TARGET_OUTLIER_SURFACES
        else None
    )
    return PostT235RowLocalOutlierComparisonRow(
        case_id=row.case_id,
        source_line_numbers=row.source_line_numbers,
        batch_size=row.batch_size,
        role=role,
        case_has_non_finite=row.case_has_non_finite,
        first_non_finite_talker_core_hook_tensor=row.first_non_finite_talker_core_hook_tensor,
        matched_outlier_surface=matched_outlier_surface,
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
        f"`{stabilization_variant}:{case_id}` for the T236 assessment."
    )


def _classify_outlier(
    comparison_rows: tuple[PostT235RowLocalOutlierComparisonRow, ...],
) -> tuple[str | None, str | None, str | None]:
    if len(comparison_rows) != 3:
        return (
            None,
            None,
            "Story 31 T236 could not resolve the full pair-versus-single case set.",
        )
    if any(not row.case_has_non_finite for row in comparison_rows):
        return (
            None,
            None,
            "One or more required T236 cases stayed finite under the row-local probe.",
        )
    if any(row.matched_outlier_surface is None for row in comparison_rows):
        return (
            None,
            None,
            "One or more required T236 cases failed outside the committed row-local corridor.",
        )
    pair_row, first_row, second_row = comparison_rows
    if (
        pair_row.matched_outlier_surface == first_row.matched_outlier_surface
        and pair_row.matched_outlier_surface != second_row.matched_outlier_surface
    ):
        return _ROW_LOCAL_DIFFERENCE, second_row.matched_outlier_surface, None
    if (
        first_row.matched_outlier_surface == second_row.matched_outlier_surface
        and pair_row.matched_outlier_surface != first_row.matched_outlier_surface
    ):
        return _PAIR_MASKING, pair_row.matched_outlier_surface, None
    if (
        pair_row.matched_outlier_surface
        == first_row.matched_outlier_surface
        == second_row.matched_outlier_surface
    ):
        return _NON_REPEATABLE, pair_row.matched_outlier_surface, None
    return (
        None,
        None,
        "Pair and single-row sub-talker cases still disagree on the dominant outlier seam.",
    )


def _next_micro_family_rule(
    *,
    classification: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _ROW_LOCAL_DIFFERENCE and dominant_surface is not None:
        return (
            f"T237 may test one upstream row-local micro-family only against `{dominant_surface}`."
        )
    if classification == _PAIR_MASKING and dominant_surface is not None:
        return (
            "T237 may test one interaction-controlled micro-family only against "
            f"`{dominant_surface}`."
        )
    if classification == _NON_REPEATABLE and dominant_surface is not None:
        return (
            "T237 may test one micro-family only against the verified dominant seam "
            f"`{dominant_surface}`."
        )
    return "T237 remains blocked until the T236 row-local outlier is resolved cleanly."
