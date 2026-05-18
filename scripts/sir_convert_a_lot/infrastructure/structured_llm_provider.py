"""HTTP-backed structured LLM provider adapter.

Purpose:
    Execute source-neutral structured-output requests against configured
    OpenAI-compatible provider endpoints and return validated structured
    response objects.

Relationships:
    - Implements the Task 296 provider execution slice behind
      `domain.structured_llm_contracts.StructuredChatProviderProtocol`.
    - Uses `infrastructure.structured_llm_payloads` for endpoint-specific
      request shapes and `infrastructure.structured_llm_responses` for response
      parsing.
    - Does not know about DigiExam parser DTOs, renderer inputs, HTTP artifact
      routes, or answer-key advisory report orchestration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import httpx

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_structured_llm_payload,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_responses import (
    parse_structured_llm_provider_payload,
)


@dataclass(frozen=True)
class StructuredLLMProviderConnection:
    """Connection settings for one structured provider profile."""

    provider_id: str
    base_url: str
    api_key: str = ""
    extra_headers: Mapping[str, str] | None = None
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("Structured provider connection id must be non-empty.")
        if not self.base_url.strip():
            raise ValueError("Structured provider base_url must be non-empty.")
        if self.timeout_seconds <= 0:
            raise ValueError("Structured provider timeout_seconds must be positive.")

    @property
    def normalized_base_url(self) -> str:
        """Base URL normalized to include the OpenAI-compatible `/v1` prefix."""

        stripped = self.base_url.strip().rstrip("/")
        if stripped.endswith("/v1"):
            return stripped
        return f"{stripped}/v1"


class HttpStructuredChatProvider:
    """Async HTTP adapter for configured structured-output providers."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        connections: Mapping[str, StructuredLLMProviderConnection],
    ) -> None:
        self._client = client
        self._connections = connections

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        """Execute one provider request and parse a structured response."""

        connection = self._connection_for(profile)
        payload = build_structured_llm_payload(profile=profile, request=request)
        try:
            response = await self._client.post(
                _endpoint_url(connection=connection, endpoint_kind=profile.endpoint_kind),
                headers=_headers(connection),
                json=payload,
                timeout=connection.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
                message="Structured provider returned an unsuccessful HTTP status.",
                provider_id=profile.provider_id,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.TimeoutException as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
                message="Structured provider request timed out.",
                provider_id=profile.provider_id,
            ) from exc
        except httpx.RequestError as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
                message="Structured provider request failed before a response was received.",
                provider_id=profile.provider_id,
            ) from exc

        try:
            response_payload: object = response.json()
        except ValueError as exc:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON,
                message="Structured provider response body was not valid JSON.",
                provider_id=profile.provider_id,
            ) from exc

        return parse_structured_llm_provider_payload(
            payload=response_payload,
            profile=profile,
            output_spec=request.output_spec,
        )

    def _connection_for(
        self, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMProviderConnection:
        connection = self._connections.get(profile.provider_id)
        if connection is None:
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_CONFIG_MISSING,
                message="Structured provider connection is not configured.",
                provider_id=profile.provider_id,
            )
        return connection


def _endpoint_url(
    *,
    connection: StructuredLLMProviderConnection,
    endpoint_kind: StructuredLLMEndpointKind,
) -> str:
    if endpoint_kind == StructuredLLMEndpointKind.RESPONSES:
        return f"{connection.normalized_base_url}/responses"
    return f"{connection.normalized_base_url}/chat/completions"


def _headers(connection: StructuredLLMProviderConnection) -> dict[str, str]:
    headers: dict[str, str] = dict(connection.extra_headers or {})
    if connection.api_key.strip():
        headers["Authorization"] = f"Bearer {connection.api_key.strip()}"
    return headers
