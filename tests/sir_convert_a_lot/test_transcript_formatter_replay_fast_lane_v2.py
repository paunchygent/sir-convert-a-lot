"""Transcript formatter replay fast-lane behavior for Service API v2.

Purpose:
    Prove saved canonical transcript JSON replay executes as a bounded
    producer-owned lane under the existing v2 job lifecycle instead of waiting
    behind generic conversion workers.

Relationships:
    - Exercises `POST /v2/convert/jobs` with `wait_seconds=0`.
    - Complements strict replay validation tests with Task 363 latency,
      telemetry, and downstream smoke evidence.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure import transcript_formatter_replay_fast_lane_v2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.transcript_formatter_replay_runtime import (
    TranscriptFormatterReplayExecutionResult,
)
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.test_audio_transcript_bundle_runtime_v2 import (
    _API_KEY,
    _headers,
)
from tests.sir_convert_a_lot.test_transcript_formatter_replay_v2 import (
    _artifact_entries,
    _canonical_bytes,
    _post_replay_job,
    _replay_job_spec,
)


def test_wait_zero_replay_succeeds_without_generic_worker_delay(tmp_path: Path) -> None:
    app = _fast_lane_app(
        tmp_path,
        run_jobs_on_submit=False,
        processing_delay_seconds=5.0,
    )
    client = TestClient(app)

    started = time.perf_counter()
    response = _post_replay_job(
        client=client,
        idempotency_key="idem-task-363-fast-lane-wait-zero",
        wait_seconds=0,
    )
    elapsed_seconds = time.perf_counter() - started

    assert elapsed_seconds < 1.0
    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.SUCCEEDED.value
    assert job["progress"]["stage"] == "succeeded"
    phase_timings = job["progress"]["phase_timings_ms"]
    assert "conversion_total_ms" in phase_timings
    assert "final_artifact_persist_ms" in phase_timings

    job_id = str(job["job_id"])
    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=_headers())
    assert result_response.status_code == 200
    assert result_response.json()["result"]["artifact"]["filename"] == (
        "transcript_replay_bundle_manifest.json"
    )


def test_wait_zero_replay_failure_is_terminal_and_fail_closed(tmp_path: Path) -> None:
    client = TestClient(
        _fast_lane_app(
            tmp_path,
            run_jobs_on_submit=False,
            processing_delay_seconds=5.0,
        )
    )

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-task-363-fast-lane-fail-closed",
        wait_seconds=0,
        spec=_replay_job_spec(
            options_patch={
                "speaker_label_overrides": [
                    {
                        "canonical_speaker_label": "UNKNOWN",
                        "display_name": "Fast Lane Label",
                    }
                ]
            }
        ),
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.FAILED.value
    assert job["progress"]["stage"] == "failed"
    job_id = str(job["job_id"])

    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=_headers())
    assert result_response.status_code == 409
    assert result_response.json()["error"]["code"] == "job_not_succeeded"

    named_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_txt",
        headers=_headers(),
    )
    assert named_response.status_code == 409
    assert named_response.json()["error"]["code"] == "job_not_succeeded"


def test_replay_fast_lane_telemetry_is_timed_and_content_safe(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    correlation_id = "corr-task-363-fast-lane-observability"
    transcript_token = "opaque-task-363-transcript-token"
    display_token = "opaque-task-363-display-token"
    caplog.set_level(logging.INFO, logger="uvicorn.error")
    client = TestClient(_fast_lane_app(tmp_path))

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-task-363-fast-lane-telemetry",
        wait_seconds=0,
        file_bytes=_fixture_bytes_with_text_token(transcript_token),
        spec=_replay_job_spec(
            options_patch={
                "speaker_label_overrides": [
                    {
                        "canonical_speaker_label": "UNKNOWN",
                        "display_name": display_token,
                    }
                ]
            }
        ),
        correlation_id=correlation_id,
    )

    assert response.status_code == 200
    assert response.json()["job"]["status"] == JobStatus.FAILED.value
    log_text = caplog.text
    assert correlation_id in log_text
    assert "transcript_formatter_replay_fast_lane_completed" in log_text
    assert "admission_ms=" in log_text
    assert "execution_ms=" in log_text
    assert transcript_token not in log_text
    assert display_token not in log_text
    assert _API_KEY not in log_text

    metrics_text = client.get("/metrics").text
    assert "sir_convert_a_lot_v2_transcript_replay_fast_lane_duration_seconds" in metrics_text
    assert 'phase="admission"' in metrics_text
    assert 'phase="execution"' in metrics_text
    assert "job_id=" not in metrics_text
    assert correlation_id not in metrics_text
    assert transcript_token not in metrics_text
    assert display_token not in metrics_text


def test_downstream_replay_fast_lane_smoke_fetches_overlay_artifact(
    tmp_path: Path,
) -> None:
    client = TestClient(_fast_lane_app(tmp_path))

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-task-363-downstream-smoke",
        wait_seconds=0,
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.SUCCEEDED.value
    job_id = str(job["job_id"])

    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=_headers())
    assert result_response.status_code == 200
    assert result_response.json()["result"]["artifact"]["filename"] == (
        "transcript_replay_bundle_manifest.json"
    )

    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=_headers())
    assert manifest_response.status_code == 200
    entries = _artifact_entries(manifest_response.json())
    assert set(entries) == {"transcript_txt", "transcript_md", "transcript_vtt", "transcript_srt"}
    assert entries["transcript_txt"]["availability"] == "available"

    txt_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_txt",
        headers=_headers(),
    )
    assert txt_response.status_code == 200
    assert "Anna Andersson" in txt_response.text
    assert "Karin Karlsson" in txt_response.text
    assert "SPEAKER_00" not in txt_response.text
    assert "SPEAKER_01" not in txt_response.text


def test_replay_fast_lane_terminalizes_during_cross_process_recovery_sweep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = _fast_lane_app(tmp_path)
    original_execute = (
        transcript_formatter_replay_fast_lane_v2.execute_transcript_formatter_replay_job
    )

    def _execute_after_worker_recovery_sweep(
        *,
        job,
    ) -> TranscriptFormatterReplayExecutionResult:
        runtime = app.state.runtime_v2
        runtime.job_store.recover_running_jobs_to_queued(active_job_ids=set())
        return original_execute(job=job)

    monkeypatch.setattr(
        transcript_formatter_replay_fast_lane_v2,
        "execute_transcript_formatter_replay_job",
        _execute_after_worker_recovery_sweep,
    )

    client = TestClient(app)

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-task-365-cross-process-recovery",
        wait_seconds=0,
    )

    assert response.status_code == 200
    job = response.json()["job"]
    assert job["status"] == JobStatus.SUCCEEDED.value
    assert job["progress"]["stage"] == "succeeded"
    job_id = str(job["job_id"])

    result_response = client.get(f"/v2/convert/jobs/{job_id}/result", headers=_headers())
    assert result_response.status_code == 200
    manifest_response = client.get(f"/v2/convert/jobs/{job_id}/artifacts", headers=_headers())
    assert manifest_response.status_code == 200

    event_statuses = [
        event.status.value
        for event in app.state.runtime_v2.job_store.list_job_events_after_sequence(
            job_id=job_id,
            after_sequence=0,
        )
    ]
    assert event_statuses[-1] == JobStatus.SUCCEEDED.value
    assert event_statuses.count(JobStatus.QUEUED.value) == 1


def _fast_lane_app(
    tmp_path: Path,
    *,
    run_jobs_on_submit: bool = True,
    processing_delay_seconds: float = 0.0,
) -> FastAPI:
    return create_app(
        ServiceConfig(
            api_key=_API_KEY,
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            run_jobs_on_submit=run_jobs_on_submit,
            processing_delay_seconds=processing_delay_seconds,
        )
    )


def _fixture_bytes_with_text_token(transcript_token: str) -> bytes:
    payload = json.loads(_canonical_bytes().decode("utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("canonical transcript fixture must decode to an object")
    segments = payload.get("segments")
    if not isinstance(segments, list):
        raise AssertionError("canonical transcript fixture must include segments")
    first_segment = segments[0]
    if not isinstance(first_segment, dict):
        raise AssertionError("canonical transcript segment must be an object")
    first_segment["text"] = transcript_token
    transcript = payload.get("transcript")
    if not isinstance(transcript, dict):
        raise AssertionError("canonical transcript fixture must include transcript text")
    transcript["text"] = transcript_token
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
