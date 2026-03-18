"""Markdown rendering for the Story 31 stability lab.

Purpose:
    Keep the compact operator-facing markdown summary separate from the Story
    31 runner so orchestration, assessment, and report rendering do not grow
    into one mixed-responsibility module.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for report persistence.
    - Reuses `story31_stability_lab_contracts.py` as the single typed report
      contract for the T229/T230, T233, T235, T236, T237, T240, and T241
      sections.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    Story31StabilityLabReport,
)


def build_report_markdown(report: Story31StabilityLabReport) -> str:
    """Render one concise markdown summary for the Story 31 matrix run."""
    lines = [
        "# Story 31 Stability Lab",
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
    _append_t229_sub_boundary_section(lines, report)
    _append_t233_input_layernorm_internal_section(lines, report)
    _append_t235_post_t234_disagreement_section(lines, report)
    _append_t236_post_t235_row_local_outlier_section(lines, report)
    _append_t237_post_t236_micro_family_section(lines, report)
    _append_t240_post_t237_downstream_convergence_section(lines, report)
    _append_t241_post_t240_layer15_output_split_section(lines, report)
    return "\n".join(lines)


def _append_t229_sub_boundary_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.sub_boundary_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T229 Sub-Boundary Assessment",
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


def _append_t233_input_layernorm_internal_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.input_layernorm_internal_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T233 Input-Layernorm Internal Assessment",
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


def _append_t235_post_t234_disagreement_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.post_t234_disagreement_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T235 Post-T234 Disagreement Assessment",
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


def _append_t236_post_t235_row_local_outlier_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.post_t235_row_local_outlier_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T236 Post-T235 Row-Local Outlier Assessment",
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


def _append_t237_post_t236_micro_family_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.post_t236_row_local_micro_family_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T237 Post-T236 Row-Local Micro-Family Assessment",
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


def _append_t240_post_t237_downstream_convergence_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.post_t237_downstream_convergence_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T240 Post-T237 Downstream Convergence Assessment",
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


def _append_t241_post_t240_layer15_output_split_section(
    lines: list[str],
    report: Story31StabilityLabReport,
) -> None:
    assessment = report.post_t240_layer15_output_split_assessment
    if assessment is None:
        return
    lines.extend(
        [
            "",
            "## T241 Post-T240 Layer-15 Output Split Assessment",
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
