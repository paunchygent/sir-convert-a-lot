"""Object-store route proof tests for terminal Sir Convert artifacts.

Purpose:
    Prove primary terminal artifacts and route-owned named terminal bundle
    artifacts are persisted and read through the Sir-owned object-store
    boundary after existing authorization checks.

Relationships:
    - Exercises `interfaces.http_routes_job_artifacts_v2` through FastAPI.
    - Uses `infrastructure.job_store_v2` terminal transitions as job-state
      authority while asserting object-backed artifact reads.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure import runtime_engine_v2 as runtime_engine_v2_module
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_bundle_artifacts import (
    build_audio_transcript_artifact_manifest,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_config import (
    TerminalObjectStoreConfig,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    ObjectStoreReadiness,
    TerminalArtifactObjectRef,
    TerminalArtifactRead,
    TerminalArtifactWriteRequest,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app
from tests.sir_convert_a_lot.service.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    disable_run_job_async,
    post_create,
)
from tests.sir_convert_a_lot.speech.test_audio_transcript_bundle_runtime_v2 import (
    _FakeAudioTranscriptionSidecar,
)
from tests.sir_convert_a_lot.speech.test_audio_transcript_bundle_runtime_v2 import (
    _headers as _audio_headers,
)
from tests.sir_convert_a_lot.speech.test_transcript_formatter_artifacts import (
    _post_audio_job,
)


def test_terminal_artifact_route_streams_object_ref_when_filesystem_artifact_is_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = _object_store_client(tmp_path)
    response = post_create(client, idempotency_key="idem-terminal-object-store")
    assert response.status_code in {200, 202}
    job_id = response.json()["job"]["job_id"]
    runtime = app.state.runtime_v2

    assert runtime.job_store.claim_queued_job(job_id) is True
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"%PDF-1.7\nobject-backed\n",
        pipeline_used="md_to_pdf_v2",
        backend_used="pandoc+weasyprint",
        acceleration_used=None,
        options_fingerprint="sha256:options",
        warnings=[],
    )
    job = runtime.get_job(job_id)
    assert job is not None
    job.artifact_path.unlink()

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr-object-primary"},
    )

    assert artifact_response.status_code == 200
    assert artifact_response.content == b"%PDF-1.7\nobject-backed\n"
    assert runtime.terminal_artifact_store.read_count == 1


def test_transcript_bundle_listing_keeps_object_backed_formatter_available(
    tmp_path: Path,
) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            run_jobs_on_submit=True,
            processing_delay_seconds=0.0,
            enable_runtime_telemetry_calls=False,
            object_store=TerminalObjectStoreConfig(
                backend="local",
                key_prefix="task-381-transcript-cold-test",
            ),
        ),
        audio_transcription_sidecar=_FakeAudioTranscriptionSidecar(),
    )
    client = TestClient(app)
    response = _post_audio_job(
        client=client,
        idempotency_key="idem-audio-cold-formatters",
        output_artifacts=("json", "txt"),
    )
    assert response.status_code == 200
    job_id = response.json()["job"]["job_id"]
    runtime = app.state.runtime_v2
    job = runtime.get_job(job_id)
    assert job is not None
    formatter_path = job.artifact_path.parent / "transcript_txt.txt"
    assert formatter_path.exists()
    formatter_path.unlink()

    manifest_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts",
        headers=_audio_headers(),
    )

    assert manifest_response.status_code == 200
    entries = _artifact_entries(build_audio_transcript_artifact_manifest(job=job))
    response_entries = _artifact_entries(manifest_response.json())
    assert entries["transcript_txt"]["availability"] == "available"
    assert response_entries["transcript_txt"]["availability"] == "available"
    size_bytes = response_entries["transcript_txt"]["size_bytes"]
    assert isinstance(size_bytes, int)
    assert size_bytes > 0
    assert response_entries["transcript_txt"]["sha256"]


def test_artifact_auth_denial_happens_before_any_object_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = _object_store_client(tmp_path)
    response = post_create(client, idempotency_key="idem-object-denial-before-read")
    assert response.status_code in {200, 202}
    job_id = response.json()["job"]["job_id"]
    runtime = app.state.runtime_v2
    assert runtime.job_store.claim_queued_job(job_id) is True
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"object bytes",
        pipeline_used="md_to_pdf_v2",
        backend_used="pandoc+weasyprint",
        acceleration_used=None,
        options_fingerprint="sha256:options",
        warnings=[],
    )

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "wrong-key", "X-Correlation-ID": "corr-object-denied"},
    )

    assert artifact_response.status_code in {401, 403}
    assert runtime.terminal_artifact_store.read_count == 0


def test_missing_object_maps_to_guarded_error_without_storage_identity_leak(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = _object_store_client(tmp_path)
    response = post_create(client, idempotency_key="idem-object-missing-no-leak")
    assert response.status_code in {200, 202}
    job_id = response.json()["job"]["job_id"]
    runtime = app.state.runtime_v2
    assert runtime.job_store.claim_queued_job(job_id) is True
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"object bytes",
        pipeline_used="md_to_pdf_v2",
        backend_used="pandoc+weasyprint",
        acceleration_used=None,
        options_fingerprint="sha256:options",
        warnings=[],
    )
    job = runtime.get_job(job_id)
    assert job is not None
    job.artifact_path.unlink()
    ref = job.terminal_artifact_object_refs["primary"]
    assert isinstance(ref, TerminalArtifactObjectRef)
    runtime.terminal_artifact_store.remove_for_test(ref)

    artifact_response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr-object-missing"},
    )

    rendered = artifact_response.text
    assert artifact_response.status_code == 404
    assert artifact_response.json()["error"]["code"] == "artifact_not_available"
    for forbidden in (
        ref.bucket,
        ref.key,
        "ACCESS_KEY",
        "SECRET_ACCESS_KEY",
        "X-Amz-",
        "r2.cloudflarestorage.com",
    ):
        assert forbidden not in rendered


def test_readyz_exposes_object_store_readiness_fields_for_local_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", str(tmp_path / "service_data"))
    client, _app = _object_store_client(tmp_path)

    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_store"]["backend"] == "local"
    assert payload["object_store"]["config_ready"] is True
    assert payload["object_store"]["reachable"] is True
    assert payload["object_store"]["api_access"] == "read_write"
    assert payload["object_store"]["worker_access"] == "read_write"
    assert payload["local_scratch"]["ready"] is True


def test_readyz_configures_worker_probe_for_normal_r2_service_app(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", str(tmp_path / "service_data"))
    object_store = TerminalObjectStoreConfig(
        backend="r2",
        endpoint_url="https://example.invalid",
        region="auto",
        bucket="sir-test",
        access_key_id="access-key",
        secret_access_key="secret-key",
        key_prefix="task-381-test",
    )
    readiness = ObjectStoreReadiness(
        backend="r2",
        config_ready=True,
        reachable=True,
        api_access="read_write",
        worker_access="read_write",
        secret_sources={"SIR_CONVERT_A_LOT_R2_BUCKET": "env:present"},
    )

    def _build_probe_store(
        *,
        config: TerminalObjectStoreConfig,
        data_root: Path,
        runtime_profile: str,
    ) -> _ReadinessOnlyStore:
        assert config == object_store
        assert data_root == tmp_path / "service_data"
        assert runtime_profile in {"service-api", "service-worker"}
        return _ReadinessOnlyStore(readiness)

    monkeypatch.setattr(
        runtime_engine_v2_module,
        "build_terminal_artifact_store",
        _build_probe_store,
    )
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data",
            enable_supervisor=False,
            run_jobs_on_submit=False,
            object_store=object_store,
        ),
        service_profile="task-381-test",
        expected_service_profile="task-381-test",
    )
    client = TestClient(app)

    response = client.get("/readyz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["object_store"]["backend"] == "r2"
    assert payload["object_store"]["api_access"] == "read_write"
    assert payload["object_store"]["worker_access"] == "read_write"
    assert payload["object_store"]["reachable"] is True
    assert payload["object_store"]["secret_sources"] == {
        "SIR_CONVERT_A_LOT_R2_BUCKET": "env:present",
        "worker:SIR_CONVERT_A_LOT_R2_BUCKET": "env:present",
    }


def test_readyz_reports_api_ready_worker_unreachable_as_distinct_r2_role_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", str(tmp_path / "service_data"))
    client, app = _object_store_client(tmp_path)
    client.get("/readyz")
    runtime = app.state.runtime_v2
    runtime.config = replace(
        runtime.config,
        object_store=TerminalObjectStoreConfig(
            backend="r2",
            endpoint_url="https://example.invalid",
            region="auto",
            bucket="sir-test",
            access_key_id="access-key",
            secret_access_key="secret-key",
            key_prefix="task-381-test",
        ),
    )
    runtime.terminal_artifact_store = _ReadinessOnlyStore(
        ObjectStoreReadiness(
            backend="r2",
            config_ready=True,
            reachable=True,
            api_access="read_write",
            worker_access="read_write",
            secret_sources={},
        )
    )
    app.state.worker_terminal_artifact_store = _ReadinessOnlyStore(
        ObjectStoreReadiness(
            backend="r2",
            config_ready=True,
            reachable=False,
            api_access="unreachable",
            worker_access="unreachable",
            secret_sources={},
            reason="worker_probe_failed",
        )
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["object_store"]["api_access"] == "read_write"
    assert payload["object_store"]["worker_access"] == "unreachable"
    assert payload["object_store"]["reachable"] is False
    assert {reason["code"] for reason in payload["reasons"]} == {"object_store_unavailable"}


def test_readyz_reports_api_unreachable_worker_ready_as_distinct_r2_role_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SIR_CONVERT_A_LOT_SERVICE_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_EXPECTED_REVISION", "test-revision")
    monkeypatch.setenv("SIR_CONVERT_A_LOT_DATA_DIR", str(tmp_path / "service_data"))
    client, app = _object_store_client(tmp_path)
    client.get("/readyz")
    runtime = app.state.runtime_v2
    runtime.config = replace(
        runtime.config,
        object_store=TerminalObjectStoreConfig(
            backend="r2",
            endpoint_url="https://example.invalid",
            region="auto",
            bucket="sir-test",
            access_key_id="access-key",
            secret_access_key="secret-key",
            key_prefix="task-381-test",
        ),
    )
    runtime.terminal_artifact_store = _ReadinessOnlyStore(
        ObjectStoreReadiness(
            backend="r2",
            config_ready=True,
            reachable=False,
            api_access="unreachable",
            worker_access="unreachable",
            secret_sources={},
            reason="api_probe_failed",
        )
    )
    app.state.worker_terminal_artifact_store = _ReadinessOnlyStore(
        ObjectStoreReadiness(
            backend="r2",
            config_ready=True,
            reachable=True,
            api_access="read_write",
            worker_access="read_write",
            secret_sources={},
        )
    )

    response = client.get("/readyz")

    assert response.status_code == 503
    payload = response.json()
    assert payload["object_store"]["api_access"] == "unreachable"
    assert payload["object_store"]["worker_access"] == "read_write"
    assert payload["object_store"]["reachable"] is False
    assert {reason["code"] for reason in payload["reasons"]} == {"object_store_unavailable"}


def _object_store_client(tmp_path: Path) -> tuple[TestClient, FastAPI]:
    return build_client(
        tmp_path,
        run_jobs_on_submit=False,
        object_store=TerminalObjectStoreConfig(
            backend="local",
            key_prefix="task-381-test",
        ),
    )


def _artifact_entries(payload: object) -> dict[str, dict[str, object]]:
    if not isinstance(payload, dict):
        raise AssertionError("Artifact manifest must be a JSON object.")
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise AssertionError("Artifact manifest must include an artifacts list.")
    entries: dict[str, dict[str, object]] = {}
    for entry in artifacts:
        if not isinstance(entry, dict):
            raise AssertionError("Artifact manifest entries must be JSON objects.")
        artifact_key = entry.get("artifact_key")
        if not isinstance(artifact_key, str):
            raise AssertionError("Artifact manifest entries must include artifact_key.")
        entries[artifact_key] = {str(key): value for key, value in entry.items()}
    return entries


class _ReadinessOnlyStore:
    backend = "r2"

    def __init__(self, readiness: ObjectStoreReadiness) -> None:
        self._readiness = readiness

    def put_artifact(self, request: TerminalArtifactWriteRequest) -> TerminalArtifactObjectRef:
        raise NotImplementedError

    def read_artifact(self, ref: TerminalArtifactObjectRef) -> TerminalArtifactRead:
        raise NotImplementedError

    def readiness(self) -> ObjectStoreReadiness:
        return self._readiness
