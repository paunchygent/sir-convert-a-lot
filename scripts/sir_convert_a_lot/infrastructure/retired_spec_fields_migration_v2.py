"""One-time migration of stored v2 job specs across the Sir exam retirement.

Purpose:
    Rewrite retained pre-retirement `jobs_v2/<job_id>/manifest.json` job specs
    so they validate against the current `JobSpecV2` contract. The exam
    retirement removed `conversion.targets`, `conversion.artifact_language`,
    and `digiexam_migration_options` from the job spec and
    `diagnostics.structured_llm_admission` from the manifest; every manifest
    written before it carries those keys, and strict stored-spec validation
    rejects the job-spec ones.

    Idempotency records store only a request fingerprint hash. Its inputs (raw
    request JSON and upload hashes) are never persisted, so a pre-retirement
    fingerprint cannot be recomputed in the post-retirement encoding. The
    migration therefore blocks while any idempotency record is still inside
    its replay window and reports when that window closes; expired records are
    already ignored and deleted by `IdempotencyStore.get`.

Relationships:
    - Runs against a stopped service data root through
      `interfaces.cli_retired_spec_fields_migration_v2`.
    - Uses `JobStoreV2Core` manifest paths and locks, and validates with the
      same stored-spec reader path as `job_store_manifest_v2`.
    - Keeps exam jobs untouched and reports them as blocking; it never deletes
      jobs, artifacts, or idempotency records.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2_core import JobStoreV2Core
from scripts.sir_convert_a_lot.infrastructure.stored_job_spec_normalization_v2 import (
    normalize_stored_job_spec_payload_v2,
)

RETIRED_JOB_SPEC_KEYS: tuple[str, ...] = ("digiexam_migration_options",)
RETIRED_CONVERSION_KEYS: tuple[str, ...] = ("targets", "artifact_language")
RETIRED_DIAGNOSTICS_KEYS: tuple[str, ...] = ("structured_llm_admission",)
RETIRED_SOURCE_FORMATS: frozenset[str] = frozenset({"digiexam_dxe"})
RETIRED_OUTPUT_FORMATS: frozenset[str] = frozenset({"examnet_migration_bundle"})


@dataclass(frozen=True)
class UnmigratableJob:
    """One retained job the migration cannot turn into a current generic job."""

    job_id: str
    reason: str


@dataclass
class RetiredSpecFieldsMigrationReport:
    """Outcome of one migration run over a service data root."""

    data_root: str
    mode: str
    outcome: str = "clean"
    jobs_scanned: int = 0
    jobs_requiring_rewrite: list[str] = field(default_factory=list)
    jobs_rewritten: list[str] = field(default_factory=list)
    dropped_artifact_language_job_ids: list[str] = field(default_factory=list)
    unmigratable_jobs: list[UnmigratableJob] = field(default_factory=list)
    live_idempotency_records: int = 0
    idempotency_window_closes_at: str | None = None

    @property
    def blocked(self) -> bool:
        """Return whether the data root must not be served by the current runtime."""
        return bool(self.unmigratable_jobs) or self.live_idempotency_records > 0


@dataclass(frozen=True)
class _ManifestPlan:
    rewritten_manifest: dict[str, object] | None
    dropped_artifact_language: bool


def migrate_retired_spec_fields(
    *,
    data_root: Path,
    idempotency_ttl_seconds: int,
    execute: bool,
) -> RetiredSpecFieldsMigrationReport:
    """Plan, and with `execute`, apply the stored-spec migration for one data root.

    Nothing is written unless `execute` is set and no job or idempotency record
    blocks the migration, so every run is either a full rewrite or a no-op.
    """
    jobs_dir = data_root / "jobs_v2"
    if not jobs_dir.is_dir():
        raise FileNotFoundError(f"no v2 job store at {jobs_dir}")
    store = JobStoreV2Core(data_root=data_root, raw_ttl_seconds=0, artifact_ttl_seconds=0)
    report = RetiredSpecFieldsMigrationReport(
        data_root=str(data_root), mode="execute" if execute else "dry_run"
    )
    _scan_idempotency_records(
        report=report,
        idempotency_dir=data_root / "idempotency",
        ttl=timedelta(seconds=idempotency_ttl_seconds),
        now=utc_now(),
    )
    plans: dict[str, _ManifestPlan] = {}
    for job_id in sorted(path.name for path in jobs_dir.iterdir() if path.is_dir()):
        manifest_path = store._manifest_path(job_id)
        if not manifest_path.exists():
            continue
        report.jobs_scanned += 1
        plan = _plan_manifest(job_id=job_id, manifest=read_json(manifest_path), report=report)
        if plan is not None and plan.rewritten_manifest is not None:
            plans[job_id] = plan
            report.jobs_requiring_rewrite.append(job_id)
            if plan.dropped_artifact_language:
                report.dropped_artifact_language_job_ids.append(job_id)

    if report.blocked:
        report.outcome = "blocked"
        return report
    if not plans:
        return report
    if not execute:
        report.outcome = "rewrite_required"
        return report
    for job_id in plans:
        with store._job_manifest_lock(job_id):
            manifest = store._read_manifest_locked(job_id)
            plan = _plan_manifest(job_id=job_id, manifest=manifest, report=report)
            if plan is None or plan.rewritten_manifest is None:
                continue
            atomic_write_json(store._manifest_path(job_id), plan.rewritten_manifest)
            report.jobs_rewritten.append(job_id)
    report.outcome = "blocked" if report.blocked else "rewritten"
    return report


def _scan_idempotency_records(
    *,
    report: RetiredSpecFieldsMigrationReport,
    idempotency_dir: Path,
    ttl: timedelta,
    now: datetime,
) -> None:
    if not idempotency_dir.is_dir():
        return
    latest_close: datetime | None = None
    for record_path in sorted(idempotency_dir.glob("*.json")):
        created_at = dt_from_rfc3339(read_json(record_path).get("created_at"))
        if created_at is None or now - created_at > ttl:
            continue
        report.live_idempotency_records += 1
        closes_at = created_at + ttl
        if latest_close is None or closes_at > latest_close:
            latest_close = closes_at
    if latest_close is not None:
        report.idempotency_window_closes_at = dt_to_rfc3339(latest_close)


def _plan_manifest(
    *,
    job_id: str,
    manifest: Mapping[str, object],
    report: RetiredSpecFieldsMigrationReport,
) -> _ManifestPlan | None:
    """Return the rewrite for one manifest, or record why it cannot be migrated."""
    spec = manifest.get("job_spec")
    if not isinstance(spec, Mapping):
        report.unmigratable_jobs.append(UnmigratableJob(job_id, "job_spec is not an object"))
        return None
    exam_reason = _exam_job_reason(manifest=manifest, spec=spec)
    if exam_reason is not None:
        report.unmigratable_jobs.append(UnmigratableJob(job_id, exam_reason))
        return None

    rewritten = {key: value for key, value in spec.items() if key not in RETIRED_JOB_SPEC_KEYS}
    conversion = spec.get("conversion")
    dropped_artifact_language = False
    if isinstance(conversion, Mapping):
        dropped_artifact_language = conversion.get("artifact_language") is not None
        rewritten["conversion"] = {
            key: value for key, value in conversion.items() if key not in RETIRED_CONVERSION_KEYS
        }
    try:
        JobSpecV2.model_validate(normalize_stored_job_spec_payload_v2(rewritten))
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        report.unmigratable_jobs.append(
            UnmigratableJob(job_id, f"invalid after migration: {location} {first['type']}")
        )
        return None
    rewritten_manifest = {**manifest, "job_spec": rewritten}
    diagnostics = manifest.get("diagnostics")
    if isinstance(diagnostics, Mapping):
        rewritten_manifest["diagnostics"] = {
            key: value for key, value in diagnostics.items() if key not in RETIRED_DIAGNOSTICS_KEYS
        }
    if rewritten_manifest == dict(manifest):
        return _ManifestPlan(rewritten_manifest=None, dropped_artifact_language=False)
    return _ManifestPlan(
        rewritten_manifest=rewritten_manifest,
        dropped_artifact_language=dropped_artifact_language,
    )


def _exam_job_reason(*, manifest: Mapping[str, object], spec: Mapping[str, object]) -> str | None:
    source = spec.get("source")
    conversion = spec.get("conversion")
    source_formats = {manifest.get("source_format")}
    output_formats = {manifest.get("output_format")}
    if isinstance(source, Mapping):
        source_formats.add(source.get("format"))
    if isinstance(conversion, Mapping):
        output_formats.add(conversion.get("output_format"))
        if conversion.get("targets"):
            return "exam job: conversion.targets is set"
    if source_formats & RETIRED_SOURCE_FORMATS:
        return "exam job: retired source format"
    if output_formats & RETIRED_OUTPUT_FORMATS:
        return "exam job: retired output format"
    if spec.get("digiexam_migration_options") is not None:
        return "exam job: digiexam_migration_options is set"
    return None
