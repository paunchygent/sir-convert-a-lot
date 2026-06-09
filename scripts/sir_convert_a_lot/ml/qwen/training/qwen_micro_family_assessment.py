"""Focused row-local micro-family row-local micro-family assessment for the Qwen stability lab lab.

Purpose:
    Classify the post-row-local outlier fp32-output-cap family against the repeatable
    line-4 seam so the next Qwen stability lab task follows the family outcome rather
    than ad hoc interpretation.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for run-time validation and
      report assembly.
    - Reuses `sft_12hz_talker_core_trace.py` for the canonical row-local outlier corridor
      and `qwen_stability_lab_contracts.py` for the typed report payload.
"""

from __future__ import annotations

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_trace import (
    talker_core_row_local_outlier_trace_names,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_hooks import (
    TALKER_CORE_POST_SUB_TALKER_DISAGREEMENT_ROW_LOCAL_OUTLIER_HOOK_PROFILE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow,
    QwenMicroFamilyAssessment,
    QwenStabilityLabSettings,
    StabilityLabMatrixRow,
)

ROW_LOCAL_MICRO_FAMILY_TARGET_LOSS_KIND = "sub_talker_loss"
ROW_LOCAL_MICRO_FAMILY_BASELINE_VARIANT = (
    LAYER16_GATED_FP32_RESCALE_1E3_LAYER16_OUT_0P5_LAYER15_OUT_0P5_LAYER16_INPUT_LN_OUTPUT_0P5
)
ROW_LOCAL_MICRO_FAMILY_CANDIDATE_VARIANTS = (
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E3,
    LAYER16_INPUT_LN_OUTPUT_0P5_FP32_OUTPUT_CAP_1E2,
)
ROW_LOCAL_MICRO_FAMILY_REQUIRED_VARIANTS = (
    ROW_LOCAL_MICRO_FAMILY_BASELINE_VARIANT,
    *ROW_LOCAL_MICRO_FAMILY_CANDIDATE_VARIANTS,
)
ROW_LOCAL_MICRO_FAMILY_TARGET_CORRIDOR_SURFACES = talker_core_row_local_outlier_trace_names()
_UPSTREAM_SURFACE = "talker_core.layer_16.input_layernorm.output"
_DOWNSTREAM_SURFACE = "talker_core.layer_15.output"
_UPSTREAM_PERSISTENT = "upstream_persistent"
_CONVERGED_DOWNSTREAM = "converged_downstream"
_NON_LOCAL_REGRESSION = "non_local_regression"


def validate_row_local_micro_family_contract(
    settings: QwenStabilityLabSettings,
) -> None:
    """Reject unsupported row-local micro-family settings before the Hemma probe starts."""
    if (
        settings.hook_profile
        != TALKER_CORE_POST_SUB_TALKER_DISAGREEMENT_ROW_LOCAL_OUTLIER_HOOK_PROFILE
    ):
        return
    if settings.stabilization_variants == ROW_LOCAL_MICRO_FAMILY_REQUIRED_VARIANTS:
        return
    raise SystemExit(
        "Qwen stability lab row-local micro-family supports only the fixed "
        "baseline plus fp32 output-cap variants."
    )


def build_row_local_micro_family_assessment(
    *,
    settings: QwenStabilityLabSettings,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
) -> QwenMicroFamilyAssessment | None:
    """
    Build the focused row-local micro-family family assessment when the outlier corridor is active.
    """
    if (
        settings.hook_profile
        != TALKER_CORE_POST_SUB_TALKER_DISAGREEMENT_ROW_LOCAL_OUTLIER_HOOK_PROFILE
    ):
        return None
    if settings.stabilization_variants != ROW_LOCAL_MICRO_FAMILY_REQUIRED_VARIANTS:
        return None
    comparison_rows = _comparison_rows_for_post_row_local_outlier_micro_family(
        matrix_rows=matrix_rows,
        stabilization_variants=settings.stabilization_variants,
        source_lines=settings.source_lines,
    )
    classification, winning_variant, dominant_surface, ambiguity_reason = _classify_family(
        comparison_rows=comparison_rows
    )
    return QwenMicroFamilyAssessment(
        baseline_variant=ROW_LOCAL_MICRO_FAMILY_BASELINE_VARIANT,
        candidate_variants=ROW_LOCAL_MICRO_FAMILY_CANDIDATE_VARIANTS,
        target_loss_kind=ROW_LOCAL_MICRO_FAMILY_TARGET_LOSS_KIND,
        target_corridor_surfaces=ROW_LOCAL_MICRO_FAMILY_TARGET_CORRIDOR_SURFACES,
        comparison_rows=comparison_rows,
        family_classification=classification,
        winning_candidate_variant=winning_variant,
        dominant_surface=dominant_surface,
        evidence_is_ambiguous=classification is None,
        ambiguity_reason=ambiguity_reason,
        next_task_rule=_next_followup_rule(
            classification=classification,
            winning_variant=winning_variant,
            dominant_surface=dominant_surface,
        ),
    )


def _comparison_rows_for_post_row_local_outlier_micro_family(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variants: tuple[str, ...],
    source_lines: tuple[int, int],
) -> tuple[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow, ...]:
    case_ids = (
        ("pair-sub-talker-loss", "pair"),
        (f"line-{source_lines[0]}-sub-talker-loss", "first_row"),
        (f"line-{source_lines[1]}-sub-talker-loss", "second_row"),
    )
    return tuple(
        _build_post_row_local_outlier_micro_family_row(
            matrix_rows=matrix_rows,
            stabilization_variant=stabilization_variant,
            case_id=case_id,
            role=role,
        )
        for stabilization_variant in stabilization_variants
        for case_id, role in case_ids
    )


def _build_post_row_local_outlier_micro_family_row(
    *,
    matrix_rows: tuple[StabilityLabMatrixRow, ...],
    stabilization_variant: str,
    case_id: str,
    role: str,
) -> PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow:
    row = _required_matrix_row(
        matrix_rows=matrix_rows,
        stabilization_variant=stabilization_variant,
        case_id=case_id,
    )
    matched_corridor_surface = (
        row.first_non_finite_talker_core_hook_tensor
        if row.first_non_finite_talker_core_hook_tensor
        in ROW_LOCAL_MICRO_FAMILY_TARGET_CORRIDOR_SURFACES
        else None
    )
    return PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow(
        stabilization_variant=stabilization_variant,
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
        f"`{stabilization_variant}:{case_id}` for the ROW_LOCAL_MICRO_FAMILY assessment."
    )


def _classify_family(
    *,
    comparison_rows: tuple[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow, ...],
) -> tuple[str | None, str | None, str | None, str | None]:
    rows_by_variant = _rows_by_variant(comparison_rows)
    baseline_rows = rows_by_variant.get(ROW_LOCAL_MICRO_FAMILY_BASELINE_VARIANT)
    if baseline_rows is None or len(baseline_rows) != 3:
        return (
            None,
            None,
            None,
            "Qwen stability lab ROW_LOCAL_MICRO_FAMILY could not resolve the "
            "full baseline case set.",
        )
    baseline_is_clean, baseline_reason = _baseline_reproduced(baseline_rows)
    if not baseline_is_clean:
        return None, None, None, baseline_reason

    converged_variants: list[str] = []
    regressed_variants: list[str] = []
    upstream_variants: list[str] = []
    for variant in ROW_LOCAL_MICRO_FAMILY_CANDIDATE_VARIANTS:
        candidate_rows = rows_by_variant.get(variant)
        if candidate_rows is None or len(candidate_rows) != 3:
            return (
                None,
                None,
                None,
                "Qwen stability lab ROW_LOCAL_MICRO_FAMILY could not resolve "
                f"the full case set for `{variant}`.",
            )
        candidate_result = _classify_candidate_rows(candidate_rows)
        if candidate_result == _CONVERGED_DOWNSTREAM:
            converged_variants.append(variant)
            continue
        if candidate_result == _UPSTREAM_PERSISTENT:
            upstream_variants.append(variant)
            continue
        if candidate_result == _NON_LOCAL_REGRESSION:
            regressed_variants.append(variant)
            continue
        return None, None, None, candidate_result

    if converged_variants:
        return _CONVERGED_DOWNSTREAM, converged_variants[0], _DOWNSTREAM_SURFACE, None
    if regressed_variants:
        return _NON_LOCAL_REGRESSION, regressed_variants[0], None, None
    if len(upstream_variants) == len(ROW_LOCAL_MICRO_FAMILY_CANDIDATE_VARIANTS):
        return _UPSTREAM_PERSISTENT, None, _UPSTREAM_SURFACE, None
    return (
        None,
        None,
        None,
        "Qwen stability lab ROW_LOCAL_MICRO_FAMILY did not resolve to one family classification.",
    )


def _rows_by_variant(
    comparison_rows: tuple[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow, ...],
) -> dict[str, tuple[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow, ...]]:
    rows_by_variant: dict[str, list[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow]] = {}
    for row in comparison_rows:
        rows_by_variant.setdefault(row.stabilization_variant, []).append(row)
    return {variant: tuple(rows) for variant, rows in rows_by_variant.items()}


def _baseline_reproduced(
    rows: tuple[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow, ...],
) -> tuple[bool, str | None]:
    pair_row, first_row, second_row = rows
    if any(not row.case_has_non_finite for row in rows):
        return False, "One or more required ROW_LOCAL_MICRO_FAMILY baseline cases stayed finite."
    if any(row.matched_corridor_surface is None for row in rows):
        return (
            False,
            "One or more required ROW_LOCAL_MICRO_FAMILY baseline cases failed "
            "outside the committed corridor.",
        )
    if pair_row.matched_corridor_surface != _DOWNSTREAM_SURFACE:
        return (
            False,
            "The ROW_LOCAL_MICRO_FAMILY baseline no longer reproduces the pair downstream seam.",
        )
    if first_row.matched_corridor_surface != _DOWNSTREAM_SURFACE:
        return (
            False,
            "The ROW_LOCAL_MICRO_FAMILY baseline no longer reproduces the line-13 downstream seam.",
        )
    if second_row.matched_corridor_surface != _UPSTREAM_SURFACE:
        return (
            False,
            "The ROW_LOCAL_MICRO_FAMILY baseline no longer reproduces the line-4 upstream seam.",
        )
    return True, None


def _classify_candidate_rows(
    rows: tuple[PostROW_LOCAL_OUTLIERRowLocalMicroFamilyComparisonRow, ...],
) -> str:
    pair_row, first_row, second_row = rows
    if any(not row.case_has_non_finite for row in rows):
        return (
            "One or more required ROW_LOCAL_MICRO_FAMILY cases stayed finite "
            "under the fp32 output-cap family."
        )
    if any(row.matched_corridor_surface is None for row in rows):
        return _NON_LOCAL_REGRESSION
    if pair_row.matched_corridor_surface != _DOWNSTREAM_SURFACE:
        return _NON_LOCAL_REGRESSION
    if first_row.matched_corridor_surface != _DOWNSTREAM_SURFACE:
        return _NON_LOCAL_REGRESSION
    if second_row.matched_corridor_surface == _DOWNSTREAM_SURFACE:
        return _CONVERGED_DOWNSTREAM
    if second_row.matched_corridor_surface == _UPSTREAM_SURFACE:
        return _UPSTREAM_PERSISTENT
    return _NON_LOCAL_REGRESSION


def _next_followup_rule(
    *,
    classification: str | None,
    winning_variant: str | None,
    dominant_surface: str | None,
) -> str:
    if classification == _UPSTREAM_PERSISTENT and dominant_surface is not None:
        return (
            "Open one diagnosis-only split of the INPUT_LAYERNORM_INTERNAL output arithmetic at "
            f"`{dominant_surface}`, specifically weight application versus final cast-back."
        )
    if (
        classification == _CONVERGED_DOWNSTREAM
        and winning_variant is not None
        and dominant_surface is not None
    ):
        return (
            "Open one diagnosis-only downstream convergence task for "
            f"`{winning_variant}` at `{dominant_surface}` before any promotion discussion."
        )
    if classification == _NON_LOCAL_REGRESSION:
        return (
            "Close ROW_LOCAL_MICRO_FAMILY as negative mechanism evidence and "
            "keep Qwen stability lab in mechanism."
        )
    return (
        "The next Qwen stability lab task remains blocked until the "
        "ROW_LOCAL_MICRO_FAMILY family resolves cleanly."
    )
