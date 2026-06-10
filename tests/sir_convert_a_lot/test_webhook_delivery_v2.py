"""Webhook delivery worker v2 reliability and security tests.

Purpose:
    Verify queue-backed webhook delivery behavior for retries, DLQ handoff,
    signature generation, and replay-safe verification semantics.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.webhook_delivery_v2`.
    - Uses webhook targets from `webhook_subscriptions_v2_store`.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping

import pytest

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import JobLifecycleEventRecordV2
from scripts.sir_convert_a_lot.infrastructure.webhook_delivery_v2 import WebhookDeliveryWorkerV2
from scripts.sir_convert_a_lot.infrastructure.webhook_signing_v2 import (
    WebhookSignatureValidationErrorV2,
    compute_webhook_signature_v2,
    verify_webhook_signature_v2,
)
from scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2_store import (
    WebhookSubscriptionStoreV2,
)


def _build_event(*, event_id: str, sequence: int, job_id: str) -> JobLifecycleEventRecordV2:
    source_format = SourceFormatV2.PDF
    target_format = OutputFormatV2.MD
    return JobLifecycleEventRecordV2(
        event_id=event_id,
        event_type="job.succeeded",
        sequence=sequence,
        occurred_at=datetime(2026, 2, 28, 12, 0, sequence, tzinfo=UTC),
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
        source_format=source_format,
        target_format=target_format,
        stage="succeeded",
        last_heartbeat_at=None,
        total_pages=10,
        processed_pages=10,
        failed_pages=0,
        percent_complete=100.0,
        pages_per_minute=120.0,
        eta_seconds=0,
        audio_total_media_seconds=None,
        audio_processed_media_seconds=None,
        audio_percent_complete=None,
        audio_current_chunk_index=None,
        audio_total_chunks=None,
    )


def _build_subscription_store(tmp_path: Path) -> WebhookSubscriptionStoreV2:
    return WebhookSubscriptionStoreV2(data_root=tmp_path / "service_data_webhook_delivery")


def _wait_until(predicate, *, timeout_seconds: float = 2.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for predicate to become true.")


def test_enqueue_events_deduplicates_same_event_and_subscription(tmp_path: Path) -> None:
    store = _build_subscription_store(tmp_path)
    store.create_subscription(
        owner_scope="owner_a",
        callback_url="https://consumer.example/hooks/dedupe",
        event_types=["job.succeeded"],
        enabled=True,
    )

    def _post_client(
        _url: str,
        _body: bytes,
        _headers: Mapping[str, str],
        _timeout: float,
    ) -> tuple[int | None, str | None]:
        return 204, None

    worker = WebhookDeliveryWorkerV2(
        data_root=tmp_path / "service_data_webhook_delivery",
        subscription_store=store,
        post_client=_post_client,
    )
    event = _build_event(event_id="evt_001", sequence=1, job_id="jobv2_dedupe")

    worker.enqueue_events(events=[event])
    worker.enqueue_events(events=[event])

    outbox_files = sorted(worker.outbox.outbox_dir.glob("*.json"))
    assert len(outbox_files) == 1


def test_worker_delivers_success_and_records_delivery_metadata(tmp_path: Path) -> None:
    store = _build_subscription_store(tmp_path)
    _, reveal = store.create_subscription(
        owner_scope="owner_b",
        callback_url="https://consumer.example/hooks/success",
        event_types=["job.succeeded"],
        enabled=True,
    )

    captured_headers: dict[str, str] = {}
    captured_body = b""

    def _post_client(
        _url: str,
        body: bytes,
        headers: Mapping[str, str],
        _timeout: float,
    ) -> tuple[int | None, str | None]:
        nonlocal captured_body, captured_headers
        captured_body = body
        captured_headers = dict(headers)
        return 204, None

    worker = WebhookDeliveryWorkerV2(
        data_root=tmp_path / "service_data_webhook_delivery",
        subscription_store=store,
        poll_interval_seconds=0.05,
        post_client=_post_client,
    )
    event = _build_event(event_id="evt_002", sequence=2, job_id="jobv2_success")
    worker.enqueue_events(events=[event])
    worker.start()

    try:
        _wait_until(lambda: len(list(worker.outbox.delivered_dir.glob("*.json"))) == 1)
    finally:
        worker.stop()

    delivered_files = list(worker.outbox.delivered_dir.glob("*.json"))
    assert len(delivered_files) == 1
    delivered_payload = json.loads(delivered_files[0].read_text(encoding="utf-8"))
    assert delivered_payload.get("delivered_status_code") == 204
    assert delivered_payload.get("delivery_latency_ms") is not None
    assert len(list(worker.outbox.outbox_dir.glob("*.json"))) == 0

    decoded_body = json.loads(captured_body.decode("utf-8"))
    assert decoded_body["api_version"] == "v2"
    assert "route" in decoded_body
    assert "progress" in decoded_body
    assert decoded_body["route"]["source_format"] == "pdf"
    assert decoded_body["route"]["target_format"] == "md"
    for key in (
        "total_pages",
        "processed_pages",
        "failed_pages",
        "percent_complete",
        "pages_per_minute",
        "eta_seconds",
    ):
        assert key in decoded_body["progress"]

    verify_webhook_signature_v2(
        headers=captured_headers,
        body_bytes=captured_body,
        signing_secrets=[reveal.value],
        replay_cache=set(),
    )


def test_worker_retries_and_then_succeeds(tmp_path: Path) -> None:
    store = _build_subscription_store(tmp_path)
    store.create_subscription(
        owner_scope="owner_c",
        callback_url="https://consumer.example/hooks/retry-success",
        event_types=["job.succeeded"],
        enabled=True,
    )
    attempts = 0

    def _post_client(
        _url: str,
        _body: bytes,
        _headers: Mapping[str, str],
        _timeout: float,
    ) -> tuple[int | None, str | None]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return 500, None
        return 202, None

    worker = WebhookDeliveryWorkerV2(
        data_root=tmp_path / "service_data_webhook_delivery",
        subscription_store=store,
        poll_interval_seconds=0.05,
        retry_schedule_seconds=(0, 0, 0, 0),
        max_attempts=5,
        post_client=_post_client,
    )
    worker.enqueue_events(
        events=[_build_event(event_id="evt_003", sequence=3, job_id="jobv2_retry")]
    )
    worker.start()

    try:
        _wait_until(lambda: len(list(worker.outbox.delivered_dir.glob("*.json"))) == 1)
    finally:
        worker.stop()

    assert attempts == 2
    metrics = worker.metrics()
    assert metrics.delivered == 1
    assert metrics.retried >= 1
    assert metrics.dlq == 0


def test_worker_moves_to_dlq_after_attempt_exhaustion(tmp_path: Path) -> None:
    store = _build_subscription_store(tmp_path)
    store.create_subscription(
        owner_scope="owner_d",
        callback_url="https://consumer.example/hooks/dlq",
        event_types=["job.succeeded"],
        enabled=True,
    )

    def _post_client(
        _url: str,
        _body: bytes,
        _headers: Mapping[str, str],
        _timeout: float,
    ) -> tuple[int | None, str | None]:
        return 500, None

    worker = WebhookDeliveryWorkerV2(
        data_root=tmp_path / "service_data_webhook_delivery",
        subscription_store=store,
        poll_interval_seconds=0.05,
        retry_schedule_seconds=(0, 0, 0, 0),
        max_attempts=3,
        post_client=_post_client,
    )
    worker.enqueue_events(events=[_build_event(event_id="evt_004", sequence=4, job_id="jobv2_dlq")])
    worker.start()

    try:
        _wait_until(lambda: len(list(worker.outbox.dlq_dir.glob("*.json"))) == 1)
    finally:
        worker.stop()

    dlq_files = list(worker.outbox.dlq_dir.glob("*.json"))
    assert len(dlq_files) == 1
    dlq_payload = json.loads(dlq_files[0].read_text(encoding="utf-8"))
    assert dlq_payload.get("terminal_state") == "dlq"
    assert dlq_payload.get("attempt_count") == 3
    assert dlq_payload.get("last_error_class") == "http_500"
    assert len(list(worker.outbox.delivered_dir.glob("*.json"))) == 0


def test_verify_webhook_signature_rejects_invalid_stale_and_replay() -> None:
    body = b'{"api_version":"v2","job_id":"jobv2_sig"}'
    timestamp = str(int(datetime(2026, 2, 28, 12, 0, 0, tzinfo=UTC).timestamp()))
    valid_headers = {
        "X-SCAL-Webhook-Id": "evt_sig_001",
        "X-SCAL-Webhook-Timestamp": timestamp,
        "X-SCAL-Webhook-Signature": "v1=invalid",
    }

    with pytest.raises(WebhookSignatureValidationErrorV2) as invalid_signature:
        verify_webhook_signature_v2(
            headers=valid_headers,
            body_bytes=body,
            signing_secrets=["whsec_live_secret"],
            now_epoch_seconds=int(timestamp),
            replay_cache=set(),
        )
    assert invalid_signature.value.code == "webhook_signature_invalid"

    signature = compute_webhook_signature_v2(
        secret="whsec_live_secret",
        timestamp=timestamp,
        body_bytes=body,
    )
    stale_headers = {
        "X-SCAL-Webhook-Id": "evt_sig_002",
        "X-SCAL-Webhook-Timestamp": timestamp,
        "X-SCAL-Webhook-Signature": signature,
    }
    with pytest.raises(WebhookSignatureValidationErrorV2) as stale_timestamp:
        verify_webhook_signature_v2(
            headers=stale_headers,
            body_bytes=body,
            signing_secrets=["whsec_live_secret"],
            now_epoch_seconds=int(timestamp) + 1000,
            replay_window_seconds=60,
            replay_cache=set(),
        )
    assert stale_timestamp.value.code == "webhook_timestamp_outside_window"

    replay_cache: set[str] = set()
    verify_webhook_signature_v2(
        headers=stale_headers,
        body_bytes=body,
        signing_secrets=["whsec_live_secret"],
        now_epoch_seconds=int(timestamp),
        replay_cache=replay_cache,
    )
    with pytest.raises(WebhookSignatureValidationErrorV2) as replay_attempt:
        verify_webhook_signature_v2(
            headers=stale_headers,
            body_bytes=body,
            signing_secrets=["whsec_live_secret"],
            now_epoch_seconds=int(timestamp),
            replay_cache=replay_cache,
        )
    assert replay_attempt.value.code == "webhook_replay_detected"
