"""Transcript replay HTTP observability tests for Service API v2.

Purpose:
    Prove replay route diagnostics preserve caller correlation identity while
    keeping uploaded transcript content and speaker display labels out of logs.

Relationships:
    - Exercises `interfaces.http_api.create_app` middleware through the public
      `transcript_json -> transcript_bundle` job lifecycle.
    - Complements replay contract tests with operator-visible observability
      evidence for live Gateway/Sir Convert proofs.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.test_transcript_formatter_replay_v2 import (
    FIXTURE_PATH,
    _app,
    _post_replay_job,
    _replay_job_spec,
)


def test_replay_request_log_includes_correlation_without_payload_tokens(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    correlation_id = "corr-task-360-replay-observability"
    transcript_token = "opaque-transcript-content-token-not-for-logs"
    display_token = "opaque-display-label-token-not-for-logs"
    caplog.set_level(logging.INFO, logger="sir_convert_a_lot.http")
    client = TestClient(_app(tmp_path))

    response = _post_replay_job(
        client=client,
        idempotency_key="idem-transcript-replay-observability",
        wait_seconds=20,
        file_bytes=_fixture_bytes_with_token(transcript_token),
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
    assert "POST" in log_text
    assert "/v2/convert/jobs" in log_text
    assert "status_code=200" in log_text
    assert transcript_token not in log_text
    assert display_token not in log_text


def _fixture_bytes_with_token(transcript_token: str) -> bytes:
    """Return canonical transcript fixture bytes with an opaque body token."""
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("canonical transcript fixture must be a JSON object")
    segments = payload.get("segments")
    if not isinstance(segments, list):
        raise AssertionError("canonical transcript fixture must include segments")
    first_segment = segments[0]
    if not isinstance(first_segment, dict):
        raise AssertionError("canonical transcript segment must be a JSON object")
    first_segment["text"] = transcript_token
    transcript = payload.get("transcript")
    if not isinstance(transcript, dict):
        raise AssertionError("canonical transcript fixture must include transcript text")
    transcript["text"] = transcript_token
    return json.dumps(payload, sort_keys=True).encode("utf-8")
