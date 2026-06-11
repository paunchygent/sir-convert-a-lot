"""Task 357 audio checkpoint replay behavior.

Purpose:
    Prove accepted audio chunk checkpoints are the durable source of retry
    progress and prevent duplicate transcript segments on replay.

Relationships:
    - Exercises `infrastructure.audio_transcript_bundle_runtime` directly at
      the sidecar client port.
    - Uses fake sidecars instead of backend-native STT/diarization internals.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_runtime import (
    execute_audio_transcript_bundle_job,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from tests.sir_convert_a_lot.audio_transcript_task357_helpers import (
    API_KEY,
    chunk_payload,
    diarization_payload,
    healthy_sidecar,
    probe_payload,
    ready_capabilities,
    stored_audio_job,
)


class _FailAfterFirstChunkSidecar:
    def __init__(self) -> None:
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
        if index == 1:
            raise ServiceError(
                status_code=503,
                code="audio_sidecar_unavailable",
                message="Transient sidecar failure.",
                retryable=True,
            )
        return chunk_payload(chunk_index=0, start_seconds=0.0, end_seconds=300.0)

    def cancel(self, request_handle: str) -> None:
        del request_handle

    def finalize(self, request_handle: str) -> None:
        del request_handle


class _ReplaySidecar(_FailAfterFirstChunkSidecar):
    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        self.chunk_requests.append(dict(request))
        chunk_obj = request.get("chunk")
        chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
        index = int(chunk.get("chunk_index", 0))
        start_seconds = float(chunk.get("start_seconds", 0.0))
        end_seconds = float(chunk.get("end_seconds", 0.0))
        return chunk_payload(
            chunk_index=index,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
        )


def test_retry_resumes_from_accepted_checkpoint_without_duplicate_segments(
    tmp_path: Path,
) -> None:
    job = stored_audio_job(tmp_path)
    config = ServiceConfig(api_key=API_KEY, data_root=tmp_path / "service_data")
    first_sidecar = _FailAfterFirstChunkSidecar()

    with pytest.raises(ServiceError) as exc_info:
        execute_audio_transcript_bundle_job(
            job=job,
            config=config,
            sidecar=first_sidecar,
            progress_callback=None,
            is_cancel_requested=lambda: False,
        )

    assert exc_info.value.code == "audio_sidecar_unavailable"
    assert [chunk_index(request) for request in first_sidecar.chunk_requests] == [0, 1]
    assert not job.artifact_path.exists()

    replay_sidecar = _ReplaySidecar()
    result = execute_audio_transcript_bundle_job(
        job=job,
        config=config,
        sidecar=replay_sidecar,
        progress_callback=None,
        is_cancel_requested=lambda: False,
    )

    assert result.backend_used == "stt_sidecar"
    assert [chunk_index(request) for request in replay_sidecar.chunk_requests] == [1]
    transcript = json.loads(job.artifact_path.read_text(encoding="utf-8"))
    segment_ids = [segment["segment_id"] for segment in transcript["segments"]]
    assert segment_ids == ["chunk-0-seg-0001", "chunk-1-seg-0001"]
    assert result.artifact_bytes == job.artifact_path.read_bytes()


def chunk_index(request: Mapping[str, object]) -> int:
    """Return the chunk index carried by a fake sidecar request."""

    chunk_obj = request.get("chunk")
    chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
    return int(chunk.get("chunk_index", -1))
