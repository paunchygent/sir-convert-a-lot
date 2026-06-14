"""Task 364 audio phase timing telemetry behavior.

Purpose:
    Prove Service API v2 persists canonical, content-safe STT phase timings for
    successful and failed audio transcript-bundle jobs.

Relationships:
    - Exercises public create/poll lifecycle projections backed by the v2 job
      store manifest.
    - Uses fake sidecars at the audio adapter boundary so timing assertions are
      about Sir Convert orchestration rather than backend-native STT libraries.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from tests.sir_convert_a_lot.audio_transcript_task357_helpers import (
    build_test_client,
    chunk_payload,
    diarization_payload,
    healthy_sidecar,
    post_audio_job,
    probe_payload,
    ready_capabilities,
)

_TASK_364_AUDIO_TIMING_KEYS = {
    "audio_probe_normalize_ms",
    "audio_diarization_ms",
    "audio_transcription_ms",
    "audio_alignment_ms",
    "audio_packaging_ms",
}


class _SuccessfulTimingSidecar:
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


class _FailingDiarizationTimingSidecar(_SuccessfulTimingSidecar):
    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        raise ServiceError(
            status_code=502,
            code="audio_diarization_failed",
            message="Injected diarization failure.",
            retryable=False,
            details={"failure_point": "diarization"},
        )


def test_successful_audio_job_persists_task364_phase_timings(
    tmp_path: Path,
) -> None:
    client = build_test_client(tmp_path, sidecar=_SuccessfulTimingSidecar())

    create_response = post_audio_job(
        client=client,
        idempotency_key="idem-task364-timings-success",
        wait_seconds=20,
    )

    assert create_response.status_code == 200
    job = create_response.json()["job"]
    assert job["status"] == "succeeded"
    progress = job["progress"]
    phase_timings = progress["phase_timings_ms"]
    assert _TASK_364_AUDIO_TIMING_KEYS.issubset(set(phase_timings))
    assert "final_artifact_persist_ms" in phase_timings
    assert "conversion_total_ms" in phase_timings
    assert progress["audio_pipeline_percent_complete"] == 100.0
    assert progress["audio_pipeline_eta_seconds"] == 0
    for key in _TASK_364_AUDIO_TIMING_KEYS:
        assert phase_timings[key] >= 0


def test_failed_audio_job_persists_phase_timings_before_service_error_leaves_runtime(
    tmp_path: Path,
) -> None:
    client = build_test_client(tmp_path, sidecar=_FailingDiarizationTimingSidecar())

    create_response = post_audio_job(
        client=client,
        idempotency_key="idem-task364-timings-failure",
        wait_seconds=20,
    )

    assert create_response.status_code == 200
    job = create_response.json()["job"]
    assert job["status"] == "failed"
    progress = job["progress"]
    phase_timings = progress["phase_timings_ms"]
    assert phase_timings["audio_probe_normalize_ms"] >= 0
    assert phase_timings["audio_diarization_ms"] >= 0
    assert "conversion_total_ms" in phase_timings
    assert "final_artifact_persist_ms" in phase_timings
    assert progress["audio_pipeline_percent_complete"] is not None
    assert progress["audio_pipeline_percent_complete"] < 100.0


def test_openapi_progress_schema_exposes_audio_pipeline_fields() -> None:
    from scripts.sir_convert_a_lot.openapi_export_v2 import build_openapi_contract_v2

    schema = build_openapi_contract_v2()
    components = schema["components"]
    assert isinstance(components, Mapping)
    schemas = components["schemas"]
    assert isinstance(schemas, Mapping)
    progress_schema = schemas["JobProgressV2"]
    assert isinstance(progress_schema, Mapping)
    properties = progress_schema["properties"]
    assert isinstance(properties, Mapping)

    pipeline_percent = properties["audio_pipeline_percent_complete"]
    pipeline_eta = properties["audio_pipeline_eta_seconds"]
    assert isinstance(pipeline_percent, Mapping)
    assert isinstance(pipeline_eta, Mapping)
    percent_number_schema = _nullable_branch(pipeline_percent, branch_type="number")
    eta_integer_schema = _nullable_branch(pipeline_eta, branch_type="integer")
    assert percent_number_schema["minimum"] == 0.0
    assert percent_number_schema["maximum"] == 100.0
    assert eta_integer_schema["minimum"] == 0


def _nullable_branch(schema: Mapping[str, object], *, branch_type: str) -> Mapping[str, object]:
    any_of_obj = schema["anyOf"]
    assert isinstance(any_of_obj, list)
    for branch in any_of_obj:
        if isinstance(branch, Mapping) and branch.get("type") == branch_type:
            return branch
    raise AssertionError(f"Missing nullable branch type: {branch_type}")
