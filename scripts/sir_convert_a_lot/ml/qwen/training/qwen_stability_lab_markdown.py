"""Markdown rendering for the Qwen stability lab.

Purpose:
    Keep the compact operator-facing markdown summary separate from the Story
    31 runner so orchestration, assessment, and report rendering do not grow
    into one mixed-responsibility module.

Relationships:
    - Imported by `qwen_stability_lab_runner.py` for report persistence.
    - Reuses `qwen_stability_lab_contracts.py` as the single typed report
      contract for the sub-boundary/input-layernorm family, input-layernorm internal, sub-talker
      disagreement, row-local outlier, row-local micro-family, downstream convergence, layer-15
      split, residual/output,
      output-return, multiply-site confirmation, and fp32-scaled output
      sections.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    QwenStabilityLabReport,
)


def build_report_markdown(report: QwenStabilityLabReport) -> str:
    """Render one concise markdown summary for the Qwen stability lab matrix run."""
    lines = [
        "# Qwen stability lab Stability Lab",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Image: `{report.image}`",
        f"- Image id: `{report.image_id}`",
        f"- Build performed: `{report.build_performed}`",
        f"- Model id: `{report.model_id}`",
        f"- Source bundle root: `{report.source_bundle_root}`",
        f"- Manifest family: `{report.manifest_family}`",
        f"- Source lines: `{report.source_line_numbers}`",
        f"- Text embedding mask policy: `{report.text_embedding_mask_policy}`",
        f"- Hook profile: `{report.hook_profile}`",
        f"- Stabilization variants: `{report.stabilization_variants}`",
        "",
        "## Matrix Rows",
        "",
        (
            "| Variant | Case | Loss | Non-finite | First Hook | Talker Hook | "
            "Gradient RCA | Parameter RCA | Anomaly |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.matrix_rows:
        lines.append(
            "| "
            f"{row.stabilization_variant} | "
            f"{row.case_id} | "
            f"{row.loss_kind} | "
            f"{row.case_has_non_finite} | "
            f"{row.first_non_finite_hook_tensor or '-'} | "
            f"{row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{row.gradient_rca_first_non_finite_surface or '-'} | "
            f"{row.parameter_first_non_finite_surface or '-'} | "
            f"{row.anomaly_operator or '-'} |"
        )
    _append_sub_boundary_sub_boundary_section(lines, report)
    _append_input_layernorm_internal_input_layernorm_internal_section(lines, report)
    _append_sub_talker_disagreement_sub_talker_disagreement_section(lines, report)
    _append_row_local_outlier_row_local_outlier_section(lines, report)
    _append_row_local_micro_family_post_row_local_outlier_micro_family_section(lines, report)
    _append_downstream_convergence_downstream_convergence_section(lines, report)
    _append_layer15_output_split_layer15_output_split_section(lines, report)
    _append_layer15_residual_output_layer15_residual_output_section(lines, report)
    _append_layer15_output_return_layer15_output_return_section(lines, report)
    _append_layer15_output_multiply_layer15_output_multiply_confirmation_section(lines, report)
    _append_fp32_scaled_layer15_output_post_layer15_output_multiply_fp32_scaled_output_section(
        lines, report
    )
    return "\n".join(lines)


def _append_sub_boundary_sub_boundary_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.sub_boundary_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## SUB_BOUNDARY Sub-Boundary Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Earliest sub-boundary: `{assessment.earliest_sub_boundary or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next micro-family rule: `{assessment.next_micro_family_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Sub-boundary |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_sub_boundary or '-'} |"
        )


def _append_input_layernorm_internal_input_layernorm_internal_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.input_layernorm_internal_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## INPUT_LAYERNORM_INTERNAL Input-Layernorm Internal Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Earliest internal surface: `{assessment.earliest_internal_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next micro-family rule: `{assessment.next_micro_family_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Internal Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_internal_surface or '-'} |"
        )


def _append_sub_talker_disagreement_sub_talker_disagreement_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.sub_talker_disagreement_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## SUB_TALKER_DISAGREEMENT Post-INPUT_LAYERNORM_OUTPUT Disagreement Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Earliest corridor surface: `{assessment.earliest_corridor_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next micro-family rule: `{assessment.next_micro_family_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_row_local_outlier_row_local_outlier_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.row_local_outlier_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## ROW_LOCAL_OUTLIER Post-SUB_TALKER_DISAGREEMENT Row-Local Outlier Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Outlier classification: `{assessment.outlier_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next micro-family rule: `{assessment.next_micro_family_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Outlier Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_outlier_surface or '-'} |"
        )


def _append_row_local_micro_family_post_row_local_outlier_micro_family_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.row_local_micro_family_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## ROW_LOCAL_MICRO_FAMILY Post-ROW_LOCAL_OUTLIER Row-Local Micro-Family Assessment",
            "",
            f"- Baseline variant: `{assessment.baseline_variant}`",
            f"- Candidate variants: `{assessment.candidate_variants}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Family classification: `{assessment.family_classification or '-'}`",
            f"- Winning candidate variant: `{assessment.winning_candidate_variant or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Variant | Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.stabilization_variant} | "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_downstream_convergence_downstream_convergence_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.downstream_convergence_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## DOWNSTREAM_CONVERGENCE Post-ROW_LOCAL_MICRO_FAMILY "
            "Downstream Convergence Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Convergence classification: `{assessment.convergence_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_layer15_output_split_layer15_output_split_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.layer15_output_split_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## LAYER15_OUTPUT_SPLIT Post-DOWNSTREAM_CONVERGENCE Layer-15 Output Split Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Convergence classification: `{assessment.convergence_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_layer15_residual_output_layer15_residual_output_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.layer15_residual_output_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## LAYER15_RESIDUAL_OUTPUT Post-LAYER15_OUTPUT_SPLIT "
            "Layer-15 Residual/Output Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Convergence classification: `{assessment.convergence_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_layer15_output_return_layer15_output_return_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.layer15_output_return_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## LAYER15_OUTPUT_RETURN Post-LAYER15_RESIDUAL_OUTPUT "
            "Layer-15 Output Return Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Convergence classification: `{assessment.convergence_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_layer15_output_multiply_layer15_output_multiply_confirmation_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.layer15_output_multiply_confirmation_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## LAYER15_OUTPUT_MULTIPLY Post-LAYER15_OUTPUT_RETURN "
            "Layer-15 Output Multiply Confirmation",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Confirmation classification: `{assessment.confirmation_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )


def _append_fp32_scaled_layer15_output_post_layer15_output_multiply_fp32_scaled_output_section(
    lines: list[str],
    report: QwenStabilityLabReport,
) -> None:
    assessment = report.fp32_scaled_layer15_output_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## FP32_SCALED_LAYER15_OUTPUT Post-LAYER15_OUTPUT_MULTIPLY "
            "FP32-Scaled Layer-15 Output Assessment",
            "",
            f"- Assessed variant: `{assessment.stabilization_variant}`",
            f"- Target loss kind: `{assessment.target_loss_kind}`",
            f"- Convergence classification: `{assessment.convergence_classification or '-'}`",
            f"- Dominant surface: `{assessment.dominant_surface or '-'}`",
            f"- Evidence ambiguous: `{assessment.evidence_is_ambiguous}`",
            f"- Ambiguity reason: `{assessment.ambiguity_reason or '-'}`",
            f"- Next task rule: `{assessment.next_task_rule}`",
            "",
            "| Case | Role | Non-finite | Talker Hook | Matched Corridor Surface |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for assessment_row in assessment.comparison_rows:
        lines.append(
            "| "
            f"{assessment_row.case_id} | "
            f"{assessment_row.role} | "
            f"{assessment_row.case_has_non_finite} | "
            f"{assessment_row.first_non_finite_talker_core_hook_tensor or '-'} | "
            f"{assessment_row.matched_corridor_surface or '-'} |"
        )
