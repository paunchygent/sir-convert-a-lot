"""Filesystem store for v2 webhook subscriptions and secret lifecycle.

Purpose:
    Implement durable owner-scoped webhook onboarding behavior with deterministic
    secret rotation overlap and redacted read/list semantics.

Relationships:
    - Used by `infrastructure.runtime_engine_v2`.
    - Depends on typed helpers in `webhook_subscriptions_v2_models`.
"""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Literal

from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import (
    atomic_write_json,
    dt_from_rfc3339,
    dt_to_rfc3339,
    read_json,
    utc_now,
)
from scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2_models import (
    WebhookDeliveryTargetV2,
    WebhookSecretNotFoundErrorV2,
    WebhookSecretRevealV2,
    WebhookSecretStateConflictErrorV2,
    WebhookSubscriptionConflictErrorV2,
    WebhookSubscriptionNotFoundErrorV2,
    WebhookSubscriptionRecordV2,
    generate_secret_value,
    generate_subscription_id,
    normalize_callback_url,
    normalize_event_types,
    parse_secret_payload,
    payload_callback_url,
    payload_enabled,
    payload_event_types,
    payload_owner_scope,
    payload_timestamps,
    secret_payload,
)


class WebhookSubscriptionStoreV2:
    """Filesystem-backed owner-scoped webhook subscription store."""

    def __init__(
        self,
        *,
        data_root: Path,
        secret_overlap_seconds: int = 24 * 3600,
    ) -> None:
        self.root_dir = data_root / "webhooks_v2"
        self.subscriptions_dir = self.root_dir / "subscriptions"
        self.subscriptions_dir.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.root_dir / ".store.lock"
        self.secret_overlap_seconds = max(1, int(secret_overlap_seconds))

    @contextmanager
    def _store_lock(self) -> Iterator[None]:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        with self._lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _subscription_path(self, subscription_id: str) -> Path:
        return self.subscriptions_dir / f"{subscription_id}.json"

    def _iter_paths(self) -> list[Path]:
        return sorted(self.subscriptions_dir.glob("*.json"))

    def _read_payload(self, path: Path) -> dict[str, object]:
        return read_json(path)

    def _write_payload(self, path: Path, payload: dict[str, object]) -> None:
        atomic_write_json(path, payload)

    def _normalize_secret_rotation_state(
        self,
        *,
        payload: dict[str, object],
        now: datetime,
    ) -> bool:
        secret_obj = payload.get("secret")
        if not isinstance(secret_obj, dict):
            return False
        next_payload = secret_obj.get("next")
        overlap_expires_at = dt_from_rfc3339(secret_obj.get("overlap_expires_at"))
        if next_payload is None or overlap_expires_at is None:
            return False
        if now < overlap_expires_at:
            return False
        secret_obj["active"] = next_payload
        secret_obj["next"] = None
        secret_obj["overlap_expires_at"] = None
        timestamps_obj = payload.get("timestamps")
        if not isinstance(timestamps_obj, dict):
            timestamps_obj = {}
            payload["timestamps"] = timestamps_obj
        timestamps_obj["updated_at"] = dt_to_rfc3339(now)
        return True

    def _record_from_payload(self, payload: dict[str, object]) -> WebhookSubscriptionRecordV2:
        subscription_id_obj = payload.get("subscription_id")
        if not isinstance(subscription_id_obj, str) or subscription_id_obj.strip() == "":
            raise ValueError("subscription payload missing subscription_id.")
        owner_scope = payload_owner_scope(payload)
        callback_url = payload_callback_url(payload)
        event_types = payload_event_types(payload)
        enabled = payload_enabled(payload)
        created_at, updated_at = payload_timestamps(payload)

        secret_obj = payload.get("secret")
        if not isinstance(secret_obj, dict):
            raise ValueError("subscription payload missing secret object.")
        active_secret = parse_secret_payload(secret_obj.get("active"))
        next_secret = parse_secret_payload(secret_obj.get("next"))
        overlap_expires_at = dt_from_rfc3339(secret_obj.get("overlap_expires_at"))

        return WebhookSubscriptionRecordV2(
            subscription_id=subscription_id_obj,
            owner_scope=owner_scope,
            callback_url=callback_url,
            event_types=event_types,
            enabled=enabled,
            created_at=created_at,
            updated_at=updated_at,
            active_secret_present=active_secret is not None,
            next_secret_present=next_secret is not None,
            overlap_expires_at=overlap_expires_at,
        )

    def _load_payload_for_owner(
        self,
        *,
        owner_scope: str,
        subscription_id: str,
        now: datetime,
    ) -> tuple[Path, dict[str, object]]:
        path = self._subscription_path(subscription_id)
        if not path.exists():
            raise WebhookSubscriptionNotFoundErrorV2(
                subscription_id=subscription_id,
                owner_scope=owner_scope,
            )
        payload = self._read_payload(path)
        changed = self._normalize_secret_rotation_state(payload=payload, now=now)
        payload_owner = payload_owner_scope(payload)
        if payload_owner != owner_scope:
            raise WebhookSubscriptionNotFoundErrorV2(
                subscription_id=subscription_id,
                owner_scope=owner_scope,
            )
        if changed:
            self._write_payload(path, payload)
        return path, payload

    def _ensure_no_duplicate_callback(
        self,
        *,
        owner_scope: str,
        callback_url: str,
        ignore_subscription_id: str | None,
        now: datetime,
    ) -> None:
        for path in self._iter_paths():
            payload = self._read_payload(path)
            changed = self._normalize_secret_rotation_state(payload=payload, now=now)
            if changed:
                self._write_payload(path, payload)
            payload_owner = payload_owner_scope(payload)
            if payload_owner != owner_scope:
                continue
            payload_subscription_id_obj = payload.get("subscription_id")
            payload_subscription_id = (
                payload_subscription_id_obj if isinstance(payload_subscription_id_obj, str) else ""
            )
            if (
                ignore_subscription_id is not None
                and payload_subscription_id == ignore_subscription_id
            ):
                continue
            payload_callback = payload_callback_url(payload)
            if payload_callback == callback_url:
                raise WebhookSubscriptionConflictErrorV2(
                    callback_url=callback_url,
                    owner_scope=owner_scope,
                )

    def create_subscription(
        self,
        *,
        owner_scope: str,
        callback_url: str,
        event_types: list[str],
        enabled: bool,
    ) -> tuple[WebhookSubscriptionRecordV2, WebhookSecretRevealV2]:
        now = utc_now()
        normalized_callback = normalize_callback_url(callback_url)
        normalized_event_types = normalize_event_types(event_types)
        with self._store_lock():
            self._ensure_no_duplicate_callback(
                owner_scope=owner_scope,
                callback_url=normalized_callback,
                ignore_subscription_id=None,
                now=now,
            )
            subscription_id = generate_subscription_id(now=now)
            secret_value = generate_secret_value()
            payload: dict[str, object] = {
                "subscription_id": subscription_id,
                "owner_scope": owner_scope,
                "callback_url": normalized_callback,
                "event_types": list(normalized_event_types),
                "enabled": enabled,
                "timestamps": {
                    "created_at": dt_to_rfc3339(now),
                    "updated_at": dt_to_rfc3339(now),
                },
                "secret": {
                    "active": secret_payload(value=secret_value, created_at=now),
                    "next": None,
                    "overlap_expires_at": None,
                },
            }
            path = self._subscription_path(subscription_id)
            self._write_payload(path, payload)
            record = self._record_from_payload(payload)
            return record, WebhookSecretRevealV2(version="active", value=secret_value)

    def list_subscriptions(self, *, owner_scope: str) -> list[WebhookSubscriptionRecordV2]:
        now = utc_now()
        results: list[WebhookSubscriptionRecordV2] = []
        with self._store_lock():
            for path in self._iter_paths():
                payload = self._read_payload(path)
                changed = self._normalize_secret_rotation_state(payload=payload, now=now)
                if changed:
                    self._write_payload(path, payload)
                payload_owner = payload_owner_scope(payload)
                if payload_owner != owner_scope:
                    continue
                results.append(self._record_from_payload(payload))
        return sorted(results, key=lambda record: record.subscription_id)

    def get_subscription(
        self,
        *,
        owner_scope: str,
        subscription_id: str,
    ) -> WebhookSubscriptionRecordV2:
        now = utc_now()
        with self._store_lock():
            _, payload = self._load_payload_for_owner(
                owner_scope=owner_scope,
                subscription_id=subscription_id,
                now=now,
            )
            return self._record_from_payload(payload)

    def update_subscription(
        self,
        *,
        owner_scope: str,
        subscription_id: str,
        callback_url: str | None,
        event_types: list[str] | None,
        enabled: bool | None,
    ) -> WebhookSubscriptionRecordV2:
        now = utc_now()
        with self._store_lock():
            path, payload = self._load_payload_for_owner(
                owner_scope=owner_scope,
                subscription_id=subscription_id,
                now=now,
            )
            if callback_url is not None:
                normalized_callback = normalize_callback_url(callback_url)
                self._ensure_no_duplicate_callback(
                    owner_scope=owner_scope,
                    callback_url=normalized_callback,
                    ignore_subscription_id=subscription_id,
                    now=now,
                )
                payload["callback_url"] = normalized_callback
            if event_types is not None:
                payload["event_types"] = list(normalize_event_types(event_types))
            if enabled is not None:
                payload["enabled"] = enabled

            timestamps_obj = payload.get("timestamps")
            if not isinstance(timestamps_obj, dict):
                timestamps_obj = {}
                payload["timestamps"] = timestamps_obj
            timestamps_obj["updated_at"] = dt_to_rfc3339(now)

            self._write_payload(path, payload)
            return self._record_from_payload(payload)

    def delete_subscription(self, *, owner_scope: str, subscription_id: str) -> None:
        now = utc_now()
        with self._store_lock():
            path, _ = self._load_payload_for_owner(
                owner_scope=owner_scope,
                subscription_id=subscription_id,
                now=now,
            )
            path.unlink(missing_ok=True)

    def rotate_secret(
        self,
        *,
        owner_scope: str,
        subscription_id: str,
    ) -> tuple[WebhookSubscriptionRecordV2, WebhookSecretRevealV2, datetime]:
        now = utc_now()
        with self._store_lock():
            path, payload = self._load_payload_for_owner(
                owner_scope=owner_scope,
                subscription_id=subscription_id,
                now=now,
            )
            secret_obj = payload.get("secret")
            if not isinstance(secret_obj, dict):
                raise WebhookSecretStateConflictErrorV2(
                    subscription_id=subscription_id,
                    reason="subscription secret state missing.",
                )
            active_secret = parse_secret_payload(secret_obj.get("active"))
            if active_secret is None:
                raise WebhookSecretStateConflictErrorV2(
                    subscription_id=subscription_id,
                    reason="active secret missing; cannot rotate.",
                )

            next_secret_value = generate_secret_value()
            overlap_expires_at = now + timedelta(seconds=self.secret_overlap_seconds)
            secret_obj["next"] = secret_payload(value=next_secret_value, created_at=now)
            secret_obj["overlap_expires_at"] = dt_to_rfc3339(overlap_expires_at)

            timestamps_obj = payload.get("timestamps")
            if not isinstance(timestamps_obj, dict):
                timestamps_obj = {}
                payload["timestamps"] = timestamps_obj
            timestamps_obj["updated_at"] = dt_to_rfc3339(now)

            self._write_payload(path, payload)
            record = self._record_from_payload(payload)
            reveal = WebhookSecretRevealV2(version="next", value=next_secret_value)
            return record, reveal, overlap_expires_at

    def revoke_secret(
        self,
        *,
        owner_scope: str,
        subscription_id: str,
        version: Literal["active", "next"],
    ) -> WebhookSubscriptionRecordV2:
        now = utc_now()
        with self._store_lock():
            path, payload = self._load_payload_for_owner(
                owner_scope=owner_scope,
                subscription_id=subscription_id,
                now=now,
            )
            secret_obj = payload.get("secret")
            if not isinstance(secret_obj, dict):
                raise WebhookSecretStateConflictErrorV2(
                    subscription_id=subscription_id,
                    reason="subscription secret state missing.",
                )

            active_secret = parse_secret_payload(secret_obj.get("active"))
            next_secret = parse_secret_payload(secret_obj.get("next"))
            if version == "next":
                if next_secret is None:
                    raise WebhookSecretNotFoundErrorV2(
                        subscription_id=subscription_id,
                        version="next",
                    )
                secret_obj["next"] = None
                secret_obj["overlap_expires_at"] = None
            else:
                if active_secret is None:
                    raise WebhookSecretNotFoundErrorV2(
                        subscription_id=subscription_id,
                        version="active",
                    )
                if next_secret is not None:
                    secret_obj["active"] = secret_obj.get("next")
                    secret_obj["next"] = None
                    secret_obj["overlap_expires_at"] = None
                else:
                    secret_obj["active"] = None
                    secret_obj["next"] = None
                    secret_obj["overlap_expires_at"] = None
                    payload["enabled"] = False

            timestamps_obj = payload.get("timestamps")
            if not isinstance(timestamps_obj, dict):
                timestamps_obj = {}
                payload["timestamps"] = timestamps_obj
            timestamps_obj["updated_at"] = dt_to_rfc3339(now)
            self._write_payload(path, payload)
            return self._record_from_payload(payload)

    def list_delivery_targets(
        self,
        *,
        event_type: Literal[
            "job.queued",
            "job.running",
            "job.succeeded",
            "job.failed",
            "job.canceled",
        ],
    ) -> list[WebhookDeliveryTargetV2]:
        now = utc_now()
        targets: list[WebhookDeliveryTargetV2] = []
        with self._store_lock():
            for path in self._iter_paths():
                payload = self._read_payload(path)
                changed = self._normalize_secret_rotation_state(payload=payload, now=now)
                if changed:
                    self._write_payload(path, payload)

                enabled = payload_enabled(payload)
                if not enabled:
                    continue
                event_types = payload_event_types(payload)
                if event_type not in event_types:
                    continue

                secret_obj = payload.get("secret")
                if not isinstance(secret_obj, dict):
                    continue
                active_secret = parse_secret_payload(secret_obj.get("active"))
                if active_secret is None:
                    continue
                signing_values: list[str] = [active_secret[0]]

                next_secret = parse_secret_payload(secret_obj.get("next"))
                overlap_expires_at = dt_from_rfc3339(secret_obj.get("overlap_expires_at"))
                if (
                    next_secret is not None
                    and overlap_expires_at is not None
                    and now < overlap_expires_at
                ):
                    signing_values.append(next_secret[0])

                subscription_id_obj = payload.get("subscription_id")
                if not isinstance(subscription_id_obj, str):
                    continue
                targets.append(
                    WebhookDeliveryTargetV2(
                        subscription_id=subscription_id_obj,
                        owner_scope=payload_owner_scope(payload),
                        callback_url=payload_callback_url(payload),
                        event_types=event_types,
                        signing_secrets=tuple(signing_values),
                    )
                )
        return sorted(targets, key=lambda item: item.subscription_id)
