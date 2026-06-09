"""Promotion-gate evaluation for the Qwen stability lab talker-core stability lab.

Purpose:
    Turn one compact Qwen stability lab matrix result into a strict promotion decision
    so the repo can distinguish fast exploration from the single next governed
    Hemma proof without building another execution harness.

Relationships:
    - Used by `qwen_stability_lab.py` for the public `gate` command.
    - Consumes `results.json` emitted by `qwen_stability_lab_runner.py`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab_contracts import (
    PromotionGateCaseAssessment,
    QwenPromotionGateReport,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso

DEFAULT_BASELINE_VARIANT = "off"
DEFAULT_CANDIDATE_VARIANT = "layer16_gated_fp32"
DEFAULT_REQUIRED_HOOK_PROFILE = "talker_core_boundary"
DEFAULT_REQUIRED_TEXT_EMBEDDING_MASK_POLICY = "text_span_only"
_REQUIRED_CASE_ORDER = (
    "pair-main-loss",
    "pair-sub-talker-loss",
    "pair-combined-loss",
)
_EXPECTED_TALKER_CORE_HOOK_BY_CASE = {
    "pair-main-loss": "talker_core.layer_16.mlp.gated_product",
    "pair-sub-talker-loss": "talker_core.layer_15.output",
    "pair-combined-loss": "talker_core.layer_16.mlp.gated_product",
}
_EXPECTED_GRADIENT_RCA_SURFACE = "input_text_embedding.grad"
_EXPECTED_PARAMETER_SURFACE = "text_embedding.weight.grad"


def evaluate_promotion_gate(
    *,
    results_payload: dict[str, object],
    results_path: Path,
    baseline_variant: str,
    candidate_variant: str,
) -> QwenPromotionGateReport:
    """Evaluate whether one Qwen stability lab candidate has earned governed-proof promotion."""
    actual_hook_profile = _required_str(results_payload, "hook_profile")
    actual_text_embedding_mask_policy = _required_str(
        results_payload,
        "text_embedding_mask_policy",
    )
    rows_by_variant_case = _rows_by_variant_case(results_payload)
    assessments = tuple(
        _assess_case(
            case_id=case_id,
            baseline_row=_required_matrix_row(rows_by_variant_case, baseline_variant, case_id),
            candidate_row=_required_matrix_row(rows_by_variant_case, candidate_variant, case_id),
        )
        for case_id in _REQUIRED_CASE_ORDER
    )
    exact_family_reproduced_by_baseline = all(
        assessment.baseline_exact_family_match for assessment in assessments
    )
    candidate_exact_surfaces_finite = all(
        assessment.candidate_exact_surfaces_finite for assessment in assessments
    )
    promotion_passed = (
        actual_hook_profile == DEFAULT_REQUIRED_HOOK_PROFILE
        and actual_text_embedding_mask_policy == DEFAULT_REQUIRED_TEXT_EMBEDDING_MASK_POLICY
        and exact_family_reproduced_by_baseline
        and candidate_exact_surfaces_finite
    )
    return QwenPromotionGateReport(
        generated_at=utc_now_iso(),
        results_path=results_path.as_posix(),
        required_hook_profile=DEFAULT_REQUIRED_HOOK_PROFILE,
        actual_hook_profile=actual_hook_profile,
        required_text_embedding_mask_policy=DEFAULT_REQUIRED_TEXT_EMBEDDING_MASK_POLICY,
        actual_text_embedding_mask_policy=actual_text_embedding_mask_policy,
        baseline_variant=baseline_variant,
        candidate_variant=candidate_variant,
        required_case_ids=_REQUIRED_CASE_ORDER,
        exact_family_reproduced_by_baseline=exact_family_reproduced_by_baseline,
        candidate_exact_surfaces_finite=candidate_exact_surfaces_finite,
        promotion_passed=promotion_passed,
        case_assessments=assessments,
    )


def gate_results_path(output_root: Path) -> Path:
    """Return the canonical JSON artifact path for one promotion-gate decision."""
    return output_root / "gate.json"


def gate_markdown_path(output_root: Path) -> Path:
    """Return the canonical markdown artifact path for one promotion-gate decision."""
    return output_root / "gate.md"


def persist_promotion_gate(output_root: Path, report: QwenPromotionGateReport) -> tuple[Path, Path]:
    """Persist the compact Qwen stability lab promotion-gate artifacts under one output root."""
    json_path = gate_results_path(output_root)
    markdown_path = gate_markdown_path(output_root)
    _write_json(json_path, asdict(report))
    _write_markdown(markdown_path, build_promotion_gate_markdown(report))
    return json_path, markdown_path


def load_results_payload(results_path: Path) -> dict[str, object]:
    """Load one previously emitted Qwen stability lab matrix payload from disk."""
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Qwen stability lab results payload was not a JSON object.")
    return payload


def build_promotion_gate_markdown(report: QwenPromotionGateReport) -> str:
    """Render one concise markdown summary for the Qwen stability lab promotion gate."""
    lines = [
        "# Qwen stability lab Promotion Gate",
        "",
        f"- Generated at: `{report.generated_at}`",
        f"- Results path: `{report.results_path}`",
        f"- Baseline variant: `{report.baseline_variant}`",
        f"- Candidate variant: `{report.candidate_variant}`",
        f"- Hook profile match: `{report.actual_hook_profile == report.required_hook_profile}`",
        (f"- Text embedding mask policy match: `{_mask_policy_matches(report)}`"),
        f"- Baseline exact family reproduced: `{report.exact_family_reproduced_by_baseline}`",
        f"- Candidate exact surfaces finite: `{report.candidate_exact_surfaces_finite}`",
        f"- Promotion passed: `{report.promotion_passed}`",
        "",
        "## Case Assessments",
        "",
    ]
    for assessment in report.case_assessments:
        lines.append(
            "- "
            f"`{assessment.case_id}` expected=`{assessment.expected_talker_core_hook}` "
            f"baseline_match=`{assessment.baseline_exact_family_match}` "
            f"candidate_finite=`{assessment.candidate_exact_surfaces_finite}` "
            f"passes=`{assessment.passes}`"
        )
    return "\n".join(lines)


def _assess_case(
    *,
    case_id: str,
    baseline_row: dict[str, object],
    candidate_row: dict[str, object],
) -> PromotionGateCaseAssessment:
    expected_talker_core_hook = _EXPECTED_TALKER_CORE_HOOK_BY_CASE[case_id]
    baseline_case_has_non_finite = _required_bool(baseline_row, "case_has_non_finite")
    baseline_exact_family_match = (
        baseline_case_has_non_finite
        and _optional_str(baseline_row, "first_non_finite_talker_core_hook_tensor")
        == expected_talker_core_hook
        and _optional_str(baseline_row, "gradient_rca_first_non_finite_surface")
        == _EXPECTED_GRADIENT_RCA_SURFACE
        and _optional_str(baseline_row, "parameter_first_non_finite_surface")
        == _EXPECTED_PARAMETER_SURFACE
    )
    candidate_case_has_non_finite = _required_bool(candidate_row, "case_has_non_finite")
    candidate_exact_surfaces_finite = (
        not candidate_case_has_non_finite
        and _optional_str(candidate_row, "first_non_finite_hook_tensor") is None
        and _optional_str(candidate_row, "first_non_finite_talker_core_hook_tensor") is None
        and _optional_str(candidate_row, "gradient_rca_first_non_finite_surface") is None
        and _optional_str(candidate_row, "parameter_first_non_finite_surface") is None
    )
    return PromotionGateCaseAssessment(
        case_id=case_id,
        loss_kind=_required_str(candidate_row, "loss_kind"),
        expected_talker_core_hook=expected_talker_core_hook,
        baseline_case_has_non_finite=baseline_case_has_non_finite,
        baseline_exact_family_match=baseline_exact_family_match,
        candidate_case_has_non_finite=candidate_case_has_non_finite,
        candidate_exact_surfaces_finite=candidate_exact_surfaces_finite,
        passes=baseline_exact_family_match and candidate_exact_surfaces_finite,
    )


def _rows_by_variant_case(
    results_payload: dict[str, object],
) -> dict[tuple[str, str], dict[str, object]]:
    rows_value = results_payload.get("matrix_rows")
    if not isinstance(rows_value, list):
        raise SystemExit("Qwen stability lab results payload was missing `matrix_rows`.")
    rows_by_variant_case: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows_value:
        if not isinstance(row, dict):
            raise SystemExit("Qwen stability lab matrix row payload was malformed.")
        rows_by_variant_case[
            (
                _required_str(row, "stabilization_variant"),
                _required_str(row, "case_id"),
            )
        ] = row
    return rows_by_variant_case


def _required_matrix_row(
    rows_by_variant_case: dict[tuple[str, str], dict[str, object]],
    variant: str,
    case_id: str,
) -> dict[str, object]:
    try:
        return rows_by_variant_case[(variant, case_id)]
    except KeyError as exc:
        raise SystemExit(
            f"Qwen stability lab could not resolve matrix row `{variant}:{case_id}`."
        ) from exc


def _write_json(path: Path, payload: object) -> None:
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Qwen stability lab promotion gate payload missing string `{key}`.")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _required_bool(payload: dict[str, object], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Qwen stability lab promotion gate payload missing boolean `{key}`.")
    return value


def _mask_policy_matches(report: QwenPromotionGateReport) -> bool:
    return report.actual_text_embedding_mask_policy == report.required_text_embedding_mask_policy
