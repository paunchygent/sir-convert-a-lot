"""Webhook signature computation and verification utilities for v2 push.

Purpose:
    Provide deterministic HMAC signing and replay-safe signature verification
    helpers for Sir Convert-a-Lot v2 webhook delivery.

Relationships:
    - Used by `infrastructure.webhook_delivery_v2` to sign outgoing webhook callbacks.
    - Used by webhook replay/security tests to validate verification semantics.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Mapping, Sequence

DEFAULT_WEBHOOK_REPLAY_WINDOW_SECONDS_V2 = 300

WebhookSignatureValidationCodeV2 = Literal[
    "webhook_signature_invalid",
    "webhook_timestamp_outside_window",
    "webhook_replay_detected",
]


@dataclass
class WebhookSignatureValidationErrorV2(Exception):
    """Deterministic signature validation error used by replay/security checks."""

    code: WebhookSignatureValidationCodeV2
    message: str


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
