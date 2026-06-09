"""Answer-key local structured-provider profile selection.

Purpose:
    Define reusable local structured-provider profiles for advisory answer-key
    completion, including the current Qwen3.6 llama.cpp vision profile.

Relationships:
    - Used by production advisory completion configuration and governed eval
      tooling that exercises the same local model settings.
    - Keeps provider runtime selection out of DigiExam candidate planning and
      asset export.
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


class AnswerKeyStructuredProviderRuntime(StrEnum):
    """Structured-provider runtimes supported for answer-key completion."""

    GRANITE_VLLM = "granite-vllm"
    LLAMA_CPP_JSON_SCHEMA = "llama-cpp-json-schema"
    LLAMA_CPP_GBNF = "llama-cpp-gbnf"


class AnswerKeyProviderProfileName(StrEnum):
    """Named answer-key local model profiles with provider-specific defaults."""

    GRANITE_VLLM = "granite-vllm"
    QWEN36_LLAMA_CPP = "qwen36-llama-cpp"
    QWEN36_LLAMA_CPP_MTP = "qwen36-llama-cpp-mtp"


@dataclass(frozen=True)
class AnswerKeyProviderSetting:
    """One serializable provider-profile setting retained in run evidence."""

    key: str
    value: str | int | float | bool | None


@dataclass(frozen=True)
class AnswerKeyProviderDefaults:
    """Default command values for one answer-key provider profile."""

    profile_name: AnswerKeyProviderProfileName
    provider_url: str
    port: int
    model: str
    provider_runtime: AnswerKeyStructuredProviderRuntime
    output_root: Path
    reports_root: Path
    container_name: str
    cache_paths: tuple[str, ...]
    expected_model_id: str | None
    context_window_tokens: int
    max_output_tokens: int
    temperature: float
    permits_vision_assets: bool = False
    request_settings: tuple[AnswerKeyProviderSetting, ...] = ()
    launch_settings: tuple[AnswerKeyProviderSetting, ...] = ()


DEFAULT_ANSWER_KEY_PROVIDER_RUNTIME = AnswerKeyStructuredProviderRuntime.GRANITE_VLLM
GRANITE_VLLM_PROVIDER_ID = "answer-key-live-validation-granite-vllm"
LLAMA_CPP_PROVIDER_ID = "answer-key-live-validation-llama-cpp"
GRANITE_ANSWER_KEY_EVAL_OUTPUT_ROOT = Path("build/verification/digiexam-granite-answer-key-live")
GRANITE_ANSWER_KEY_EVAL_REPORTS_ROOT = (
    GRANITE_ANSWER_KEY_EVAL_OUTPUT_ROOT / "advisory-corpus-reports"
)
GRANITE_ANSWER_KEY_PROVIDER_URL = "http://127.0.0.1:8017"
GRANITE_ANSWER_KEY_PROVIDER_PORT = 8017
GRANITE_ANSWER_KEY_MODEL = "ibm-granite/granite-4.1-8b-fp8"
GRANITE_ANSWER_KEY_CONTEXT_WINDOW_TOKENS = 4096
GRANITE_ANSWER_KEY_TEMPERATURE = 0.0
GRANITE_ANSWER_KEY_MAX_OUTPUT_TOKENS = 512
GRANITE_ANSWER_KEY_CONTAINER_NAME = "sir-convert-answer-key-live-validation-granite-vllm"
GRANITE_ANSWER_KEY_CACHE_PATHS = (
    "/srv/scratch/sir-convert-a-lot/cache/huggingface",
    "/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface",
)
QWEN36_LLAMA_CPP_EVAL_OUTPUT_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/verification/digiexam-qwen36-27b-q6k-answer-key-local"
)
QWEN36_LLAMA_CPP_EVAL_REPORTS_ROOT = QWEN36_LLAMA_CPP_EVAL_OUTPUT_ROOT / "advisory-corpus-reports"
QWEN36_LLAMA_CPP_PROVIDER_URL = "http://127.0.0.1:8082"
QWEN36_LLAMA_CPP_PROVIDER_PORT = 8082
QWEN36_LLAMA_CPP_MODEL = "qwen3.6-27b-q6k"
QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS = 16384
QWEN36_LLAMA_CPP_MAX_OUTPUT_TOKENS = 4096
QWEN36_LLAMA_CPP_TEMPERATURE = 0.15
QWEN36_LLAMA_CPP_CONTAINER_NAME = "answer-key-live-validation-qwen36-llama-cpp-local"
QWEN36_LLAMA_CPP_CACHE_PATH = "/srv/scratch/sir-convert-a-lot/cache/llama.cpp"
QWEN36_LLAMA_CPP_SERVER_BINARY = "/srv/scratch/sir-convert-a-lot/bin/llama-server"
QWEN36_LLAMA_CPP_HF_REPO = "unsloth/Qwen3.6-27B-GGUF:default"
QWEN36_LLAMA_CPP_HF_FILE = "Qwen3.6-27B-Q6_K.gguf"
QWEN36_LLAMA_CPP_MTP_MODEL = "qwen3.6-27b-q6k-mtp"
QWEN36_LLAMA_CPP_MTP_HF_REPO = "unsloth/Qwen3.6-27B-MTP-GGUF"
QWEN36_LLAMA_CPP_MTP_HF_FILE = "Qwen3.6-27B-Q6_K.gguf"
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
    (QWEN36_LLAMA_CPP_EVAL_OUTPUT_ROOT / "vision-assets").as_posix(),
)
QWEN36_LLAMA_CPP_MTP_REQUIRED_PROCESS_ARGS = (
    *QWEN36_LLAMA_CPP_REQUIRED_PROCESS_ARGS,
    "--spec-type",
    "draft-mtp",
    "--spec-draft-n-max",
    "2",
)

ANSWER_KEY_PROVIDER_DEFAULTS = {
    AnswerKeyProviderProfileName.GRANITE_VLLM: AnswerKeyProviderDefaults(
        profile_name=AnswerKeyProviderProfileName.GRANITE_VLLM,
        provider_url=GRANITE_ANSWER_KEY_PROVIDER_URL,
        port=GRANITE_ANSWER_KEY_PROVIDER_PORT,
        model=GRANITE_ANSWER_KEY_MODEL,
        provider_runtime=AnswerKeyStructuredProviderRuntime.GRANITE_VLLM,
        output_root=GRANITE_ANSWER_KEY_EVAL_OUTPUT_ROOT,
        reports_root=GRANITE_ANSWER_KEY_EVAL_REPORTS_ROOT,
        container_name=GRANITE_ANSWER_KEY_CONTAINER_NAME,
        cache_paths=GRANITE_ANSWER_KEY_CACHE_PATHS,
        expected_model_id=None,
        context_window_tokens=GRANITE_ANSWER_KEY_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=GRANITE_ANSWER_KEY_MAX_OUTPUT_TOKENS,
        temperature=GRANITE_ANSWER_KEY_TEMPERATURE,
        request_settings=(
            AnswerKeyProviderSetting("stream", False),
            AnswerKeyProviderSetting("temperature", GRANITE_ANSWER_KEY_TEMPERATURE),
        ),
        launch_settings=(
            AnswerKeyProviderSetting("host_bind", "127.0.0.1"),
            AnswerKeyProviderSetting("port", GRANITE_ANSWER_KEY_PROVIDER_PORT),
            AnswerKeyProviderSetting("request_logging_disabled", True),
        ),
    ),
    AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP: AnswerKeyProviderDefaults(
        profile_name=AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP,
        provider_url=QWEN36_LLAMA_CPP_PROVIDER_URL,
        port=QWEN36_LLAMA_CPP_PROVIDER_PORT,
        model=QWEN36_LLAMA_CPP_MODEL,
        provider_runtime=AnswerKeyStructuredProviderRuntime.LLAMA_CPP_JSON_SCHEMA,
        output_root=QWEN36_LLAMA_CPP_EVAL_OUTPUT_ROOT,
        reports_root=QWEN36_LLAMA_CPP_EVAL_REPORTS_ROOT,
        container_name=QWEN36_LLAMA_CPP_CONTAINER_NAME,
        cache_paths=(QWEN36_LLAMA_CPP_CACHE_PATH,),
        expected_model_id=QWEN36_LLAMA_CPP_MODEL,
        context_window_tokens=QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=QWEN36_LLAMA_CPP_MAX_OUTPUT_TOKENS,
        temperature=QWEN36_LLAMA_CPP_TEMPERATURE,
        permits_vision_assets=True,
        request_settings=(
            AnswerKeyProviderSetting("stream", False),
            AnswerKeyProviderSetting("temperature", QWEN36_LLAMA_CPP_TEMPERATURE),
        ),
        launch_settings=(
            AnswerKeyProviderSetting("host_bind", "127.0.0.1"),
            AnswerKeyProviderSetting("port", QWEN36_LLAMA_CPP_PROVIDER_PORT),
            AnswerKeyProviderSetting("ctx_size", QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS),
            AnswerKeyProviderSetting("n_gpu_layers", "all"),
            AnswerKeyProviderSetting("fit", "off"),
            AnswerKeyProviderSetting("flash_attn", True),
            AnswerKeyProviderSetting("jinja", True),
            AnswerKeyProviderSetting("reasoning", "off"),
            AnswerKeyProviderSetting("offline", True),
        ),
    ),
    AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP: AnswerKeyProviderDefaults(
        profile_name=AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP,
        provider_url=QWEN36_LLAMA_CPP_PROVIDER_URL,
        port=QWEN36_LLAMA_CPP_PROVIDER_PORT,
        model=QWEN36_LLAMA_CPP_MTP_MODEL,
        provider_runtime=AnswerKeyStructuredProviderRuntime.LLAMA_CPP_JSON_SCHEMA,
        output_root=QWEN36_LLAMA_CPP_EVAL_OUTPUT_ROOT,
        reports_root=QWEN36_LLAMA_CPP_EVAL_REPORTS_ROOT,
        container_name=QWEN36_LLAMA_CPP_CONTAINER_NAME,
        cache_paths=(QWEN36_LLAMA_CPP_CACHE_PATH,),
        expected_model_id=QWEN36_LLAMA_CPP_MTP_MODEL,
        context_window_tokens=QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS,
        max_output_tokens=QWEN36_LLAMA_CPP_MAX_OUTPUT_TOKENS,
        temperature=QWEN36_LLAMA_CPP_TEMPERATURE,
        permits_vision_assets=True,
        request_settings=(
            AnswerKeyProviderSetting("stream", False),
            AnswerKeyProviderSetting("temperature", QWEN36_LLAMA_CPP_TEMPERATURE),
        ),
        launch_settings=(
            AnswerKeyProviderSetting("host_bind", "127.0.0.1"),
            AnswerKeyProviderSetting("port", QWEN36_LLAMA_CPP_PROVIDER_PORT),
            AnswerKeyProviderSetting("ctx_size", QWEN36_LLAMA_CPP_CONTEXT_WINDOW_TOKENS),
            AnswerKeyProviderSetting("n_gpu_layers", "all"),
            AnswerKeyProviderSetting("fit", "off"),
            AnswerKeyProviderSetting("flash_attn", True),
            AnswerKeyProviderSetting("jinja", True),
            AnswerKeyProviderSetting("reasoning", "off"),
            AnswerKeyProviderSetting("offline", True),
            AnswerKeyProviderSetting("spec_type", "draft-mtp"),
            AnswerKeyProviderSetting("spec_draft_n_max", 2),
        ),
    ),
}

DEFAULT_ANSWER_KEY_PROVIDER_DEFAULTS = ANSWER_KEY_PROVIDER_DEFAULTS[
    AnswerKeyProviderProfileName.GRANITE_VLLM
]
DEFAULT_ANSWER_KEY_CONTEXT_WINDOW_TOKENS = (
    DEFAULT_ANSWER_KEY_PROVIDER_DEFAULTS.context_window_tokens
)
DEFAULT_ANSWER_KEY_MAX_OUTPUT_TOKENS = DEFAULT_ANSWER_KEY_PROVIDER_DEFAULTS.max_output_tokens
DEFAULT_ANSWER_KEY_TEMPERATURE = DEFAULT_ANSWER_KEY_PROVIDER_DEFAULTS.temperature


def answer_key_provider_runtime_values() -> tuple[str, ...]:
    """Return CLI-safe runtime values."""

    return tuple(runtime.value for runtime in AnswerKeyStructuredProviderRuntime)


def answer_key_provider_profile_values() -> tuple[str, ...]:
    """Return CLI-safe named provider-profile values."""

    return tuple(profile.value for profile in AnswerKeyProviderProfileName)


def parse_answer_key_provider_profile_name(value: str) -> AnswerKeyProviderProfileName:
    """Parse a named answer-key provider profile value."""

    try:
        return AnswerKeyProviderProfileName(value)
    except ValueError as exc:
        values = ", ".join(answer_key_provider_profile_values())
        message = f"Unsupported answer-key provider profile {value!r}; expected {values}."
        raise ValueError(message) from exc


def answer_key_defaults_for_provider_profile(value: str) -> AnswerKeyProviderDefaults:
    """Return default CLI values for a named answer-key provider profile."""

    profile_name = parse_answer_key_provider_profile_name(value)
    return ANSWER_KEY_PROVIDER_DEFAULTS[profile_name]


def parse_answer_key_provider_runtime(value: str) -> AnswerKeyStructuredProviderRuntime:
    """Parse an answer-key provider runtime value."""

    try:
        return AnswerKeyStructuredProviderRuntime(value)
    except ValueError as exc:
        values = ", ".join(answer_key_provider_runtime_values())
        message = f"Unsupported answer-key provider runtime {value!r}; expected {values}."
        raise ValueError(message) from exc


def build_answer_key_provider_profile(
    *,
    runtime: AnswerKeyStructuredProviderRuntime,
    model: str,
    context_window_tokens: int = DEFAULT_ANSWER_KEY_CONTEXT_WINDOW_TOKENS,
    max_output_tokens: int = DEFAULT_ANSWER_KEY_MAX_OUTPUT_TOKENS,
    temperature: float = DEFAULT_ANSWER_KEY_TEMPERATURE,
    supports_multimodal_vision: bool = False,
) -> StructuredLLMProviderProfile:
    """Build the structured-provider profile for one answer-key runtime."""

    if runtime == AnswerKeyStructuredProviderRuntime.GRANITE_VLLM:
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
    if runtime == AnswerKeyStructuredProviderRuntime.LLAMA_CPP_JSON_SCHEMA:
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
