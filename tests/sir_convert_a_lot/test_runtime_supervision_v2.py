"""Focused tests for v2 runtime worker supervision.

Purpose:
    Prove the extracted supervisor starts queued jobs up to capacity while
    skipping already-active workers.

Relationships:
    - Tests `infrastructure.runtime_supervision_v2`.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import StoredJobRecordV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_supervision_v2 import RuntimeSupervisorV2


class _FakeSupervisorStore:
    def __init__(self, records: dict[str, StoredJobRecordV2]) -> None:
        self.records = records

    def sweep_expired(self) -> None:
        return None

    def recover_running_jobs_to_queued(self, *, active_job_ids: set[str]) -> list[str]:
        del active_job_ids
        return []

    def list_job_ids(self) -> list[str]:
        return list(self.records)

    def get_job(self, job_id: str) -> StoredJobRecordV2:
        return self.records[job_id]


def _spec(filename: str) -> JobSpecV2:
    return JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": filename, "format": "md"},
            "conversion": {"output_format": "pdf"},
            "retention": {"pin": False},
        }
    )


def _record(tmp_path: Path, *, job_id: str, status: JobStatus) -> StoredJobRecordV2:
    now = datetime.now(UTC)
    upload_path = tmp_path / f"{job_id}.md"
    artifact_path = tmp_path / f"{job_id}.pdf"
    return StoredJobRecordV2(
        job_id=job_id,
        spec=_spec(f"{job_id}.md"),
        owner_api_key_scope="service-api-key",
        source_filename=f"{job_id}.md",
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
        status=status,
        created_at=now,
        updated_at=now,
        completed_at=None,
        raw_expires_at=now,
        artifact_expires_at=now,
        pinned=False,
        progress_stage="queued",
        last_heartbeat_at=None,
        current_phase_started_at=None,
        phase_timings_ms={},
        total_pages=None,
        processed_pages=None,
        failed_pages=None,
        percent_complete=None,
        pages_per_minute=None,
        eta_seconds=None,
        warnings=[],
        upload_path=upload_path,
        resources_zip_path=None,
        reference_docx_path=None,
        artifact_path=artifact_path,
        artifact_sha256=None,
        artifact_size_bytes=None,
        pipeline_used=None,
        backend_used=None,
        acceleration_used=None,
        ocr_enabled=None,
        ocr_engine_used=None,
        ocr_languages_used=None,
        acceleration_policy_requested=None,
        gpu_runtime_kind=None,
        gpu_device_count=None,
        gpu_busy_percent=None,
        gpu_memory_used_percent=None,
        options_fingerprint=None,
        template_id=None,
        template_version=None,
        template_artifact_sha256=None,
        parallel_enabled=None,
        max_chunk_workers=None,
        chunk_size_pages=None,
        effective_gpu_stage_limit=None,
        scheduling_mode=None,
        failure_code=None,
        failure_message=None,
        failure_retryable=False,
        failure_details=None,
    )


def test_runtime_supervisor_starts_queued_jobs_until_capacity(tmp_path: Path) -> None:
    active_job_ids = {"job_active"}
    started: list[str] = []

    def _run_job_async(job_id: str) -> None:
        started.append(job_id)
        active_job_ids.add(job_id)

    supervisor = RuntimeSupervisorV2(
        config=ServiceConfig(api_key="secret-key", data_root=tmp_path),
        job_store=_FakeSupervisorStore(
            {
                "job_active": _record(tmp_path, job_id="job_active", status=JobStatus.QUEUED),
                "job_queued_a": _record(tmp_path, job_id="job_queued_a", status=JobStatus.QUEUED),
                "job_queued_b": _record(tmp_path, job_id="job_queued_b", status=JobStatus.QUEUED),
            }
        ),
        active_job_ids=active_job_ids,
        lock=threading.Lock(),
        shutdown_event=threading.Event(),
        run_job_async=_run_job_async,
        emit_capacity=lambda: None,
    )

    supervisor._start_queued_jobs_until_capacity(max_workers=2)

    assert started == ["job_queued_a"]
    assert active_job_ids == {"job_active", "job_queued_a"}
