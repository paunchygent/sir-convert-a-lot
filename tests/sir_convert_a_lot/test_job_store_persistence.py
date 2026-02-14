"""Durability tests for the filesystem job store.

Purpose:
    Ensure v1 job records and idempotency survive runtime restarts, and that
    expired jobs return a contract-consistent error code.

Relationships:
    - Exercises `infrastructure.runtime_engine.ServiceRuntime` with a real on-disk data root.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobSpec, JobStatus
from scripts.sir_convert_a_lot.infrastructure.runtime_engine import (
    ServiceConfig,
    ServiceError,
    ServiceRuntime,
)


def _spec(filename: str, *, pin: bool = False) -> JobSpec:
    return JobSpec.model_validate(
        {
            "api_version": "v1",
            "source": {"kind": "upload", "filename": filename},
            "conversion": {
                "output_format": "md",
                "backend_strategy": "auto",
                "ocr_mode": "auto",
                "table_mode": "fast",
                "normalize": "standard",
            },
            "execution": {
                "acceleration_policy": "gpu_required",
                "priority": "normal",
                "document_timeout_seconds": 1800,
            },
            "retention": {"pin": pin},
        }
    )


def _pdf_bytes(label: str) -> bytes:
    return f"%PDF-1.4\n% {label}\n%%EOF\n".encode("utf-8")


def test_idempotency_survives_runtime_restart(tmp_path: Path) -> None:
    data_root = tmp_path / "service_data"
    config = ServiceConfig(
        api_key="k",
        data_root=data_root,
        processing_delay_seconds=0.0,
        enable_supervisor=False,
    )

    runtime = ServiceRuntime(config)
    job = runtime.create_job(_spec("paper.pdf"), _pdf_bytes("x"), "paper.pdf")

    scope_key = "k:POST:/v1/convert/jobs:idem-key"
    runtime.put_idempotency(scope_key, fingerprint="fp1", job_id=job.job_id)
    assert runtime.get_idempotency(scope_key) is not None

    restarted = ServiceRuntime(config)
    record = restarted.get_idempotency(scope_key)
    assert record is not None
    assert record.job_id == job.job_id
    assert record.fingerprint == "fp1"


def test_running_job_is_recovered_to_queued_on_restart(tmp_path: Path) -> None:
    data_root = tmp_path / "service_data"
    config = ServiceConfig(
        api_key="k", data_root=data_root, processing_delay_seconds=0.0, enable_supervisor=False
    )

    runtime = ServiceRuntime(config)
    job = runtime.create_job(_spec("paper.pdf"), _pdf_bytes("x"), "paper.pdf")
    runtime._set_job_status(job.job_id, status=JobStatus.RUNNING, stage="starting")

    restarted = ServiceRuntime(config)
    recovered = restarted.get_job(job.job_id)
    assert recovered is not None
    assert recovered.status.value == "queued"


def test_expired_job_returns_job_expired_error_code(tmp_path: Path) -> None:
    data_root = tmp_path / "service_data"
    config = ServiceConfig(
        api_key="k",
        data_root=data_root,
        processing_delay_seconds=0.0,
        result_ttl_seconds=1,
        upload_ttl_seconds=1,
        enable_supervisor=False,
    )

    runtime = ServiceRuntime(config)
    job = runtime.create_job(_spec("paper.pdf"), _pdf_bytes("x"), "paper.pdf")

    manifest_path = data_root / "jobs" / job.job_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    retention = payload.get("retention")
    assert isinstance(retention, dict)
    retention["artifact_expires_at"] = "2000-01-01T00:00:00Z"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ServiceError) as excinfo:
        runtime.get_job(job.job_id)
    assert excinfo.value.code == "job_expired"


def test_pinned_job_is_exempt_from_expiry(tmp_path: Path) -> None:
    data_root = tmp_path / "service_data"
    config = ServiceConfig(
        api_key="k",
        data_root=data_root,
        processing_delay_seconds=0.0,
        result_ttl_seconds=1,
        upload_ttl_seconds=1,
        enable_supervisor=False,
    )

    runtime = ServiceRuntime(config)
    job = runtime.create_job(_spec("paper.pdf", pin=True), _pdf_bytes("x"), "paper.pdf")

    manifest_path = data_root / "jobs" / job.job_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    retention = payload.get("retention")
    assert isinstance(retention, dict)
    retention["artifact_expires_at"] = "2000-01-01T00:00:00Z"
    retention["raw_expires_at"] = "2000-01-01T00:00:00Z"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    loaded = runtime.get_job(job.job_id)
    assert loaded is not None
    assert loaded.expires_at is None


def test_sweeper_deletes_raw_after_raw_ttl_but_keeps_job(tmp_path: Path) -> None:
    data_root = tmp_path / "service_data"
    config = ServiceConfig(
        api_key="k", data_root=data_root, processing_delay_seconds=0.0, enable_supervisor=False
    )

    runtime = ServiceRuntime(config)
    job = runtime.create_job(_spec("paper.pdf"), _pdf_bytes("x"), "paper.pdf")

    manifest_path = data_root / "jobs" / job.job_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    retention = payload.get("retention")
    assert isinstance(retention, dict)
    retention["raw_expires_at"] = "2000-01-01T00:00:00Z"
    retention["artifact_expires_at"] = "2999-01-01T00:00:00Z"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    runtime.job_store.sweep_expired()

    raw_path = data_root / "jobs" / job.job_id / "raw" / "input.pdf"
    assert not raw_path.exists()

    loaded = runtime.get_job(job.job_id)
    assert loaded is not None
    assert loaded.status.value == "queued"


def test_run_job_clears_active_slot_when_job_missing(tmp_path: Path) -> None:
    data_root = tmp_path / "service_data"
    config = ServiceConfig(
        api_key="k",
        data_root=data_root,
        processing_delay_seconds=0.0,
        enable_supervisor=False,
    )
    runtime = ServiceRuntime(config)

    job_id = "job_missing"
    runtime._active_job_ids.add(job_id)
    runtime._run_job(job_id)
    assert job_id not in runtime._active_job_ids
