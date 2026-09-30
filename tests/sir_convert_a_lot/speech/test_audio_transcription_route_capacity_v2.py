"""Audio transcription Service API v2 upload-size and route-capacity admission.

Purpose:
    Prove `audio -> transcript_bundle` admission applies the audio-specific
    upload size cap and the per-instance active STT job capacity, and that
    capacity admission keeps retained-job sweeps bounded.

Relationships:
    - Exercises `interfaces.http_create_job_routes_v2` and
      `infrastructure.job_store_v2` without invoking STT sidecars.
    - Builds clients and submissions through
      `audio_route_admission_test_support`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from tests.sir_convert_a_lot.identity_test_support import (
    IdentitySigner as _IdentitySigner,
)
from tests.sir_convert_a_lot.speech.audio_route_admission_test_support import (
    client as _client,
)
from tests.sir_convert_a_lot.speech.audio_route_admission_test_support import (
    post_audio_job as _post_audio_job,
)


def test_create_job_audio_upload_uses_route_specific_size_cap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.sir_convert_a_lot.interfaces import http_create_job_routes_v2

    monkeypatch.setattr(http_create_job_routes_v2, "MAX_AUDIO_UPLOAD_BYTES", 8)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False, max_upload_bytes=4)

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-route-cap",
        idempotency_key="idem-audio-route-cap",
        file_bytes=b"12345",
    )

    assert response.status_code == 202
    assert response.json()["job"]["status"] == JobStatus.QUEUED.value


def test_create_job_audio_upload_over_route_cap_uses_audio_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts.sir_convert_a_lot.interfaces import http_create_job_routes_v2

    monkeypatch.setattr(http_create_job_routes_v2, "MAX_AUDIO_UPLOAD_BYTES", 8)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False, max_upload_bytes=4)

    response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-route-cap-over",
        idempotency_key="idem-audio-route-cap-over",
        file_bytes=b"123456789",
    )

    assert response.status_code == 413
    error = response.json()["error"]
    assert error["code"] == "audio_upload_size_exceeded"
    assert error["details"] == {"limit_bytes": 8}


def test_create_job_rejects_third_active_audio_job_at_route_capacity(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-capacity",
        idempotency_key="idem-audio-capacity-first",
    )
    second_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-capacity",
        idempotency_key="idem-audio-capacity-second",
    )
    third_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-capacity",
        idempotency_key="idem-audio-capacity-third",
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert third_response.status_code == 429
    error = third_response.json()["error"]
    assert error["code"] == "audio_route_capacity_exceeded"
    assert error["details"] == {
        "exhausted_cap": "max_active_stt_jobs_per_instance",
    }


def test_audio_route_capacity_admission_does_not_resweep_for_each_retained_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audio admission must keep retained-job scans bounded before returning 202."""
    sweep_calls = 0
    original_sweep_expired = JobStoreV2.sweep_expired

    def _counting_sweep_expired(self: JobStoreV2) -> None:
        nonlocal sweep_calls
        sweep_calls += 1
        original_sweep_expired(self)

    monkeypatch.setattr(JobStoreV2, "sweep_expired", _counting_sweep_expired)
    identity = _IdentitySigner()
    client = _client(tmp_path, identity, run_jobs_on_submit=False)

    first_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-sweep-capacity",
        idempotency_key="idem-audio-sweep-first",
    )
    second_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-sweep-capacity",
        idempotency_key="idem-audio-sweep-second",
    )
    sweep_calls = 0
    third_response = _post_audio_job(
        client=client,
        identity=identity,
        subject="teacher-audio-sweep-capacity",
        idempotency_key="idem-audio-sweep-third",
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert third_response.status_code == 429
    assert sweep_calls == 0
