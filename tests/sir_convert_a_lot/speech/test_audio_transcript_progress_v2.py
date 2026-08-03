"""Task 357 public audio progress behavior.

Purpose:
    Prove Service API v2 polling exposes deterministic audio chunk totals and
    monotonic numeric progress during active transcript execution.

Relationships:
    - Exercises the public job lifecycle through `interfaces.http_api`.
    - Uses a fake sidecar at `infrastructure.audio_transcription_sidecar_client`.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from pathlib import Path

from fastapi.testclient import TestClient

from tests.sir_convert_a_lot.speech.audio_transcript_task357_helpers import (
    build_test_app,
    chunk_payload,
    diarization_payload,
    headers,
    healthy_sidecar,
    post_audio_job,
    probe_payload,
    ready_capabilities,
)


class _BlockingChunkSidecar:
    def __init__(self) -> None:
        self.first_chunk_started = threading.Event()
        self.second_chunk_started = threading.Event()
        self.release_first_chunk = threading.Event()
        self.release_second_chunk = threading.Event()
        self.chunk_requests: list[Mapping[str, object]] = []

    def health(self) -> Mapping[str, object]:
        return healthy_sidecar()

    def capabilities(self) -> Mapping[str, object]:
        return ready_capabilities()

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        return probe_payload(duration_seconds=600.0)

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        return diarization_payload()

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.chunk_requests.append(dict(request))
        chunk_obj = request.get("chunk")
        chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
        index = int(chunk.get("chunk_index", 0))
        start_seconds = float(chunk.get("start_seconds", 0.0))
        end_seconds = float(chunk.get("end_seconds", 0.0))
        if index == 0:
            self.first_chunk_started.set()
            self.release_first_chunk.wait(timeout=5.0)
        else:
            self.second_chunk_started.set()
            self.release_second_chunk.wait(timeout=5.0)
        return chunk_payload(
            chunk_index=index,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )

    def cancel(self, request_handle: str) -> None:
        del request_handle

    def finalize(self, request_handle: str) -> None:
        del request_handle


def test_public_polling_exposes_planned_totals_before_first_chunk_completes(
    tmp_path: Path,
) -> None:
    sidecar = _BlockingChunkSidecar()
    app = build_test_app(tmp_path, sidecar=sidecar)
    client = TestClient(app)

    create_response = post_audio_job(
        client=client,
        idempotency_key="idem-task357-progress-running",
        wait_seconds=0,
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]
    assert sidecar.first_chunk_started.wait(timeout=5.0)

    poll_response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())

    assert poll_response.status_code == 200
    progress = poll_response.json()["job"]["progress"]
    assert progress["stage"] == "transcribing"
    assert progress["audio_total_media_seconds"] == 600.0
    assert progress["audio_total_chunks"] == 2
    assert progress["audio_processed_media_seconds"] == 0.0
    assert progress["audio_percent_complete"] == 0.0
    assert progress["audio_current_chunk_index"] == 0
    assert progress["total_pages"] is None
    assert progress["processed_pages"] is None
    assert progress["percent_complete"] is None

    sidecar.release_first_chunk.set()
    assert sidecar.second_chunk_started.wait(timeout=5.0)
    mid_response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())
    time.sleep(0.15)
    heartbeat_only_response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())

    mid_progress = mid_response.json()["job"]["progress"]
    heartbeat_progress = heartbeat_only_response.json()["job"]["progress"]
    assert mid_progress["audio_processed_media_seconds"] == 300.0
    assert mid_progress["audio_percent_complete"] == 50.0
    assert mid_progress["audio_current_chunk_index"] == 0
    assert heartbeat_progress["audio_processed_media_seconds"] == 300.0
    assert heartbeat_progress["audio_percent_complete"] == 50.0
    assert heartbeat_progress["last_heartbeat_at"] >= mid_progress["last_heartbeat_at"]

    sidecar.release_second_chunk.set()
    terminal_response = _wait_for_terminal(client=client, job_id=job_id)
    assert terminal_response["status"] == "succeeded"
    terminal_progress_obj = terminal_response["progress"]
    assert isinstance(terminal_progress_obj, Mapping)
    terminal_progress = terminal_progress_obj
    assert terminal_progress["audio_processed_media_seconds"] == 600.0
    assert terminal_progress["audio_percent_complete"] == 100.0
    assert terminal_progress["audio_current_chunk_index"] == 1


def _wait_for_terminal(*, client: TestClient, job_id: str) -> Mapping[str, object]:
    for _ in range(80):
        response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())
        response_payload = response.json()
        assert isinstance(response_payload, Mapping)
        payload_obj = response_payload["job"]
        assert isinstance(payload_obj, Mapping)
        status_obj = payload_obj["status"]
        if status_obj in {"succeeded", "failed", "canceled"}:
            return {str(key): value for key, value in payload_obj.items()}
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for terminal audio job.")
