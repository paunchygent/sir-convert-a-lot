"""HTTP-boundary tests for the Sir exam-retirement stored job-spec migration.

Purpose:
    Prove that retained manifests in the real pre-retirement schema break
    generic job reads and admission, that the one-time migration's dry run
    changes nothing, that `--execute` makes the store readable and admissible
    again, that re-running it is a no-op, that exam jobs block it without
    writes, and that live idempotency records neither block it nor change.

Relationships:
    - Exercises `infrastructure.retired_spec_fields_migration_v2` through
      `interfaces.cli_retired_spec_fields_migration_v2.main` and the public v2 routes.
    - Uses the route-test client helpers from
      `http_routes_jobs_v2_edge_cases_test_support`.
"""

from __future__ import annotations

import copy
import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.interfaces.cli_retired_spec_fields_migration_v2 import (
    EXIT_BLOCKED,
    EXIT_CURRENT,
    EXIT_REWRITE_REQUIRED,
    main,
)
from tests.sir_convert_a_lot.service.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    disable_run_job_async,
    post_create,
)

# `JobSpecV2.model_validate(...).model_dump(mode="json")` at revision
# 184bc836^ (last pre-retirement schema) for a pinned note.md -> pdf request;
# `build_initial_manifest` stored exactly this dump as `job_spec`.
PRE_RETIREMENT_GENERIC_JOB_SPEC: dict[str, object] = {
    "api_version": "v2",
    "audio_transcription_options": None,
    "conversion": {
        "artifact_language": None,
        "css_filenames": [],
        "output_format": "pdf",
        "page_css_mode": None,
        "pdf_layout": None,
        "reference_docx_filename": None,
        "targets": [],
        "template": None,
    },
    "digiexam_migration_options": None,
    "execution": None,
    "pdf_options": None,
    "retention": {"pin": True},
    "source": {"filename": "note.md", "format": "md", "kind": "upload"},
    "transcript_formatter_options": None,
}
EXPIRED_RECORD_AGE = timedelta(hours=25)
# Fingerprint encoding before the retirement: three empty exam-companion slots.
PRE_RETIREMENT_FINGERPRINT = "d35869ee0d3e07dac28097b45d2b6b0541f2d809aa7283e207b52e30256939ce"


def _retained_generic_job(tmp_path: Path) -> tuple[TestClient, FastAPI, str, Path]:
    """Admit one generic job, rewrite it to the pre-retirement shape, and pin its live record."""
    _, app = build_client(tmp_path, run_jobs_on_submit=False)
    client = TestClient(app, raise_server_exceptions=False)
    created = post_create(client, idempotency_key="idem-retained-generic")
    assert created.status_code == 202
    job_id = created.json()["job"]["job_id"]
    manifest_path = _store_pre_retirement_spec(app, job_id, PRE_RETIREMENT_GENERIC_JOB_SPEC)
    _set_idempotency_record_fingerprint(
        app.state.runtime_v2.idempotency_store.dir, fingerprint=PRE_RETIREMENT_FINGERPRINT
    )
    return client, app, job_id, manifest_path


def _store_pre_retirement_spec(app: FastAPI, job_id: str, spec: dict[str, object]) -> Path:
    """Write `spec` and the retired diagnostics slot into one job's stored manifest."""
    manifest_path: Path = app.state.runtime_v2.job_store._manifest_path(job_id)
    manifest = read_json(manifest_path)
    manifest["job_spec"] = copy.deepcopy(spec)
    source = spec["source"]
    conversion = spec["conversion"]
    assert isinstance(source, dict) and isinstance(conversion, dict)
    manifest["source_format"] = source["format"]
    manifest["output_format"] = conversion["output_format"]
    diagnostics = manifest["diagnostics"]
    assert isinstance(diagnostics, dict)
    diagnostics["structured_llm_admission"] = None
    atomic_write_json(manifest_path, manifest)
    return manifest_path


def _set_idempotency_record_fingerprint(idempotency_dir: Path, *, fingerprint: str) -> None:
    for record_path in idempotency_dir.glob("*.json"):
        record = read_json(record_path)
        record["fingerprint"] = fingerprint
        atomic_write_json(record_path, record)


def _age_idempotency_records(idempotency_dir: Path) -> None:
    for record_path in idempotency_dir.glob("*.json"):
        record = read_json(record_path)
        record["created_at"] = dt_to_rfc3339(utc_now() - EXPIRED_RECORD_AGE)
        atomic_write_json(record_path, record)


def _run_migration(
    data_root: Path, capsys: pytest.CaptureFixture[str], *extra: str
) -> tuple[int, dict[str, object]]:
    exit_code = main(["--data-root", str(data_root), *extra])
    report = json.loads(capsys.readouterr().out)
    assert isinstance(report, dict)
    return exit_code, report


def test_pre_retirement_manifest_is_unreadable_until_migrated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    disable_run_job_async(monkeypatch)
    client, app, job_id, manifest_path = _retained_generic_job(tmp_path)
    data_root = app.state.runtime_v2.job_store.data_root

    assert client.get(f"/v2/convert/jobs/{job_id}", headers=_headers()).status_code == 500
    assert post_create(client, idempotency_key="idem-new-before").status_code == 500

    before = manifest_path.read_bytes()
    exit_code, report = _run_migration(data_root, capsys)
    assert exit_code == EXIT_REWRITE_REQUIRED
    assert report["mode"] == "dry_run"
    assert report["outcome"] == "rewrite_required"
    assert report["jobs_requiring_rewrite"] == [job_id]
    assert report["jobs_rewritten"] == []
    assert manifest_path.read_bytes() == before

    exit_code, report = _run_migration(data_root, capsys, "--execute")
    assert exit_code == EXIT_CURRENT
    assert report["outcome"] == "rewritten"
    assert report["jobs_rewritten"] == [job_id]
    migrated = read_json(manifest_path)
    migrated_spec = migrated["job_spec"]
    assert isinstance(migrated_spec, dict)
    assert "digiexam_migration_options" not in migrated_spec
    conversion = migrated_spec["conversion"]
    assert isinstance(conversion, dict)
    assert "targets" not in conversion
    assert "artifact_language" not in conversion
    diagnostics = migrated["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert "structured_llm_admission" not in diagnostics
    assert migrated["job_id"] == job_id
    assert migrated["status"] == json.loads(before)["status"]

    read = client.get(f"/v2/convert/jobs/{job_id}", headers=_headers())
    assert read.status_code == 200
    assert read.json()["job"]["job_id"] == job_id


def test_migrated_store_admits_and_replays_generic_requests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    disable_run_job_async(monkeypatch)
    client, app, job_id, _ = _retained_generic_job(tmp_path)
    data_root = app.state.runtime_v2.job_store.data_root
    _age_idempotency_records(app.state.runtime_v2.idempotency_store.dir)
    exit_code, _ = _run_migration(data_root, capsys, "--execute")
    assert exit_code == EXIT_CURRENT

    # The pre-retirement record is past its replay window, so the same key
    # admits a fresh job instead of a false payload conflict.
    retried = post_create(client, idempotency_key="idem-retained-generic")
    assert retried.status_code == 202
    retried_job_id = retried.json()["job"]["job_id"]
    assert retried_job_id != job_id

    replay = post_create(client, idempotency_key="idem-retained-generic")
    assert replay.status_code == 202
    assert replay.headers["X-Idempotent-Replay"] == "true"
    assert replay.json()["job"]["job_id"] == retried_job_id

    changed = post_create(
        client, idempotency_key="idem-retained-generic", file_bytes=b"# Changed\n"
    )
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"

    fresh = post_create(client, idempotency_key="idem-new-after")
    assert fresh.status_code == 202
    assert client.get(f"/v2/convert/jobs/{job_id}", headers=_headers()).status_code == 200


def test_migration_rerun_is_a_no_op(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    disable_run_job_async(monkeypatch)
    _, app, _, manifest_path = _retained_generic_job(tmp_path)
    data_root = app.state.runtime_v2.job_store.data_root
    assert _run_migration(data_root, capsys, "--execute")[0] == EXIT_CURRENT
    after_first = manifest_path.read_bytes()

    exit_code, report = _run_migration(data_root, capsys, "--execute")
    assert exit_code == EXIT_CURRENT
    assert report["outcome"] == "clean"
    assert report["jobs_requiring_rewrite"] == []
    assert report["jobs_rewritten"] == []
    assert manifest_path.read_bytes() == after_first

    exit_code, report = _run_migration(data_root, capsys)
    assert exit_code == EXIT_CURRENT
    assert report["outcome"] == "clean"


def test_exam_job_blocks_migration_without_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    disable_run_job_async(monkeypatch)
    _, app = build_client(tmp_path, run_jobs_on_submit=False)
    client = TestClient(app, raise_server_exceptions=False)
    generic_job_id = post_create(client, idempotency_key="idem-generic").json()["job"]["job_id"]
    exam_job_id = post_create(client, idempotency_key="idem-exam").json()["job"]["job_id"]
    exam_spec = copy.deepcopy(PRE_RETIREMENT_GENERIC_JOB_SPEC)
    exam_spec["source"] = {"filename": "exam.dxe", "format": "digiexam_dxe", "kind": "upload"}
    exam_conversion = exam_spec["conversion"]
    assert isinstance(exam_conversion, dict)
    exam_conversion["output_format"] = "examnet_migration_bundle"
    generic_manifest_path = _store_pre_retirement_spec(
        app, generic_job_id, PRE_RETIREMENT_GENERIC_JOB_SPEC
    )
    exam_manifest_path = _store_pre_retirement_spec(app, exam_job_id, exam_spec)
    runtime = app.state.runtime_v2
    generic_before = generic_manifest_path.read_bytes()
    exam_before = exam_manifest_path.read_bytes()

    exit_code, report = _run_migration(runtime.job_store.data_root, capsys, "--execute")

    assert exit_code == EXIT_BLOCKED
    assert report["outcome"] == "blocked"
    assert report["jobs_rewritten"] == []
    assert report["unmigratable_jobs"] == [
        {"job_id": exam_job_id, "reason": "exam job: retired source format"}
    ]
    assert generic_manifest_path.read_bytes() == generic_before
    assert exam_manifest_path.read_bytes() == exam_before


def test_live_idempotency_record_does_not_block_and_is_left_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    disable_run_job_async(monkeypatch)
    client, app, job_id, manifest_path = _retained_generic_job(tmp_path)
    runtime = app.state.runtime_v2
    record_dir = runtime.idempotency_store.dir
    records_before = {path.name: path.read_bytes() for path in record_dir.glob("*.json")}
    manifest_before = manifest_path.read_bytes()

    exit_code, report = _run_migration(runtime.job_store.data_root, capsys)
    assert exit_code == EXIT_REWRITE_REQUIRED
    assert report["outcome"] == "rewrite_required"
    assert report["jobs_rewritten"] == []
    assert "live_idempotency_records" not in report
    assert "idempotency_window_closes_at" not in report
    assert manifest_path.read_bytes() == manifest_before
    assert {path.name: path.read_bytes() for path in record_dir.glob("*.json")} == records_before

    exit_code, report = _run_migration(runtime.job_store.data_root, capsys, "--execute")
    assert exit_code == EXIT_CURRENT
    assert report["outcome"] == "rewritten"
    assert report["jobs_rewritten"] == [job_id]
    assert "live_idempotency_records" not in report
    assert "idempotency_window_closes_at" not in report
    assert {path.name: path.read_bytes() for path in record_dir.glob("*.json")} == records_before

    retried = post_create(
        client, idempotency_key="idem-retained-generic", file_bytes=b"# Changed\n"
    )
    assert retried.status_code == 409
    assert retried.json()["error"]["code"] == "idempotency_key_reused_with_different_payload"
    assert {path.name: path.read_bytes() for path in record_dir.glob("*.json")} == records_before


def _headers() -> dict[str, str]:
    return {"X-API-Key": "secret-key"}
