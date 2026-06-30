"""Story 58 live replay proof redaction and evidence extraction.

Purpose:
    Convert Service API v2 responses and optional log captures into the
    metadata-only evidence allowed by Story 58 closeout.

Relationships:
    - Used by `story58_live_replay_proof` after live HTTP calls complete.
    - Keeps content, credentials, signatures, idempotency keys, grants, prompts,
      and private paths out of retained proof files.
"""

from __future__ import annotations

import re
from pathlib import Path

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import (
    JsonList,
    JsonObject,
)

ARTIFACT_REFERENCE_KEYS = frozenset(
    (
        "schema_version",
        "job_id",
        "artifact_set_id",
        "artifact_key",
        "content_sha256",
        "request_id",
        "source_binding_digest",
        "source_state_sha256",
        "correction_payload_digest",
        "target_set_digest",
        "replay_profile_version",
        "created_at",
    )
)
ARTIFACT_METADATA_KEYS = frozenset(
    (
        "schema_version",
        "artifact_set_id",
        "artifact_key",
        "content_sha256",
        "sha256",
        "hash",
        "size_bytes",
        "availability",
        "created_at",
    )
)
SCHEMA_VERSION_KEYS = frozenset(
    (
        "schema_version",
        "source_schema_version",
        "effective_schema_version",
        "manifest_schema_version",
    )
)


def redacted_response_payload(*, status_code: int, payload: JsonObject) -> JsonObject:
    """Return the Story 58 allow-listed response evidence payload."""

    redacted: JsonObject = {"http_status": status_code}
    error = _error_summary(payload)
    if error:
        redacted["error"] = error
    job = _job_summary(payload)
    if job:
        redacted["job"] = job
    idempotency = _idempotency_summary(payload)
    if idempotency:
        redacted["idempotency"] = idempotency
    route_id = _find_first_string(payload, "route_id")
    if route_id is not None:
        redacted["route_id"] = route_id
    route_key = _find_first_string(payload, "route_key")
    if route_key is not None:
        redacted["route_key"] = route_key
    schema_versions = _schema_versions(payload)
    if schema_versions:
        redacted["schema_versions"] = schema_versions
    artifact_references = correction_replay_artifact_references(payload)
    if artifact_references:
        redacted["correction_replay_artifact_references"] = artifact_references
    artifact_metadata = artifact_metadata_entries(payload)
    if artifact_metadata:
        redacted["artifact_metadata"] = artifact_metadata
    return redacted


def readyz_summary(payload: JsonObject) -> JsonObject:
    """Return the safe readiness fields retained by the proof run."""

    return {
        "ready": payload.get("ready"),
        "service_revision": payload.get("service_revision"),
        "service_profile": payload.get("service_profile"),
    }


def artifact_metadata_entries(payload: object) -> list[JsonObject]:
    """Collect allow-listed artifact metadata entries from a response payload."""

    entries: list[JsonObject] = []
    _collect_artifact_metadata(payload, entries)
    return entries


def correction_replay_artifact_references(payload: object) -> list[JsonObject]:
    """Collect typed correction replay artifact references from a payload."""

    references: list[JsonObject] = []
    _collect_artifact_references(payload, references)
    return references


def redact_log_capture(*, source: Path, target: Path, secrets: tuple[str, ...]) -> None:
    """Write a metadata-only log capture summary to target."""

    text = source.read_text(encoding="utf-8", errors="replace")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    job_ids = sorted(set(re.findall(r"jobv2_[A-Za-z0-9_]+", text)))
    request_ids = sorted(set(re.findall(r"req_[A-Za-z0-9_]+", text)))
    artifact_set_ids = sorted(set(re.findall(r"(?:a|cr)set_[A-Za-z0-9_]+", text)))
    error_codes = sorted(set(re.findall(r"[a-z][a-z0-9_]*_(?:error|mismatch|unavailable)", text)))
    lines = [
        "schema_version: story58_live_replay_log_capture_redacted_v1",
        f"source_name: {source.name}",
        f"line_count: {len(text.splitlines())}",
        f"job_ids: {', '.join(job_ids)}",
        f"request_ids: {', '.join(request_ids)}",
        f"artifact_set_ids: {', '.join(artifact_set_ids)}",
        f"error_codes: {', '.join(error_codes)}",
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _error_summary(payload: JsonObject) -> JsonObject:
    error = payload.get("error")
    if not isinstance(error, dict):
        return {}
    summary: JsonObject = {}
    code = error.get("code")
    retryable = error.get("retryable")
    if isinstance(code, str):
        summary["code"] = code
    if isinstance(retryable, bool):
        summary["retryable"] = retryable
    return summary


def _job_summary(payload: JsonObject) -> JsonObject:
    job = payload.get("job")
    summary: JsonObject = {}
    if isinstance(job, dict):
        for key in ("job_id", "status", "route_id", "created_at", "updated_at"):
            value = job.get(key)
            if isinstance(value, str):
                summary[key] = value
    for key in ("job_id", "status"):
        value = payload.get(key)
        if isinstance(value, str):
            summary.setdefault(key, value)
    return summary


def _idempotency_summary(payload: JsonObject) -> JsonObject:
    idempotency = payload.get("idempotency")
    if not isinstance(idempotency, dict):
        return {}
    summary: JsonObject = {}
    for key in (
        "state",
        "reason",
        "active_job_id",
        "replayed_job_id",
        "reattempt_of_job_id",
    ):
        value = idempotency.get(key)
        if isinstance(value, str):
            summary[key] = value
    idempotent_replay = idempotency.get("idempotent_replay")
    if isinstance(idempotent_replay, bool):
        summary["idempotent_replay"] = idempotent_replay
    attempt_count = idempotency.get("attempt_count")
    if isinstance(attempt_count, int):
        summary["attempt_count"] = attempt_count
    previous_attempts = idempotency.get("previous_attempts")
    if isinstance(previous_attempts, list):
        summary["previous_attempts"] = _previous_attempts(previous_attempts)
    return summary


def _previous_attempts(items: JsonList) -> list[JsonObject]:
    attempts: list[JsonObject] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        attempt: JsonObject = {}
        for key in ("job_id", "status"):
            value = item.get(key)
            if isinstance(value, str):
                attempt[key] = value
        retryable = item.get("failure_retryable")
        if isinstance(retryable, bool):
            attempt["failure_retryable"] = retryable
        if attempt:
            attempts.append(attempt)
    return attempts


def _collect_artifact_references(value: object, references: list[JsonObject]) -> None:
    if isinstance(value, dict):
        schema_version = value.get("schema_version")
        if schema_version == "correction_replay_artifact_reference_v1":
            reference: JsonObject = {}
            for key in ARTIFACT_REFERENCE_KEYS:
                item = value.get(key)
                if isinstance(item, str):
                    reference[key] = item
            if reference:
                references.append(reference)
        for child in value.values():
            _collect_artifact_references(child, references)
    elif isinstance(value, list):
        for child in value:
            _collect_artifact_references(child, references)


def _collect_artifact_metadata(value: object, entries: list[JsonObject]) -> None:
    if isinstance(value, dict):
        if any(key in value for key in ARTIFACT_METADATA_KEYS):
            entry: JsonObject = {}
            for key in ARTIFACT_METADATA_KEYS:
                item = value.get(key)
                if isinstance(item, (str, int)):
                    entry[key] = item
            if entry:
                entries.append(entry)
        for child in value.values():
            _collect_artifact_metadata(child, entries)
    elif isinstance(value, list):
        for child in value:
            _collect_artifact_metadata(child, entries)


def _schema_versions(payload: object) -> JsonObject:
    versions: JsonObject = {}
    _collect_schema_versions(payload, versions)
    return versions


def _collect_schema_versions(value: object, versions: JsonObject) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in SCHEMA_VERSION_KEYS and isinstance(item, str):
                versions[key] = item
            _collect_schema_versions(item, versions)
    elif isinstance(value, list):
        for child in value:
            _collect_schema_versions(child, versions)


def _find_first_string(value: object, key: str) -> str | None:
    if isinstance(value, dict):
        item = value.get(key)
        if isinstance(item, str):
            return item
        for child in value.values():
            found = _find_first_string(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_first_string(child, key)
            if found is not None:
                return found
    return None
