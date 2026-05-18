"""API tests for operator-owned structured LLM settings routes.

Purpose:
    Prove Task 325 exposes hot provider routing mutation only through
    HuleEdu-signed internal identity, while API-key/public callers cannot change
    running service settings.

Relationships:
    - Exercises `interfaces.http_routes_structured_llm_settings_v2` through the
      FastAPI app factory.
    - Reuses the source-neutral structured LLM provider contracts without
      adding provider route fields to conversion job specs.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)
from scripts.sir_convert_a_lot.interfaces.http_api import create_app

_API_KEY = "secret-key"
_KEY_ID = "gateway-identity-rs256-v1"
_LOCAL_PROVIDER_ID = "qwen36-llama-cpp-mtp"
_OPENAI_PROVIDER_ID = "openai-gpt-5.4-mini-2026-03-17"


def test_structured_llm_settings_route_requires_internal_identity(tmp_path: Path) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)

    response = client.put(
        "/v2/operator/structured-llm/provider-routing",
        headers={"X-API-Key": _API_KEY},
        json=_openai_settings_body(version=2),
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "auth_invalid_internal_identity"


def test_structured_llm_settings_route_updates_running_store_for_operator(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = identity.headers(
        subject="operator-1",
        grants={
            "sir-convert:structured-llm-settings:read",
            "sir-convert:structured-llm-settings:write",
        },
    )

    response = client.put(
        "/v2/operator/structured-llm/provider-routing",
        headers=headers,
        json=_openai_settings_body(version=2),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["version"] == 2
    assert payload["settings"]["active_provider_profile_id"] == _OPENAI_PROVIDER_ID
    assert payload["settings"]["allowed_internal_route_classes"] == ["operator_api_only"]
    assert payload["audit_event"]["success"] is True
    assert payload["audit_event"]["previous_settings_version"] == 1

    read_response = client.get(
        "/v2/operator/structured-llm/provider-routing",
        headers=headers,
    )

    assert read_response.status_code == 200
    assert read_response.json()["active_provider_profile_id"] == _OPENAI_PROVIDER_ID


def test_structured_llm_settings_route_rejects_stale_update_and_preserves_active(
    tmp_path: Path,
) -> None:
    identity = _IdentitySigner()
    client = _client(tmp_path, identity)
    headers = identity.headers(
        subject="operator-1",
        grants={
            "sir-convert:structured-llm-settings:read",
            "sir-convert:structured-llm-settings:write",
        },
    )

    response = client.put(
        "/v2/operator/structured-llm/provider-routing",
        headers=headers,
        json=_openai_settings_body(version=1),
    )

    assert response.status_code == 409
    assert response.json()["error"]["details"]["failure_code"] == "stale_version"
    read_response = client.get(
        "/v2/operator/structured-llm/provider-routing",
        headers=headers,
    )
    assert read_response.json()["active_provider_profile_id"] == _LOCAL_PROVIDER_ID


def _client(tmp_path: Path, identity: "_IdentitySigner") -> TestClient:
    return TestClient(
        create_app(
            config=ServiceConfig(
                api_key=_API_KEY,
                data_root=tmp_path,
                internal_identity_public_keys={_KEY_ID: identity.public_key_pem},
                structured_llm=_structured_config(),
            )
        )
    )


def _structured_config() -> StructuredLLMRuntimeConfig:
    local_profile = StructuredLLMProviderProfile(
        provider_id=_LOCAL_PROVIDER_ID,
        model="qwen3.6-27b-q6k-mtp",
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=16384,
        max_output_tokens=4096,
        temperature=0.15,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
        ),
    )
    openai_profile = StructuredLLMProviderProfile(
        provider_id=_OPENAI_PROVIDER_ID,
        model="gpt-5.4-mini-2026-03-17",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=400000,
        max_output_tokens=4096,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
    )
    return StructuredLLMRuntimeConfig(
        enabled=True,
        provider_set=StructuredChatProviderSet(
            primary=local_profile,
            fallback=openai_profile,
        ),
        connections={
            _LOCAL_PROVIDER_ID: StructuredLLMProviderConnection(
                provider_id=_LOCAL_PROVIDER_ID,
                base_url="http://127.0.0.1:8082",
            ),
            _OPENAI_PROVIDER_ID: StructuredLLMProviderConnection(
                provider_id=_OPENAI_PROVIDER_ID,
                base_url="https://api.openai.com",
                api_key="test-token",
            ),
        },
        remote_providers_enabled=True,
        remote_fallback_policy_authorized=True,
    )


def _openai_settings_body(*, version: int) -> dict[str, object]:
    return {
        "version": version,
        "active_provider_profile_id": _OPENAI_PROVIDER_ID,
        "allowed_internal_route_classes": ["operator_api_only"],
        "remote_provider_authorized": True,
        "rollout_label": "openai-mini-eval",
    }


class _IdentitySigner:
    """Small RS256 test signer matching HuleEdu InternalIdentityContextV1."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self._private_key.public_key()
        self.public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def headers(self, *, subject: str, grants: set[str]) -> dict[str, str]:
        now = int(time.time())
        context = {
            "context_version": 1,
            "iss": "api_gateway_service",
            "aud": "sir-convert-a-lot",
            "sub": subject,
            "session_id": f"sess-{subject}",
            "roles": ["operator"],
            "grants": sorted(grants),
            "policy_version": "operator-structured-llm-settings-v1",
            "iat": now,
            "exp": now + 30,
            "jti": f"jti-{subject}",
            "source_app": "huleedu",
        }
        encoded = _b64url(json.dumps(context, sort_keys=True, separators=(",", ":")).encode())
        signature = self._private_key.sign(
            encoded.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return {
            "X-API-Key": _API_KEY,
            "X-HuleEdu-Identity-Context-Version": "1",
            "X-HuleEdu-Identity-Context": encoded,
            "X-HuleEdu-Identity-Key-Id": _KEY_ID,
            "X-HuleEdu-Identity-Signature": f"rs256={_b64url(signature)}",
        }


def _b64url(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
