"""Task 364 audio phase progress behavior.

Purpose:
    Prove Service API v2 exposes truthful full-pipeline audio progress during
    explicit STT phase transitions without advancing numeric work from
    heartbeat freshness alone.

Relationships:
    - Exercises the public job lifecycle through `interfaces.http_api`.
    - Uses fake sidecars at the STT adapter boundary to block diarization and
      transcription without importing backend-native audio dependencies.
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


class _BlockingDiarizationSidecar:
    def __init__(self) -> None:
        self.diarize_started = threading.Event()
        self.release_diarize = threading.Event()
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
        self.diarize_started.set()
        self.release_diarize.wait(timeout=5.0)
        return diarization_payload()

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.chunk_requests.append(dict(request))
        chunk_obj = request.get("chunk")
        chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
        return chunk_payload(
            chunk_index=int(chunk.get("chunk_index", 0)),
            start_seconds=float(chunk.get("start_seconds", 0.0)),
            end_seconds=float(chunk.get("end_seconds", 0.0)),
        )

    def cancel(self, request_handle: str) -> None:
        del request_handle

    def finalize(self, request_handle: str) -> None:
        del request_handle


def test_public_progress_enters_diarizing_before_blocking_sidecar_call(
    tmp_path: Path,
) -> None:
    sidecar = _BlockingDiarizationSidecar()
    app = build_test_app(tmp_path, sidecar=sidecar)
    client = TestClient(app)

    create_response = post_audio_job(
        client=client,
        idempotency_key="idem-task364-diarizing-progress",
        wait_seconds=0,
    )

    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]
    assert sidecar.diarize_started.wait(timeout=5.0)

    try:
        poll_response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())
        assert poll_response.status_code == 200
        first_progress = poll_response.json()["job"]["progress"]
        assert first_progress["stage"] == "diarizing"
        assert first_progress["audio_total_media_seconds"] == 600.0
        assert first_progress["audio_total_chunks"] == 2
        assert first_progress["audio_processed_media_seconds"] == 0.0
        assert first_progress["audio_percent_complete"] == 0.0
        assert first_progress["audio_current_chunk_index"] == 0
        assert 0.0 < first_progress["audio_pipeline_percent_complete"] < 100.0
        assert first_progress["audio_pipeline_eta_seconds"] >= 0

        time.sleep(0.15)
        heartbeat_response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())
        heartbeat_progress = heartbeat_response.json()["job"]["progress"]
        assert heartbeat_progress["stage"] == "diarizing"
        assert heartbeat_progress["last_heartbeat_at"] >= first_progress["last_heartbeat_at"]
        assert (
            heartbeat_progress["audio_pipeline_percent_complete"]
            == first_progress["audio_pipeline_percent_complete"]
        )
        assert (
            heartbeat_progress["audio_pipeline_eta_seconds"]
            == first_progress["audio_pipeline_eta_seconds"]
        )
        assert heartbeat_progress["audio_processed_media_seconds"] == 0.0
        assert heartbeat_progress["audio_percent_complete"] == 0.0
    finally:
        sidecar.release_diarize.set()

    terminal = _wait_for_terminal(client=client, job_id=job_id)
    assert terminal["status"] == "succeeded"
    terminal_progress_obj = terminal["progress"]
    assert isinstance(terminal_progress_obj, Mapping)
    assert terminal_progress_obj["audio_pipeline_percent_complete"] == 100.0
    assert terminal_progress_obj["audio_pipeline_eta_seconds"] == 0


def _wait_for_terminal(*, client: TestClient, job_id: str) -> Mapping[str, object]:
    for _ in range(80):
        response = client.get(f"/v2/convert/jobs/{job_id}", headers=headers())
        payload = response.json()
        job_obj = payload["job"]
        assert isinstance(job_obj, Mapping)
        status_obj = job_obj["status"]
        if status_obj in {"succeeded", "failed", "canceled"}:
            return {str(key): value for key, value in job_obj.items()}
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for terminal audio job.")
