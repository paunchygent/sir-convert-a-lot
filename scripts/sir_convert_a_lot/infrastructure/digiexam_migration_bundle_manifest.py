"""DigiExam migration bundle manifest and report helpers.

Purpose:
    Build deterministic artifact entries, support reports, manifest bytes, and
    terminal bundle status for the DigiExam migration service route.

Relationships:
    - Used by `infrastructure.digiexam_migration_bundle_builder` after parser,
      PDF, and QTI target execution.
    - Mirrors artifact-key and availability contracts from
      `domain.digiexam_migration_bundle_contracts`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import StrEnum
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    ARTIFACT_DEFINITIONS,
    REQUIRED_ARTIFACT_KEYS,
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
    DigiExamMigrationBundleStatus,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def artifact_path(artifacts_dir: Path, key: DigiExamMigrationArtifactKey) -> Path:
    """Return the deterministic filesystem path for one bundle artifact key."""

    return artifacts_dir / ARTIFACT_DEFINITIONS[key].filename


def available_entry(
    *,
    job: StoredJobV2,
    key: DigiExamMigrationArtifactKey,
    path: Path,
) -> DigiExamMigrationArtifactEntry:
    """Create an available manifest entry from persisted artifact bytes."""

    definition = ARTIFACT_DEFINITIONS[key]
    payload = path.read_bytes()
    return DigiExamMigrationArtifactEntry(
        artifact_key=key,
        filename=definition.filename,
        content_type=definition.content_type,
        availability=DigiExamMigrationArtifactAvailability.AVAILABLE,
        size_bytes=len(payload),
        sha256=f"sha256:{hashlib.sha256(payload).hexdigest()}",
        download_path=f"/v2/convert/jobs/{job.job_id}/artifacts/{key.value}",
    )


def unavailable_entry(
    *,
    job: StoredJobV2,
    key: DigiExamMigrationArtifactKey,
    unavailable_code: str,
) -> DigiExamMigrationArtifactEntry:
    """Create an unavailable entry for a target that could not be produced."""

    definition = ARTIFACT_DEFINITIONS[key]
    return DigiExamMigrationArtifactEntry(
        artifact_key=key,
        filename=definition.filename,
        content_type=definition.content_type,
        availability=DigiExamMigrationArtifactAvailability.UNAVAILABLE,
        size_bytes=None,
        sha256=None,
        download_path=None,
        unavailable_code=unavailable_code,
    )


def failed_entry(
    *,
    job: StoredJobV2,
    key: DigiExamMigrationArtifactKey,
    unavailable_code: str,
) -> DigiExamMigrationArtifactEntry:
    """Create a failed entry for a target that attempted generation."""

    definition = ARTIFACT_DEFINITIONS[key]
    return DigiExamMigrationArtifactEntry(
        artifact_key=key,
        filename=definition.filename,
        content_type=definition.content_type,
        availability=DigiExamMigrationArtifactAvailability.FAILED,
        size_bytes=None,
        sha256=None,
        download_path=None,
        unavailable_code=unavailable_code,
    )


def not_requested_entry(
    *,
    job: StoredJobV2,
    key: DigiExamMigrationArtifactKey,
    depends_on: str | None = None,
) -> DigiExamMigrationArtifactEntry:
    """Create a manifest entry for a target-specific artifact skipped by request."""

    definition = ARTIFACT_DEFINITIONS[key]
    return DigiExamMigrationArtifactEntry(
        artifact_key=key,
        filename=definition.filename,
        content_type=definition.content_type,
        availability=DigiExamMigrationArtifactAvailability.NOT_REQUESTED,
        size_bytes=None,
        sha256=None,
        download_path=None,
        depends_on=depends_on,
    )


def not_requested_qti_entries(
    job: StoredJobV2,
) -> dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactEntry]:
    """Return QTI package/report entries for requests that skipped QTI."""

    return {
        DigiExamMigrationArtifactKey.QTI_PACKAGE: not_requested_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.QTI_PACKAGE,
        ),
        DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT: not_requested_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.QTI_VALIDATION_REPORT,
            depends_on=DigiExamMigrationArtifactKey.QTI_PACKAGE.value,
        ),
    }


def complete_entries(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    pdf_entry: DigiExamMigrationArtifactEntry,
    qti_entries: dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactEntry],
    effective_ir_entry: DigiExamMigrationArtifactEntry | None = None,
    ingestion_overlay_report_entry: DigiExamMigrationArtifactEntry | None = None,
    answer_key_completion_report_entry: DigiExamMigrationArtifactEntry | None = None,
) -> tuple[DigiExamMigrationArtifactEntry, ...]:
    """Return the full ordered required artifact entry list for a bundle."""

    entries: dict[DigiExamMigrationArtifactKey, DigiExamMigrationArtifactEntry] = {
        DigiExamMigrationArtifactKey.BUNDLE_MANIFEST: _manifest_entry(job),
        DigiExamMigrationArtifactKey.EXAMNET_PDF: pdf_entry,
        **qti_entries,
        DigiExamMigrationArtifactKey.EFFECTIVE_IR_JSON: (
            effective_ir_entry
            or not_requested_entry(job=job, key=DigiExamMigrationArtifactKey.EFFECTIVE_IR_JSON)
        ),
        DigiExamMigrationArtifactKey.INGESTION_OVERLAY_REPORT: (
            ingestion_overlay_report_entry
            or not_requested_entry(
                job=job,
                key=DigiExamMigrationArtifactKey.INGESTION_OVERLAY_REPORT,
            )
        ),
        DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT: not_requested_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT,
        ),
    }
    if answer_key_completion_report_entry is not None:
        entries[DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT] = (
            answer_key_completion_report_entry
        )
    for key in (
        DigiExamMigrationArtifactKey.IR_JSON,
        DigiExamMigrationArtifactKey.MIGRATION_MANIFEST,
        DigiExamMigrationArtifactKey.TARGET_READINESS_REPORT,
        DigiExamMigrationArtifactKey.MANUAL_FOLLOW_UP_REPORT,
        DigiExamMigrationArtifactKey.WARNINGS_REPORT,
        DigiExamMigrationArtifactKey.ASSET_SUMMARY,
    ):
        entries[key] = available_entry(job=job, key=key, path=artifact_path(artifacts_dir, key))
    return tuple(entries[key] for key in REQUIRED_ARTIFACT_KEYS)


def write_manual_follow_up_report(
    *,
    path: Path,
    exam_follow_ups: object,
    qti_follow_ups: list[object],
) -> int:
    """Write the teacher-facing manual follow-up report and return entry count."""

    entries: list[object] = []
    if isinstance(exam_follow_ups, list):
        entries.extend(exam_follow_ups)
    entries.extend(qti_follow_ups)
    lines = ["# Manuell uppföljning", ""]
    if not entries:
        lines.append("Inga manuella åtgärder krävs.")
    for index, entry in enumerate(entries, start=1):
        if isinstance(entry, dict):
            reason = entry.get("reason") or entry.get("reason_code")
            title = entry.get("title") or entry.get("item_id") or "Prov"
            message = entry.get("message") or "Kontrollera frågan manuellt."
            lines.extend(
                [f"## {index}. {title}", "", f"- Orsak: {reason}", f"- Åtgärd: {message}", ""]
            )
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return len(entries)


def write_warnings_report(
    *,
    path: Path,
    parser_warnings: object,
    pdf_warnings: object,
    qti_warnings: list[str],
) -> list[str]:
    """Write the bundle warnings report and return flattened warning messages."""

    payload = {
        "schema_version": "digiexam_migration_warnings_v1",
        "parser_warnings": parser_warnings,
        "examnet_pdf_warnings": pdf_warnings,
        "qti_warnings": qti_warnings,
    }
    write_json(path, payload)
    messages: list[str] = []
    for warning_group in (parser_warnings, pdf_warnings):
        if isinstance(warning_group, list):
            for warning in warning_group:
                if isinstance(warning, dict):
                    message = warning.get("message")
                    if isinstance(message, str):
                        messages.append(message)
    messages.extend(qti_warnings)
    return messages


def bundle_status(
    entries: tuple[DigiExamMigrationArtifactEntry, ...],
    manual_follow_up_count: int,
) -> DigiExamMigrationBundleStatus:
    """Classify the terminal bundle status from requested target availability."""

    target_keys = {
        DigiExamMigrationArtifactKey.EXAMNET_PDF,
        DigiExamMigrationArtifactKey.QTI_PACKAGE,
    }
    target_entries = [entry for entry in entries if entry.artifact_key in target_keys]
    requested_target_entries = [
        entry
        for entry in target_entries
        if entry.availability != DigiExamMigrationArtifactAvailability.NOT_REQUESTED
    ]
    available_targets = [
        entry
        for entry in requested_target_entries
        if entry.availability == DigiExamMigrationArtifactAvailability.AVAILABLE
    ]
    failed_targets = [
        entry
        for entry in requested_target_entries
        if entry.availability == DigiExamMigrationArtifactAvailability.FAILED
    ]
    if not available_targets:
        if failed_targets:
            return DigiExamMigrationBundleStatus.FAILED
        return DigiExamMigrationBundleStatus.NEEDS_REVIEW
    if manual_follow_up_count > 0 or len(available_targets) != len(requested_target_entries):
        return DigiExamMigrationBundleStatus.PARTIAL
    return DigiExamMigrationBundleStatus.COMPLETE


def write_json(path: Path, payload: object) -> None:
    """Write deterministic JSON bytes for bundle support artifacts."""

    path.write_bytes(json_bytes(payload))


def json_bytes(payload: object) -> bytes:
    """Return deterministic JSON bytes for manifest-compatible payloads."""

    text = json.dumps(json_ready(payload), ensure_ascii=False, indent=2, sort_keys=True)
    return f"{text}\n".encode("utf-8")


def json_ready(value: object) -> object:
    """Normalize dataclasses, enums, tuples, and dictionaries for JSON output."""

    if is_dataclass(value) and not isinstance(value, type):
        return json_ready(asdict(value))
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, dict):
        return {str(key): json_ready(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [json_ready(child) for child in value]
    return value


def expires_at(job: StoredJobV2) -> str | None:
    """Return the job expiration timestamp in API JSON form."""

    if job.expires_at is None:
        return None
    return job.expires_at.isoformat().replace("+00:00", "Z")


def _manifest_entry(job: StoredJobV2) -> DigiExamMigrationArtifactEntry:
    definition = ARTIFACT_DEFINITIONS[DigiExamMigrationArtifactKey.BUNDLE_MANIFEST]
    return DigiExamMigrationArtifactEntry(
        artifact_key=DigiExamMigrationArtifactKey.BUNDLE_MANIFEST,
        filename=definition.filename,
        content_type=definition.content_type,
        availability=DigiExamMigrationArtifactAvailability.AVAILABLE,
        size_bytes=None,
        sha256=None,
        download_path=f"/v2/convert/jobs/{job.job_id}/artifacts/bundle_manifest",
    )
