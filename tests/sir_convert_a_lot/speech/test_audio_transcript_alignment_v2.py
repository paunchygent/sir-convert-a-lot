"""Task 357 cross-chunk transcript alignment behavior.

Purpose:
    Prove final transcript JSON persistence is gated by global diarization
    alignment and preserves speaker-label stability across chunk boundaries.

Relationships:
    - Exercises `infrastructure.audio_transcript_bundle_runtime` directly at
      the sidecar client port with fake provider responses.
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
from tests.sir_convert_a_lot.speech.audio_transcript_task357_helpers import (
    API_KEY,
    chunk_payload,
    healthy_sidecar,
    probe_payload,
    ready_capabilities,
    stored_audio_job,
)


class _AlignmentSidecar:
    def __init__(self, *, diarization_windows: list[dict[str, object]]) -> None:
        self._diarization_windows = diarization_windows

    def health(self) -> Mapping[str, object]:
        return healthy_sidecar()

    def capabilities(self) -> Mapping[str, object]:
        return ready_capabilities()

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        return probe_payload(duration_seconds=600.0)

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        return {
            "status": "succeeded",
            "diarization": {
                "status": "succeeded",
                "mode_used": "auto",
                "windows": self._diarization_windows,
            },
            "warnings": [],
        }

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
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


def test_successful_chunks_use_global_diarization_for_stable_speaker_labels(
    tmp_path: Path,
) -> None:
    job = stored_audio_job(tmp_path)
    sidecar = _AlignmentSidecar(
        diarization_windows=[
            {
                "window_id": "speaker-window-0001",
                "start_seconds": 0.0,
                "end_seconds": 600.0,
                "speaker_label": "SPEAKER_00",
            }
        ]
    )

    execute_audio_transcript_bundle_job(
        job=job,
        config=ServiceConfig(api_key=API_KEY, data_root=tmp_path / "service_data"),
        sidecar=sidecar,
        progress_callback=None,
        is_cancel_requested=lambda: False,
    )

    transcript = json.loads(job.artifact_path.read_text(encoding="utf-8"))
    assert [segment["speaker_label"] for segment in transcript["segments"]] == [
        "SPEAKER_00",
        "SPEAKER_00",
    ]
    assert transcript["diarization"]["status"] == "succeeded"


def test_segment_in_diarization_gap_uses_nearest_global_speaker_label(
    tmp_path: Path,
) -> None:
    job = stored_audio_job(tmp_path)
    sidecar = _AlignmentSidecar(
        diarization_windows=[
            {
                "window_id": "speaker-window-0001",
                "start_seconds": 0.0,
                "end_seconds": 250.0,
                "speaker_label": "SPEAKER_00",
            },
            {
                "window_id": "speaker-window-0002",
                "start_seconds": 350.0,
                "end_seconds": 600.0,
                "speaker_label": "SPEAKER_00",
            },
        ]
    )

    execute_audio_transcript_bundle_job(
        job=job,
        config=ServiceConfig(api_key=API_KEY, data_root=tmp_path / "service_data"),
        sidecar=sidecar,
        progress_callback=None,
        is_cancel_requested=lambda: False,
    )

    transcript = json.loads(job.artifact_path.read_text(encoding="utf-8"))
    assert [segment["speaker_label"] for segment in transcript["segments"]] == [
        "SPEAKER_00",
        "SPEAKER_00",
    ]


def test_final_json_is_not_persisted_when_cross_chunk_alignment_fails(
    tmp_path: Path,
) -> None:
    job = stored_audio_job(tmp_path)
    sidecar = _AlignmentSidecar(
        diarization_windows=[
            {
                "window_id": "speaker-window-0001",
                "start_seconds": 0.0,
                "end_seconds": 250.0,
                "speaker_label": "SPEAKER_00",
            }
        ]
    )

    with pytest.raises(ServiceError) as exc_info:
        execute_audio_transcript_bundle_job(
            job=job,
            config=ServiceConfig(api_key=API_KEY, data_root=tmp_path / "service_data"),
            sidecar=sidecar,
            progress_callback=None,
            is_cancel_requested=lambda: False,
        )

    assert exc_info.value.code == "audio_segment_alignment_failed"
    assert not job.artifact_path.exists()
