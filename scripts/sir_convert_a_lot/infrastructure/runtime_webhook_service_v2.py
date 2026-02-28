"""Webhook runtime service for v2 onboarding and delivery orchestration.

Purpose:
    Encapsulate webhook onboarding CRUD, secret lifecycle error mapping, and
    lifecycle-event enqueue behavior so runtime orchestration stays SRP-focused.

Relationships:
    - Composed by `infrastructure.runtime_engine_v2`.
    - Uses `webhook_subscriptions_v2_store` for owner-scoped subscription state.
    - Uses `webhook_delivery_v2` worker for outbox delivery queueing.
"""

from __future__ import annotations

import hashlib

from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import JobExpiredV2, JobMissingV2
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.webhook_delivery_v2 import WebhookDeliveryWorkerV2
from scripts.sir_convert_a_lot.infrastructure.webhook_subscriptions_v2 import (
    WebhookEndpointInvalidErrorV2,
    WebhookEventTypeInvalidErrorV2,
    WebhookSecretNotFoundErrorV2,
    WebhookSecretStateConflictErrorV2,
    WebhookSecretVersionV2,
    WebhookSubscriptionConflictErrorV2,
    WebhookSubscriptionNotFoundErrorV2,
    WebhookSubscriptionRecordV2,
    WebhookSubscriptionStoreV2,
)


class RuntimeWebhookServiceV2:
    """Owner-scoped webhook runtime service with delivery queue integration."""

    def __init__(
        self,
        *,
        job_store: JobStoreV2,
        webhook_store: WebhookSubscriptionStoreV2,
        webhook_delivery_worker: WebhookDeliveryWorkerV2 | None,
        enable_webhook_delivery: bool,
        sse_replay_horizon_seconds: int,
    ) -> None:
        self.job_store = job_store
        self.webhook_store = webhook_store
        self.webhook_delivery_worker = webhook_delivery_worker
        self.enable_webhook_delivery = enable_webhook_delivery
        self.sse_replay_horizon_seconds = sse_replay_horizon_seconds

    def _owner_scope_for_api_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    def _raise_webhook_validation_error(
        self,
        exc: WebhookEndpointInvalidErrorV2 | WebhookEventTypeInvalidErrorV2,
    ) -> None:
        if isinstance(exc, WebhookEndpointInvalidErrorV2):
            raise ServiceError(
                status_code=422,
                code="webhook_endpoint_invalid",
                message="Webhook callback URL is invalid.",
                retryable=False,
                details={"callback_url": exc.callback_url, "reason": exc.reason},
            ) from exc

        raise ServiceError(
            status_code=422,
            code="validation_error",
            message="Webhook subscription validation failed.",
            retryable=False,
            details={"reason": exc.reason},
        ) from exc

    def _raise_webhook_missing_error(self, subscription_id: str) -> None:
        raise ServiceError(
            status_code=404,
            code="webhook_subscription_not_found",
            message="Webhook subscription was not found.",
            retryable=False,
            details={"subscription_id": subscription_id},
        )

    def create_webhook_subscription(
        self,
        *,
        api_key: str,
        callback_url: str,
        event_types: list[str],
        enabled: bool,
    ) -> tuple[WebhookSubscriptionRecordV2, str]:
        try:
            record, reveal = self.webhook_store.create_subscription(
                owner_scope=self._owner_scope_for_api_key(api_key),
                callback_url=callback_url,
                event_types=event_types,
                enabled=enabled,
            )
            return record, reveal.value
        except (WebhookEndpointInvalidErrorV2, WebhookEventTypeInvalidErrorV2) as exc:
            self._raise_webhook_validation_error(exc)
        except WebhookSubscriptionConflictErrorV2 as exc:
            raise ServiceError(
                status_code=409,
                code="webhook_subscription_conflict",
                message="Webhook subscription already exists for callback URL.",
                retryable=False,
                details={
                    "callback_url": exc.callback_url,
                    "owner_scope": exc.owner_scope,
                },
            ) from exc
        raise AssertionError("Unreachable webhook create branch.")

    def list_webhook_subscriptions(self, *, api_key: str) -> list[WebhookSubscriptionRecordV2]:
        return self.webhook_store.list_subscriptions(
            owner_scope=self._owner_scope_for_api_key(api_key),
        )

    def get_webhook_subscription(
        self,
        *,
        api_key: str,
        subscription_id: str,
    ) -> WebhookSubscriptionRecordV2:
        try:
            return self.webhook_store.get_subscription(
                owner_scope=self._owner_scope_for_api_key(api_key),
                subscription_id=subscription_id,
            )
        except WebhookSubscriptionNotFoundErrorV2 as exc:
            self._raise_webhook_missing_error(exc.subscription_id)
        raise AssertionError("Unreachable webhook get branch.")

    def update_webhook_subscription(
        self,
        *,
        api_key: str,
        subscription_id: str,
        callback_url: str | None,
        event_types: list[str] | None,
        enabled: bool | None,
    ) -> WebhookSubscriptionRecordV2:
        if callback_url is None and event_types is None and enabled is None:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="At least one mutable field must be provided.",
                retryable=False,
                details={"field": "body"},
            )
        try:
            return self.webhook_store.update_subscription(
                owner_scope=self._owner_scope_for_api_key(api_key),
                subscription_id=subscription_id,
                callback_url=callback_url,
                event_types=event_types,
                enabled=enabled,
            )
        except WebhookSubscriptionNotFoundErrorV2 as exc:
            self._raise_webhook_missing_error(exc.subscription_id)
        except (WebhookEndpointInvalidErrorV2, WebhookEventTypeInvalidErrorV2) as exc:
            self._raise_webhook_validation_error(exc)
        except WebhookSubscriptionConflictErrorV2 as exc:
            raise ServiceError(
                status_code=409,
                code="webhook_subscription_conflict",
                message="Webhook subscription already exists for callback URL.",
                retryable=False,
                details={
                    "callback_url": exc.callback_url,
                    "owner_scope": exc.owner_scope,
                },
            ) from exc
        raise AssertionError("Unreachable webhook update branch.")

    def rotate_webhook_secret(
        self,
        *,
        api_key: str,
        subscription_id: str,
    ) -> tuple[WebhookSubscriptionRecordV2, str]:
        try:
            record, reveal, _ = self.webhook_store.rotate_secret(
                owner_scope=self._owner_scope_for_api_key(api_key),
                subscription_id=subscription_id,
            )
            return record, reveal.value
        except WebhookSubscriptionNotFoundErrorV2 as exc:
            self._raise_webhook_missing_error(exc.subscription_id)
        except WebhookSecretStateConflictErrorV2 as exc:
            raise ServiceError(
                status_code=409,
                code="webhook_secret_conflict",
                message=exc.reason,
                retryable=False,
            ) from exc
        raise AssertionError("Unreachable webhook rotate branch.")

    def revoke_webhook_secret(
        self,
        *,
        api_key: str,
        subscription_id: str,
        version: WebhookSecretVersionV2 | None,
    ) -> tuple[WebhookSubscriptionRecordV2, WebhookSecretVersionV2]:
        resolved_version: WebhookSecretVersionV2 = "active" if version is None else version
        try:
            record = self.webhook_store.revoke_secret(
                owner_scope=self._owner_scope_for_api_key(api_key),
                subscription_id=subscription_id,
                version=resolved_version,
            )
            return record, resolved_version
        except WebhookSubscriptionNotFoundErrorV2 as exc:
            self._raise_webhook_missing_error(exc.subscription_id)
        except WebhookSecretNotFoundErrorV2 as exc:
            raise ServiceError(
                status_code=404,
                code="webhook_secret_not_found",
                message="Webhook secret version was not found for subscription.",
                retryable=False,
                details={"subscription_id": exc.subscription_id, "version": exc.version},
            ) from exc
        except WebhookSecretStateConflictErrorV2 as exc:
            raise ServiceError(
                status_code=409,
                code="webhook_secret_conflict",
                message=exc.reason,
                retryable=False,
            ) from exc
        raise AssertionError("Unreachable webhook revoke branch.")

    def delete_webhook_subscription(self, *, api_key: str, subscription_id: str) -> None:
        try:
            self.webhook_store.delete_subscription(
                owner_scope=self._owner_scope_for_api_key(api_key),
                subscription_id=subscription_id,
            )
        except WebhookSubscriptionNotFoundErrorV2 as exc:
            self._raise_webhook_missing_error(exc.subscription_id)

    def enqueue_webhook_events_for_job(self, *, job_id: str) -> None:
        if not self.enable_webhook_delivery:
            return
        if self.webhook_delivery_worker is None:
            return
        try:
            events = self.job_store.list_job_events_after_sequence(
                job_id=job_id,
                after_sequence=0,
                replay_horizon_seconds=self.sse_replay_horizon_seconds,
            )
        except (JobMissingV2, JobExpiredV2):
            return
        if len(events) == 0:
            return
        self.webhook_delivery_worker.enqueue_events(events=events)
