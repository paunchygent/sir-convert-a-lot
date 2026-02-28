"""Queue-backed webhook delivery worker and signing utilities for v2 push.

Purpose:
    Provide deterministic webhook outbox delivery with retries, DLQ handoff,
    HMAC signing, and replay-safe verification helpers for async push events.

Relationships:
    - Consumed by `infrastructure.runtime_engine_v2` for webhook push delivery.
    - Reads webhook targets from `infrastructure.webhook_subscriptions_v2_store`.
    - Consumes job lifecycle events from `infrastructure.job_events_v2`.
"""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Iterator, Literal, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import JobLifecycleEventRecordV2
from scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2 import (
    WebhookDeliveryTargetV2,
    WebhookSubscriptionStoreV2,
)

DEFAULT_WEBHOOK_RETRY_SCHEDULE_SECONDS_V2: tuple[int, ...] = (2, 10, 30, 120)
DEFAULT_WEBHOOK_MAX_ATTEMPTS_V2 = 5
DEFAULT_WEBHOOK_REPLAY_WINDOW_SECONDS_V2 = 300

WebhookSignatureValidationCodeV2 = Literal[
    "webhook_signature_invalid",
    "webhook_timestamp_outside_window",
    "webhook_replay_detected",
]
WebhookPostResultV2 = tuple[int | None, str | None]
WebhookPostClientV2 = Callable[[str, bytes, Mapping[str, str], float], WebhookPostResultV2]


@dataclass
class WebhookSignatureValidationErrorV2(Exception):
    """Deterministic signature validation error used by replay/security checks."""

    code: WebhookSignatureValidationCodeV2
    message: str


@dataclass(frozen=True)
class WebhookDeliveryMetricsV2:
    """Counters for webhook delivery observability and runbook reporting."""

    delivered: int
    retried: int
    dlq: int
    failures: int


def compute_webhook_signature_v2(*, secret: str, timestamp: str, body_bytes: bytes) -> str:
    """Return webhook HMAC signature using canonical `<timestamp>.<body>` input."""
    signed_payload = timestamp.encode("utf-8") + b"." + body_bytes
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"v1={digest}"


def verify_webhook_signature_v2(
    *,
    headers: Mapping[str, str],
    body_bytes: bytes,
    signing_secrets: Sequence[str],
    now_epoch_seconds: int | None = None,
    replay_window_seconds: int = DEFAULT_WEBHOOK_REPLAY_WINDOW_SECONDS_V2,
    replay_cache: set[str] | None = None,
) -> None:
    """Verify callback signature, timestamp freshness, and replay key uniqueness."""
    signature = headers.get("X-SCAL-Webhook-Signature")
    timestamp = headers.get("X-SCAL-Webhook-Timestamp")
    webhook_id = headers.get("X-SCAL-Webhook-Id")
    if signature is None or timestamp is None or webhook_id is None:
        raise WebhookSignatureValidationErrorV2(
            code="webhook_signature_invalid",
            message="Missing webhook signature headers.",
        )

    try:
        timestamp_int = int(timestamp)
    except ValueError as exc:
        raise WebhookSignatureValidationErrorV2(
            code="webhook_signature_invalid",
            message="Webhook timestamp header is invalid.",
        ) from exc

    resolved_now = (
        int(datetime.now(UTC).timestamp()) if now_epoch_seconds is None else now_epoch_seconds
    )
    if abs(resolved_now - timestamp_int) > max(1, replay_window_seconds):
        raise WebhookSignatureValidationErrorV2(
            code="webhook_timestamp_outside_window",
            message="Webhook timestamp is outside replay window.",
        )

    expected_candidates = {
        compute_webhook_signature_v2(secret=secret, timestamp=timestamp, body_bytes=body_bytes)
        for secret in signing_secrets
    }
    if signature not in expected_candidates:
        raise WebhookSignatureValidationErrorV2(
            code="webhook_signature_invalid",
            message="Webhook signature mismatch.",
        )

    replay_key = f"{webhook_id}:{timestamp}:{signature}"
    if replay_cache is not None:
        if replay_key in replay_cache:
            raise WebhookSignatureValidationErrorV2(
                code="webhook_replay_detected",
                message="Webhook replay detected for id/timestamp/signature key.",
            )
        replay_cache.add(replay_key)


def _default_webhook_post_client_v2(
    callback_url: str,
    body_bytes: bytes,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> WebhookPostResultV2:
    request = Request(
        url=callback_url,
        method="POST",
        data=body_bytes,
        headers=dict(headers),
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return response.getcode(), None
    except HTTPError as exc:
        return exc.code, f"http_{exc.code}"
    except URLError:
        return None, "network_error"
    except TimeoutError:
        return None, "timeout_error"
    except Exception:
        return None, "delivery_error"


class WebhookDeliveryOutboxV2:
    """Filesystem-backed outbox for webhook deliveries with retry + DLQ state."""

    def __init__(self, *, data_root: Path, max_attempts: int) -> None:
        self.root_dir = data_root / "webhooks_v2" / "delivery"
        self.outbox_dir = self.root_dir / "outbox"
        self.delivered_dir = self.root_dir / "delivered"
        self.dlq_dir = self.root_dir / "dlq"
        self._lock_path = self.root_dir / ".delivery.lock"
        self.max_attempts = max(1, max_attempts)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.delivered_dir.mkdir(parents=True, exist_ok=True)
        self.dlq_dir.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _entry_path(self, directory: Path, delivery_id: str) -> Path:
        return directory / f"{delivery_id}.json"

    def enqueue(
        self,
        *,
        event: JobLifecycleEventRecordV2,
        target: WebhookDeliveryTargetV2,
    ) -> None:
        delivery_id = f"{event.event_id}__{target.subscription_id}"
        created_at = utc_now()
        payload: dict[str, object] = {
            "delivery_id": delivery_id,
            "subscription_id": target.subscription_id,
            "owner_scope": target.owner_scope,
            "callback_url": target.callback_url,
            "signing_secrets": list(target.signing_secrets),
            "attempt_count": 0,
            "max_attempts": self.max_attempts,
            "created_at": dt_to_rfc3339(created_at),
            "next_attempt_at": dt_to_rfc3339(created_at),
            "last_error_class": None,
            "last_status_code": None,
            "event": {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "sequence": event.sequence,
                "occurred_at": dt_to_rfc3339(event.occurred_at),
                "job_id": event.job_id,
                "status": str(event.status),
            },
        }
        with self._lock():
            outbox_path = self._entry_path(self.outbox_dir, delivery_id)
            delivered_path = self._entry_path(self.delivered_dir, delivery_id)
            dlq_path = self._entry_path(self.dlq_dir, delivery_id)
            if outbox_path.exists() or delivered_path.exists() or dlq_path.exists():
                return
            atomic_write_json(outbox_path, payload)

    def due_entries(self, *, now: datetime) -> list[tuple[Path, dict[str, object]]]:
        with self._lock():
            entries: list[tuple[Path, dict[str, object]]] = []
            for path in sorted(self.outbox_dir.glob("*.json")):
                payload = read_json(path)
                next_attempt_at = dt_from_rfc3339(payload.get("next_attempt_at"))
                if next_attempt_at is None or next_attempt_at <= now:
                    entries.append((path, payload))
            return entries

    def mark_retry(
        self,
        *,
        path: Path,
        payload: dict[str, object],
        next_attempt_at: datetime,
        error_class: str,
        status_code: int | None,
    ) -> None:
        with self._lock():
            attempt_count_obj = payload.get("attempt_count")
            attempt_count = int(attempt_count_obj) if isinstance(attempt_count_obj, int) else 0
            payload["attempt_count"] = attempt_count + 1
            payload["next_attempt_at"] = dt_to_rfc3339(next_attempt_at)
            payload["last_error_class"] = error_class
            payload["last_status_code"] = status_code
            atomic_write_json(path, payload)

    def mark_delivered(
        self,
        *,
        path: Path,
        payload: dict[str, object],
        delivered_at: datetime,
        status_code: int,
        latency_ms: int,
    ) -> None:
        delivery_id_obj = payload.get("delivery_id")
        if not isinstance(delivery_id_obj, str):
            return
        with self._lock():
            payload["delivered_at"] = dt_to_rfc3339(delivered_at)
            payload["delivered_status_code"] = status_code
            payload["delivery_latency_ms"] = latency_ms
            delivered_path = self._entry_path(self.delivered_dir, delivery_id_obj)
            atomic_write_json(delivered_path, payload)
            path.unlink(missing_ok=True)

    def mark_dlq(
        self,
        *,
        path: Path,
        payload: dict[str, object],
        failed_at: datetime,
        error_class: str,
        status_code: int | None,
    ) -> None:
        delivery_id_obj = payload.get("delivery_id")
        if not isinstance(delivery_id_obj, str):
            return
        with self._lock():
            attempt_count_obj = payload.get("attempt_count")
            attempt_count = int(attempt_count_obj) if isinstance(attempt_count_obj, int) else 0
            payload["attempt_count"] = attempt_count + 1
            payload["failed_at"] = dt_to_rfc3339(failed_at)
            payload["last_error_class"] = error_class
            payload["last_status_code"] = status_code
            payload["terminal_state"] = "dlq"
            dlq_path = self._entry_path(self.dlq_dir, delivery_id_obj)
            atomic_write_json(dlq_path, payload)
            path.unlink(missing_ok=True)


class WebhookDeliveryWorkerV2:
    """Background worker that processes webhook outbox entries with retries."""

    def __init__(
        self,
        *,
        data_root: Path,
        subscription_store: WebhookSubscriptionStoreV2,
        poll_interval_seconds: float = 0.2,
        request_timeout_seconds: float = 5.0,
        retry_schedule_seconds: Sequence[int] = DEFAULT_WEBHOOK_RETRY_SCHEDULE_SECONDS_V2,
        max_attempts: int = DEFAULT_WEBHOOK_MAX_ATTEMPTS_V2,
        post_client: WebhookPostClientV2 = _default_webhook_post_client_v2,
    ) -> None:
        self.subscription_store = subscription_store
        self.outbox = WebhookDeliveryOutboxV2(data_root=data_root, max_attempts=max_attempts)
        self.poll_interval_seconds = max(0.05, poll_interval_seconds)
        self.request_timeout_seconds = max(0.1, request_timeout_seconds)
        self.retry_schedule_seconds = tuple(max(0, int(item)) for item in retry_schedule_seconds)
        self.max_attempts = max(1, max_attempts)
        self._post_client = post_client
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._delivered_count = 0
        self._retried_count = 0
        self._dlq_count = 0
        self._failure_count = 0

    def start(self) -> None:
        """Start the worker loop if it is not already running."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the worker loop and wait for thread shutdown."""
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=max(1.0, self.poll_interval_seconds * 8))

    def metrics(self) -> WebhookDeliveryMetricsV2:
        """Return current delivery counters for runbook observability."""
        return WebhookDeliveryMetricsV2(
            delivered=self._delivered_count,
            retried=self._retried_count,
            dlq=self._dlq_count,
            failures=self._failure_count,
        )

    def enqueue_events(self, *, events: Sequence[JobLifecycleEventRecordV2]) -> None:
        """Enqueue webhook deliveries for one batch of lifecycle events."""
        for event in events:
            targets = self.subscription_store.list_delivery_targets(event_type=event.event_type)
            for target in targets:
                self.outbox.enqueue(event=event, target=target)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            now = utc_now()
            due = self.outbox.due_entries(now=now)
            for path, payload in due:
                self._process_entry(path=path, payload=payload, now=now)
            self._stop_event.wait(timeout=self.poll_interval_seconds)

    def _process_entry(self, *, path: Path, payload: dict[str, object], now: datetime) -> None:
        body_bytes, headers = self._delivery_payload(payload=payload, now=now)
        callback_url_obj = payload.get("callback_url")
        if not isinstance(callback_url_obj, str) or callback_url_obj.strip() == "":
            self.outbox.mark_dlq(
                path=path,
                payload=payload,
                failed_at=now,
                error_class="callback_url_missing",
                status_code=None,
            )
            self._dlq_count += 1
            return

        started = datetime.now(UTC)
        status_code, transport_error = self._post_client(
            callback_url_obj,
            body_bytes,
            headers,
            self.request_timeout_seconds,
        )
        latency_ms = max(0, int((datetime.now(UTC) - started).total_seconds() * 1000))
        if status_code is not None and 200 <= status_code < 300:
            self.outbox.mark_delivered(
                path=path,
                payload=payload,
                delivered_at=now,
                status_code=status_code,
                latency_ms=latency_ms,
            )
            self._delivered_count += 1
            return

        self._failure_count += 1
        error_class = transport_error or (
            f"http_{status_code}" if status_code is not None else "unknown"
        )
        attempt_count_obj = payload.get("attempt_count")
        attempt_count = int(attempt_count_obj) if isinstance(attempt_count_obj, int) else 0
        next_attempt_number = attempt_count + 1
        if next_attempt_number >= self.max_attempts:
            self.outbox.mark_dlq(
                path=path,
                payload=payload,
                failed_at=now,
                error_class=error_class,
                status_code=status_code,
            )
            self._dlq_count += 1
            return

        retry_delay = self._retry_delay_seconds(attempt_number=next_attempt_number)
        self.outbox.mark_retry(
            path=path,
            payload=payload,
            next_attempt_at=now + timedelta(seconds=retry_delay),
            error_class=error_class,
            status_code=status_code,
        )
        self._retried_count += 1

    def _retry_delay_seconds(self, *, attempt_number: int) -> int:
        if len(self.retry_schedule_seconds) == 0:
            return 0
        schedule_index = min(max(0, attempt_number - 1), len(self.retry_schedule_seconds) - 1)
        return self.retry_schedule_seconds[schedule_index]

    def _delivery_payload(
        self, *, payload: dict[str, object], now: datetime
    ) -> tuple[bytes, dict[str, str]]:
        event_obj = payload.get("event")
        if not isinstance(event_obj, dict):
            raise ValueError("delivery payload missing event object")

        job_id_obj = event_obj.get("job_id")
        event_id_obj = event_obj.get("event_id")
        event_type_obj = event_obj.get("event_type")
        sequence_obj = event_obj.get("sequence")
        occurred_at_obj = event_obj.get("occurred_at")
        status_obj = event_obj.get("status")
        if (
            not isinstance(job_id_obj, str)
            or not isinstance(event_id_obj, str)
            or not isinstance(event_type_obj, str)
            or not isinstance(sequence_obj, int)
            or not isinstance(occurred_at_obj, str)
            or not isinstance(status_obj, str)
        ):
            raise ValueError("delivery payload event object is malformed")

        callback_payload = {
            "api_version": "v2",
            "event_id": event_id_obj,
            "event_type": event_type_obj,
            "sequence": sequence_obj,
            "occurred_at": occurred_at_obj,
            "job_id": job_id_obj,
            "status": status_obj,
            "result_links": {
                "result": f"/v2/convert/jobs/{job_id_obj}/result",
                "artifact": f"/v2/convert/jobs/{job_id_obj}/artifact",
            },
        }
        body_bytes = json.dumps(callback_payload, separators=(",", ":"), sort_keys=True).encode(
            "utf-8"
        )
        timestamp = str(int(now.timestamp()))

        signing_secrets_obj = payload.get("signing_secrets")
        if not isinstance(signing_secrets_obj, list) or len(signing_secrets_obj) == 0:
            raise ValueError("delivery payload missing signing secrets")
        first_secret = signing_secrets_obj[0]
        if not isinstance(first_secret, str):
            raise ValueError("delivery payload contains non-string signing secret")
        signature = compute_webhook_signature_v2(
            secret=first_secret,
            timestamp=timestamp,
            body_bytes=body_bytes,
        )
        headers = {
            "Content-Type": "application/json",
            "X-SCAL-Webhook-Id": event_id_obj,
            "X-SCAL-Webhook-Timestamp": timestamp,
            "X-SCAL-Webhook-Signature": signature,
        }
        return body_bytes, headers
