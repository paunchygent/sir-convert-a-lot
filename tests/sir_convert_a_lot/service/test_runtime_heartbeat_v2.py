"""Runtime heartbeat v2 loop branch coverage tests.

Purpose:
    Verify heartbeat worker termination behavior for non-running jobs and
    missing/expired job conditions without relying on flaky timing.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.runtime_heartbeat_v2`.
    - Uses v2 job-store exceptions from `job_store_models_v2`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.runtime_heartbeat_v2 import (
    start_conversion_heartbeat_v2,
)


def test_heartbeat_thread_exits_when_touch_returns_false(monkeypatch, tmp_path: Path) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )
    calls = 0

    def _return_false(job_id: str) -> bool:
        nonlocal calls
        del job_id
        calls += 1
        return False

    monkeypatch.setattr(store, "touch_heartbeat", _return_false)

    stop_event, thread = start_conversion_heartbeat_v2(
        job_store=store,
        job_id="jobv2_heartbeat_false",
        heartbeat_interval_seconds=0.01,
    )

    thread.join(timeout=1.0)
    stop_event.set()

    assert thread.is_alive() is False
    assert calls == 1


@pytest.mark.parametrize("error_type", [JobMissingV2, JobExpiredV2])
def test_heartbeat_thread_exits_when_touch_raises_missing_or_expired(
    monkeypatch, tmp_path: Path, error_type: type[JobMissingV2] | type[JobExpiredV2]
) -> None:
    store = JobStoreV2(
        data_root=tmp_path / "service_data",
        raw_ttl_seconds=3600,
        artifact_ttl_seconds=3600,
    )
    calls = 0

    def _raise_error(job_id: str) -> bool:
        nonlocal calls
        calls += 1
        raise error_type(job_id=job_id)

    monkeypatch.setattr(store, "touch_heartbeat", _raise_error)

    stop_event, thread = start_conversion_heartbeat_v2(
        job_store=store,
        job_id="jobv2_heartbeat_error",
        heartbeat_interval_seconds=0.01,
    )

    thread.join(timeout=1.0)
    stop_event.set()

    assert thread.is_alive() is False
    assert calls == 1
