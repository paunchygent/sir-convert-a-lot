"""Audio transcript-bundle sidecar cleanup, cancellation, and failure behavior."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_runtime import (
    AudioProgressUpdateV2,
    execute_audio_transcript_bundle_job,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpoint_models import (
    PdfConversionCanceledV2,
)
from tests.sir_convert_a_lot.speech.audio_transcript_bundle_runtime_test_support import (
    _API_KEY,
    _app,
    _headers,
    _post_audio_job,
    _stored_audio_job,
)
from tests.sir_convert_a_lot.speech.audio_transcript_sidecar_test_doubles import (
    _BlockingAudioTranscriptionSidecar,
    _CleanupTrackingAudioTranscriptionSidecar,
)


def test_audio_success_finalizes_sidecar_normalized_media(tmp_path: Path) -> None:
    sidecar = _CleanupTrackingAudioTranscriptionSidecar(scratch_root=tmp_path / "sidecar")
    job = _stored_audio_job(tmp_path)

    execute_audio_transcript_bundle_job(
        job=job,
        config=ServiceConfig(api_key=_API_KEY, data_root=tmp_path / "service_data"),
        sidecar=sidecar,
        progress_callback=None,
        is_cancel_requested=lambda: False,
    )

    assert sidecar.finalized_handles == [job.job_id]
    assert not sidecar.scratch_path.exists()
    assert job.artifact_path.exists()


@pytest.mark.parametrize(
    ("code", "retryable"),
    [
        ("audio_diarization_failed", False),
        ("audio_sidecar_unavailable", True),
    ],
)
def test_audio_terminal_failure_finalizes_sidecar_normalized_media(
    tmp_path: Path,
    code: str,
    retryable: bool,
) -> None:
    sidecar = _CleanupTrackingAudioTranscriptionSidecar(
        scratch_root=tmp_path / "sidecar",
        failure=(code, retryable),
    )
    job = _stored_audio_job(tmp_path)

    with pytest.raises(ServiceError) as exc_info:
        execute_audio_transcript_bundle_job(
            job=job,
            config=ServiceConfig(api_key=_API_KEY, data_root=tmp_path / "service_data"),
            sidecar=sidecar,
            progress_callback=None,
            is_cancel_requested=lambda: False,
        )

    assert exc_info.value.code == code
    assert sidecar.finalized_handles == [job.job_id]
    assert not sidecar.scratch_path.exists()
    assert not job.artifact_path.exists()


def test_canceling_running_audio_job_propagates_to_sidecar_and_keeps_no_artifact(
    tmp_path: Path,
) -> None:
    sidecar = _BlockingAudioTranscriptionSidecar(scratch_root=tmp_path / "sidecar")
    app = _app(tmp_path, sidecar=sidecar)
    client = TestClient(app)
    create_response = _post_audio_job(
        client=client,
        idempotency_key="idem-audio-runtime-in-flight-cancel",
        wait_seconds=0,
    )
    assert create_response.status_code == 202
    job_id = create_response.json()["job"]["job_id"]
    assert sidecar.chunk_started.wait(timeout=5.0)

    cancel_response = client.post(
        f"/v2/convert/jobs/{job_id}/cancel",
        headers=_headers(),
    )

    assert cancel_response.status_code == 202
    assert sidecar.cancel_received.is_set()
    assert sidecar.canceled_handles == [job_id]
    sidecar.release_chunk.set()
    runtime = app.state.runtime_v2
    stored_job = runtime.get_job(job_id)
    assert stored_job is not None
    assert stored_job.status == JobStatus.CANCELED
    assert _eventually_canceled(runtime=runtime, job_id=job_id)
    stored_job = runtime.get_job(job_id)
    assert stored_job is not None
    assert stored_job.status == JobStatus.CANCELED
    assert not stored_job.artifact_path.exists()
    assert not sidecar.scratch_path.exists()

    result_response = client.get(
        f"/v2/convert/jobs/{job_id}/result",
        headers=_headers(),
    )
    assert result_response.status_code == 409
    assert result_response.json()["error"]["code"] == "job_not_succeeded"

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/transcript_json",
        headers=_headers(),
    )
    assert artifact_response.status_code == 409
    assert artifact_response.json()["error"]["code"] == "job_not_succeeded"


def test_audio_cancellation_cancels_sidecar_without_publishing_artifact(
    tmp_path: Path,
) -> None:
    sidecar = _CleanupTrackingAudioTranscriptionSidecar(scratch_root=tmp_path / "sidecar")
    job = _stored_audio_job(tmp_path)
    progress_updates: list[AudioProgressUpdateV2] = []

    with pytest.raises(PdfConversionCanceledV2):
        execute_audio_transcript_bundle_job(
            job=job,
            config=ServiceConfig(
                api_key=_API_KEY,
                data_root=tmp_path / "service_data",
                enable_supervisor=False,
            ),
            sidecar=sidecar,
            progress_callback=progress_updates.append,
            is_cancel_requested=lambda: True,
        )

    assert sidecar.canceled_handles == [job.job_id]
    assert sidecar.chunk_requests == []
    assert not sidecar.scratch_path.exists()
    assert not job.artifact_path.exists()
    assert [update.stage for update in progress_updates] == ["probing_media"]


def _eventually_canceled(*, runtime: ServiceRuntimeV2, job_id: str) -> bool:
    deadline = threading.Event()
    for _ in range(50):
        stored_job = runtime.get_job(job_id)
        if stored_job is not None and stored_job.status == JobStatus.CANCELED:
            return True
        deadline.wait(timeout=0.02)
    return False
