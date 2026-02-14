"""Filesystem-backed job store for Sir Convert-a-Lot v1.

Purpose:
    Provide a durable, contract-aligned job persistence layer for the v1 async
    conversion API. The job store is the source of truth for job status, job
    metadata, retention, and recovery after service restarts.

Relationships:
    - Used by `infrastructure.runtime_engine.ServiceRuntime` as the canonical job state store.
    - Storage layout is aligned with `docs/converters/pdf_to_md_service_api_v1.md`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _atomic_write_json(path: Path, payload: dict[str, object]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return payload


def _dt_to_rfc3339(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dt_from_rfc3339(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid datetime value: {value!r}")
    # Python 3.11 accepts Z with fromisoformat only after normalization.
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).astimezone(UTC)


@dataclass(frozen=True)
class StoredJobRecord:
    """Durable job record loaded from the filesystem journal."""

    job_id: str
    spec: JobSpec
    source_filename: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    raw_expires_at: datetime
    artifact_expires_at: datetime
    pinned: bool
    progress_stage: str
    pages_total: int | None
    pages_processed: int | None
    warnings: list[str]
    artifact_path: Path
    upload_path: Path
    artifact_sha256: str | None
    artifact_size_bytes: int | None
    backend_used: str | None
    acceleration_used: str | None
    options_fingerprint: str | None
    failure_code: str | None
    failure_message: str | None
    failure_retryable: bool
    failure_details: dict[str, object] | None

    @property
    def expires_at(self) -> datetime | None:
        # v1 API exposes a single expires_at; use artifact expiry as the canonical
        # "job visible" TTL.
        return None if self.pinned else self.artifact_expires_at


class JobStore:
    """Filesystem-backed store for v1 conversion jobs."""

    def __init__(
        self,
        *,
        data_root: Path,
        raw_ttl_seconds: int,
        artifact_ttl_seconds: int,
        tombstone_ttl_seconds: int = 30 * 24 * 3600,
    ) -> None:
        self.data_root = data_root
        self.jobs_dir = data_root / "jobs"
        self.expired_dir = data_root / "expired"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.expired_dir.mkdir(parents=True, exist_ok=True)
        self.raw_ttl_seconds = raw_ttl_seconds
        self.artifact_ttl_seconds = artifact_ttl_seconds
        self.tombstone_ttl_seconds = tombstone_ttl_seconds

    def _job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def _manifest_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "manifest.json"

    def _raw_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "raw" / "input.pdf"

    def _artifact_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "artifacts" / "output.md"

    def _log_path(self, job_id: str) -> Path:
        return self._job_dir(job_id) / "logs" / "run.log"

    def _tombstone_path(self, job_id: str) -> Path:
        return self.expired_dir / f"{job_id}.json"

    def create_job(
        self,
        *,
        job_id: str,
        spec: JobSpec,
        source_filename: str,
        upload_bytes: bytes,
    ) -> StoredJobRecord:
        now = _utc_now()

        job_dir = self._job_dir(job_id)
        (job_dir / "raw").mkdir(parents=True, exist_ok=True)
        (job_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_dir / "logs").mkdir(parents=True, exist_ok=True)

        upload_path = self._raw_path(job_id)
        self._artifact_path(job_id)
        log_path = self._log_path(job_id)

        upload_path.write_bytes(upload_bytes)
        log_path.write_text("", encoding="utf-8")

        pinned = bool(spec.retention.pin)
        raw_expires_at = now + timedelta(seconds=self.raw_ttl_seconds)
        artifact_expires_at = now + timedelta(seconds=self.artifact_ttl_seconds)

        manifest: dict[str, object] = {
            "job_id": job_id,
            "job_spec": spec.model_dump(mode="json"),
            "status": JobStatus.QUEUED.value,
            "source_filename": source_filename,
            "progress": {"stage": "queued", "pages_total": None, "pages_processed": None},
            "timestamps": {
                "created_at": _dt_to_rfc3339(now),
                "updated_at": _dt_to_rfc3339(now),
                "completed_at": None,
            },
            "retention": {
                "pinned": pinned,
                "raw_expires_at": _dt_to_rfc3339(raw_expires_at),
                "artifact_expires_at": _dt_to_rfc3339(artifact_expires_at),
            },
            "result_metadata": None,
            "error": None,
        }
        _atomic_write_json(self._manifest_path(job_id), manifest)

        return self.get_job(job_id)

    def get_job(self, job_id: str) -> StoredJobRecord:
        manifest_path = self._manifest_path(job_id)
        if not manifest_path.exists():
            tombstone = self._tombstone_path(job_id)
            if tombstone.exists():
                raise JobExpired(job_id=job_id)
            raise JobMissing(job_id=job_id)

        payload = _read_json(manifest_path)
        job_id_obj = payload.get("job_id")
        if job_id_obj != job_id:
            raise ValueError(f"manifest job_id mismatch: {manifest_path}")

        spec_payload = payload.get("job_spec")
        if not isinstance(spec_payload, dict):
            raise ValueError(f"manifest missing job_spec object: {manifest_path}")
        spec = JobSpec.model_validate(spec_payload)

        status_value = payload.get("status")
        if not isinstance(status_value, str):
            raise ValueError(f"manifest missing status: {manifest_path}")
        status = JobStatus(status_value)

        timestamps = payload.get("timestamps")
        if not isinstance(timestamps, dict):
            raise ValueError(f"manifest missing timestamps: {manifest_path}")
        created_at = _dt_from_rfc3339(timestamps.get("created_at"))
        updated_at = _dt_from_rfc3339(timestamps.get("updated_at"))
        completed_at = _dt_from_rfc3339(timestamps.get("completed_at"))
        if created_at is None or updated_at is None:
            raise ValueError(f"manifest missing required timestamps: {manifest_path}")

        retention = payload.get("retention")
        if not isinstance(retention, dict):
            raise ValueError(f"manifest missing retention object: {manifest_path}")
        pinned_obj = retention.get("pinned")
        pinned = bool(pinned_obj) if isinstance(pinned_obj, bool) else False
        raw_expires_at = _dt_from_rfc3339(retention.get("raw_expires_at"))
        artifact_expires_at = _dt_from_rfc3339(retention.get("artifact_expires_at"))
        if raw_expires_at is None or artifact_expires_at is None:
            raise ValueError(f"manifest missing retention timestamps: {manifest_path}")

        source_filename = payload.get("source_filename")
        if not isinstance(source_filename, str) or source_filename.strip() == "":
            raise ValueError(f"manifest missing source_filename: {manifest_path}")

        progress = payload.get("progress")
        if not isinstance(progress, dict):
            raise ValueError(f"manifest missing progress: {manifest_path}")
        stage_obj = progress.get("stage")
        stage = stage_obj if isinstance(stage_obj, str) else "unknown"
        pages_total = progress.get("pages_total")
        pages_processed = progress.get("pages_processed")
        pages_total_val = pages_total if isinstance(pages_total, int) else None
        pages_processed_val = pages_processed if isinstance(pages_processed, int) else None

        result_obj = payload.get("result_metadata")
        error_obj = payload.get("error")

        warnings: list[str] = []
        artifact_sha256: str | None = None
        artifact_size_bytes: int | None = None
        backend_used: str | None = None
        acceleration_used: str | None = None
        options_fingerprint: str | None = None
        failure_code: str | None = None
        failure_message: str | None = None
        failure_retryable = False
        failure_details: dict[str, object] | None = None

        if isinstance(result_obj, dict):
            warnings_obj = result_obj.get("warnings")
            if isinstance(warnings_obj, list):
                warnings = [w for w in warnings_obj if isinstance(w, str)]

            artifact_obj = result_obj.get("artifact")
            if isinstance(artifact_obj, dict):
                sha_obj = artifact_obj.get("sha256")
                size_obj = artifact_obj.get("size_bytes")
                artifact_sha256 = sha_obj if isinstance(sha_obj, str) else None
                artifact_size_bytes = size_obj if isinstance(size_obj, int) else None

            meta_obj = result_obj.get("conversion_metadata")
            if isinstance(meta_obj, dict):
                backend_obj = meta_obj.get("backend_used")
                accel_obj = meta_obj.get("acceleration_used")
                options_obj = meta_obj.get("options_fingerprint")
                backend_used = backend_obj if isinstance(backend_obj, str) else None
                acceleration_used = accel_obj if isinstance(accel_obj, str) else None
                options_fingerprint = options_obj if isinstance(options_obj, str) else None

        if isinstance(error_obj, dict):
            code_obj = error_obj.get("code")
            message_obj = error_obj.get("message")
            retryable_obj = error_obj.get("retryable")
            details_obj = error_obj.get("details")
            failure_code = code_obj if isinstance(code_obj, str) else None
            failure_message = message_obj if isinstance(message_obj, str) else None
            failure_retryable = retryable_obj if isinstance(retryable_obj, bool) else False
            failure_details = details_obj if isinstance(details_obj, dict) else None

        record = StoredJobRecord(
            job_id=job_id,
            spec=spec,
            source_filename=source_filename,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            completed_at=completed_at,
            raw_expires_at=raw_expires_at,
            artifact_expires_at=artifact_expires_at,
            pinned=pinned,
            progress_stage=stage,
            pages_total=pages_total_val,
            pages_processed=pages_processed_val,
            warnings=warnings,
            upload_path=self._raw_path(job_id),
            artifact_path=self._artifact_path(job_id),
            artifact_sha256=artifact_sha256,
            artifact_size_bytes=artifact_size_bytes,
            backend_used=backend_used,
            acceleration_used=acceleration_used,
            options_fingerprint=options_fingerprint,
            failure_code=failure_code,
            failure_message=failure_message,
            failure_retryable=failure_retryable,
            failure_details=failure_details,
        )

        now = _utc_now()
        if not record.pinned and now > record.artifact_expires_at:
            # Job exists but is expired.
            raise JobExpired(job_id=job_id)

        return record

    def update_progress(
        self,
        job_id: str,
        *,
        status: JobStatus,
        stage: str,
        pages_processed: int | None = None,
        pages_total: int | None = None,
    ) -> StoredJobRecord:
        manifest_path = self._manifest_path(job_id)
        payload = _read_json(manifest_path)
        now = _utc_now()

        payload["status"] = status.value
        progress = payload.get("progress")
        if not isinstance(progress, dict):
            progress = {}
            payload["progress"] = progress
        progress["stage"] = stage
        if pages_processed is not None:
            progress["pages_processed"] = pages_processed
        if pages_total is not None:
            progress["pages_total"] = pages_total

        timestamps = payload.get("timestamps")
        if not isinstance(timestamps, dict):
            timestamps = {}
            payload["timestamps"] = timestamps
        timestamps["updated_at"] = _dt_to_rfc3339(now)

        _atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

    def mark_succeeded(
        self,
        job_id: str,
        *,
        markdown_bytes: bytes,
        backend_used: str,
        acceleration_used: str,
        options_fingerprint: str,
        warnings: list[str],
    ) -> StoredJobRecord:
        artifact_path = self._artifact_path(job_id)
        artifact_path.write_bytes(markdown_bytes)
        sha = hashlib.sha256(markdown_bytes).hexdigest()

        manifest_path = self._manifest_path(job_id)
        payload = _read_json(manifest_path)
        now = _utc_now()

        payload["status"] = JobStatus.SUCCEEDED.value
        timestamps = payload.get("timestamps")
        if not isinstance(timestamps, dict):
            timestamps = {}
            payload["timestamps"] = timestamps
        timestamps["updated_at"] = _dt_to_rfc3339(now)
        timestamps["completed_at"] = _dt_to_rfc3339(now)

        payload["error"] = None
        payload["result_metadata"] = {
            "artifact": {
                "markdown_filename": artifact_path.name,
                "size_bytes": len(markdown_bytes),
                "sha256": sha,
            },
            "conversion_metadata": {
                "backend_used": backend_used,
                "acceleration_used": acceleration_used,
                "options_fingerprint": options_fingerprint,
            },
            "warnings": list(warnings),
        }

        _atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

    def mark_failed(
        self,
        job_id: str,
        *,
        code: str,
        message: str,
        retryable: bool,
        details: dict[str, object] | None,
    ) -> StoredJobRecord:
        manifest_path = self._manifest_path(job_id)
        payload = _read_json(manifest_path)
        now = _utc_now()

        payload["status"] = JobStatus.FAILED.value
        timestamps = payload.get("timestamps")
        if not isinstance(timestamps, dict):
            timestamps = {}
            payload["timestamps"] = timestamps
        timestamps["updated_at"] = _dt_to_rfc3339(now)
        timestamps["completed_at"] = _dt_to_rfc3339(now)

        payload["result_metadata"] = None
        payload["error"] = {
            "code": code,
            "message": message,
            "retryable": retryable,
            "details": details,
        }

        _atomic_write_json(manifest_path, payload)
        return self.get_job(job_id)

    def mark_canceled(self, job_id: str) -> StoredJobRecord:
        return self.update_progress(job_id, status=JobStatus.CANCELED, stage="canceled")

    def list_job_ids(self) -> list[str]:
        return sorted(path.name for path in self.jobs_dir.iterdir() if path.is_dir())

    def recover_running_jobs_to_queued(self, *, active_job_ids: set[str]) -> list[str]:
        """Convert orphaned running jobs to queued.

        This is deterministic and safe on startup because no worker processes are tracked in v1.
        """
        recovered: list[str] = []
        for job_id in self.list_job_ids():
            if job_id in active_job_ids:
                continue
            try:
                record = self.get_job(job_id)
            except (JobMissing, JobExpired):
                continue
            if record.status == JobStatus.RUNNING:
                self.update_progress(job_id, status=JobStatus.QUEUED, stage="queued")
                recovered.append(job_id)
        return recovered

    def sweep_expired(self) -> None:
        """Sweep expired jobs and retain tombstones so the API can return job_expired."""
        now = _utc_now()

        # Expire old tombstones.
        tombstone_ttl = timedelta(seconds=self.tombstone_ttl_seconds)
        for tombstone in self.expired_dir.glob("*.json"):
            try:
                payload = _read_json(tombstone)
                expired_at = _dt_from_rfc3339(payload.get("expired_at"))
            except Exception:
                continue
            if expired_at is not None and now - expired_at > tombstone_ttl:
                tombstone.unlink(missing_ok=True)

        for job_id in self.list_job_ids():
            manifest_path = self._manifest_path(job_id)
            if not manifest_path.exists():
                continue
            try:
                record = self.get_job(job_id)
            except JobExpired:
                # Create/refresh tombstone and remove directory contents.
                tombstone_payload: dict[str, object] = {
                    "job_id": job_id,
                    "expired_at": _dt_to_rfc3339(now),
                }
                _atomic_write_json(self._tombstone_path(job_id), tombstone_payload)
                # Remove job directory (best-effort).
                for child in self._job_dir(job_id).rglob("*"):
                    if child.is_file():
                        child.unlink(missing_ok=True)
                for child in sorted(self._job_dir(job_id).rglob("*"), reverse=True):
                    if child.is_dir():
                        try:
                            child.rmdir()
                        except OSError:
                            pass
                try:
                    self._job_dir(job_id).rmdir()
                except OSError:
                    pass
                continue
            except JobMissing:
                continue

            if record.pinned:
                continue

            if now > record.raw_expires_at:
                raw_dir = self._job_dir(job_id) / "raw"
                if raw_dir.exists():
                    for child in raw_dir.rglob("*"):
                        if child.is_file():
                            child.unlink(missing_ok=True)
                    for child in sorted(raw_dir.rglob("*"), reverse=True):
                        if child.is_dir():
                            try:
                                child.rmdir()
                            except OSError:
                                pass
                    try:
                        raw_dir.rmdir()
                    except OSError:
                        pass


@dataclass(frozen=True)
class IdempotencyRecord:
    """Durable idempotency record for create-job replay and collision behavior."""

    fingerprint: str
    job_id: str
    created_at: datetime


class IdempotencyStore:
    """Filesystem-backed idempotency store."""

    def __init__(self, *, data_root: Path, ttl_seconds: int) -> None:
        self.dir = data_root / "idempotency"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(seconds=ttl_seconds)

    def _path_for_scope(self, scope_key: str) -> Path:
        digest = hashlib.sha256(scope_key.encode("utf-8")).hexdigest()
        return self.dir / f"{digest}.json"

    def get(self, scope_key: str) -> IdempotencyRecord | None:
        path = self._path_for_scope(scope_key)
        if not path.exists():
            return None
        payload = _read_json(path)
        fingerprint = payload.get("fingerprint")
        job_id = payload.get("job_id")
        created_at = _dt_from_rfc3339(payload.get("created_at"))
        if not isinstance(fingerprint, str) or not isinstance(job_id, str) or created_at is None:
            return None
        if _utc_now() - created_at > self.ttl:
            path.unlink(missing_ok=True)
            return None
        return IdempotencyRecord(fingerprint=fingerprint, job_id=job_id, created_at=created_at)

    def put(self, scope_key: str, fingerprint: str, job_id: str) -> None:
        payload: dict[str, object] = {
            "fingerprint": fingerprint,
            "job_id": job_id,
            "created_at": _dt_to_rfc3339(_utc_now()),
        }
        _atomic_write_json(self._path_for_scope(scope_key), payload)


@dataclass(frozen=True)
class JobMissing(Exception):
    job_id: str


@dataclass(frozen=True)
class JobExpired(Exception):
    job_id: str
