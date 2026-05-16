"""Task 309 advisory report adjudication against teacher goldens.

Purpose:
    Build an item-centered diagnostic packet for Task 309 live validation that
    shows what the model saw, what the teacher golden says, what the model
    suggested, and why the row is blocked, correct, manual, or unscored.

Relationships:
    - Consumes the Task 309 fixture manifests and per-file advisory reports.
    - Reconstructs provider requests through the same Task 312 candidate
      planner used by production advisory execution.
    - Produces validation-only evidence for failure-path analysis; it still
      avoids raw provider responses.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task309_provider_run_metadata import (
    load_task309_provider_run_metadata_from_report,
    structured_profile_from_task309_provider_run_metadata,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    answer_key_candidate_planner_for_profile,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    write_task309_json,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import StructuredLLMProviderProfile
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_structured_llm_payload,
)

TASK309_ADVISORY_EVALUATION_SCHEMA_VERSION = "task309_advisory_adjudication_v2"

# Gap-fill synonym groups for golden evaluation.
# Each frozenset contains terms that are considered equivalent for answer-key
# comparison purposes.  The evaluator canonicalises both expected and actual
# values through these groups before comparing.  Terms that are merely
# *related* (e.g. "kärnan" for "cellkärna") but not exact synonyms must NOT
# be included.
_GAP_SYNONYM_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"cellkärna", "cellkärnan", "nukleus"}),
    frozenset({"baspar", "basparet"}),
    frozenset({"nervcell", "neuron", "neuronen"}),
    frozenset({"artär", "artären", "artärer"}),
    frozenset({"ven", "vener", "venen", "venerna"}),
    frozenset({"koldioxid", "co2"}),
    frozenset({"syre", "o2"}),
    frozenset({"växtcell", "växtcellen"}),
    frozenset({"djurcell", "djurcellen"}),
    frozenset({"ribosom", "ribosomen"}),
    frozenset({"mitokondrie", "mitokondrier"}),
)


@dataclass(frozen=True)
class Task309EvaluationFinding:
    """One item-centered adjudication finding."""

    category: str
    source_filename: str
    item_id: str
    item_type: str
    sequence: int
    decision_state: str
    backend_failure_code: str | None
    manifest_eligible: bool | None
    manifest_skip_reason: str | None
    detail: str
    teacher_answer: str | None
    model_answer: str | None
    teacher_answer_json: str | None
    model_output_json: str | None
    item_context_json: str | None
    system_prompt: str | None
    user_payload_json: str | None
    provider_payload_json: str | None
    output_mode: str | None
    output_contract_json: str | None
    provider_response_status_code: int | None
    raw_provider_response_text: str | None
    provider_response_payload_json: str | None
    decoded_provider_content_json: str | None

    def to_payload(self) -> dict[str, object]:
        """Return JSON-safe finding payload."""

        return {
            "category": self.category,
            "source_filename": self.source_filename,
            "item_id": self.item_id,
            "item_type": self.item_type,
            "sequence": self.sequence,
            "decision_state": self.decision_state,
            "backend_failure_code": self.backend_failure_code,
            "manifest_eligible": self.manifest_eligible,
            "manifest_skip_reason": self.manifest_skip_reason,
            "detail": self.detail,
            "teacher_answer": self.teacher_answer,
            "model_answer": self.model_answer,
            "teacher_answer_json": self.teacher_answer_json,
            "model_output_json": self.model_output_json,
            "item_context_json": self.item_context_json,
            "system_prompt": self.system_prompt,
            "user_payload_json": self.user_payload_json,
            "provider_payload_json": self.provider_payload_json,
            "output_mode": self.output_mode,
            "output_contract_json": self.output_contract_json,
            "provider_response_status_code": self.provider_response_status_code,
            "raw_provider_response_text": self.raw_provider_response_text,
            "provider_response_payload_json": self.provider_response_payload_json,
            "decoded_provider_content_json": self.decoded_provider_content_json,
        }


@dataclass(frozen=True)
class Task309AdvisoryEvaluationReport:
    """Redacted-but-useful advisory evaluation summary."""

    schema_version: str
    expected_answer_manifest_path: str
    validation_manifest_path: str
    reports_root: str
    provider_run_metadata_json: str
    model_settings_json: str
    report_count: int
    golden_count: int
    report_item_count: int
    suggested_count: int
    correct_suggestion_count: int
    wrong_but_valid_count: int
    manual_follow_up_count: int
    unscored_manual_follow_up_count: int
    skipped_count: int
    unknown_id_count: int
    duplicate_id_count: int
    missing_golden_count: int
    partial_gap_answer_count: int
    malformed_success_count: int
    finding_count: int
    finding_category_counts: tuple[dict[str, object], ...]
    findings: tuple[Task309EvaluationFinding, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload."""

        return {
            "schema_version": self.schema_version,
            "expected_answer_manifest_path": self.expected_answer_manifest_path,
            "validation_manifest_path": self.validation_manifest_path,
            "reports_root": self.reports_root,
            "provider_run_metadata_json": self.provider_run_metadata_json,
            "model_settings_json": self.model_settings_json,
            "report_count": self.report_count,
            "golden_count": self.golden_count,
            "report_item_count": self.report_item_count,
            "suggested_count": self.suggested_count,
            "correct_suggestion_count": self.correct_suggestion_count,
            "wrong_but_valid_count": self.wrong_but_valid_count,
            "manual_follow_up_count": self.manual_follow_up_count,
            "unscored_manual_follow_up_count": self.unscored_manual_follow_up_count,
            "skipped_count": self.skipped_count,
            "unknown_id_count": self.unknown_id_count,
            "duplicate_id_count": self.duplicate_id_count,
            "missing_golden_count": self.missing_golden_count,
            "partial_gap_answer_count": self.partial_gap_answer_count,
            "malformed_success_count": self.malformed_success_count,
            "finding_count": self.finding_count,
            "finding_category_counts": self.finding_category_counts,
            "findings": tuple(finding.to_payload() for finding in self.findings),
        }


@dataclass(frozen=True)
class _Comparison:
    category: str
    detail: str


def evaluate_task309_advisory_reports(
    *,
    expected_answer_manifest_path: Path,
    reports_root: Path,
    run_report_path: Path | None = None,
) -> Task309AdvisoryEvaluationReport:
    """Evaluate retained advisory reports and build an adjudication packet."""

    validation_manifest_path = (
        expected_answer_manifest_path.parent / "validation-corpus-manifest.json"
    )
    goldens = _load_goldens(expected_answer_manifest_path)
    manifest_items = _load_manifest_items(validation_manifest_path)
    item_contexts = _load_item_contexts(expected_answer_manifest_path.parent)
    provider_run_metadata = load_task309_provider_run_metadata_from_report(
        run_report_path=run_report_path
    )
    diagnostic_profile = structured_profile_from_task309_provider_run_metadata(
        provider_run_metadata
    )
    report_paths = tuple(sorted(reports_root.glob("*.answer-key-completion-report.json")))
    seen_report_keys: set[tuple[str, str]] = set()
    findings: list[Task309EvaluationFinding] = []
    report_item_count = 0
    suggested_count = 0
    correct_suggestion_count = 0
    wrong_but_valid_count = 0
    manual_follow_up_count = 0
    unscored_manual_follow_up_count = 0
    skipped_count = 0
    unknown_id_count = 0
    duplicate_id_count = 0
    missing_golden_count = 0
    partial_gap_answer_count = 0
    malformed_success_count = 0

    for report_path in report_paths:
        source_filename = _source_filename_from_report_path(report_path)
        report = _load_object(report_path)
        items = _object_sequence(report.get("items"), label=f"{report_path}:items")
        for item in items:
            report_item_count += 1
            item_id = _required_str(item, "item_id")
            item_type = _required_str(item, "item_type")
            sequence = _required_int(item, "sequence")
            decision_state = _required_str(item, "decision_state")
            backend_failure_code = _optional_str(item.get("backend_failure_code"))
            key = (source_filename, item_id)
            manifest_item = manifest_items.get(key)
            manifest_eligible = _optional_bool(manifest_item, "eligible")
            manifest_skip_reason = _optional_mapping_str(manifest_item, "skip_reason")
            context = item_contexts.get(key)

            if key in seen_report_keys:
                duplicate_id_count += 1
                findings.append(
                    _finding(
                        category="duplicate_id",
                        source_filename=source_filename,
                        item_id=item_id,
                        item_type=item_type,
                        sequence=sequence,
                        decision_state=decision_state,
                        backend_failure_code=backend_failure_code,
                        manifest_item=manifest_item,
                        context=context,
                        report_item=item,
                        diagnostic_profile=diagnostic_profile,
                        teacher_answer=None,
                        model_answer=None,
                        detail="Duplicate report item id.",
                    )
                )
            seen_report_keys.add(key)

            if decision_state == "skipped":
                skipped_count += 1
                continue

            golden = goldens.get(key)
            if decision_state == "manual_follow_up_required":
                manual_follow_up_count += 1
                category = "manual_follow_up"
                if golden is None and manifest_eligible is False:
                    unscored_manual_follow_up_count += 1
                    category = "unscored_manual_follow_up"
                elif golden is None:
                    missing_golden_count += 1
                    category = "missing_golden"
                findings.append(
                    _finding(
                        category=category,
                        source_filename=source_filename,
                        item_id=item_id,
                        item_type=item_type,
                        sequence=sequence,
                        decision_state=decision_state,
                        backend_failure_code=backend_failure_code,
                        manifest_item=manifest_item,
                        context=context,
                        report_item=item,
                        diagnostic_profile=diagnostic_profile,
                        teacher_answer=_answer_label_for_golden(golden),
                        model_answer=None,
                        detail=_manual_detail(
                            backend_failure_code=backend_failure_code,
                            manifest_eligible=manifest_eligible,
                            manifest_skip_reason=manifest_skip_reason,
                        ),
                    )
                )
                continue

            if golden is None:
                missing_golden_count += 1
                findings.append(
                    _finding(
                        category="missing_golden",
                        source_filename=source_filename,
                        item_id=item_id,
                        item_type=item_type,
                        sequence=sequence,
                        decision_state=decision_state,
                        backend_failure_code=backend_failure_code,
                        manifest_item=manifest_item,
                        context=context,
                        report_item=item,
                        diagnostic_profile=diagnostic_profile,
                        teacher_answer=None,
                        model_answer=_answer_label(_optional_object(item, "answer_payload")),
                        model_output_json=_optional_payload_json(item, "answer_payload"),
                        detail="Suggested item has no teacher golden.",
                    )
                )
                continue

            if decision_state != "suggested":
                unknown_id_count += 1
                findings.append(
                    _finding(
                        category="unknown_decision_state",
                        source_filename=source_filename,
                        item_id=item_id,
                        item_type=item_type,
                        sequence=sequence,
                        decision_state=decision_state,
                        backend_failure_code=backend_failure_code,
                        manifest_item=manifest_item,
                        context=context,
                        report_item=item,
                        diagnostic_profile=diagnostic_profile,
                        teacher_answer=_answer_label_for_golden(golden),
                        model_answer=_answer_label(_optional_object(item, "answer_payload")),
                        teacher_answer_json=_payload_json(golden, "expected_answer_payload"),
                        model_output_json=_optional_payload_json(item, "answer_payload"),
                        detail=f"Unexpected decision_state={decision_state}.",
                    )
                )
                continue

            suggested_count += 1
            answer_payload = _optional_object(item, "answer_payload")
            if answer_payload is None:
                malformed_success_count += 1
                findings.append(
                    _finding(
                        category="malformed_success",
                        source_filename=source_filename,
                        item_id=item_id,
                        item_type=item_type,
                        sequence=sequence,
                        decision_state=decision_state,
                        backend_failure_code=backend_failure_code,
                        manifest_item=manifest_item,
                        context=context,
                        report_item=item,
                        diagnostic_profile=diagnostic_profile,
                        teacher_answer=_answer_label_for_golden(golden),
                        model_answer=None,
                        teacher_answer_json=_payload_json(golden, "expected_answer_payload"),
                        detail="Suggested item lacks answer_payload object.",
                    )
                )
                continue

            expected_payload = _required_object(golden, "expected_answer_payload")
            comparison = _compare_payloads(
                expected_payload=expected_payload, actual_payload=answer_payload
            )
            if comparison.category == "correct":
                correct_suggestion_count += 1
                findings.append(
                    _finding(
                        category="correct_suggestion",
                        source_filename=source_filename,
                        item_id=item_id,
                        item_type=item_type,
                        sequence=sequence,
                        decision_state=decision_state,
                        backend_failure_code=backend_failure_code,
                        manifest_item=manifest_item,
                        context=context,
                        report_item=item,
                        diagnostic_profile=diagnostic_profile,
                        teacher_answer=_answer_label(expected_payload),
                        model_answer=_answer_label(answer_payload),
                        teacher_answer_json=_canonical_json(expected_payload),
                        model_output_json=_canonical_json(answer_payload),
                        detail=comparison.detail,
                    )
                )
                continue
            if comparison.category == "partial_gap_answer":
                partial_gap_answer_count += 1
            wrong_but_valid_count += 1
            findings.append(
                _finding(
                    category=comparison.category,
                    source_filename=source_filename,
                    item_id=item_id,
                    item_type=item_type,
                    sequence=sequence,
                    decision_state=decision_state,
                    backend_failure_code=backend_failure_code,
                    manifest_item=manifest_item,
                    context=context,
                    report_item=item,
                    diagnostic_profile=diagnostic_profile,
                    teacher_answer=_answer_label(expected_payload),
                    model_answer=_answer_label(answer_payload),
                    teacher_answer_json=_canonical_json(expected_payload),
                    model_output_json=_canonical_json(answer_payload),
                    detail=comparison.detail,
                )
            )

    category_counts = Counter(finding.category for finding in findings)
    provider_run_metadata_json = provider_run_metadata.to_json()
    return Task309AdvisoryEvaluationReport(
        schema_version=TASK309_ADVISORY_EVALUATION_SCHEMA_VERSION,
        expected_answer_manifest_path=expected_answer_manifest_path.as_posix(),
        validation_manifest_path=validation_manifest_path.as_posix(),
        reports_root=reports_root.as_posix(),
        provider_run_metadata_json=provider_run_metadata_json,
        model_settings_json=provider_run_metadata_json,
        report_count=len(report_paths),
        golden_count=len(goldens),
        report_item_count=report_item_count,
        suggested_count=suggested_count,
        correct_suggestion_count=correct_suggestion_count,
        wrong_but_valid_count=wrong_but_valid_count,
        manual_follow_up_count=manual_follow_up_count,
        unscored_manual_follow_up_count=unscored_manual_follow_up_count,
        skipped_count=skipped_count,
        unknown_id_count=unknown_id_count,
        duplicate_id_count=duplicate_id_count,
        missing_golden_count=missing_golden_count,
        partial_gap_answer_count=partial_gap_answer_count,
        malformed_success_count=malformed_success_count,
        finding_count=len(findings),
        finding_category_counts=tuple(
            {"category": key, "count": category_counts[key]} for key in sorted(category_counts)
        ),
        findings=tuple(findings),
    )


def write_task309_advisory_evaluation(
    *,
    output_root: Path,
    report: Task309AdvisoryEvaluationReport,
) -> tuple[Path, Path]:
    """Write JSON and Markdown adjudication artifacts."""

    output_root.mkdir(parents=True, exist_ok=True)
    json_path = output_root / "advisory-golden-evaluation.json"
    markdown_path = output_root / "advisory-golden-evaluation.md"
    write_task309_json(report.to_payload(), json_path)
    markdown_path.write_text(_markdown(report).rstrip() + "\n", encoding="utf-8")
    return json_path, markdown_path


def _load_goldens(path: Path) -> dict[tuple[str, str], dict[str, object]]:
    payload = _load_object(path)
    entries = _object_sequence(payload.get("entries"), label=f"{path}:entries")
    return {
        (_required_str(entry, "source_filename"), _required_str(entry, "item_id")): entry
        for entry in entries
    }


def _load_manifest_items(path: Path) -> dict[tuple[str, str], dict[str, object]]:
    payload = _load_object(path)
    files = _object_sequence(payload.get("files"), label=f"{path}:files")
    indexed: dict[tuple[str, str], dict[str, object]] = {}
    for file_payload in files:
        filename = _required_str(file_payload, "filename")
        items = _object_sequence(file_payload.get("items"), label=f"{filename}:items")
        for item in items:
            indexed[(filename, _required_str(item, "item_id"))] = item
    return indexed


def _load_item_contexts(corpus_root: Path) -> dict[tuple[str, str], DigiExamIrItem]:
    parser = DigiExamDxeParser()
    contexts: dict[tuple[str, str], DigiExamIrItem] = {}
    for source_path in sorted(corpus_root.glob("*.dxe")):
        exam = build_digiexam_intermediate_exam(parser.parse_file(source_path))
        for item in exam.items:
            contexts[(source_path.name, item.item_id)] = item
    return contexts


def _finding(
    *,
    category: str,
    source_filename: str,
    item_id: str,
    item_type: str,
    sequence: int,
    decision_state: str,
    backend_failure_code: str | None,
    manifest_item: dict[str, object] | None,
    context: DigiExamIrItem | None,
    report_item: dict[str, object] | None,
    diagnostic_profile: StructuredLLMProviderProfile | None,
    teacher_answer: str | None,
    model_answer: str | None,
    detail: str,
    teacher_answer_json: str | None = None,
    model_output_json: str | None = None,
) -> Task309EvaluationFinding:
    exchange_payload = _provider_exchange_diagnostic(report_item)
    request_payload = _request_diagnostic(context, diagnostic_profile)
    return Task309EvaluationFinding(
        category=category,
        source_filename=source_filename,
        item_id=item_id,
        item_type=item_type,
        sequence=sequence,
        decision_state=decision_state,
        backend_failure_code=backend_failure_code,
        manifest_eligible=_optional_bool(manifest_item, "eligible"),
        manifest_skip_reason=_optional_mapping_str(manifest_item, "skip_reason"),
        detail=detail,
        teacher_answer=teacher_answer,
        model_answer=model_answer,
        teacher_answer_json=teacher_answer_json,
        model_output_json=model_output_json,
        item_context_json=_item_context_json(context),
        system_prompt=_optional_mapping_str(request_payload, "system_prompt"),
        user_payload_json=_optional_mapping_str(request_payload, "user_payload_json"),
        provider_payload_json=_first_present_str(
            _optional_mapping_str(exchange_payload, "request_payload_json"),
            _optional_mapping_str(request_payload, "provider_payload_json"),
        ),
        output_mode=_first_present_str(
            _optional_mapping_str(exchange_payload, "output_mode"),
            _optional_mapping_str(request_payload, "output_mode"),
        ),
        output_contract_json=_optional_mapping_str(request_payload, "output_contract_json"),
        provider_response_status_code=_optional_mapping_int(
            exchange_payload, "response_status_code"
        ),
        raw_provider_response_text=_optional_mapping_str(exchange_payload, "raw_response_text"),
        provider_response_payload_json=_optional_mapping_str(
            exchange_payload, "response_payload_json"
        ),
        decoded_provider_content_json=_optional_mapping_str(
            exchange_payload, "decoded_content_json"
        ),
    )


def _request_diagnostic(
    item: DigiExamIrItem | None,
    profile: StructuredLLMProviderProfile | None,
) -> dict[str, object] | None:
    if item is None or profile is None:
        return None
    plan = answer_key_candidate_planner_for_profile(profile).plan_candidate(
        job_id="task309-diagnostic",
        item=item,
        profile=profile,
    )
    if plan is None:
        return None
    output_spec = plan.request.output_spec
    contract: dict[str, object] = {
        "schema_name": output_spec.schema_name,
        "schema_version": output_spec.schema_version,
        "json_schema": output_spec.json_schema,
        "choice_values": output_spec.choice_values,
    }
    provider_payload_json = (
        _canonical_json(
            build_structured_llm_payload(
                profile=plan.provider_profile,
                request=plan.request,
            )
        )
        if plan.provider_profile is not None
        else None
    )
    return {
        "system_prompt": plan.request.system_prompt,
        "user_payload_json": plan.request.user_payload,
        "provider_payload_json": provider_payload_json,
        "output_mode": plan.provider_profile.output_mode.value
        if plan.provider_profile is not None
        else None,
        "output_contract_json": _canonical_json(contract),
    }


def _provider_exchange_diagnostic(
    report_item: dict[str, object] | None,
) -> dict[str, object] | None:
    if report_item is None:
        return None
    exchange = report_item.get("task309_provider_exchange")
    if exchange is None:
        return None
    if not isinstance(exchange, dict):
        raise ValueError("task309_provider_exchange must be an object.")
    return _json_object(exchange)


def _item_context_json(item: DigiExamIrItem | None) -> str | None:
    if item is None:
        return None
    payload: dict[str, object] = {
        "item_id": item.item_id,
        "sequence": item.sequence,
        "item_type": item.item_type.value,
        "title": item.title,
        "prompt_html": item.prompt_html or "",
        "prompt_lines": list(item.prompt_lines),
        "alternatives": [
            {"alternative_id": alternative.id, "text": alternative.title}
            for alternative in item.alternatives
        ],
        "gaps": [{"gap_id": gap.guid, "validations": list(gap.validations)} for gap in item.gaps],
        "embedded_asset_count": len(item.embedded_assets) + len(item.embedded_asset_references),
        "warning_codes": [warning.code for warning in item.warnings],
    }
    return _canonical_json(payload)


def _manual_detail(
    *,
    backend_failure_code: str | None,
    manifest_eligible: bool | None,
    manifest_skip_reason: str | None,
) -> str:
    return (
        f"Manual follow-up. backend_failure_code={backend_failure_code}; "
        f"manifest_eligible={manifest_eligible}; manifest_skip_reason={manifest_skip_reason}."
    )


def _compare_payloads(
    *,
    expected_payload: dict[str, object],
    actual_payload: dict[str, object],
) -> _Comparison:
    expected_kind = _required_str(expected_payload, "kind")
    actual_kind = _required_str(actual_payload, "kind")
    if expected_kind != actual_kind:
        return _Comparison(
            "wrong_but_valid", f"kind mismatch expected={expected_kind} actual={actual_kind}"
        )
    if expected_kind == "choice":
        expected_ids = _int_tuple(expected_payload.get("correct_alternative_ids"))
        actual_ids = _int_tuple(actual_payload.get("correct_alternative_ids"))
        if expected_ids == actual_ids:
            return _Comparison("correct", "choice IDs match.")
        return _Comparison(
            "wrong_but_valid",
            "choice ID mismatch "
            f"expected={_int_label(expected_ids)} actual={_int_label(actual_ids)}",
        )
    if expected_kind == "gap_fill":
        return _compare_gap_payloads(
            expected_payload=expected_payload, actual_payload=actual_payload
        )
    return _Comparison("wrong_but_valid", f"unsupported answer kind={expected_kind}")


def _compare_gap_payloads(
    *,
    expected_payload: dict[str, object],
    actual_payload: dict[str, object],
) -> _Comparison:
    expected_gaps = _canonical_gap_map(expected_payload.get("gap_answers"))
    actual_gaps = _canonical_gap_map(actual_payload.get("gap_answers"))
    missing_gaps = tuple(sorted(set(expected_gaps) - set(actual_gaps)))
    extra_gaps = tuple(sorted(set(actual_gaps) - set(expected_gaps)))
    if missing_gaps or extra_gaps:
        return _Comparison(
            "partial_gap_answer",
            f"gap id mismatch missing={_str_label(missing_gaps)} extra={_str_label(extra_gaps)}",
        )
    value_mismatches: list[str] = []
    for gap_id, expected_values in expected_gaps.items():
        actual_values = actual_gaps[gap_id]
        if len(actual_values) == 0 or not actual_values.issubset(expected_values):
            value_mismatches.append(
                f"{gap_id}: expected={_str_label(tuple(sorted(expected_values)))} "
                f"actual={_str_label(tuple(sorted(actual_values)))}"
            )
    if value_mismatches:
        return _Comparison(
            "wrong_but_valid",
            f"gap value mismatches={len(value_mismatches)}; " + "; ".join(value_mismatches),
        )
    return _Comparison("correct", "gap IDs and values match.")


def _markdown(report: Task309AdvisoryEvaluationReport) -> str:
    lines = [
        "# Task 309 Advisory Golden Evaluation",
        "",
        f"- report_count: `{report.report_count}`",
        f"- golden_count: `{report.golden_count}`",
        f"- report_item_count: `{report.report_item_count}`",
        f"- suggested_count: `{report.suggested_count}`",
        f"- correct_suggestion_count: `{report.correct_suggestion_count}`",
        f"- wrong_but_valid_count: `{report.wrong_but_valid_count}`",
        f"- manual_follow_up_count: `{report.manual_follow_up_count}`",
        f"- unscored_manual_follow_up_count: `{report.unscored_manual_follow_up_count}`",
        f"- skipped_count: `{report.skipped_count}`",
        f"- unknown_id_count: `{report.unknown_id_count}`",
        f"- duplicate_id_count: `{report.duplicate_id_count}`",
        f"- missing_golden_count: `{report.missing_golden_count}`",
        f"- partial_gap_answer_count: `{report.partial_gap_answer_count}`",
        f"- malformed_success_count: `{report.malformed_success_count}`",
        f"- finding_count: `{report.finding_count}`",
        "",
        "## Provider Run Metadata",
        "",
        "```json",
        report.provider_run_metadata_json,
        "```",
        "",
        "## Failure Buckets",
    ]
    for count in report.finding_category_counts:
        lines.append(f"- `{count['category']}`: `{count['count']}`")
    for section in _finding_sections(report.findings):
        section_findings = tuple(
            finding for finding in report.findings if finding.category in section.categories
        )
        if not section_findings:
            continue
        lines.extend(["", f"## {section.title}"])
        for finding in section_findings:
            _append_finding_markdown(lines, finding)
    return "\n".join(lines)


@dataclass(frozen=True)
class _FindingSection:
    title: str
    categories: tuple[str, ...]


def _finding_sections(
    findings: tuple[Task309EvaluationFinding, ...],
) -> tuple[_FindingSection, ...]:
    known = {
        "correct_suggestion",
        "wrong_but_valid",
        "partial_gap_answer",
        "malformed_success",
        "manual_follow_up",
        "unscored_manual_follow_up",
        "missing_golden",
        "unknown_decision_state",
        "duplicate_id",
    }
    other = tuple(sorted({finding.category for finding in findings} - known))
    sections = [
        _FindingSection("Correct Key Suggestions", ("correct_suggestion",)),
        _FindingSection(
            "Incorrect Key Suggestions",
            ("wrong_but_valid", "partial_gap_answer", "malformed_success"),
        ),
        _FindingSection("Manual Follow-Up Provider Attempts", ("manual_follow_up",)),
        _FindingSection("Unscored Or Ineligible Manual Follow-Up", ("unscored_manual_follow_up",)),
        _FindingSection(
            "Corpus Or Report Contract Problems",
            ("missing_golden", "unknown_decision_state", "duplicate_id"),
        ),
    ]
    if other:
        sections.append(_FindingSection("Other Diagnostics", other))
    return tuple(sections)


def _append_finding_markdown(lines: list[str], finding: Task309EvaluationFinding) -> None:
    lines.extend(
        [
            "",
            f"### {finding.source_filename} {finding.item_id}",
            "",
            f"- category: `{finding.category}`",
            f"- item_type: `{finding.item_type}`",
            f"- sequence: `{finding.sequence}`",
            f"- decision_state: `{finding.decision_state}`",
            f"- backend_failure_code: `{finding.backend_failure_code}`",
            f"- manifest_eligible: `{finding.manifest_eligible}`",
            f"- manifest_skip_reason: `{finding.manifest_skip_reason}`",
            f"- detail: {finding.detail}",
            f"- teacher_answer: `{finding.teacher_answer}`",
            f"- model_answer: `{finding.model_answer}`",
            f"- provider_response_status_code: `{finding.provider_response_status_code}`",
        ]
    )
    if finding.output_mode is not None:
        lines.append(f"- provider_output_mode: `{finding.output_mode}`")
    _append_code_block(lines, "Teacher Golden Payload", "json", finding.teacher_answer_json)
    _append_code_block(lines, "Decoded Model Output Payload", "json", finding.model_output_json)
    _append_code_block(lines, "Item Context", "json", finding.item_context_json)
    _append_code_block(lines, "System Prompt", "text", finding.system_prompt)
    _append_code_block(lines, "User Payload Shown To Model", "json", finding.user_payload_json)
    _append_code_block(
        lines,
        "Full Provider Request Payload",
        "json",
        finding.provider_payload_json,
    )
    _append_code_block(lines, "Output Contract", "json", finding.output_contract_json)
    _append_code_block(
        lines,
        "Raw Provider Response Text",
        "json",
        finding.raw_provider_response_text,
    )
    _append_code_block(
        lines,
        "Provider Response Payload",
        "json",
        finding.provider_response_payload_json,
    )
    _append_code_block(
        lines,
        "Decoded Provider Content",
        "json",
        finding.decoded_provider_content_json,
    )


def _append_code_block(lines: list[str], title: str, language: str, value: str | None) -> None:
    if value is None:
        lines.extend([f"- {title}: `not_applicable`"])
        return
    lines.extend([f"- {title}:", f"```{language}", value, "```"])


def _answer_label_for_golden(golden: dict[str, object] | None) -> str | None:
    if golden is None:
        return None
    return _answer_label(_required_object(golden, "expected_answer_payload"))


def _answer_label(payload: dict[str, object] | None) -> str | None:
    if payload is None:
        return None
    kind = _required_str(payload, "kind")
    if kind == "choice":
        return f"choice:{_int_label(_int_tuple(payload.get('correct_alternative_ids')))}"
    if kind == "gap_fill":
        gap_map = _gap_map(payload.get("gap_answers"))
        parts = [
            f"{gap_id}={_str_label(tuple(sorted(values)))}"
            for gap_id, values in sorted(gap_map.items())
        ]
        return "gap_fill:" + "; ".join(parts)
    return kind


def _gap_map(raw_gaps: object) -> dict[str, set[str]]:
    gaps = _object_sequence(raw_gaps, label="gap_answers")
    mapped: dict[str, set[str]] = {}
    for gap in gaps:
        gap_id = _required_str(gap, "gap_id")
        values = gap.get("accepted_values")
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Malformed accepted_values for gap_id={gap_id}.")
        mapped[gap_id] = {_normalize(value) for value in values}
    return mapped


def _source_filename_from_report_path(path: Path) -> str:
    suffix = ".answer-key-completion-report"
    stem = path.stem
    if not stem.endswith(suffix):
        raise ValueError(f"Unexpected report filename: {path.name}")
    return f"{stem[: -len(suffix)]}.dxe"


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return _json_object(payload)


def _object_sequence(value: object, *, label: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        raise ValueError(f"Expected list: {label}")
    items: list[dict[str, object]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"Expected object entry: {label}")
        items.append(_json_object(item))
    return tuple(items)


def _optional_object(payload: dict[str, object], key: str) -> dict[str, object] | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"Expected object for key={key}.")
    return _json_object(value)


def _required_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = _optional_object(payload, key)
    if value is None:
        raise ValueError(f"Expected object for key={key}.")
    return value


def _json_object(value: Mapping[object, object]) -> dict[str, object]:
    return {str(key): item for key, item in value.items()}


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"Expected non-empty string for key={key}.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Expected integer for key={key}.")
    return value


def _optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _optional_mapping_str(payload: Mapping[str, object] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _first_present_str(primary: str | None, fallback: str | None) -> str | None:
    if primary is not None:
        return primary
    return fallback


def _optional_mapping_int(payload: Mapping[str, object] | None, key: str) -> int | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _optional_bool(payload: Mapping[str, object] | None, key: str) -> bool | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, bool) else None


def _payload_json(payload: dict[str, object], key: str) -> str:
    return _canonical_json(_required_object(payload, key))


def _optional_payload_json(payload: dict[str, object], key: str) -> str | None:
    value = _optional_object(payload, key)
    return _canonical_json(value) if value is not None else None


def _int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
        raise ValueError("Expected integer list.")
    return tuple(sorted(value))


def _normalize(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def _canonicalize_gap_value(value: str) -> str:
    """Return the canonical form of a gap value via synonym groups."""

    normalized = _normalize(value)
    for group in _GAP_SYNONYM_GROUPS:
        if normalized in group:
            return min(group)
    return normalized


def _canonical_gap_map(raw_gaps: object) -> dict[str, set[str]]:
    """Build a gap map with values canonicalised through synonym groups."""

    gaps = _object_sequence(raw_gaps, label="gap_answers")
    mapped: dict[str, set[str]] = {}
    for gap in gaps:
        gap_id = _required_str(gap, "gap_id")
        values = gap.get("accepted_values")
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Malformed accepted_values for gap_id={gap_id}.")
        mapped[gap_id] = {_canonicalize_gap_value(value) for value in values}
    return mapped


def _int_label(values: tuple[int, ...]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


def _str_label(values: tuple[str, ...]) -> str:
    return "[" + ",".join(values) + "]"


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
