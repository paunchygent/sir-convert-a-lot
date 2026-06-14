"""Task 364 audio progress telemetry redaction behavior.

Purpose:
    Prove public progress and timing telemetry for audio transcript-bundle jobs
    stays operational and never carries transcript content, speaker display
    names, media hashes, raw filenames, credentials, signed headers, or artifact
    bytes.

Relationships:
    - Exercises the Service API v2 job lifecycle projection consumed by
      downstream products such as Skriptoteket.
    - Uses a fake sidecar carrying intentionally sensitive source-like values
      to keep redaction assertions focused on progress telemetry.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from tests.sir_convert_a_lot.audio_transcript_task357_helpers import (
    build_test_client,
    chunk_payload,
    healthy_sidecar,
    post_audio_job,
    ready_capabilities,
)


class _SensitivePayloadSidecar:
    def health(self) -> Mapping[str, object]:
        return healthy_sidecar()

    def capabilities(self) -> Mapping[str, object]:
        return ready_capabilities()

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        return {
            "status": "succeeded",
            "media": {
                "duration_seconds": 9.5,
                "normalized_audio_sha256": "sha256:sensitive-normalized-media-hash",
                "normalized_audio_handle": "sir-stt-normalized:sensitive-handle",
            },
            "runtime_metadata": {
                "acceleration_used": "rocm",
                "normalization_profile": "wav_16khz_mono_s16",
            },
            "warnings": ["operator-only warning without transcript"],
        }

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        return {
            "status": "succeeded",
            "diarization": {
                "status": "succeeded",
                "mode_used": "auto",
                "windows": [
                    {
                        "window_id": "secret-window-id",
                        "start_seconds": 0.0,
                        "end_seconds": 9.5,
                        "speaker_label": "SPEAKER_SECRET_DISPLAY_NAME",
                    }
                ],
            },
            "warnings": [],
        }

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        chunk_obj = request.get("chunk")
        chunk = chunk_obj if isinstance(chunk_obj, Mapping) else {}
        payload = chunk_payload(
            chunk_index=int(chunk.get("chunk_index", 0)),
            start_seconds=float(chunk.get("start_seconds", 0.0)),
            end_seconds=float(chunk.get("end_seconds", 9.5)),
        )
        segments_obj = payload["segments"]
        assert isinstance(segments_obj, list)
        first_segment = segments_obj[0]
        assert isinstance(first_segment, dict)
        first_segment["text"] = "CLASSIFIED TRANSCRIPT UTTERANCE"
        return payload

    def cancel(self, request_handle: str) -> None:
        del request_handle

    def finalize(self, request_handle: str) -> None:
        del request_handle


def test_audio_progress_and_timing_payloads_exclude_source_content_and_secrets(
    tmp_path: Path,
) -> None:
    client = build_test_client(tmp_path, sidecar=_SensitivePayloadSidecar())

    create_response = post_audio_job(
        client=client,
        idempotency_key="idem-task364-redaction",
        wait_seconds=20,
    )

    assert create_response.status_code == 200
    job = create_response.json()["job"]
    assert job["status"] == "succeeded"
    progress = job["progress"]
    assert progress["audio_pipeline_percent_complete"] == 100.0
    assert progress["audio_pipeline_eta_seconds"] == 0

    serialized_progress = json.dumps(progress, sort_keys=True)
    forbidden_fragments = [
        "CLASSIFIED TRANSCRIPT UTTERANCE",
        "SPEAKER_SECRET_DISPLAY_NAME",
        "teacher-meeting.m4a",
        "sha256:sensitive-normalized-media-hash",
        "sir-stt-normalized:sensitive-handle",
        "SECRET_HEADER",
        "audio bytes",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in serialized_progress
