"""Webhook subscription store v2 lifecycle tests.

Purpose:
    Verify owner-scoped webhook storage behavior and deterministic secret
    lifecycle semantics used by v2 webhook onboarding and push delivery flows.

Relationships:
    - Tests `scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2_store`.
    - Complements HTTP onboarding contract tests in
      `tests.sir_convert_a_lot.test_api_contract_v2_webhook_onboarding`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.infrastructure import (
    webhook_subscriptions_v2_store as webhook_store_module,
)
from scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2 import (
    WebhookSecretNotFoundErrorV2,
    WebhookSubscriptionNotFoundErrorV2,
    WebhookSubscriptionStoreV2,
)


def _build_store(tmp_path: Path, *, overlap_seconds: int = 24 * 3600) -> WebhookSubscriptionStoreV2:
    return WebhookSubscriptionStoreV2(
        data_root=tmp_path / "service_data_webhook_store_v2",
        secret_overlap_seconds=overlap_seconds,
    )


def _set_now(monkeypatch: pytest.MonkeyPatch, now: datetime) -> None:
    monkeypatch.setattr(webhook_store_module, "utc_now", lambda: now)


def test_owner_scope_isolation_for_list_and_get(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    owner_a = "owner_a"
    owner_b = "owner_b"

    record_a, _ = store.create_subscription(
        owner_scope=owner_a,
        callback_url="https://consumer-a.example/hooks/scal",
        event_types=["job.succeeded"],
        enabled=True,
    )
    record_b, _ = store.create_subscription(
        owner_scope=owner_b,
        callback_url="https://consumer-b.example/hooks/scal",
        event_types=["job.failed"],
        enabled=True,
    )

    listed_a = store.list_subscriptions(owner_scope=owner_a)
    listed_b = store.list_subscriptions(owner_scope=owner_b)
    assert [item.subscription_id for item in listed_a] == [record_a.subscription_id]
    assert [item.subscription_id for item in listed_b] == [record_b.subscription_id]

    with pytest.raises(WebhookSubscriptionNotFoundErrorV2):
        store.get_subscription(
            owner_scope=owner_a,
            subscription_id=record_b.subscription_id,
        )


def test_list_delivery_targets_excludes_disabled_and_deleted_subscriptions(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    owner_scope = "owner_targets"

    enabled_record, _ = store.create_subscription(
        owner_scope=owner_scope,
        callback_url="https://consumer.example/hooks/enabled",
        event_types=["job.succeeded"],
        enabled=True,
    )
    disabled_record, _ = store.create_subscription(
        owner_scope=owner_scope,
        callback_url="https://consumer.example/hooks/disabled",
        event_types=["job.succeeded"],
        enabled=False,
    )

    targets = store.list_delivery_targets(event_type="job.succeeded")
    assert [target.subscription_id for target in targets] == [enabled_record.subscription_id]
    assert all(target.subscription_id != disabled_record.subscription_id for target in targets)

    store.delete_subscription(
        owner_scope=owner_scope, subscription_id=enabled_record.subscription_id
    )
    targets_after_delete = store.list_delivery_targets(event_type="job.succeeded")
    assert targets_after_delete == []


def test_secret_rotation_overlap_and_expiry_affects_delivery_signing_keys(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    overlap_seconds = 3600
    store = _build_store(tmp_path, overlap_seconds=overlap_seconds)
    owner_scope = "owner_overlap"
    created_at = datetime(2026, 2, 28, 12, 0, 0, tzinfo=UTC)
    _set_now(monkeypatch, created_at)

    record, _ = store.create_subscription(
        owner_scope=owner_scope,
        callback_url="https://consumer.example/hooks/overlap",
        event_types=["job.succeeded"],
        enabled=True,
    )

    rotate_at = created_at + timedelta(seconds=10)
    _set_now(monkeypatch, rotate_at)
    store.rotate_secret(owner_scope=owner_scope, subscription_id=record.subscription_id)

    during_overlap = rotate_at + timedelta(seconds=30)
    _set_now(monkeypatch, during_overlap)
    targets_during_overlap = store.list_delivery_targets(event_type="job.succeeded")
    assert len(targets_during_overlap) == 1
    assert len(targets_during_overlap[0].signing_secrets) == 2

    after_expiry = rotate_at + timedelta(seconds=overlap_seconds + 1)
    _set_now(monkeypatch, after_expiry)
    targets_after_expiry = store.list_delivery_targets(event_type="job.succeeded")
    assert len(targets_after_expiry) == 1
    assert len(targets_after_expiry[0].signing_secrets) == 1

    refreshed_record = store.get_subscription(
        owner_scope=owner_scope,
        subscription_id=record.subscription_id,
    )
    assert refreshed_record.next_secret_present is False
    assert refreshed_record.overlap_expires_at is None


def test_revoke_secret_behaviors_are_deterministic(tmp_path: Path) -> None:
    store = _build_store(tmp_path)
    owner_scope = "owner_revoke"

    record, _ = store.create_subscription(
        owner_scope=owner_scope,
        callback_url="https://consumer.example/hooks/revoke",
        event_types=["job.succeeded"],
        enabled=True,
    )

    with pytest.raises(WebhookSecretNotFoundErrorV2):
        store.revoke_secret(
            owner_scope=owner_scope,
            subscription_id=record.subscription_id,
            version="next",
        )

    post_revoke_record = store.revoke_secret(
        owner_scope=owner_scope,
        subscription_id=record.subscription_id,
        version="active",
    )
    assert post_revoke_record.enabled is False
    assert post_revoke_record.active_secret_present is False
    assert post_revoke_record.next_secret_present is False

    targets = store.list_delivery_targets(event_type="job.succeeded")
    assert targets == []
