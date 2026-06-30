"""Story 58 live Service API replay proof runner.

Purpose:
    Run operator-declared Service API v2 replay/correction proof cases and
    retain a redacted evidence bundle for Story 58 closeout.

Relationships:
    - Uses the Service API v2 HTTP boundary through `httpx`.
    - Uses Story 58 evidence redaction helpers to retain only approved
      operational metadata.
    - Complements Tasks 375-378 implementation reviews without changing route
      behavior or mutating production state outside supplied safe requests.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_context import (
    Story58ProofContext,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_evidence import (
    artifact_metadata_entries,
    readyz_summary,
    redact_log_capture,
    redacted_response_payload,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_invariants import (
    case_invariant_result,
    readiness_result,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_manifest import (
    case_requests,
    known_case_ids,
    load_case_manifest,
    manifest_cases_by_id,
    missing_case_evidence,
    optional_string,
    request_expectation,
    setup_reason,
    summary_payload,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import (
    CASE_LABELS,
    JsonObject,
    Story58CaseEvidence,
    Story58CaseId,
    Story58LiveReplayProofSettings,
    Story58RequestEvidence,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_report import render_report
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_transport import (
    execute_manifest_request,
    fetch_json,
)


def run_story58_live_replay_proof(
    settings: Story58LiveReplayProofSettings,
    *,
    client: httpx.Client | None = None,
) -> Path:
    """Run the Story 58 proof matrix and return the summary path."""

    _validate_settings(settings)
    run_dir = _run_dir(settings.output_root)
    manifest = load_case_manifest(settings.case_manifest)
    owned_client = client is None
    active_client = client or httpx.Client(
        base_url=settings.service_url.rstrip("/"),
        timeout=settings.timeout_seconds,
    )
    try:
        return _run_with_client(
            settings=settings,
            client=active_client,
            run_dir=run_dir,
            manifest=manifest,
        )
    finally:
        if owned_client:
            active_client.close()


def _run_with_client(
    *,
    settings: Story58LiveReplayProofSettings,
    client: httpx.Client,
    run_dir: Path,
    manifest: JsonObject,
) -> Path:
    correlation_id = f"corr_story58_live_replay_{int(time.time())}"
    ready_status, ready_payload = fetch_json(
        client,
        path="/readyz",
        api_key=settings.api_key,
        correlation_id=correlation_id,
    )
    readyz = readyz_summary(ready_payload)
    readyz["http_status"] = ready_status
    ready_passed, ready_reason = readiness_result(readyz)
    readyz["status"] = "passed" if ready_passed else "failed"
    readyz["reason"] = ready_reason
    _write_json(run_dir / "readyz.redacted.json", readyz)
    if settings.monitoring_pointers:
        _write_json(
            run_dir / "monitoring-pointers.json",
            {
                "schema_version": "story58_live_replay_monitoring_pointers_v1",
                "pointers": list(settings.monitoring_pointers),
            },
        )

    cases_by_id = manifest_cases_by_id(manifest)
    delegated_command = optional_string(manifest.get("delegated_generic_smoke_command"))
    case_evidence: list[Story58CaseEvidence] = []
    for case_id in known_case_ids():
        case_spec = cases_by_id.get(case_id)
        case_evidence.append(
            _run_case(
                case_id=case_id,
                case_spec=case_spec,
                manifest_root=settings.case_manifest.parent,
                client=client,
                api_key=settings.api_key,
                correlation_id=correlation_id,
                run_dir=run_dir,
                delegated_generic_smoke_command=delegated_command,
            )
        )
    _write_log_captures(settings=settings, run_dir=run_dir)

    summary = summary_payload(
        settings=settings,
        run_dir=run_dir,
        readyz=readyz,
        cases=tuple(case_evidence),
    )
    summary_path = run_dir / "summary.json"
    _write_json(summary_path, summary)
    (run_dir / "report.md").write_text(
        render_report(summary=summary, cases=tuple(case_evidence)),
        encoding="utf-8",
    )
    return summary_path


def _run_case(
    *,
    case_id: Story58CaseId,
    case_spec: JsonObject | None,
    manifest_root: Path,
    client: httpx.Client,
    api_key: str,
    correlation_id: str,
    run_dir: Path,
    delegated_generic_smoke_command: str | None,
) -> Story58CaseEvidence:
    if case_spec is None:
        return missing_case_evidence(
            case_id=case_id,
            delegated_generic_smoke_command=delegated_generic_smoke_command,
        )
    label = optional_string(case_spec.get("label")) or CASE_LABELS[case_id]
    if case_spec.get("safe_to_run") is False:
        return Story58CaseEvidence(
            case_id=case_id,
            label=label,
            status="requires_governed_setup",
            reason=setup_reason(case_spec),
        )
    requests = case_requests(case_spec)
    if not requests:
        return Story58CaseEvidence(
            case_id=case_id,
            label=label,
            status="requires_governed_setup",
            reason=setup_reason(case_spec),
        )

    request_evidence: list[Story58RequestEvidence] = []
    proof_context = Story58ProofContext()
    for index, request_spec in enumerate(requests, start=1):
        request_evidence.append(
            _run_request(
                case_id=case_id,
                index=index,
                request_spec=request_spec,
                proof_context=proof_context,
                manifest_root=manifest_root,
                client=client,
                api_key=api_key,
                correlation_id=f"{correlation_id}_{case_id}_{index}",
                run_dir=run_dir,
            )
        )
    request_failures = [request.reason for request in request_evidence if not request.passed]
    if request_failures:
        return Story58CaseEvidence(
            case_id=case_id,
            label=label,
            status="failed",
            reason="; ".join(request_failures),
            requests=tuple(request_evidence),
        )
    invariant_passed, invariant_reason = case_invariant_result(
        case_id=case_id,
        requests=tuple(request_evidence),
    )
    if not invariant_passed:
        return Story58CaseEvidence(
            case_id=case_id,
            label=label,
            status="failed",
            reason=invariant_reason,
            requests=tuple(request_evidence),
        )
    return Story58CaseEvidence(
        case_id=case_id,
        label=label,
        status="passed",
        reason=invariant_reason,
        requests=tuple(request_evidence),
    )


def _run_request(
    *,
    case_id: Story58CaseId,
    index: int,
    request_spec: JsonObject,
    proof_context: Story58ProofContext,
    manifest_root: Path,
    client: httpx.Client,
    api_key: str,
    correlation_id: str,
    run_dir: Path,
) -> Story58RequestEvidence:
    resolved_request = proof_context.interpolated_request(request_spec)
    status_code, payload = execute_manifest_request(
        client=client,
        request_spec=resolved_request,
        manifest_root=manifest_root,
        api_key=api_key,
        correlation_id=correlation_id,
    )
    redacted = redacted_response_payload(status_code=status_code, payload=payload)
    proof_context.capture(request_spec=request_spec, redacted_payload=redacted)
    case_dir = run_dir / "cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    response_path = case_dir / f"{case_id}-{index}-response.redacted.json"
    _write_json(response_path, redacted)
    artifact_path = _write_artifact_metadata(
        case_dir=case_dir,
        case_id=case_id,
        index=index,
        redacted=redacted,
    )
    passed, reason = _expectation_result(
        redacted=redacted,
        expect=request_expectation(request_spec),
    )
    label = optional_string(request_spec.get("label")) or f"{case_id} request {index}"
    return Story58RequestEvidence(
        label=label,
        status_code=status_code,
        response_path=response_path,
        artifact_metadata_path=artifact_path,
        passed=passed,
        reason=reason,
        redacted_payload=redacted,
    )


def _expectation_result(*, redacted: JsonObject, expect: JsonObject) -> tuple[bool, str]:
    http_status = expect.get("http_status")
    if http_status is not None and not _status_matches(redacted.get("http_status"), http_status):
        return False, f"HTTP status {redacted.get('http_status')!r} did not match {http_status!r}"
    error_code = optional_string(expect.get("error_code"))
    if error_code is not None and _nested_string(redacted, ("error", "code")) != error_code:
        return False, f"error.code did not match {error_code}"
    idempotency_state = optional_string(expect.get("idempotency_state"))
    if (
        idempotency_state is not None
        and _nested_string(redacted, ("idempotency", "state")) != idempotency_state
    ):
        return False, f"idempotency.state did not match {idempotency_state}"
    idempotency_reason = optional_string(expect.get("idempotency_reason"))
    if (
        idempotency_reason is not None
        and _nested_string(redacted, ("idempotency", "reason")) != idempotency_reason
    ):
        return False, f"idempotency.reason did not match {idempotency_reason}"
    route_id = optional_string(expect.get("route_id"))
    if route_id is not None and redacted.get("route_id") != route_id:
        return False, f"route_id did not match {route_id}"
    route_key = optional_string(expect.get("route_key"))
    if route_key is not None and redacted.get("route_key") != route_key:
        return False, f"route_key did not match {route_key}"
    return True, "Declared live expectation passed."


def _status_matches(actual: object, expected: object) -> bool:
    if isinstance(expected, int):
        return actual == expected
    if isinstance(expected, list):
        return any(isinstance(item, int) and actual == item for item in expected)
    raise SystemExit("http_status expectation must be an int or list of ints")


def _write_artifact_metadata(
    *,
    case_dir: Path,
    case_id: Story58CaseId,
    index: int,
    redacted: JsonObject,
) -> Path | None:
    entries = artifact_metadata_entries(redacted)
    if not entries:
        return None
    artifact_path = case_dir / f"{case_id}-{index}-artifact-metadata.json"
    _write_json(
        artifact_path,
        {
            "schema_version": "story58_live_replay_artifact_metadata_v1",
            "entries": entries,
        },
    )
    return artifact_path


def _write_log_captures(*, settings: Story58LiveReplayProofSettings, run_dir: Path) -> None:
    if not settings.log_capture_paths:
        return
    log_dir = run_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for path in settings.log_capture_paths:
        target = log_dir / f"{path.stem}.redacted{path.suffix}"
        redact_log_capture(source=path, target=target, secrets=(settings.api_key,))


def _validate_settings(settings: Story58LiveReplayProofSettings) -> None:
    if settings.api_key.strip() == "":
        raise SystemExit("api_key must not be empty")
    if settings.service_url.strip() == "":
        raise SystemExit("service_url must not be empty")
    if not settings.case_manifest.is_file():
        raise SystemExit(f"case manifest not found: {settings.case_manifest}")
    if settings.timeout_seconds <= 0:
        raise SystemExit("timeout_seconds must be positive")
    for path in settings.log_capture_paths:
        if not path.is_file():
            raise SystemExit(f"log capture not found: {path}")


def _run_dir(output_root: Path) -> Path:
    run_dir = output_root / datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _nested_string(payload: JsonObject, path: tuple[str, str]) -> str | None:
    current = payload.get(path[0])
    if not isinstance(current, dict):
        return None
    value = current.get(path[1])
    return value if isinstance(value, str) else None


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
