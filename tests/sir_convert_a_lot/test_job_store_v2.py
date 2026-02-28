"""Job-store v2 housekeeping branch coverage tests.

Purpose:
    Validate v2 recovery and sweeping behavior for active/orphaned running
    jobs, tombstone lifecycle cleanup, and raw-directory expiration handling.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.job_store_v2`.
    - Complements persistence and cancellation CAS tests in existing v2 suites.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import JobExpiredV2, JobMissingV2
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2


def _md_to_pdf_spec(*, filename: str, pin: bool = False) -> JobSpecV2:
    return JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": filename, "format": "md"},
            "conversion": {
                "output_format": "pdf",
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "retention": {"pin": pin},
        }
    )


def _set_retention(
    *,
    store: JobStoreV2,
    job_id: str,
    raw_expires_at: str,
    artifact_expires_at: str,
) -> None:
    manifest_path = store._manifest_path(job_id)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    retention = payload.get("retention")
    assert isinstance(retention, dict)
    retention["raw_expires_at"] = raw_expires_at
    retention["artifact_expires_at"] = artifact_expires_at
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def test_recover_running_jobs_to_queued_recovers_only_orphaned_running_jobs(
    tmp_path: Path,
) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )

    store.create_job(
        job_id="jobv2_running_active",
        spec=_md_to_pdf_spec(filename="active.md"),
        upload_bytes=b"# Active\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    store.create_job(
        job_id="jobv2_running_orphan",
        spec=_md_to_pdf_spec(filename="orphan.md"),
        upload_bytes=b"# Orphan\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    store.create_job(
        job_id="jobv2_queued",
        spec=_md_to_pdf_spec(filename="queued.md"),
        upload_bytes=b"# Queued\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )

    assert store.claim_queued_job("jobv2_running_active") is True
    assert store.claim_queued_job("jobv2_running_orphan") is True

    recovered = store.recover_running_jobs_to_queued(active_job_ids={"jobv2_running_active"})

    assert recovered == ["jobv2_running_orphan"]
    assert store.get_job("jobv2_running_active").status == JobStatus.RUNNING
    assert store.get_job("jobv2_running_orphan").status == JobStatus.QUEUED
    assert store.get_job("jobv2_queued").status == JobStatus.QUEUED


def test_sweep_expired_creates_and_cleans_tombstones(tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
        tombstone_ttl_seconds=1,
    )

    job_id = "jobv2_expired_tombstone"
    store.create_job(
        job_id=job_id,
        spec=_md_to_pdf_spec(filename="expired.md"),
        upload_bytes=b"# Expired\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    _set_retention(
        store=store,
        job_id=job_id,
        raw_expires_at="2000-01-01T00:00:00Z",
        artifact_expires_at="2000-01-01T00:00:00Z",
    )

    store.sweep_expired()

    job_dir = store.jobs_dir / job_id
    tombstone_path = store._tombstone_path(job_id)
    assert not job_dir.exists()
    assert tombstone_path.exists()
    with pytest.raises(JobExpiredV2):
        store.get_job(job_id)

    tombstone_payload = json.loads(tombstone_path.read_text(encoding="utf-8"))
    assert isinstance(tombstone_payload, dict)
    tombstone_payload["expired_at"] = "2000-01-01T00:00:00Z"
    tombstone_path.write_text(
        json.dumps(tombstone_payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    store.sweep_expired()

    assert not tombstone_path.exists()
    with pytest.raises(JobMissingV2):
        store.get_job(job_id)


def test_sweep_expired_removes_raw_dir_after_raw_ttl_only(tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )

    job_id = "jobv2_raw_cleanup"
    store.create_job(
        job_id=job_id,
        spec=_md_to_pdf_spec(filename="raw.md"),
        upload_bytes=b"# Raw cleanup\n",
        resources_zip_bytes=b"fake zip bytes",
        reference_docx_bytes=None,
    )
    _set_retention(
        store=store,
        job_id=job_id,
        raw_expires_at="2000-01-01T00:00:00Z",
        artifact_expires_at="2999-01-01T00:00:00Z",
    )

    raw_dir = store._job_dir(job_id) / "raw"
    assert raw_dir.exists()

    store.sweep_expired()

    assert not raw_dir.exists()
    remaining = store.get_job(job_id)
    assert remaining.status == JobStatus.QUEUED


def test_sweep_expired_ignores_malformed_tombstone_payload(tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
        tombstone_ttl_seconds=1,
    )
    malformed_tombstone = store.expired_dir / "jobv2_malformed_tombstone.json"
    malformed_tombstone.write_text(
        json.dumps({"job_id": "jobv2_malformed_tombstone", "expired_at": 123}),
        encoding="utf-8",
    )

    store.sweep_expired()

    assert malformed_tombstone.exists()


def test_sweep_expired_keeps_raw_files_for_pinned_jobs(tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )

    job_id = "jobv2_pinned_raw_kept"
    store.create_job(
        job_id=job_id,
        spec=_md_to_pdf_spec(filename="pinned.md", pin=True),
        upload_bytes=b"# Pinned\n",
        resources_zip_bytes=b"fake zip bytes",
        reference_docx_bytes=None,
    )
    _set_retention(
        store=store,
        job_id=job_id,
        raw_expires_at="2000-01-01T00:00:00Z",
        artifact_expires_at="2999-01-01T00:00:00Z",
    )

    raw_dir = store._job_dir(job_id) / "raw"
    assert raw_dir.exists()

    store.sweep_expired()

    assert raw_dir.exists()
    assert store.get_job(job_id).pinned is True


def test_sweep_expired_skips_jobs_without_manifest(tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )

    orphan_job_id = "jobv2_missing_manifest"
    orphan_raw = store._job_dir(orphan_job_id) / "raw"
    orphan_raw.mkdir(parents=True, exist_ok=True)
    orphan_input = orphan_raw / "input.md"
    orphan_input.write_text("# Orphan without manifest\n", encoding="utf-8")
    assert not store._manifest_path(orphan_job_id).exists()

    store.sweep_expired()

    assert orphan_input.exists()
    assert store._job_dir(orphan_job_id).exists()
