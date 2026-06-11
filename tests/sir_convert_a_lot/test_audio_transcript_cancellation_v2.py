"""Task 357 audio cancellation cleanup behavior.

Purpose:
    Prove cancellation during checkpointed chunk execution stops future chunk
    scheduling and leaves no terminal transcript artifact or partial checkpoint.

Relationships:
    - Exercises `infrastructure.audio_transcript_bundle_runtime` cancellation
      through the sidecar client port.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_runtime import (
    AudioProgressUpdateV2,
    execute_audio_transcript_bundle_job,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfConversionCanceledV2,
)
from tests.sir_convert_a_lot.audio_transcript_task357_helpers import (
    API_KEY,
    chunk_payload,
    diarization_payload,
    healthy_sidecar,
    probe_payload,
    ready_capabilities,
    stored_audio_job,
)


class _CancellationSidecar:
    def __init__(self) -> None:
        self.chunk_requests: list[Mapping[str, object]] = []
        self.canceled_handles: list[str] = []
        self.finalized_handles: list[str] = []

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
        return chunk_payload(
            chunk_index=int(chunk.get("chunk_index", 0)),
            start_seconds=float(chunk.get("start_seconds", 0.0)),
            end_seconds=float(chunk.get("end_seconds", 0.0)),
        )

    def cancel(self, request_handle: str) -> None:
        self.canceled_handles.append(request_handle)

    def finalize(self, request_handle: str) -> None:
        self.finalized_handles.append(request_handle)


def test_cancellation_after_checkpoint_stops_chunks_and_purges_partial_state(
    tmp_path: Path,
) -> None:
    job = stored_audio_job(tmp_path)
    sidecar = _CancellationSidecar()
    updates: list[AudioProgressUpdateV2] = []
    cancel_requested = False

    def _progress(update: AudioProgressUpdateV2) -> None:
        nonlocal cancel_requested
        updates.append(update)
        if update.audio_processed_media_seconds == 300.0:
            cancel_requested = True

    with pytest.raises(PdfConversionCanceledV2):
        execute_audio_transcript_bundle_job(
            job=job,
            config=ServiceConfig(api_key=API_KEY, data_root=tmp_path / "service_data"),
            sidecar=sidecar,
            progress_callback=_progress,
            is_cancel_requested=lambda: cancel_requested,
        )

    assert len(sidecar.chunk_requests) == 1
    assert sidecar.canceled_handles == [job.job_id]
    assert sidecar.finalized_handles == [job.job_id]
    assert not job.artifact_path.exists()
    assert not (job.artifact_path.parent / "audio_chunk_checkpoints.json").exists()
    assert [
        update.audio_processed_media_seconds for update in updates if update.stage == "transcribing"
    ] == [
        0.0,
        300.0,
    ]
