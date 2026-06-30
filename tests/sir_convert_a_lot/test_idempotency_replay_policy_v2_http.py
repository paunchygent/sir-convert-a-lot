"""HTTP preservation tests for Service API v2 idempotent replay policy.

Purpose:
    Preserve public create-job replay behavior while the business policy moves
    behind the application-layer idempotency replay service.

Relationships:
    - Exercises `interfaces.http_routes_jobs_v2` through the public FastAPI
      route.
    - Complements pure application-service tests in
      `test_idempotency_replay_service_v2`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from tests.sir_convert_a_lot.http_routes_jobs_v2_edge_cases_test_support import (
    build_client,
    disable_run_job_async,
    post_create,
)


def test_running_idempotency_replay_remains_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_run_job_async(monkeypatch)
    client, app = build_client(tmp_path)

    first = post_create(
        client,
        idempotency_key="idem-task-375-running-strict",
        file_bytes=b"stable-running-body",
    )
    assert first.status_code == 202
    job_id = first.json()["job"]["job_id"]
    assert app.state.runtime_v2.job_store.claim_queued_job(job_id)

    replay = post_create(
        client,
        idempotency_key="idem-task-375-running-strict",
        file_bytes=b"stable-running-body",
    )

    assert replay.status_code == 202
    assert replay.headers["X-Idempotent-Replay"] == "true"
    payload = replay.json()
    assert payload["job"]["job_id"] == job_id
    assert payload["job"]["status"] == JobStatus.RUNNING.value
    assert payload["idempotency"]["state"] == "strict_replay"
    assert payload["idempotency"]["reason"] is None
