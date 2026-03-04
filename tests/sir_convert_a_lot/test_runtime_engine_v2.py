"""Runtime-engine v2 branch coverage tests.

Purpose:
    Exercise key v2 runtime control-flow branches for cancel outcomes,
    async deduplication, and failure classification during job execution.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2`.
    - Uses the real filesystem-backed `JobStoreV2` via `ServiceRuntimeV2`.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2
from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
    JobStateConflictV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import V2ExecutionResult


class _NoopJoinThread:
    """Minimal thread-like stub with a compatible join API."""

    def join(self, timeout: float | None = None) -> None:
        del timeout


def _runtime_config(
    data_root: Path,
    *,
    enable_supervisor: bool = False,
    supervisor_poll_seconds: float = 0.2,
    processing_delay_seconds: float = 0.0,
) -> ServiceConfig:
    return ServiceConfig(
        api_key="secret-key",
        data_root=data_root,
        enable_supervisor=enable_supervisor,
        supervisor_poll_seconds=supervisor_poll_seconds,
        processing_delay_seconds=processing_delay_seconds,
    )


def _md_to_pdf_spec(*, filename: str) -> JobSpecV2:
    return JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": filename, "format": "md"},
            "conversion": {
                "output_format": "pdf",
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "retention": {"pin": False},
        }
    )


def test_create_job_raises_when_immediate_readback_is_missing(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(runtime, "get_job", lambda _job_id: None)

    with pytest.raises(RuntimeError, match="created v2 job must be loadable immediately"):
        runtime.create_job(
            spec=_md_to_pdf_spec(filename="missing-readback.md"),
            upload_bytes=b"# Missing readback\n",
            resources_zip_bytes=None,
            reference_docx_bytes=None,
        )


def test_get_job_maps_job_expired_to_service_error(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(runtime.job_store, "sweep_expired", lambda: None)

    def _raise_expired(job_id: str):
        raise JobExpiredV2(job_id=job_id)

    monkeypatch.setattr(runtime.job_store, "get_job", _raise_expired)

    with pytest.raises(ServiceError) as excinfo:
        runtime.get_job("jobv2_expired")

    error = excinfo.value
    assert error.status_code == 404
    assert error.code == "job_expired"
    assert error.retryable is False
    assert error.details == {"job_id": "jobv2_expired"}


def test_shutdown_returns_early_without_supervisor(tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))

    assert runtime._supervisor_thread is None
    runtime.shutdown()

    assert runtime._shutdown_event.is_set()


def test_shutdown_skips_join_for_dead_supervisor(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    dead_supervisor = threading.Thread(target=lambda: None, daemon=True)
    join_called = False

    def _record_join(timeout: float | None = None) -> None:
        nonlocal join_called
        del timeout
        join_called = True

    monkeypatch.setattr(dead_supervisor, "join", _record_join)
    runtime._supervisor_thread = dead_supervisor

    runtime.shutdown()

    assert runtime._shutdown_event.is_set()
    assert join_called is False


def test_shutdown_joins_alive_supervisor_with_expected_timeout(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(
        _runtime_config(tmp_path / "service_data", supervisor_poll_seconds=0.4)
    )
    release_supervisor = threading.Event()
    alive_supervisor = threading.Thread(target=release_supervisor.wait, daemon=True)
    alive_supervisor.start()
    join_calls: list[float | None] = []
    original_join = alive_supervisor.join

    def _record_join(timeout: float | None = None) -> None:
        join_calls.append(timeout)
        release_supervisor.set()
        original_join(timeout)

    monkeypatch.setattr(alive_supervisor, "join", _record_join)
    runtime._supervisor_thread = alive_supervisor

    runtime.shutdown()

    assert runtime._shutdown_event.is_set()
    assert len(join_calls) == 1
    assert join_calls[0] == pytest.approx(1.6)


@pytest.mark.parametrize(
    ("raised_error", "expected_outcome"),
    [
        (JobMissingV2(job_id="jobv2_cancel"), "missing"),
        (JobExpiredV2(job_id="jobv2_cancel"), "missing"),
        (
            JobStateConflictV2(
                job_id="jobv2_cancel",
                expected_statuses=(JobStatus.QUEUED, JobStatus.RUNNING),
                actual_status=JobStatus.SUCCEEDED,
            ),
            "conflict",
        ),
    ],
)
def test_cancel_job_maps_mark_canceled_errors(
    monkeypatch, tmp_path: Path, raised_error: Exception, expected_outcome: str
) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(
        runtime, "get_job", lambda _job_id: SimpleNamespace(status=JobStatus.QUEUED)
    )

    def _raise_error(_job_id: str):
        raise raised_error

    monkeypatch.setattr(runtime.job_store, "mark_canceled", _raise_error)

    assert runtime.cancel_job("jobv2_cancel") == expected_outcome


def test_run_job_returns_early_when_claim_fails(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(runtime.job_store, "claim_queued_job", lambda _job_id: False)

    def _unexpected_get_job(_job_id: str) -> None:
        raise AssertionError("get_job should not be called when claim_queued_job returns False")

    monkeypatch.setattr(runtime, "get_job", _unexpected_get_job)

    runtime._run_job("jobv2_claim_false")


def test_run_job_returns_early_when_job_missing_after_claim(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(runtime.job_store, "claim_queued_job", lambda _job_id: True)
    monkeypatch.setattr(runtime, "get_job", lambda _job_id: None)

    def _unexpected_update_progress(*args, **kwargs) -> None:
        del args, kwargs
        raise AssertionError("update_progress should not run when job disappears after claim")

    monkeypatch.setattr(runtime.job_store, "update_progress", _unexpected_update_progress)

    runtime._run_job("jobv2_missing_after_claim")


def test_run_job_returns_early_when_job_is_canceled_after_delay(
    monkeypatch, tmp_path: Path
) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(runtime.job_store, "claim_queued_job", lambda _job_id: True)

    get_job_responses = iter(
        [
            SimpleNamespace(status=JobStatus.QUEUED),
            SimpleNamespace(status=JobStatus.CANCELED),
        ]
    )
    monkeypatch.setattr(runtime, "get_job", lambda _job_id: next(get_job_responses))

    def _unexpected_update_progress(*args, **kwargs) -> None:
        del args, kwargs
        raise AssertionError("update_progress should not run for canceled jobs")

    monkeypatch.setattr(runtime.job_store, "update_progress", _unexpected_update_progress)

    runtime._run_job("jobv2_canceled_after_delay")


def test_run_job_returns_when_mark_succeeded_conflicts(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    monkeypatch.setattr(runtime.job_store, "claim_queued_job", lambda _job_id: True)

    get_job_responses = iter(
        [
            SimpleNamespace(status=JobStatus.QUEUED, source_format=SourceFormatV2.MD),
            SimpleNamespace(status=JobStatus.RUNNING, source_format=SourceFormatV2.MD),
        ]
    )
    monkeypatch.setattr(runtime, "get_job", lambda _job_id: next(get_job_responses))
    monkeypatch.setattr(runtime.job_store, "update_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime.job_store, "touch_heartbeat", lambda _job_id: True)
    monkeypatch.setattr(
        runtime_engine_v2,
        "start_conversion_heartbeat_v2",
        lambda **kwargs: (threading.Event(), _NoopJoinThread()),
    )
    monkeypatch.setattr(
        runtime_engine_v2,
        "execute_v2_job_conversion",
        lambda **kwargs: V2ExecutionResult(
            artifact_bytes=b"%PDF-1.4\n",
            pipeline_used="md_to_pdf_v2",
            backend_used="pandoc+weasyprint",
            acceleration_used=None,
            warnings=[],
            phase_timings_ms={},
            options_fingerprint="f00d",
        ),
    )

    def _raise_conflict(*args, **kwargs) -> None:
        del args, kwargs
        raise JobStateConflictV2(
            job_id="jobv2_mark_succeeded_conflict",
            expected_statuses=(JobStatus.RUNNING,),
            actual_status=JobStatus.CANCELED,
        )

    monkeypatch.setattr(runtime.job_store, "mark_succeeded", _raise_conflict)

    mark_failed_called = False

    def _mark_failed(*args, **kwargs) -> None:
        nonlocal mark_failed_called
        del args, kwargs
        mark_failed_called = True

    monkeypatch.setattr(runtime.job_store, "mark_failed", _mark_failed)

    runtime._run_job("jobv2_mark_succeeded_conflict")

    assert mark_failed_called is False


def test_cancel_job_returns_all_expected_outcomes(tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))

    assert runtime.cancel_job("jobv2_missing") == "missing"

    cancelable = runtime.create_job(
        spec=_md_to_pdf_spec(filename="cancelable.md"),
        upload_bytes=b"# Cancel me\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    assert runtime.cancel_job(cancelable.job_id) == "accepted"
    canceled = runtime.get_job(cancelable.job_id)
    assert canceled is not None
    assert canceled.status == JobStatus.CANCELED
    assert runtime.cancel_job(cancelable.job_id) == "already_canceled"

    terminal = runtime.create_job(
        spec=_md_to_pdf_spec(filename="terminal.md"),
        upload_bytes=b"# Terminal\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    assert runtime.job_store.claim_queued_job(terminal.job_id) is True
    runtime.job_store.mark_failed(
        terminal.job_id,
        code="forced_failure",
        message="forced terminal state for branch test",
        retryable=False,
        details=None,
        phase_timings_ms={},
    )
    assert runtime.cancel_job(terminal.job_id) == "conflict"


def test_run_job_async_deduplicates_active_job_id(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    run_started = threading.Event()
    release_run = threading.Event()
    call_count = 0

    def _fake_run_job(job_id: str) -> None:
        nonlocal call_count
        call_count += 1
        run_started.set()
        release_run.wait(timeout=2.0)
        with runtime._lock:
            runtime._active_job_ids.discard(job_id)

    monkeypatch.setattr(runtime, "_run_job", _fake_run_job)

    runtime.run_job_async("jobv2_duplicate_check")
    assert run_started.wait(timeout=1.0)
    runtime.run_job_async("jobv2_duplicate_check")
    time.sleep(0.05)
    release_run.set()

    deadline = time.monotonic() + 1.0
    while "jobv2_duplicate_check" in runtime._active_job_ids and time.monotonic() < deadline:
        time.sleep(0.01)

    assert call_count == 1


def test_run_job_marks_failed_when_executor_raises_service_error(
    monkeypatch, tmp_path: Path
) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    job = runtime.create_job(
        spec=_md_to_pdf_spec(filename="service-error.md"),
        upload_bytes=b"# Service error\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )

    def _fake_heartbeat(**kwargs):
        del kwargs
        return threading.Event(), _NoopJoinThread()

    def _raise_service_error(**kwargs):
        del kwargs
        raise ServiceError(
            status_code=503,
            code="conversion_backend_unavailable",
            message="backend temporarily unavailable",
            retryable=True,
            details={"backend": "test"},
        )

    monkeypatch.setattr(runtime_engine_v2, "start_conversion_heartbeat_v2", _fake_heartbeat)
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _raise_service_error)

    runtime._run_job(job.job_id)

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.status == JobStatus.FAILED
    assert stored.failure_code == "conversion_backend_unavailable"
    assert stored.failure_message == "backend temporarily unavailable"
    assert stored.failure_retryable is True
    assert stored.failure_details == {"backend": "test"}


def test_run_job_marks_failed_on_unexpected_exception(monkeypatch, tmp_path: Path) -> None:
    runtime = ServiceRuntimeV2(_runtime_config(tmp_path / "service_data"))
    job = runtime.create_job(
        spec=_md_to_pdf_spec(filename="unexpected.md"),
        upload_bytes=b"# Unexpected exception\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )

    def _fake_heartbeat(**kwargs):
        del kwargs
        return threading.Event(), _NoopJoinThread()

    def _raise_unexpected(**kwargs):
        del kwargs
        raise RuntimeError("kaboom")

    monkeypatch.setattr(runtime_engine_v2, "start_conversion_heartbeat_v2", _fake_heartbeat)
    monkeypatch.setattr(runtime_engine_v2, "execute_v2_job_conversion", _raise_unexpected)

    runtime._run_job(job.job_id)

    stored = runtime.get_job(job.job_id)
    assert stored is not None
    assert stored.status == JobStatus.FAILED
    assert stored.failure_code == "conversion_internal_error"
    assert stored.failure_message is not None
    assert "Unexpected conversion error: kaboom" in stored.failure_message
    assert stored.failure_retryable is True
    assert stored.failure_details is None
