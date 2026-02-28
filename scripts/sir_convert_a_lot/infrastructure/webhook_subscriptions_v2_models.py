"""Typed models and validation helpers for v2 webhook subscriptions.

Purpose:
    Centralize webhook subscription dataclasses, errors, and input normalization
    used by the v2 onboarding store and HTTP route layers.

Relationships:
    - Used by `infrastructure.webhook_subscriptions_v2_store`.
    - Re-exported via `infrastructure.webhook_subscriptions_v2` for stable imports.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import urlparse, urlunparse

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    dt_from_rfc3339,
    dt_to_rfc3339,
)
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import generate_event_ulid

WebhookEventTypeV2 = Literal[
    "job.queued",
    "job.running",
    "job.succeeded",
    "job.failed",
    "job.canceled",
]
WebhookSecretVersionV2 = Literal["active", "next"]

EVENT_TYPE_ORDER_V2: tuple[WebhookEventTypeV2, ...] = (
    "job.queued",
    "job.running",
    "job.succeeded",
    "job.failed",
    "job.canceled",
)
ALLOWED_EVENT_TYPES_V2: set[str] = set(EVENT_TYPE_ORDER_V2)


class WebhookSubscriptionErrorV2(Exception):
    """Base class for webhook subscription persistence errors."""


@dataclass
class WebhookSubscriptionNotFoundErrorV2(WebhookSubscriptionErrorV2):
    """Raised when an owner-scoped subscription cannot be found."""

    subscription_id: str
    owner_scope: str


@dataclass
class WebhookSubscriptionConflictErrorV2(WebhookSubscriptionErrorV2):
    """Raised for deterministic create/update conflicts."""

    callback_url: str
    owner_scope: str


@dataclass
class WebhookEndpointInvalidErrorV2(WebhookSubscriptionErrorV2):
    """Raised when callback URL validation fails."""

    callback_url: str
    reason: str


@dataclass
class WebhookEventTypeInvalidErrorV2(WebhookSubscriptionErrorV2):
    """Raised when event types are malformed or unsupported."""

    reason: str


@dataclass
class WebhookSecretNotFoundErrorV2(WebhookSubscriptionErrorV2):
    """Raised when a requested secret version does not exist."""

    subscription_id: str
    version: WebhookSecretVersionV2


@dataclass
class WebhookSecretStateConflictErrorV2(WebhookSubscriptionErrorV2):
    """Raised when secret lifecycle operation cannot be completed."""

    subscription_id: str
    reason: str


@dataclass(frozen=True)
class WebhookSecretRevealV2:
    """One-time secret reveal payload returned on create/rotate operations."""

    version: WebhookSecretVersionV2
    value: str
    revealed_once: bool = True


@dataclass(frozen=True)
class WebhookSubscriptionRecordV2:
    """Owner-scoped webhook subscription record with redacted secret metadata."""

    subscription_id: str
    owner_scope: str
    callback_url: str
    event_types: tuple[WebhookEventTypeV2, ...]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    active_secret_present: bool
    next_secret_present: bool
    overlap_expires_at: datetime | None


@dataclass(frozen=True)
class WebhookDeliveryTargetV2:
    """Materialized delivery target used by webhook delivery worker logic."""

    subscription_id: str
    owner_scope: str
    callback_url: str
    event_types: tuple[WebhookEventTypeV2, ...]
    signing_secrets: tuple[str, ...]


def normalize_owner_scope_from_api_key(api_key: str) -> str:
    """Build stable owner scope identifier from API key material."""
    normalized = api_key.strip()
    hashed = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"owner_{hashed}"


def generate_subscription_id(*, now: datetime) -> str:
    """Generate deterministic-format webhook subscription identifier."""
    return f"whsub_{generate_event_ulid(now=now)}"


def generate_secret_value() -> str:
    """Generate one webhook signing secret value."""
    token = secrets.token_urlsafe(24)
    return f"whsec_live_{token}"


def normalize_event_types(event_types: list[str]) -> tuple[WebhookEventTypeV2, ...]:
    """Normalize user-supplied event types into canonical ordered tuple."""
    if len(event_types) == 0:
        raise WebhookEventTypeInvalidErrorV2(reason="event_types must not be empty.")

    seen: set[str] = set()
    for event_type in event_types:
        normalized = event_type.strip()
        if normalized == "":
            raise WebhookEventTypeInvalidErrorV2(reason="event_types must not contain blanks.")
        if normalized not in ALLOWED_EVENT_TYPES_V2:
            raise WebhookEventTypeInvalidErrorV2(reason=f"unsupported event_type: {normalized}")
        seen.add(normalized)

    ordered = tuple(event for event in EVENT_TYPE_ORDER_V2 if event in seen)
    return ordered


def normalize_callback_url(callback_url: str) -> str:
    """Normalize and validate callback URL string."""
    cleaned = callback_url.strip()
    if cleaned == "":
        raise WebhookEndpointInvalidErrorV2(
            callback_url=callback_url,
            reason="callback_url must not be blank.",
        )

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise WebhookEndpointInvalidErrorV2(
            callback_url=callback_url,
            reason="callback_url scheme must be http or https.",
        )
    if parsed.netloc.strip() == "":
        raise WebhookEndpointInvalidErrorV2(
            callback_url=callback_url,
            reason="callback_url must include host.",
        )

    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def secret_payload(*, value: str, created_at: datetime) -> dict[str, object]:
    """Build persisted secret payload object."""
    return {
        "value": value,
        "created_at": dt_to_rfc3339(created_at),
    }


def parse_secret_payload(secret_obj: object) -> tuple[str, datetime] | None:
    """Parse persisted secret payload into `(value, created_at)` tuple."""
    if not isinstance(secret_obj, dict):
        return None
    value_obj = secret_obj.get("value")
    created_at = dt_from_rfc3339(secret_obj.get("created_at"))
    if not isinstance(value_obj, str) or created_at is None:
        return None
    return value_obj, created_at


def payload_event_types(payload: dict[str, object]) -> tuple[WebhookEventTypeV2, ...]:
    """Parse and validate `event_types` from one persisted payload."""
    event_types_obj = payload.get("event_types")
    if not isinstance(event_types_obj, list):
        raise ValueError("subscription payload missing event_types list.")
    normalized_input: list[str] = []
    for item in event_types_obj:
        if not isinstance(item, str):
            raise ValueError("subscription payload event_types must be strings.")
        normalized_input.append(item)
    return normalize_event_types(normalized_input)


def payload_owner_scope(payload: dict[str, object]) -> str:
    """Parse `owner_scope` field from one persisted payload."""
    owner_scope_obj = payload.get("owner_scope")
    if not isinstance(owner_scope_obj, str) or owner_scope_obj.strip() == "":
        raise ValueError("subscription payload missing owner_scope.")
    return owner_scope_obj


def payload_callback_url(payload: dict[str, object]) -> str:
    """Parse and normalize `callback_url` from one persisted payload."""
    callback_obj = payload.get("callback_url")
    if not isinstance(callback_obj, str):
        raise ValueError("subscription payload missing callback_url.")
    return normalize_callback_url(callback_obj)


def payload_enabled(payload: dict[str, object]) -> bool:
    """Parse `enabled` flag from one persisted payload."""
    enabled_obj = payload.get("enabled")
    if not isinstance(enabled_obj, bool):
        raise ValueError("subscription payload missing enabled boolean.")
    return enabled_obj


def payload_timestamps(payload: dict[str, object]) -> tuple[datetime, datetime]:
    """Parse required `created_at`/`updated_at` timestamps from payload."""
    timestamps_obj = payload.get("timestamps")
    if not isinstance(timestamps_obj, dict):
        raise ValueError("subscription payload missing timestamps object.")
    created_at = dt_from_rfc3339(timestamps_obj.get("created_at"))
    updated_at = dt_from_rfc3339(timestamps_obj.get("updated_at"))
    if created_at is None or updated_at is None:
        raise ValueError("subscription payload has invalid timestamps.")
    return created_at, updated_at
