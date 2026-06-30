"""Story 58 live replay proof manifest and summary helpers.

Purpose:
    Parse operator-declared proof manifests and shape sanitized summary entries
    for Story 58 live replay closeout.

Relationships:
    - Used by the Story 58 proof orchestrator before and after Service API
      requests.
    - Depends on proof models only, keeping manifest validation separate from
      HTTP transport and evidence redaction.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import (
    CASE_LABELS,
    STORY58_CASE_IDS,
    CaseStatus,
    JsonObject,
    Story58CaseEvidence,
    Story58CaseId,
    Story58LiveReplayProofSettings,
)

DEFAULT_REQUIRES_SETUP_REASON = "No safe operator-supplied case request was provided."


def load_case_manifest(path: Path) -> JsonObject:
    """Load and validate a Story 58 proof case manifest."""

    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SystemExit(f"case manifest is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise SystemExit("case manifest must be a JSON object")
    schema_version = payload.get("schema_version")
    if schema_version != "story58_live_replay_case_manifest_v1":
        raise SystemExit(
            "case manifest schema_version must be story58_live_replay_case_manifest_v1"
        )
    return payload


def manifest_cases_by_id(manifest: JsonObject) -> dict[Story58CaseId, JsonObject]:
    """Return case specs keyed by Story 58 matrix id."""

    cases = manifest.get("cases")
    if not isinstance(cases, list):
        raise SystemExit("case manifest must contain a cases list")
    by_id: dict[Story58CaseId, JsonObject] = {}
    for item in cases:
        if not isinstance(item, dict):
            raise SystemExit("case manifest entries must be objects")
        case_id = case_id_from_value(item.get("case_id"))
        by_id[case_id] = dict(item)
    return by_id


def case_id_from_value(value: object) -> Story58CaseId:
    """Validate and return a supported Story 58 case id."""

    if value == "compatible_strict_digiexam_replay":
        return "compatible_strict_digiexam_replay"
    if value == "stale_incompatible_digiexam_replay":
        return "stale_incompatible_digiexam_replay"
    if value == "missing_source_correction_apply_fail_closed":
        return "missing_source_correction_apply_fail_closed"
    if value == "exact_duplicate_correction_retry_reuses_artifact_set":
        return "exact_duplicate_correction_retry_reuses_artifact_set"
    if value == "distinct_correction_applies_distinct_artifact_sets":
        return "distinct_correction_applies_distinct_artifact_sets"
    if value == "stale_mismatched_nested_correction_artifact_download_fail_closed":
        return "stale_mismatched_nested_correction_artifact_download_fail_closed"
    if value == "generic_idempotency_preservation_smoke":
        return "generic_idempotency_preservation_smoke"
    raise SystemExit(f"unsupported Story 58 case_id: {value!r}")


def case_requests(case_spec: JsonObject) -> list[JsonObject]:
    """Return manifest request specs for a case."""

    requests = case_spec.get("requests")
    if requests is None:
        return []
    if not isinstance(requests, list):
        raise SystemExit("case requests must be a list")
    result: list[JsonObject] = []
    for request in requests:
        if not isinstance(request, dict):
            raise SystemExit("case request entries must be objects")
        result.append(dict(request))
    return result


def request_expectation(request_spec: JsonObject) -> JsonObject:
    """Return a request expectation object from a request spec."""

    expect = request_spec.get("expect")
    if expect is None:
        return {}
    if not isinstance(expect, dict):
        raise SystemExit("request expect value must be an object")
    return dict(expect)


def setup_reason(case_spec: JsonObject) -> str:
    """Return the governed setup reason for an unexecuted case."""

    return (
        optional_string(case_spec.get("requires_governed_setup_reason"))
        or DEFAULT_REQUIRES_SETUP_REASON
    )


def missing_case_evidence(
    *,
    case_id: Story58CaseId,
    delegated_generic_smoke_command: str | None,
) -> Story58CaseEvidence:
    """Return an honest skipped/setup-required case for an undeclared matrix case."""

    if case_id == "generic_idempotency_preservation_smoke" and delegated_generic_smoke_command:
        return Story58CaseEvidence(
            case_id=case_id,
            label=CASE_LABELS[case_id],
            status="skipped",
            reason=f"Delegated to external command: {delegated_generic_smoke_command}",
            external_command=delegated_generic_smoke_command,
        )
    return Story58CaseEvidence(
        case_id=case_id,
        label=CASE_LABELS[case_id],
        status="requires_governed_setup",
        reason=DEFAULT_REQUIRES_SETUP_REASON,
    )


def summary_payload(
    *,
    settings: Story58LiveReplayProofSettings,
    run_dir: Path,
    readyz: JsonObject,
    cases: tuple[Story58CaseEvidence, ...],
) -> JsonObject:
    """Return the sanitized top-level proof summary payload."""

    return {
        "schema_version": "story58_live_replay_proof_summary_v1",
        "generated_at": datetime.now(tz=UTC).replace(microsecond=0).isoformat(),
        "overall_status": overall_status(cases, readyz=readyz),
        "service_url": settings.service_url.rstrip("/"),
        "service_revision": readyz.get("service_revision"),
        "readiness": readyz,
        "run_dir": run_dir.as_posix(),
        "cases": [_case_payload(case, run_dir=run_dir) for case in cases],
    }


def overall_status(
    cases: tuple[Story58CaseEvidence, ...],
    *,
    readyz: JsonObject,
) -> CaseStatus:
    """Return the aggregate proof status from case statuses."""

    if readyz.get("status") == "failed":
        return "failed"
    statuses = [case.status for case in cases]
    if "failed" in statuses:
        return "failed"
    if "requires_governed_setup" in statuses:
        return "requires_governed_setup"
    if "skipped" in statuses:
        return "skipped"
    return "passed"


def optional_string(value: object) -> str | None:
    """Return non-empty strings only."""

    return value if isinstance(value, str) and value.strip() != "" else None


def known_case_ids() -> tuple[Story58CaseId, ...]:
    """Return the ordered Story 58 proof matrix ids."""

    return STORY58_CASE_IDS


def _case_payload(case: Story58CaseEvidence, *, run_dir: Path) -> JsonObject:
    payload: JsonObject = {
        "case_id": case.case_id,
        "label": case.label,
        "status": case.status,
        "reason": case.reason,
        "requests": [
            {
                "label": request.label,
                "http_status": request.status_code,
                "response_path": request.response_path.relative_to(run_dir).as_posix(),
                "artifact_metadata_path": request.artifact_metadata_path.relative_to(
                    run_dir
                ).as_posix()
                if request.artifact_metadata_path is not None
                else None,
            }
            for request in case.requests
        ],
    }
    if case.external_command is not None:
        payload["external_command"] = case.external_command
    return payload
