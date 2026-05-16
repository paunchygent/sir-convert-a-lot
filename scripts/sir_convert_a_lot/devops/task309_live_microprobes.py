"""Task 309 structured-provider microprobes.

Purpose:
    Execute redacted structured-output microprobes against the selected Task
    309 provider before full-corpus answer-key validation.

Relationships:
    - Uses the generic Task 296 HTTP structured-provider adapter.
    - Proves vLLM choice/schema modes or llama.cpp JSON Schema/GBNF modes.
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
from scripts.sir_convert_a_lot.devops.task309_structured_provider_profiles import (
    DEFAULT_TASK309_PROVIDER_RUNTIME,
    Task309StructuredProviderRuntime,
    build_task309_provider_profile,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_gbnf import (
    choice_answer_key_decision_gbnf,
    gap_fill_answer_key_decision_gbnf,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_CHOICE_ANSWER_KEY_DECISION_SCHEMA_VERSION,
    DIGIEXAM_GAP_FILL_ANSWER_KEY_DECISION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
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
    provider_runtime: str
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
    provider_runtime: Task309StructuredProviderRuntime = DEFAULT_TASK309_PROVIDER_RUNTIME,
    require_provider_ready: bool = True,
    timeout_seconds: float = 30.0,
) -> Task309MicroprobeReport:
    """Run the Task 309 provider microprobes."""

    return asyncio.run(
        _run_task309_microprobes(
            provider_url=provider_url,
            model=model,
            provider_runtime=provider_runtime,
            require_provider_ready=require_provider_ready,
            timeout_seconds=timeout_seconds,
        )
    )


async def _run_task309_microprobes(
    *,
    provider_url: str,
    model: str,
    provider_runtime: Task309StructuredProviderRuntime,
    require_provider_ready: bool,
    timeout_seconds: float,
) -> Task309MicroprobeReport:
    from urllib.parse import urlparse

    parsed = urlparse(provider_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ready = build_task309_provider_status(
        provider_url=provider_url,
        port=port,
        timeout_seconds=min(timeout_seconds, 2.0),
    ).ready
    if require_provider_ready and not ready:
        return Task309MicroprobeReport(
            schema_version=TASK309_MICROPROBE_REPORT_SCHEMA_VERSION,
            provider_url=provider_url,
            model=model,
            provider_runtime=provider_runtime.value,
            provider_ready=False,
            blocked=True,
            results=(),
        )
    profile = build_task309_provider_profile(runtime=provider_runtime, model=model)
    async with httpx.AsyncClient() as client:
        provider = _provider(
            provider_url=provider_url,
            timeout_seconds=timeout_seconds,
            client=client,
            provider_id=profile.provider_id,
        )
        results = [
            await _microprobe(provider, request, profile, expected)
            for request, profile, expected in _microprobe_requests(profile=profile)
        ]
    return Task309MicroprobeReport(
        schema_version=TASK309_MICROPROBE_REPORT_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
        provider_runtime=provider_runtime.value,
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
    provider_id: str,
) -> HttpStructuredChatProvider:
    connection = StructuredLLMProviderConnection(
        provider_id=provider_id,
        base_url=provider_url,
        timeout_seconds=timeout_seconds,
    )
    return HttpStructuredChatProvider(client=client, connections={provider_id: connection})


def _microprobe_requests(
    *,
    profile: StructuredLLMProviderProfile,
) -> tuple[tuple[StructuredLLMRequest, StructuredLLMProviderProfile, dict[str, object]], ...]:
    if profile.endpoint_kind == StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS:
        return _vllm_microprobe_requests(profile)
    return _llama_cpp_microprobe_requests(profile)


def _vllm_microprobe_requests(
    profile: StructuredLLMProviderProfile,
) -> tuple[tuple[StructuredLLMRequest, StructuredLLMProviderProfile, dict[str, object]], ...]:
    return (
        (
            _request("microprobe-choice", _choice_probe_spec(), '{"answer":"B"}'),
            replace(profile, output_mode=StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE),
            {"choice": "B"},
        ),
        (
            _request("microprobe-choice-object", _choice_object_spec(), '{"answer":2}'),
            profile,
            {"decision_state": "answered", "correct_alternative_ids": [2]},
        ),
        (
            _request("microprobe-gap-object", _gap_probe_spec(), '{"gap_id":"gap-1"}'),
            profile,
            {"decision_state": "answered", "gap_id": "gap-1"},
        ),
    )


def _llama_cpp_microprobe_requests(
    profile: StructuredLLMProviderProfile,
) -> tuple[tuple[StructuredLLMRequest, StructuredLLMProviderProfile, dict[str, object]], ...]:
    choice_spec = _choice_object_spec()
    gap_spec = _gap_probe_spec()
    if profile.output_mode == StructuredLLMOutputMode.GBNF:
        choice_spec = replace(choice_spec, gbnf_grammar=choice_answer_key_decision_gbnf())
        gap_spec = replace(gap_spec, gbnf_grammar=gap_fill_answer_key_decision_gbnf())
    return (
        (
            _request("microprobe-choice-object", choice_spec, '{"answer":2}'),
            profile,
            {"decision_state": "answered", "correct_alternative_ids": [2]},
        ),
        (
            _request("microprobe-gap-object", gap_spec, '{"gap_id":"gap-1"}'),
            profile,
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
