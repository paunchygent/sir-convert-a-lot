"""Task 309 structured-provider profile selection.

Purpose:
    Define the live-validation provider profiles that Task 309 can run against
    after Granite/vLLM demotion and while testing llama.cpp structured output.

Relationships:
    - Used by Task 309 microprobes and in-process advisory corpus execution.
    - Keeps provider runtime selection out of DigiExam candidate planning.
    - Restricts llama.cpp validation to JSON Schema or GBNF-constrained JSON
      output rather than free-form JSON prompting.
"""

from __future__ import annotations

from enum import StrEnum

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
)


class Task309StructuredProviderRuntime(StrEnum):
    """Task 309 live-validation provider runtimes."""

    GRANITE_VLLM = "granite-vllm"
    LLAMA_CPP_JSON_SCHEMA = "llama-cpp-json-schema"
    LLAMA_CPP_GBNF = "llama-cpp-gbnf"


DEFAULT_TASK309_PROVIDER_RUNTIME = Task309StructuredProviderRuntime.GRANITE_VLLM
GRANITE_VLLM_PROVIDER_ID = "task309-granite-vllm"
LLAMA_CPP_PROVIDER_ID = "task309-llama-cpp"


def task309_provider_runtime_values() -> tuple[str, ...]:
    """Return CLI-safe runtime values."""

    return tuple(runtime.value for runtime in Task309StructuredProviderRuntime)


def parse_task309_provider_runtime(value: str) -> Task309StructuredProviderRuntime:
    """Parse a Task 309 provider runtime value."""

    try:
        return Task309StructuredProviderRuntime(value)
    except ValueError as exc:
        values = ", ".join(task309_provider_runtime_values())
        message = f"Unsupported Task 309 provider runtime {value!r}; expected {values}."
        raise ValueError(message) from exc


def build_task309_provider_profile(
    *,
    runtime: Task309StructuredProviderRuntime,
    model: str,
    context_window_tokens: int = 4096,
    max_output_tokens: int = 512,
) -> StructuredLLMProviderProfile:
    """Build the structured-provider profile for one Task 309 runtime."""

    if runtime == Task309StructuredProviderRuntime.GRANITE_VLLM:
        return StructuredLLMProviderProfile(
            provider_id=GRANITE_VLLM_PROVIDER_ID,
            model=model,
            endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
            output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
            is_remote=False,
            context_window_tokens=context_window_tokens,
            max_output_tokens=max_output_tokens,
            temperature=0.0,
            capabilities=StructuredLLMProviderCapabilities(
                supports_json_schema=True,
                supports_gbnf=False,
                supports_vllm_structured_choice=True,
            ),
        )
    if runtime == Task309StructuredProviderRuntime.LLAMA_CPP_JSON_SCHEMA:
        return StructuredLLMProviderProfile(
            provider_id=LLAMA_CPP_PROVIDER_ID,
            model=model,
            endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
            output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
            is_remote=False,
            context_window_tokens=context_window_tokens,
            max_output_tokens=max_output_tokens,
            temperature=0.15,
            capabilities=StructuredLLMProviderCapabilities(
                supports_json_schema=True,
                supports_gbnf=True,
                supports_vllm_structured_choice=False,
            ),
        )
    return StructuredLLMProviderProfile(
        provider_id=LLAMA_CPP_PROVIDER_ID,
        model=model,
        endpoint_kind=StructuredLLMEndpointKind.LLAMA_CPP_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.GBNF,
        is_remote=False,
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        temperature=0.15,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
        ),
    )
