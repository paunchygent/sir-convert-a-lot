"""Markdown rendering for the Story 31 stability lab.

Purpose:
    Keep the compact operator-facing markdown summary separate from the Story
    31 runner so orchestration, assessment, and report rendering do not grow
    into one mixed-responsibility module.

Relationships:
    - Imported by `story31_stability_lab_runner.py` for report persistence.
    - Reuses `story31_stability_lab_contracts.py` as the single typed report
      contract for both T229/T230 and T233 sections.
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
