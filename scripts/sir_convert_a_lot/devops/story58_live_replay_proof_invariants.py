"""Story 58 live replay proof invariant checks.

Purpose:
    Enforce code-owned Story 58 matrix proof conditions over redacted Service
    API responses so operator manifests can add expectations but cannot weaken
    closeout proof requirements.

Relationships:
    - Consumed by the Story 58 proof orchestrator after HTTP evidence capture.
    - Uses only redacted proof models and does not import Service API route
      implementation modules.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_evidence import (
    artifact_metadata_entries,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import (
    JsonObject,
    Story58CaseId,
    Story58RequestEvidence,
)

DIGIEXAM_ROUTE_ID = "digiexam_dxe_to_examnet_migration_bundle"
STALE_REATTEMPT_REASON = "terminal_artifact_contract_incompatible"
MISSING_SOURCE_ERROR = "exam_authoring_correction_source_job_unavailable"
ARTIFACT_SET_MISSING_ERROR = "correction_replay_artifact_set_not_found"
ARTIFACT_REFERENCE_MISMATCH_ERROR = "correction_replay_artifact_reference_mismatch"
GENERIC_IDEMPOTENCY_STATES = frozenset(("fresh_admission", "strict_replay", "service_reattempt"))


def case_invariant_result(
    *,
    case_id: Story58CaseId,
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    """Return whether a case satisfies its Story 58 proof invariant."""

    if case_id == "compatible_strict_digiexam_replay":
        return _strict_replay_result(requests)
    if case_id == "stale_incompatible_digiexam_replay":
        return _stale_incompatible_result(requests)
    if case_id == "missing_source_correction_apply_fail_closed":
        return _missing_source_result(requests)
    if case_id == "exact_duplicate_correction_retry_reuses_artifact_set":
        return _same_artifact_set_result(requests)
    if case_id == "distinct_correction_applies_distinct_artifact_sets":
        return _distinct_artifact_sets_result(requests)
    if case_id == "stale_mismatched_nested_correction_artifact_download_fail_closed":
        return _stale_nested_download_result(requests)
    if case_id == "generic_idempotency_preservation_smoke":
        return _generic_idempotency_result(requests)
    return False, f"Unsupported Story 58 case id: {case_id}"


def readiness_result(readyz: JsonObject) -> tuple[bool, str]:
    """Return whether readiness metadata is sufficient for retained proof."""

    if readyz.get("http_status") != 200:
        return False, "readyz did not return HTTP 200."
    if readyz.get("ready") is not True:
        return False, "readyz did not report ready=true."
    revision = readyz.get("service_revision")
    if not isinstance(revision, str) or revision.strip() == "":
        return False, "readyz did not expose a non-empty service_revision."
    return True, "readyz proved runtime readiness and service revision."


def _strict_replay_result(requests: tuple[Story58RequestEvidence, ...]) -> tuple[bool, str]:
    if any(
        _idempotency_state(request.redacted_payload) == "strict_replay"
        and _route_id(request.redacted_payload) == DIGIEXAM_ROUTE_ID
        for request in requests
    ):
        return True, "DigiExam strict replay metadata was proven."
    return False, "No response proved DigiExam strict replay metadata."


def _stale_incompatible_result(
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    if any(
        _idempotency_state(request.redacted_payload) == "service_reattempt"
        and _idempotency_reason(request.redacted_payload) == STALE_REATTEMPT_REASON
        and _route_id(request.redacted_payload) == DIGIEXAM_ROUTE_ID
        for request in requests
    ):
        return True, "Stale incompatible DigiExam service reattempt was proven."
    return False, "No response proved terminal-artifact-incompatible DigiExam reattempt."


def _missing_source_result(
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    if any(
        request.status_code == 409 and _error_code(request.redacted_payload) == MISSING_SOURCE_ERROR
        for request in requests
    ):
        return True, "Missing-source correction apply fail-closed was proven."
    return False, "No response proved the governed missing-source 409 error."


def _same_artifact_set_result(
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    identities = _successful_request_identities(requests)
    if len(identities) < 2:
        return False, "Duplicate retry needs at least two successful artifact-set responses."
    if len(set(identities)) == 1:
        return True, "Duplicate correction retry reused the artifact set."
    return False, "Duplicate correction retry resolved to different artifact sets."


def _distinct_artifact_sets_result(
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    identities = _successful_request_identities(requests)
    if len(identities) < 2:
        return False, "Distinct applies need at least two successful artifact-set responses."
    if len(set(identities)) == len(identities):
        return True, "Distinct correction applies produced distinct artifact sets."
    return False, "Distinct correction applies reused an artifact set."


def _stale_nested_download_result(
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    for request in requests:
        error_code = _error_code(request.redacted_payload)
        if request.status_code == 404 and error_code == ARTIFACT_SET_MISSING_ERROR:
            return True, "Missing correction replay artifact set failed closed."
        if request.status_code == 409 and error_code == ARTIFACT_REFERENCE_MISMATCH_ERROR:
            return True, "Mismatched correction replay artifact reference failed closed."
    return False, "No response proved the governed nested artifact download failure."


def _generic_idempotency_result(
    requests: tuple[Story58RequestEvidence, ...],
) -> tuple[bool, str]:
    if any(
        200 <= request.status_code < 300
        and _idempotency_state(request.redacted_payload) in GENERIC_IDEMPOTENCY_STATES
        for request in requests
    ):
        return True, "Generic idempotency metadata was proven from a safe response."
    return False, "No safe response proved generic idempotency metadata."


def _successful_request_identities(
    requests: tuple[Story58RequestEvidence, ...],
) -> list[str]:
    identities: list[str] = []
    for request in requests:
        if not 200 <= request.status_code < 300:
            continue
        identity = request_artifact_set_identity(request.redacted_payload)
        if identity is not None:
            identities.append(identity)
    return identities


def request_artifact_set_identity(payload: JsonObject) -> str | None:
    """Return a single request-level artifact-set identity when unambiguous."""

    artifact_set_ids = set(_artifact_set_ids(payload))
    if len(artifact_set_ids) != 1:
        return None
    return next(iter(artifact_set_ids))


def _artifact_set_ids(payload: JsonObject) -> list[str]:
    ids: list[str] = []
    for entry in artifact_metadata_entries(payload):
        artifact_set_id = entry.get("artifact_set_id")
        if isinstance(artifact_set_id, str):
            ids.append(artifact_set_id)
    references = payload.get("correction_replay_artifact_references")
    if isinstance(references, list):
        for reference in references:
            if isinstance(reference, dict):
                artifact_set_id = reference.get("artifact_set_id")
                if isinstance(artifact_set_id, str):
                    ids.append(artifact_set_id)
    return ids


def _idempotency_state(payload: JsonObject) -> str | None:
    return _nested_string(payload, "idempotency", "state")


def _idempotency_reason(payload: JsonObject) -> str | None:
    return _nested_string(payload, "idempotency", "reason")


def _error_code(payload: JsonObject) -> str | None:
    return _nested_string(payload, "error", "code")


def _route_id(payload: JsonObject) -> str | None:
    value = payload.get("route_id")
    return value if isinstance(value, str) else None


def _nested_string(payload: JsonObject, parent: str, key: str) -> str | None:
    value = payload.get(parent)
    if not isinstance(value, dict):
        return None
    item = value.get(key)
    return item if isinstance(item, str) else None
