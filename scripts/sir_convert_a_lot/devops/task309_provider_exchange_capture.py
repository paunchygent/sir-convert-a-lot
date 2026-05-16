"""Task 309 provider exchange capture.

Purpose:
    Capture validation-only structured-provider requests and responses for
    Task 309 live runs while preserving the normal provider decoding contract.

Relationships:
    - Used by `task309_live_execution` for advisory corpus evidence.
    - Delegates payload construction to the generic structured LLM payload
      builder used by production providers.
    - Keeps raw exchange retention isolated from normal answer-key completion
      report and capture contracts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import httpx
from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_payloads import (
    build_structured_llm_payload,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
    _endpoint_url,
    _headers,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_responses import (
    parse_structured_llm_provider_payload,
)


@dataclass(frozen=True)
class Task309ProviderExchange:
    """One validation-only provider request/response exchange."""

    job_id: str
    item_id: str
    provider_profile_id: str
    model: str
    endpoint_kind: str
    output_mode: str
    request_payload_json: str
    response_status_code: int | None
    raw_response_text: str | None
    response_payload_json: str | None
    decoded_content_json: str | None
    failure_code: str | None

    def to_payload(self) -> dict[str, object]:
        """Return JSON-safe exchange evidence."""

        return _json_object(asdict(self))


class Task309CapturingStructuredChatProvider:
    """HTTP provider adapter that keeps validation-only raw exchanges."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        connections: dict[str, StructuredLLMProviderConnection],
    ) -> None:
        self._client = client
        self._connections = connections
        self._exchanges: dict[tuple[str, str], Task309ProviderExchange] = {}

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        """Execute a provider request while retaining validation evidence."""

        connection = self._connection_for(profile)
        payload = build_structured_llm_payload(profile=profile, request=request)
        request_payload_json = _canonical_json(payload)
        raw_response_text: str | None = None
        response_status_code: int | None = None
        response_payload_json: str | None = None
        try:
            response = await self._client.post(
                _endpoint_url(connection=connection, endpoint_kind=profile.endpoint_kind),
                headers=_headers(connection),
                json=payload,
                timeout=connection.timeout_seconds,
            )
            response_status_code = response.status_code
            raw_response_text = response.text
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._record_exchange(
                request=request,
                profile=profile,
                request_payload_json=request_payload_json,
                response_status_code=exc.response.status_code,
                raw_response_text=raw_response_text,
                response_payload_json=None,
                decoded_content_json=None,
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR.value,
            )
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
                message="Structured provider returned an unsuccessful HTTP status.",
                provider_id=profile.provider_id,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.RequestError as exc:
            self._record_request_failure(
                request=request,
                profile=profile,
                request_payload_json=request_payload_json,
                response_status_code=response_status_code,
                raw_response_text=raw_response_text,
            )
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED,
                message="Structured provider request failed before a response was received.",
                provider_id=profile.provider_id,
            ) from exc
        return self._parse_success_response(
            request=request,
            profile=profile,
            response=response,
            response_status_code=response_status_code,
            request_payload_json=request_payload_json,
            raw_response_text=raw_response_text,
            response_payload_json=response_payload_json,
        )

    def exchanges_for_job(self, job_id: str) -> dict[str, Task309ProviderExchange]:
        """Return captured exchanges for one source-file job id."""

        return {
            item_id: exchange
            for (exchange_job_id, item_id), exchange in self._exchanges.items()
            if exchange_job_id == job_id
        }

    def _parse_success_response(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        response: httpx.Response,
        response_status_code: int | None,
        request_payload_json: str,
        raw_response_text: str | None,
        response_payload_json: str | None,
    ) -> StructuredLLMResponse:
        try:
            response_payload: object = response.json()
        except ValueError as exc:
            self._record_exchange(
                request=request,
                profile=profile,
                request_payload_json=request_payload_json,
                response_status_code=response_status_code,
                raw_response_text=raw_response_text,
                response_payload_json=None,
                decoded_content_json=None,
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON.value,
            )
            raise StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_INVALID_JSON,
                message="Structured provider response body was not valid JSON.",
                provider_id=profile.provider_id,
            ) from exc
        parsed_payload_json = _canonical_json(response_payload)
        try:
            parsed = parse_structured_llm_provider_payload(
                payload=response_payload,
                profile=profile,
                output_spec=request.output_spec,
            )
        except StructuredLLMProviderError as exc:
            self._record_exchange(
                request=request,
                profile=profile,
                request_payload_json=request_payload_json,
                response_status_code=response_status_code,
                raw_response_text=raw_response_text,
                response_payload_json=parsed_payload_json,
                decoded_content_json=None,
                failure_code=exc.failure_code.value,
            )
            raise
        self._record_exchange(
            request=request,
            profile=profile,
            request_payload_json=request_payload_json,
            response_status_code=response_status_code,
            raw_response_text=raw_response_text,
            response_payload_json=(
                parsed_payload_json if response_payload_json is None else response_payload_json
            ),
            decoded_content_json=_canonical_json(parsed.content),
            failure_code=None,
        )
        return parsed

    def _record_request_failure(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        request_payload_json: str,
        response_status_code: int | None,
        raw_response_text: str | None,
    ) -> None:
        self._record_exchange(
            request=request,
            profile=profile,
            request_payload_json=request_payload_json,
            response_status_code=response_status_code,
            raw_response_text=raw_response_text,
            response_payload_json=None,
            decoded_content_json=None,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_REQUEST_FAILED.value,
        )

    def _record_exchange(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
        request_payload_json: str,
        response_status_code: int | None,
        raw_response_text: str | None,
        response_payload_json: str | None,
        decoded_content_json: str | None,
        failure_code: str | None,
    ) -> None:
        self._exchanges[(request.job_id, request.item_id)] = Task309ProviderExchange(
            job_id=request.job_id,
            item_id=request.item_id,
            provider_profile_id=profile.provider_id,
            model=profile.model,
            endpoint_kind=profile.endpoint_kind.value,
            output_mode=profile.output_mode.value,
            request_payload_json=request_payload_json,
            response_status_code=response_status_code,
            raw_response_text=raw_response_text,
            response_payload_json=response_payload_json,
            decoded_content_json=decoded_content_json,
            failure_code=failure_code,
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


def _canonical_json(payload: object) -> str:
    return json.dumps(
        _json_payload_value(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Task 309 provider exchange must serialize to an object.")
    return {str(key): _json_payload_value(child) for key, child in value.items()}


def _json_payload_value(value: object) -> JsonValue:
    if isinstance(value, dict):
        return {str(key): _json_payload_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_payload_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported Task 309 exchange JSON value: {type(value).__name__}")
