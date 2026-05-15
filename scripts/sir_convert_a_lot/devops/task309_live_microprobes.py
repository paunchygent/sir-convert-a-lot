"""Task 309 Granite/vLLM provider microprobes.

Purpose:
    Execute redacted structured-output microprobes against the persistent
    Granite/vLLM provider before full-corpus answer-key validation.

Relationships:
    - Uses the generic Task 296 HTTP structured-provider adapter.
    - Proves the Task 309 required output modes: vLLM choice, vLLM JSON Schema
      choice object, and vLLM JSON Schema gap-fill object.
    - Produces report rows without raw prompts or raw provider responses.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass, replace

import httpx

from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_PROVIDER_MODEL,
    DEFAULT_PROVIDER_URL,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_status import (
    build_task309_provider_status,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
    StructuredLLMProviderConnection,
)

TASK309_MICROPROBE_REPORT_SCHEMA_VERSION = "task309_granite_microprobe_report_v1"
PROVIDER_ID = "task309-granite-vllm"


@dataclass(frozen=True)
class Task309MicroprobeResult:
    """One redacted provider microprobe result."""

    probe_id: str
    output_mode: str
    schema_name: str
    ok: bool
    latency_ms: float | None
    finish_reason: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    failure_code: str | None


@dataclass(frozen=True)
class Task309MicroprobeReport:
    """Redacted provider microprobe report."""

    schema_version: str
    provider_url: str
    model: str
    provider_ready: bool
    blocked: bool
    results: tuple[Task309MicroprobeResult, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the microprobe report."""

        return _json_object(asdict(self))


def run_task309_microprobes(
    *,
    provider_url: str = DEFAULT_PROVIDER_URL,
    model: str = DEFAULT_PROVIDER_MODEL,
    require_provider_ready: bool = True,
    timeout_seconds: float = 30.0,
) -> Task309MicroprobeReport:
    """Run the Task 309 provider microprobes."""

    return asyncio.run(
        _run_task309_microprobes(
            provider_url=provider_url,
            model=model,
            require_provider_ready=require_provider_ready,
            timeout_seconds=timeout_seconds,
        )
    )


async def _run_task309_microprobes(
    *,
    provider_url: str,
    model: str,
    require_provider_ready: bool,
    timeout_seconds: float,
) -> Task309MicroprobeReport:
    ready = build_task309_provider_status(
        provider_url=provider_url,
        timeout_seconds=min(timeout_seconds, 2.0),
    ).ready
    if require_provider_ready and not ready:
        return Task309MicroprobeReport(
            schema_version=TASK309_MICROPROBE_REPORT_SCHEMA_VERSION,
            provider_url=provider_url,
            model=model,
            provider_ready=False,
            blocked=True,
            results=(),
        )
    async with httpx.AsyncClient() as client:
        provider = _provider(
            provider_url=provider_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        results = [
            await _microprobe(provider, request, profile, expected)
            for request, profile, expected in _microprobe_requests(model=model)
        ]
    return Task309MicroprobeReport(
        schema_version=TASK309_MICROPROBE_REPORT_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
        provider_ready=ready,
        blocked=False,
        results=tuple(results),
    )


async def _microprobe(
    provider: HttpStructuredChatProvider,
    request: StructuredLLMRequest,
    profile: StructuredLLMProviderProfile,
    expected: dict[str, object],
) -> Task309MicroprobeResult:
    started = time.perf_counter()
    try:
        response = await provider.complete_structured_chat(request=request, profile=profile)
    except StructuredLLMProviderError as exc:
        return Task309MicroprobeResult(
            probe_id=request.item_id,
            output_mode=profile.output_mode.value,
            schema_name=request.output_spec.schema_name,
            ok=False,
            latency_ms=round((time.perf_counter() - started) * 1000, 3),
            finish_reason=None,
            prompt_tokens=None,
            completion_tokens=None,
            total_tokens=None,
            failure_code=exc.failure_code.value,
        )
    return Task309MicroprobeResult(
        probe_id=request.item_id,
        output_mode=profile.output_mode.value,
        schema_name=request.output_spec.schema_name,
        ok=_content_matches(response, expected),
        latency_ms=round((time.perf_counter() - started) * 1000, 3),
        finish_reason=response.finish_reason,
        prompt_tokens=response.usage.prompt_tokens,
        completion_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens,
        failure_code=None,
    )


def _provider(
    *,
    provider_url: str,
    timeout_seconds: float,
    client: httpx.AsyncClient,
) -> HttpStructuredChatProvider:
    connection = StructuredLLMProviderConnection(
        provider_id=PROVIDER_ID,
        base_url=provider_url,
        timeout_seconds=timeout_seconds,
    )
    return HttpStructuredChatProvider(client=client, connections={PROVIDER_ID: connection})


def _microprobe_requests(
    *,
    model: str,
) -> tuple[tuple[StructuredLLMRequest, StructuredLLMProviderProfile, dict[str, object]], ...]:
    return (
        (
            _request("microprobe-choice", _choice_probe_spec(), '{"answer":"B"}'),
            _choice_profile(model),
            {"choice": "B"},
        ),
        (
            _request("microprobe-choice-object", _choice_object_spec(), '{"answer":2}'),
            _json_profile(model),
            {"decision_state": "answered", "correct_alternative_ids": [2]},
        ),
        (
            _request("microprobe-gap-object", _gap_probe_spec(), '{"gap_id":"gap-1"}'),
            _json_profile(model),
            {"decision_state": "answered", "gap_id": "gap-1"},
        ),
    )


def _request(
    item_id: str,
    output_spec: StructuredOutputSpec,
    user_payload: str,
) -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="task309-microprobe",
        item_id=item_id,
        item_type="microprobe",
        prompt_template_version="task309_granite_microprobe_v1",
        system_prompt="Return only the constrained answer requested by the schema.",
        user_payload=user_payload,
        output_spec=output_spec,
        estimated_input_tokens=max(1, len(user_payload) // 4),
        max_output_tokens=128,
        allow_remote_fallback=False,
    )


def _base_profile(model: str) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id=PROVIDER_ID,
        model=model,
        endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=4096,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=True,
        ),
    )


def _choice_profile(model: str) -> StructuredLLMProviderProfile:
    return replace(_base_profile(model), output_mode=StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE)


def _json_profile(model: str) -> StructuredLLMProviderProfile:
    return _base_profile(model)


def _choice_probe_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name="task309_choice_microprobe",
        schema_version="task309_choice_microprobe_v1",
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"choice": {"type": "string", "enum": ["A", "B", "C"]}},
            "required": ["choice"],
        },
        choice_values=("A", "B", "C"),
    )


def _choice_object_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision_state": {"type": "string", "enum": ["answered"]},
                "correct_alternative_ids": {"type": "array", "items": {"type": "integer"}},
                "manual_follow_up_code": {"type": ["string", "null"]},
            },
            "required": ["decision_state", "correct_alternative_ids", "manual_follow_up_code"],
        },
    )


def _gap_probe_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        schema_version=DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
        json_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "decision_state": {"type": "string", "enum": ["answered"]},
                "gap_answers": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "gap_id": {"type": "string"},
                            "accepted_values": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["gap_id", "accepted_values"],
                    },
                },
                "manual_follow_up_code": {"type": ["string", "null"]},
            },
            "required": ["decision_state", "gap_answers", "manual_follow_up_code"],
        },
    )


def _content_matches(response: StructuredLLMResponse, expected: dict[str, object]) -> bool:
    if expected.get("choice") is not None:
        return response.content.get("choice") == expected["choice"]
    if response.content.get("decision_state") != expected.get("decision_state"):
        return False
    if expected.get("correct_alternative_ids") is not None:
        return (
            response.content.get("correct_alternative_ids") == expected["correct_alternative_ids"]
        )
    gap_answers = response.content.get("gap_answers")
    return (
        isinstance(gap_answers, list)
        and bool(gap_answers)
        and isinstance(gap_answers[0], dict)
        and gap_answers[0].get("gap_id") == expected.get("gap_id")
    )


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Task 309 microprobe report must serialize to an object.")
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported Task 309 microprobe JSON value: {type(value).__name__}")
