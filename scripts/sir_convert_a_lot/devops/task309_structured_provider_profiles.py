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

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

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


class Task309ProviderProfileName(StrEnum):
    """Named Task 309 operator profiles with provider-specific defaults."""

    GRANITE_VLLM = "granite-vllm"
    QWEN36_LLAMA_CPP = "qwen36-llama-cpp"


@dataclass(frozen=True)
class Task309ProviderSetting:
    """One serializable provider-profile setting retained in eval evidence."""

    key: str
    value: str | int | float | bool | None


@dataclass(frozen=True)
class Task309ProviderDefaults:
    """Default command values for one Task 309 provider profile."""

    profile_name: Task309ProviderProfileName
    provider_url: str
    port: int
    model: str
    provider_runtime: Task309StructuredProviderRuntime
    output_root: Path
    reports_root: Path
    container_name: str
    cache_paths: tuple[str, ...]
    expected_model_id: str | None
    context_window_tokens: int
    max_output_tokens: int
    temperature: float
    permits_vision_assets: bool = False
    request_settings: tuple[Task309ProviderSetting, ...] = ()
    launch_settings: tuple[Task309ProviderSetting, ...] = ()


DEFAULT_TASK309_PROVIDER_RUNTIME = Task309StructuredProviderRuntime.GRANITE_VLLM
GRANITE_VLLM_PROVIDER_ID = "task309-granite-vllm"
LLAMA_CPP_PROVIDER_ID = "task309-llama-cpp"
GRANITE_TASK309_OUTPUT_ROOT = Path("build/verification/task-309-granite-answer-key-live")
GRANITE_TASK309_REPORTS_ROOT = GRANITE_TASK309_OUTPUT_ROOT / "advisory-corpus-reports"
GRANITE_TASK309_PROVIDER_URL = "http://127.0.0.1:8017"
GRANITE_TASK309_PROVIDER_PORT = 8017
GRANITE_TASK309_MODEL = "ibm-granite/granite-4.1-8b-fp8"
GRANITE_TASK309_CONTEXT_WINDOW_TOKENS = 4096
GRANITE_TASK309_TEMPERATURE = 0.0
TASK309_PROVIDER_MAX_OUTPUT_TOKENS = 512
GRANITE_TASK309_CONTAINER_NAME = "sir-convert-task309-granite-vllm"
GRANITE_TASK309_CACHE_PATHS = (
    "/srv/scratch/sir-convert-a-lot/cache/huggingface",
    "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
)
QWEN36_LLAMA_CPP_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/task-309-qwen36-27b-q6k-hemma-local"
)
QWEN36_LLAMA_CPP_REPORTS_ROOT = QWEN36_LLAMA_CPP_OUTPUT_ROOT / "advisory-corpus-reports"
QWEN36_LLAMA_CPP_PROVIDER_URL = "http://127.0.0.1:8082"
QWEN36_LLAMA_CPP_PROVIDER_PORT = 8082
QWEN36_LLAMA_CPP_MODEL = "qwen3.6-27b-q6k"
QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS = 32768
QWEN36_LLAMA_CPP_TEMPERATURE = 0.15
QWEN36_LLAMA_CPP_CONTAINER_NAME = "task309-qwen36-llama-cpp-local"
QWEN36_LLAMA_CPP_CACHE_PATH = "/srv/scratch/sir-convert-a-lot/cache/llama.cpp"
QWEN36_LLAMA_CPP_SERVER_BINARY = "/srv/scratch/sir-convert-a-lot/bin/llama-server"
QWEN36_LLAMA_CPP_HF_REPO = "unsloth/Qwen3.6-27B-GGUF"
QWEN36_LLAMA_CPP_HF_FILE = "Qwen3.6-27B-Q6_K.gguf"
QWEN36_LLAMA_CPP_REQUIRED_PROCESS_ARGS = (
    "--host",
    "127.0.0.1",
    "--port",
    str(QWEN36_LLAMA_CPP_PROVIDER_PORT),
    "--ctx-size",
    str(QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS),
    "--n-gpu-layers",
    "all",
    "--fit",
    "off",
    "--flash-attn",
    "on",
    "--jinja",
    "--reasoning",
    "off",
    "--temp",
    str(QWEN36_LLAMA_CPP_TEMPERATURE),
    "--offline",
    "--media-path",
    (QWEN36_LLAMA_CPP_OUTPUT_ROOT / "vision-assets").as_posix(),
)

TASK309_PROVIDER_DEFAULTS = {
    Task309ProviderProfileName.GRANITE_VLLM: Task309ProviderDefaults(
        profile_name=Task309ProviderProfileName.GRANITE_VLLM,
        provider_url=GRANITE_TASK309_PROVIDER_URL,
        port=GRANITE_TASK309_PROVIDER_PORT,
        model=GRANITE_TASK309_MODEL,
        provider_runtime=Task309StructuredProviderRuntime.GRANITE_VLLM,
        output_root=GRANITE_TASK309_OUTPUT_ROOT,
        reports_root=GRANITE_TASK309_REPORTS_ROOT,
        container_name=GRANITE_TASK309_CONTAINER_NAME,
        cache_paths=GRANITE_TASK309_CACHE_PATHS,
        expected_model_id=None,
        context_window_tokens=GRANITE_TASK309_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=TASK309_PROVIDER_MAX_OUTPUT_TOKENS,
        temperature=GRANITE_TASK309_TEMPERATURE,
        request_settings=(
            Task309ProviderSetting("stream", False),
            Task309ProviderSetting("temperature", GRANITE_TASK309_TEMPERATURE),
        ),
        launch_settings=(
            Task309ProviderSetting("host_bind", "127.0.0.1"),
            Task309ProviderSetting("port", GRANITE_TASK309_PROVIDER_PORT),
            Task309ProviderSetting("request_logging_disabled", True),
        ),
    ),
    Task309ProviderProfileName.QWEN36_LLAMA_CPP: Task309ProviderDefaults(
        profile_name=Task309ProviderProfileName.QWEN36_LLAMA_CPP,
        provider_url=QWEN36_LLAMA_CPP_PROVIDER_URL,
        port=QWEN36_LLAMA_CPP_PROVIDER_PORT,
        model=QWEN36_LLAMA_CPP_MODEL,
        provider_runtime=Task309StructuredProviderRuntime.LLAMA_CPP_JSON_SCHEMA,
        output_root=QWEN36_LLAMA_CPP_OUTPUT_ROOT,
        reports_root=QWEN36_LLAMA_CPP_REPORTS_ROOT,
        container_name=QWEN36_LLAMA_CPP_CONTAINER_NAME,
        cache_paths=(QWEN36_LLAMA_CPP_CACHE_PATH,),
        expected_model_id=QWEN36_LLAMA_CPP_MODEL,
        context_window_tokens=QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=TASK309_PROVIDER_MAX_OUTPUT_TOKENS,
        temperature=QWEN36_LLAMA_CPP_TEMPERATURE,
        permits_vision_assets=True,
        request_settings=(
            Task309ProviderSetting("stream", False),
            Task309ProviderSetting("temperature", QWEN36_LLAMA_CPP_TEMPERATURE),
        ),
        launch_settings=(
            Task309ProviderSetting("host_bind", "127.0.0.1"),
            Task309ProviderSetting("port", QWEN36_LLAMA_CPP_PROVIDER_PORT),
            Task309ProviderSetting("ctx_size", QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS),
            Task309ProviderSetting("n_gpu_layers", "all"),
            Task309ProviderSetting("fit", "off"),
            Task309ProviderSetting("flash_attn", True),
            Task309ProviderSetting("jinja", True),
            Task309ProviderSetting("reasoning", "off"),
            Task309ProviderSetting("offline", True),
        ),
    ),
}

DEFAULT_TASK309_PROVIDER_DEFAULTS = TASK309_PROVIDER_DEFAULTS[
    Task309ProviderProfileName.GRANITE_VLLM
]
DEFAULT_TASK309_CONTEXT_WINDOW_TOKENS = DEFAULT_TASK309_PROVIDER_DEFAULTS.context_window_tokens
DEFAULT_TASK309_MAX_OUTPUT_TOKENS = DEFAULT_TASK309_PROVIDER_DEFAULTS.max_output_tokens
DEFAULT_TASK309_TEMPERATURE = DEFAULT_TASK309_PROVIDER_DEFAULTS.temperature


def task309_provider_runtime_values() -> tuple[str, ...]:
    """Return CLI-safe runtime values."""

    return tuple(runtime.value for runtime in Task309StructuredProviderRuntime)


def task309_provider_profile_values() -> tuple[str, ...]:
    """Return CLI-safe named provider-profile values."""

    return tuple(profile.value for profile in Task309ProviderProfileName)


def parse_task309_provider_profile_name(value: str) -> Task309ProviderProfileName:
    """Parse a Task 309 named provider profile value."""

    try:
        return Task309ProviderProfileName(value)
    except ValueError as exc:
        values = ", ".join(task309_provider_profile_values())
        message = f"Unsupported Task 309 provider profile {value!r}; expected {values}."
        raise ValueError(message) from exc


def task309_defaults_for_provider_profile(value: str) -> Task309ProviderDefaults:
    """Return default CLI values for a named Task 309 provider profile."""

    profile_name = parse_task309_provider_profile_name(value)
    return TASK309_PROVIDER_DEFAULTS[profile_name]


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
    context_window_tokens: int = DEFAULT_TASK309_CONTEXT_WINDOW_TOKENS,
    max_output_tokens: int = DEFAULT_TASK309_MAX_OUTPUT_TOKENS,
    temperature: float = DEFAULT_TASK309_TEMPERATURE,
    supports_multimodal_vision: bool = False,
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
            temperature=temperature,
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
            temperature=temperature,
            capabilities=StructuredLLMProviderCapabilities(
                supports_json_schema=True,
                supports_gbnf=True,
                supports_vllm_structured_choice=False,
                supports_multimodal_vision=supports_multimodal_vision,
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
        temperature=temperature,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=True,
            supports_vllm_structured_choice=False,
            supports_multimodal_vision=supports_multimodal_vision,
        ),
    )
