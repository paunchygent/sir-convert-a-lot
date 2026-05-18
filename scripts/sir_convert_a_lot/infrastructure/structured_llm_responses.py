"""Structured LLM provider response parsing.

Purpose:
    Parse provider-specific JSON responses into source-neutral structured
    response objects while converting malformed or schema-incompatible payloads
    into typed backend failures.

Relationships:
    - Consumes `domain.structured_llm_contracts` and is used by HTTP provider
      adapters after endpoint execution.
    - Keeps raw upstream payloads out of normal production capture and out of
      the provider return type.
    - Supports the endpoint families whose request payloads are built by
      `infrastructure.structured_llm_payloads`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMResponse,
    StructuredLLMUsage,
    StructuredOutputSpec,
)


def parse_structured_llm_provider_payload(
    *,
    payload: object,
    profile: StructuredLLMProviderProfile,
    output_spec: StructuredOutputSpec,
) -> StructuredLLMResponse:
    """Parse a provider payload into a validated structured response."""

    if not isinstance(payload, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider response was not a JSON object.",
        )

    content = _extract_content(payload=payload, profile=profile)
    _validate_content_schema(content=content, output_spec=output_spec, profile=profile)
    return StructuredLLMResponse(
        content=content,
        finish_reason=_extract_finish_reason(payload=payload, profile=profile),
        usage=_extract_usage(payload),
    )


def _extract_content(
    *,
    payload: dict[object, object],
    profile: StructuredLLMProviderProfile,
) -> dict[str, JsonValue]:
    if profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES:
        return _extract_responses_content(payload=payload, profile=profile)
    return _extract_chat_completions_content(payload=payload, profile=profile)


def _extract_chat_completions_content(
    *,
    payload: dict[object, object],
    profile: StructuredLLMProviderProfile,
) -> dict[str, JsonValue]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise _empty_content_error(profile)
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise _empty_content_error(profile)
    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise _empty_content_error(profile)
    content = message.get("content")
    if profile.output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE:
        if not isinstance(content, str) or not content.strip():
            raise _empty_content_error(profile)
        return {"choice": content.strip()}
    if not isinstance(content, str) or not content.strip():
        raise _empty_content_error(profile)
    return _loads_content_object(content=content, profile=profile)


def _extract_responses_content(
    *,
    payload: dict[object, object],
    profile: StructuredLLMProviderProfile,
) -> dict[str, JsonValue]:
    if isinstance(payload.get("refusal"), str):
        raise _refusal_error(profile)
    direct_output = payload.get("output")
    if isinstance(direct_output, dict):
        if isinstance(direct_output.get("refusal"), str):
            raise _refusal_error(profile)
        return _string_keyed_content(direct_output, profile=profile)

    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return _loads_content_object(content=output_text, profile=profile)

    if isinstance(direct_output, list):
        for item in direct_output:
            extracted = _extract_responses_output_item(item=item, profile=profile)
            if extracted is not None:
                return extracted
    raise _empty_content_error(profile)


def _extract_responses_output_item(
    *,
    item: object,
    profile: StructuredLLMProviderProfile,
) -> dict[str, JsonValue] | None:
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("refusal"), str):
        raise _refusal_error(profile)
    content_items = item.get("content")
    if not isinstance(content_items, list):
        return None
    for content_item in content_items:
        if not isinstance(content_item, dict):
            continue
        if isinstance(content_item.get("refusal"), str) or content_item.get("type") == "refusal":
            raise _refusal_error(profile)
        text = content_item.get("text")
        if isinstance(text, str) and text.strip():
            return _loads_content_object(content=text, profile=profile)
    return None


def _loads_content_object(
    *,
    content: str,
    profile: StructuredLLMProviderProfile,
) -> dict[str, JsonValue]:
    try:
        decoded: object = json.loads(content)
    except json.JSONDecodeError as exc:
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_CONTENT_NOT_JSON,
            message="Structured provider content was not valid JSON.",
        ) from exc
    if not isinstance(decoded, dict):
        raise _provider_error(
            profile=profile,
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
            message="Structured provider content JSON was not an object.",
        )
    return _string_keyed_content(decoded, profile=profile)


def _string_keyed_content(
    payload: dict[object, object], *, profile: StructuredLLMProviderProfile
) -> dict[str, JsonValue]:
    content: dict[str, JsonValue] = {}
    for key, value in payload.items():
        if not isinstance(key, str):
            raise _provider_error(
                profile=profile,
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
                message="Structured provider content contained non-JSON object data.",
            )
        content[key] = _coerce_json_value(value=value, profile=profile)
    return content


def _validate_content_schema(
    *,
    content: dict[str, JsonValue],
    output_spec: StructuredOutputSpec,
    profile: StructuredLLMProviderProfile,
) -> None:
    required = output_spec.json_schema.get("required")
    if isinstance(required, list):
        missing = [
            field_name
            for field_name in required
            if isinstance(field_name, str) and field_name not in content
        ]
        if missing:
            raise _schema_mismatch(profile, "Structured provider content missed required fields.")

    properties = output_spec.json_schema.get("properties")
    allowed_keys = frozenset(properties) if isinstance(properties, dict) else frozenset[str]()
    if output_spec.json_schema.get("additionalProperties") is False:
        unknown_keys = frozenset(content) - allowed_keys
        if unknown_keys:
            raise _schema_mismatch(profile, "Structured provider content had unknown fields.")

    if isinstance(properties, dict):
        for key, value in content.items():
            schema = properties.get(key)
            if isinstance(schema, dict) and not _matches_declared_type(value, schema):
                raise _schema_mismatch(
                    profile,
                    "Structured provider content field did not match its declared JSON type.",
                )


def _matches_declared_type(value: JsonValue, schema: Mapping[str, JsonValue]) -> bool:
    declared_type = schema.get("type")
    if declared_type == "string":
        return isinstance(value, str)
    if declared_type == "boolean":
        return isinstance(value, bool)
    if declared_type == "array":
        return isinstance(value, list)
    if declared_type == "object":
        return isinstance(value, dict)
    if declared_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    return True


def _extract_finish_reason(
    *,
    payload: dict[object, object],
    profile: StructuredLLMProviderProfile,
) -> str | None:
    if profile.endpoint_kind == StructuredLLMEndpointKind.RESPONSES:
        status = payload.get("status")
        return status if isinstance(status, str) else None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    finish_reason = first_choice.get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _extract_usage(payload: dict[object, object]) -> StructuredLLMUsage:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return StructuredLLMUsage()
    prompt_tokens = _optional_int(usage.get("prompt_tokens"))
    if prompt_tokens is None:
        prompt_tokens = _optional_int(usage.get("input_tokens"))
    completion_tokens = _optional_int(usage.get("completion_tokens"))
    if completion_tokens is None:
        completion_tokens = _optional_int(usage.get("output_tokens"))
    return StructuredLLMUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=_optional_int(usage.get("total_tokens")),
    )


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _coerce_json_value(*, value: object, profile: StructuredLLMProviderProfile) -> JsonValue:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list):
        return [_coerce_json_value(value=item, profile=profile) for item in value]
    if isinstance(value, dict):
        coerced: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise _provider_error(
                    profile=profile,
                    failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
                    message="Structured provider content contained non-JSON object data.",
                )
            coerced[key] = _coerce_json_value(value=item, profile=profile)
        return coerced
    raise _provider_error(
        profile=profile,
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_RESPONSE_NOT_OBJECT,
        message="Structured provider content contained non-JSON object data.",
    )


def _empty_content_error(profile: StructuredLLMProviderProfile) -> StructuredLLMProviderError:
    return _provider_error(
        profile=profile,
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_EMPTY_CONTENT,
        message="Structured provider response did not contain model content.",
    )


def _schema_mismatch(
    profile: StructuredLLMProviderProfile, message: str
) -> StructuredLLMProviderError:
    return _provider_error(
        profile=profile,
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_SCHEMA_MISMATCH,
        message=message,
    )


def _refusal_error(profile: StructuredLLMProviderProfile) -> StructuredLLMProviderError:
    return _provider_error(
        profile=profile,
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_REFUSAL,
        message="Structured provider returned a refusal instead of schema content.",
    )


def _provider_error(
    *,
    profile: StructuredLLMProviderProfile,
    failure_code: StructuredLLMBackendFailureCode,
    message: str,
) -> StructuredLLMProviderError:
    return StructuredLLMProviderError(
        failure_code=failure_code,
        message=message,
        provider_id=profile.provider_id,
    )
