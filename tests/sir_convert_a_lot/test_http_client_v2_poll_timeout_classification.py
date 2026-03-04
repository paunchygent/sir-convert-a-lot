"""HTTP client v2 polling timeout classification tests.

Purpose:
    Validate that the v2 client distinguishes between:
      - active long-running jobs that exceed the local poll window, and
      - stalled jobs with stale heartbeat/progress activity.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_client_v2.SirConvertALotClientV2`.
    - Ensures CLI/adapter-facing error codes remain stable for manifest semantics.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest

from scripts.sir_convert_a_lot.interfaces.http_client_v2 import (
    ClientErrorV2,
    SirConvertALotClientV2,
)


def _rfc3339(dt: datetime) -> str:
    return dt.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_wait_for_terminal_status_timeout_is_active_when_heartbeat_is_fresh() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    payload = {
        "api_version": "v2",
        "job": {
            "job_id": "job_active",
            "status": "running",
            "created_at": _rfc3339(now - timedelta(seconds=10)),
            "updated_at": _rfc3339(now - timedelta(seconds=1)),
            "progress": {"stage": "convert", "last_heartbeat_at": _rfc3339(now)},
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_active":
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"api_version": "v2", "error": {"code": "not_found"}})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test", transport=transport)
    with SirConvertALotClientV2(
        base_url="http://test", api_key="k", http_client=http_client
    ) as client:
        with pytest.raises(ClientErrorV2) as exc_info:
            client.wait_for_terminal_status(
                "job_active",
                timeout_seconds=0.0,
                stall_timeout_seconds=30.0,
                poll_interval_seconds=0.0,
            )

    assert exc_info.value.code == "job_poll_window_exceeded"
    assert exc_info.value.status_code == 202
    assert exc_info.value.job_id == "job_active"


def test_wait_for_terminal_status_timeout_is_stalled_when_heartbeat_is_stale() -> None:
    now = datetime.now(UTC).replace(microsecond=0)
    payload = {
        "api_version": "v2",
        "job": {
            "job_id": "job_stalled",
            "status": "running",
            "created_at": _rfc3339(now - timedelta(seconds=600)),
            "updated_at": _rfc3339(now - timedelta(seconds=600)),
            "progress": {
                "stage": "convert",
                "last_heartbeat_at": _rfc3339(now - timedelta(seconds=600)),
            },
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_stalled":
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"api_version": "v2", "error": {"code": "not_found"}})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test", transport=transport)
    with SirConvertALotClientV2(
        base_url="http://test", api_key="k", http_client=http_client
    ) as client:
        with pytest.raises(ClientErrorV2) as exc_info:
            client.wait_for_terminal_status(
                "job_stalled",
                timeout_seconds=0.0,
                stall_timeout_seconds=30.0,
                poll_interval_seconds=0.0,
            )

    assert exc_info.value.code == "job_timeout"
    assert exc_info.value.status_code == 408
    assert exc_info.value.job_id == "job_stalled"


def test_wait_for_terminal_status_timeout_is_active_when_activity_timestamp_is_missing() -> None:
    payload = {"api_version": "v2", "job": {"job_id": "job_minimal", "status": "running"}}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v2/convert/jobs/job_minimal":
            return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"api_version": "v2", "error": {"code": "not_found"}})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(base_url="http://test", transport=transport)
    with SirConvertALotClientV2(
        base_url="http://test", api_key="k", http_client=http_client
    ) as client:
        with pytest.raises(ClientErrorV2) as exc_info:
            client.wait_for_terminal_status(
                "job_minimal",
                timeout_seconds=0.0,
                stall_timeout_seconds=30.0,
                poll_interval_seconds=0.0,
            )

    assert exc_info.value.code == "job_poll_window_exceeded"
    assert exc_info.value.status_code == 202
    assert exc_info.value.job_id == "job_minimal"
