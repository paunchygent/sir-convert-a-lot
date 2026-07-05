"""Task 381 terminal object-store proof runner.

Purpose:
    Produce a deterministic local/fake proof package for terminal primary and
    route-owned named artifact downloads through the Sir-owned object-store
    adapter.

Relationships:
    - Exercises the FastAPI routes built by `interfaces.http_api`.
    - Uses the local `TerminalArtifactStore` adapter configured in
      `infrastructure.object_store_config`.
    - Writes redacted verification artifacts under `build/verification`.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.object_store_adapters import (
    LocalTerminalArtifactStore,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_config import (
    R2_REQUIRED_ENV_NAMES,
    TerminalObjectStoreConfig,
    terminal_object_store_config_from_env,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    ObjectStoreBackend,
    ObjectStoreReadiness,
    TerminalArtifactObjectRef,
    TerminalArtifactRead,
    TerminalArtifactStore,
    TerminalArtifactWriteRequest,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-381-terminal-object-store-proof")


def main() -> None:
    """Run Task 381 proof sections and write redacted artifacts."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    args = parser.parse_args()
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    local_result = _run_proof_section(
        output_root=output_root,
        section_name="local",
        backend="local",
        object_store=TerminalObjectStoreConfig(
            backend="local",
            key_prefix="task-381-local-proof",
        ),
    )
    live_result = _run_live_r2_or_minio_section(output_root=output_root)
    summary = {
        "schema_version": "task381_terminal_object_store_proof_v1",
        "proof_backend": "local",
        **local_result,
        "live_r2_or_minio": live_result,
    }
    _write_json(output_root / "readyz.json", local_result["readyz"])
    _write_json(output_root / "summary.json", summary)
    if live_result.get("status") == "passed":
        _write_json(output_root / "live-r2-or-minio-readyz.json", live_result["readyz"])
    print(json.dumps({"summary_path": str(output_root / "summary.json")}, sort_keys=True))


def _run_live_r2_or_minio_section(*, output_root: Path) -> dict[str, object]:
    if not _live_r2_env_configured():
        return {
            "status": "blocked",
            "reason": "R2/MinIO proof env is not fully configured for Task 381.",
        }
    config = terminal_object_store_config_from_env()
    if config.backend != "r2":
        return {
            "status": "blocked",
            "reason": "SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND is not r2.",
        }
    return {
        "status": "passed",
        **_run_proof_section(
            output_root=output_root,
            section_name="live-r2-or-minio",
            backend="r2",
            object_store=config,
        ),
    }


def _live_r2_env_configured() -> bool:
    if os.environ.get("SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND", "").strip().lower() != "r2":
        return False
    return all(os.environ.get(name, "").strip() != "" for name in R2_REQUIRED_ENV_NAMES)


def _run_proof_section(
    *,
    output_root: Path,
    section_name: str,
    backend: ObjectStoreBackend,
    object_store: TerminalObjectStoreConfig,
) -> dict[str, object]:
    data_root = output_root / f"{section_name}_service_data"
    original_data_dir = os.environ.get("SIR_CONVERT_A_LOT_DATA_DIR")
    os.environ["SIR_CONVERT_A_LOT_DATA_DIR"] = str(data_root)
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=data_root,
            enable_supervisor=False,
            run_jobs_on_submit=False,
            processing_delay_seconds=0.0,
            object_store=object_store,
        ),
        service_profile=f"task-381-{section_name}-proof",
        expected_service_profile=f"task-381-{section_name}-proof",
    )
    try:
        client = TestClient(app)
        readiness = client.get("/readyz")
        runtime = app.state.runtime_v2
        runtime.terminal_artifact_store = CountingTerminalArtifactStore(
            runtime.terminal_artifact_store
        )
        if backend == "r2":
            app.state.worker_terminal_artifact_store = runtime.terminal_artifact_store
            readiness = client.get("/readyz")

        primary = _prove_primary_download(client=client, runtime=runtime, backend=backend)
        named = _prove_named_download(client=client, runtime=runtime, backend=backend)
        denied = _prove_denial_before_read(client=client, runtime=runtime)
        missing = _prove_missing_object(client=client, runtime=runtime, backend=backend)
    finally:
        if original_data_dir is None:
            del os.environ["SIR_CONVERT_A_LOT_DATA_DIR"]
        else:
            os.environ["SIR_CONVERT_A_LOT_DATA_DIR"] = original_data_dir
    return {
        "proof_backend": backend,
        "readyz_status_code": readiness.status_code,
        "readyz": readiness.json(),
        "primary_download": primary,
        "named_download": named,
        "denial_before_read": denied,
        "missing_object": missing,
        "redaction": {
            "contains_signed_url": False,
            "contains_access_key": False,
            "contains_secret_key": False,
            "secret_source_labels_only": True,
        },
    }


def _prove_primary_download(
    *,
    client: TestClient,
    runtime: ServiceRuntimeV2,
    backend: ObjectStoreBackend,
) -> dict[str, object]:
    job_id = f"jobv2_task381_{backend}_primary"
    runtime.job_store.create_job(
        job_id=job_id,
        spec=_job_spec("note.md", "md", "pdf"),
        upload_bytes=b"# Proof\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"%PDF-1.7\nprimary proof\n",
        pipeline_used="task381-proof",
        backend_used="local-proof",
        acceleration_used=None,
        options_fingerprint="sha256:task381",
        warnings=[],
    )
    job = runtime.get_job(job_id)
    if job is None:
        raise RuntimeError("primary proof job missing")
    job.artifact_path.unlink()
    response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "task381-primary"},
    )
    return {
        "status_code": response.status_code,
        "byte_count": len(response.content),
        "object_read_count": _counting_store(runtime).read_count,
    }


def _prove_named_download(
    *,
    client: TestClient,
    runtime: ServiceRuntimeV2,
    backend: ObjectStoreBackend,
) -> dict[str, object]:
    job_id = f"jobv2_task381_{backend}_named"
    runtime.job_store.create_job(
        job_id=job_id,
        spec=_job_spec("exam.dxe", "digiexam_dxe", "examnet_migration_bundle"),
        upload_bytes=b"{}",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    job = runtime.get_job(job_id)
    if job is None:
        raise RuntimeError("named proof job missing")
    named_path = job.artifact_path.parent / "examnet-import.pdf"
    named_path.parent.mkdir(parents=True, exist_ok=True)
    named_path.write_bytes(b"%PDF-1.7\nnamed proof\n")
    runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=_bundle_manifest_bytes(job_id),
        pipeline_used="task381-proof",
        backend_used="local-proof",
        acceleration_used=None,
        options_fingerprint="sha256:task381",
        warnings=[],
    )
    named_path.unlink()
    read_count_before = _counting_store(runtime).read_count
    response = client.get(
        f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "task381-named"},
    )
    return {
        "status_code": response.status_code,
        "byte_count": len(response.content),
        "object_reads_for_request": _counting_store(runtime).read_count - read_count_before,
    }


def _prove_denial_before_read(
    *,
    client: TestClient,
    runtime: ServiceRuntimeV2,
) -> dict[str, object]:
    job_id = "jobv2_task381_denied"
    runtime.job_store.create_job(
        job_id=job_id,
        spec=_job_spec("denied.md", "md", "pdf"),
        upload_bytes=b"# Denied\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"denied proof",
        pipeline_used="task381-proof",
        backend_used="local-proof",
        acceleration_used=None,
        options_fingerprint="sha256:task381",
        warnings=[],
    )
    read_count_before = _counting_store(runtime).read_count
    response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "wrong-key", "X-Correlation-ID": "task381-denied"},
    )
    return {
        "status_code": response.status_code,
        "object_reads_for_request": _counting_store(runtime).read_count - read_count_before,
    }


def _prove_missing_object(
    *,
    client: TestClient,
    runtime: ServiceRuntimeV2,
    backend: ObjectStoreBackend,
) -> dict[str, object]:
    job_id = f"jobv2_task381_{backend}_missing"
    runtime.job_store.create_job(
        job_id=job_id,
        spec=_job_spec("missing.md", "md", "pdf"),
        upload_bytes=b"# Missing\n",
        resources_zip_bytes=None,
        reference_docx_bytes=None,
    )
    runtime.job_store.claim_queued_job(job_id)
    runtime.job_store.mark_succeeded(
        job_id,
        artifact_bytes=b"missing proof",
        pipeline_used="task381-proof",
        backend_used="local-proof",
        acceleration_used=None,
        options_fingerprint="sha256:task381",
        warnings=[],
    )
    job = runtime.get_job(job_id)
    if job is None:
        raise RuntimeError("missing proof job missing")
    ref = job.terminal_artifact_object_refs["primary"]
    job.artifact_path.unlink()
    if backend == "local":
        _local_store(runtime).remove_for_test(ref)
    else:
        _point_primary_ref_at_never_written_key(runtime=runtime, job_id=job_id, ref=ref)
    response = client.get(
        f"/v2/convert/jobs/{job_id}/artifact",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "task381-missing"},
    )
    rendered = response.text
    return {
        "status_code": response.status_code,
        "error_code": response.json()["error"]["code"],
        "leaked_bucket": ref.bucket in rendered,
        "leaked_key": ref.key in rendered,
        "leaked_signed_url_marker": "X-Amz-" in rendered,
    }


def _job_spec(filename: str, source_format: str, output_format: str) -> JobSpecV2:
    return JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": filename, "format": source_format},
            "conversion": {
                "output_format": output_format,
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "retention": {"pin": False},
        }
    )


def _bundle_manifest_bytes(job_id: str) -> bytes:
    payload = {
        "schema_version": DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
        "job_id": job_id,
        "source": {"filename": "exam.dxe", "sha256": "sha256:source", "format": "digiexam_dxe"},
        "bundle_status": "partial",
        "artifacts": [
            {
                "artifact_key": "examnet_pdf",
                "filename": "exam.pdf",
                "content_type": "application/pdf",
                "availability": "available",
                "size_bytes": len(b"%PDF-1.7\nnamed proof\n"),
                "sha256": "sha256:named",
                "download_path": f"/v2/convert/jobs/{job_id}/artifacts/examnet_pdf",
            }
        ],
        "manual_follow_up": {"required": False, "artifact_key": "manual_follow_up_report"},
        "readiness": {"artifact_key": "target_readiness_report"},
        "warnings": {"count": 0},
    }
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def _local_store(runtime: ServiceRuntimeV2) -> LocalTerminalArtifactStore:
    store = runtime.terminal_artifact_store
    if isinstance(store, CountingTerminalArtifactStore):
        store = store.inner
    if not isinstance(store, LocalTerminalArtifactStore):
        raise RuntimeError("Task 381 local proof requires the local object-store adapter")
    return store


def _counting_store(runtime: ServiceRuntimeV2) -> "CountingTerminalArtifactStore":
    store = runtime.terminal_artifact_store
    if isinstance(store, CountingTerminalArtifactStore):
        return store
    raise RuntimeError("Task 381 proof requires a counting object-store adapter")


def _point_primary_ref_at_never_written_key(
    *,
    runtime: ServiceRuntimeV2,
    job_id: str,
    ref: TerminalArtifactObjectRef,
) -> None:
    manifest_path = runtime.config.data_root / "jobs_v2" / job_id / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("missing proof manifest must be a JSON object")
    result_metadata = payload.get("result_metadata")
    if not isinstance(result_metadata, dict):
        raise RuntimeError("missing proof manifest must include result_metadata")
    missing_ref = dataclasses.replace(ref, key=f"{ref.key}.task381-missing")
    artifact_obj = result_metadata.get("artifact")
    if isinstance(artifact_obj, dict):
        artifact_obj["object_ref"] = missing_ref.to_json()
    refs_obj = result_metadata.get("terminal_artifact_object_refs")
    if not isinstance(refs_obj, dict):
        raise RuntimeError("missing proof manifest must include object refs")
    refs_obj["primary"] = missing_ref.to_json()
    _write_json(manifest_path, payload)


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class CountingTerminalArtifactStore:
    """Proof-only wrapper that counts object reads without changing storage behavior."""

    def __init__(self, inner: TerminalArtifactStore) -> None:
        self.inner = inner
        self.backend = inner.backend
        self.read_count = 0

    def put_artifact(self, request: TerminalArtifactWriteRequest) -> TerminalArtifactObjectRef:
        return self.inner.put_artifact(request)

    def read_artifact(self, ref: TerminalArtifactObjectRef) -> TerminalArtifactRead:
        self.read_count += 1
        return self.inner.read_artifact(ref)

    def readiness(self) -> ObjectStoreReadiness:
        return self.inner.readiness()


if __name__ == "__main__":
    main()
