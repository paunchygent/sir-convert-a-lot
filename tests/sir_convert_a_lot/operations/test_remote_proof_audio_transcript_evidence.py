"""Tests for remote-proof audio transcript evidence runner.

Purpose:
    Prove the Task 365 STT evidence runner uses the asynchronous Service API
    contract instead of a synchronous completion request.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.devops.remote_proof_audio_transcript_evidence`.
    - Protects local Skriptoteket proof diagnostics by isolating the
      remote-proof Service API and hosted STT sidecar boundary.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.remote_proof_audio_transcript_evidence import (
    AudioTranscriptEvidenceSettings,
    run_audio_transcript_evidence,
)


def test_audio_transcript_evidence_submits_async_polls_and_scrubs_api_key(
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "source.mp3"
    audio_path.write_bytes(b"audio-bytes")
    requested_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(str(request.url))
        if request.method == "GET" and request.url.path == "/readyz":
            return httpx.Response(
                200,
                json={
                    "ready": True,
                    "service_revision": "abc123",
                    "service_profile": "remote-proof",
                },
            )
        if request.method == "POST" and request.url.path == "/v2/convert/jobs":
            assert request.url.params["wait_seconds"] == "0"
            assert request.headers["X-API-Key"] == "secret-proof-key"
            return httpx.Response(
                202,
                json={
                    "job": {
                        "job_id": "jobv2_async_stt",
                        "status": "queued",
                        "progress": {"stage": "queued"},
                    }
                },
            )
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/jobv2_async_stt":
            return httpx.Response(
                200,
                json={
                    "job": {
                        "job_id": "jobv2_async_stt",
                        "status": "succeeded",
                        "progress": {
                            "stage": "succeeded",
                            "audio_total_media_seconds": 10.0,
                            "audio_processed_media_seconds": 10.0,
                            "audio_percent_complete": 100.0,
                        },
                    }
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v2/convert/jobs/jobv2_async_stt/result"
        ):
            return httpx.Response(
                200,
                json={
                    "result": {
                        "conversion_metadata": {
                            "pipeline_used": "audio_to_transcript_bundle_v2",
                            "backend_used": "stt_sidecar",
                            "acceleration_used": "rocm",
                        }
                    }
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v2/convert/jobs/jobv2_async_stt/artifacts"
        ):
            return httpx.Response(
                200,
                json={
                    "artifacts": [
                        {
                            "artifact_key": "transcript_json",
                            "availability": "available",
                        }
                    ]
                },
            )
        if (
            request.method == "GET"
            and request.url.path == "/v2/convert/jobs/jobv2_async_stt/artifacts/transcript_json"
        ):
            return httpx.Response(
                200,
                json={
                    "schema_version": "transcript_json_v1",
                    "segments": [{"speaker_label": "SPEAKER_00", "text": "Hello"}],
                },
            )
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    client = httpx.Client(
        base_url="http://proof-service.test",
        transport=httpx.MockTransport(handler),
        timeout=30.0,
    )

    summary_path = run_audio_transcript_evidence(
        AudioTranscriptEvidenceSettings(
            service_url="http://proof-service.test",
            api_key="secret-proof-key",
            audio_file=audio_path,
            output_root=tmp_path / "evidence",
            speaker_count=2,
            timeout_seconds=30.0,
            poll_interval_seconds=0.0,
            expected_service_profile="remote-proof",
        ),
        client=client,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "succeeded"
    assert summary["job_id"] == "jobv2_async_stt"
    assert summary["readyz"]["service_profile"] == "remote-proof"
    assert summary["transcript_json"]["segment_count"] == 1
    assert any("wait_seconds=0" in path for path in requested_paths)
    assert "secret-proof-key" not in "\n".join(
        path.read_text(encoding="utf-8") for path in summary_path.parent.glob("*.json")
    )
