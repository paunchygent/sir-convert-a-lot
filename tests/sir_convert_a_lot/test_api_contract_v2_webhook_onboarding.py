"""Contract tests for v2 webhook onboarding endpoints.

Purpose:
    Verify deterministic webhook onboarding CRUD and secret lifecycle behavior
    for service API v2 async push subscriptions.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.http_routes_webhooks_v2`.
    - Uses the canonical API app from `scripts.sir_convert_a_lot.service`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import create_app


def _build_client(
    tmp_path: Path,
    *,
    enable_webhook_onboarding: bool,
    internal_api_key: str | None = None,
) -> TestClient:
    default_capabilities = frozenset({"jobs:read", "push:read", "push:write"})
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            internal_api_key=internal_api_key,
            data_root=tmp_path / "service_data_webhook_onboarding",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_webhook_onboarding=enable_webhook_onboarding,
            api_capabilities=default_capabilities,
        )
    )
    return TestClient(app)


def _create_subscription(
    client: TestClient,
    *,
    callback_url: str = "https://consumer.example/hooks/sir-convert-a-lot",
    event_types: list[str] | None = None,
    enabled: bool = True,
):
    body = {
        "callback_url": callback_url,
        "event_types": event_types or ["job.succeeded", "job.failed", "job.canceled"],
        "enabled": enabled,
    }
    return client.post(
        "/v2/push/webhooks/subscriptions",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_create"},
        json=body,
    )


def test_create_list_get_redacts_secret_material(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    create_response = _create_subscription(client)
    assert create_response.status_code == 201
    create_payload = create_response.json()
    assert create_payload["api_version"] == "v2"
    assert create_payload["secret"]["version"] == "active"
    assert create_payload["secret"]["revealed_once"] is True
    assert create_payload["secret"]["value"].startswith("whsec_")
    subscription_id = create_payload["subscription"]["subscription_id"]

    list_response = client.get(
        "/v2/push/webhooks/subscriptions",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_list"},
    )
    assert list_response.status_code == 200
    list_payload = list_response.json()
    subscriptions = list_payload["subscriptions"]
    assert len(subscriptions) == 1
    assert "secret" not in subscriptions[0]
    assert subscriptions[0]["subscription_id"] == subscription_id

    get_response = client.get(
        f"/v2/push/webhooks/subscriptions/{subscription_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_get"},
    )
    assert get_response.status_code == 200
    get_payload = get_response.json()
    assert get_payload["subscription"]["subscription_id"] == subscription_id
    assert "secret" not in get_payload["subscription"]


def test_patch_updates_subscription_fields(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    create_response = _create_subscription(client)
    subscription_id = create_response.json()["subscription"]["subscription_id"]

    patch_response = client.patch(
        f"/v2/push/webhooks/subscriptions/{subscription_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_patch"},
        json={
            "callback_url": "https://consumer.example/hooks/scal-prod",
            "event_types": ["job.succeeded", "job.failed"],
            "enabled": False,
        },
    )
    assert patch_response.status_code == 200
    payload = patch_response.json()
    assert payload["subscription"]["callback_url"] == "https://consumer.example/hooks/scal-prod"
    assert payload["subscription"]["event_types"] == ["job.succeeded", "job.failed"]
    assert payload["subscription"]["enabled"] is False


def test_duplicate_callback_is_rejected_for_same_owner(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    first = _create_subscription(client, callback_url="https://consumer.example/hooks/duplicate")
    assert first.status_code == 201

    second = _create_subscription(client, callback_url="https://consumer.example/hooks/duplicate")
    assert second.status_code == 409
    payload = second.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "webhook_subscription_conflict"


def test_invalid_callback_url_returns_webhook_endpoint_invalid(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    response = _create_subscription(client, callback_url="not-a-url")
    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "webhook_endpoint_invalid"


def test_patch_requires_mutable_fields(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    create_response = _create_subscription(client)
    subscription_id = create_response.json()["subscription"]["subscription_id"]

    response = client.patch(
        f"/v2/push/webhooks/subscriptions/{subscription_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_patch_empty"},
        json={},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "validation_error"
    assert payload["error"]["details"] == {"field": "body"}


def test_rotate_and_revoke_secret_overlap_semantics(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    create_response = _create_subscription(client)
    subscription_id = create_response.json()["subscription"]["subscription_id"]

    rotate_response = client.post(
        f"/v2/push/webhooks/subscriptions/{subscription_id}/rotate-secret",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_rotate"},
        json={"reason": "scheduled_rotation"},
    )
    assert rotate_response.status_code == 200
    rotate_payload = rotate_response.json()
    assert rotate_payload["secret"]["version"] == "next"
    assert rotate_payload["secret"]["value"].startswith("whsec_")
    assert rotate_payload["overlap"]["active_and_next_valid"] is True
    assert rotate_payload["overlap"]["overlap_hours"] == 24
    assert rotate_payload["overlap"]["overlap_expires_at"] is not None

    revoke_next_response = client.post(
        f"/v2/push/webhooks/subscriptions/{subscription_id}/revoke-secret",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_revoke_next"},
        json={"version": "next"},
    )
    assert revoke_next_response.status_code == 200
    revoke_next_payload = revoke_next_response.json()
    assert revoke_next_payload["revoked_version"] == "next"
    assert revoke_next_payload["overlap"]["active_and_next_valid"] is False
    assert revoke_next_payload["overlap"]["overlap_expires_at"] is None

    rotate_again = client.post(
        f"/v2/push/webhooks/subscriptions/{subscription_id}/rotate-secret",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_rotate_again"},
        json={"reason": "second_rotation"},
    )
    assert rotate_again.status_code == 200

    revoke_active_response = client.post(
        f"/v2/push/webhooks/subscriptions/{subscription_id}/revoke-secret",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_revoke_active"},
        json={"version": "active"},
    )
    assert revoke_active_response.status_code == 200
    revoke_active_payload = revoke_active_response.json()
    assert revoke_active_payload["revoked_version"] == "active"
    assert revoke_active_payload["overlap"]["active_and_next_valid"] is False


def test_delete_subscription_returns_204_and_hides_record(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    create_response = _create_subscription(client)
    subscription_id = create_response.json()["subscription"]["subscription_id"]

    delete_response = client.delete(
        f"/v2/push/webhooks/subscriptions/{subscription_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_delete"},
    )
    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = client.get(
        f"/v2/push/webhooks/subscriptions/{subscription_id}",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_get_after_delete"},
    )
    assert get_response.status_code == 404
    payload = get_response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "webhook_subscription_not_found"


def test_webhook_routes_require_api_key(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    response = client.get("/v2/push/webhooks/subscriptions")
    assert response.status_code == 401
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "auth_invalid_api_key"


def test_webhook_routes_reject_invalid_api_key(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=True)
    response = client.get(
        "/v2/push/webhooks/subscriptions",
        headers={"X-API-Key": "wrong-key", "X-Correlation-ID": "corr_invalid_api_key"},
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "auth_invalid_api_key"


def test_webhook_routes_reject_internal_api_key(tmp_path: Path) -> None:
    client = _build_client(
        tmp_path,
        enable_webhook_onboarding=True,
        internal_api_key="internal-secret-key",
    )
    response = client.get(
        "/v2/push/webhooks/subscriptions",
        headers={
            "X-API-Key": "internal-secret-key",
            "X-Correlation-ID": "corr_internal_api_key",
        },
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "auth_invalid_api_key"


def test_webhook_read_routes_require_push_read_scope(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_webhook_onboarding_scope_read",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_webhook_onboarding=True,
            api_capabilities=frozenset({"push:write"}),
        )
    )
    client = TestClient(app)

    create_response = _create_subscription(client)
    assert create_response.status_code == 201

    list_response = client.get(
        "/v2/push/webhooks/subscriptions",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_scope_read_list"},
    )
    assert list_response.status_code == 403
    payload = list_response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "insufficient_scope"
    assert payload["error"]["details"] == {
        "required_capability": "push:read",
        "surface": "webhook_onboarding",
    }


def test_webhook_write_routes_require_push_write_scope(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_webhook_onboarding_scope_write",
            enable_supervisor=False,
            processing_delay_seconds=0.0,
            enable_webhook_onboarding=True,
            api_capabilities=frozenset({"push:read"}),
        )
    )
    client = TestClient(app)

    response = _create_subscription(client)
    assert response.status_code == 403
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "insufficient_scope"
    assert payload["error"]["details"] == {
        "required_capability": "push:write",
        "surface": "webhook_onboarding",
    }


def test_webhook_routes_return_push_disabled_when_feature_flag_off(tmp_path: Path) -> None:
    client = _build_client(tmp_path, enable_webhook_onboarding=False)
    response = client.get(
        "/v2/push/webhooks/subscriptions",
        headers={"X-API-Key": "secret-key", "X-Correlation-ID": "corr_webhook_disabled"},
    )
    assert response.status_code == 503
    payload = response.json()
    assert payload["api_version"] == "v2"
    assert payload["error"]["code"] == "push_disabled"
