"""Source-neutral structured LLM provider contracts.

Purpose:
    Define the generic structured-output provider boundary used by answer-key
    completion without coupling provider mechanics to DigiExam parsing,
    renderer inputs, or target exporters.

Relationships:
    - Implements the Task 296 first slice for local-first provider routing,
      prompt budget preflight, and metadata-only capture.
    - Feeds later advisory answer-key completion services that consume
      `ExamAuthoringIR v1` item contracts.
    - Is consumed by infrastructure payload builders and future provider
      adapters for OpenAI-compatible, llama.cpp, and vLLM runtimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain import structured_llm_provider_diagnostics as llm_diag

StructuredLLMProviderSlot = Literal["primary", "fallback"]


class StructuredLLMEndpointKind(StrEnum):
    """Supported structured provider endpoint families."""

    CHAT_COMPLETIONS = "chat_completions"
    RESPONSES = "responses"
    LLAMA_CPP_CHAT_COMPLETIONS = "llama_cpp_chat_completions"
    VLLM_CHAT_COMPLETIONS = "vllm_chat_completions"


class StructuredLLMOutputMode(StrEnum):
    """Provider-specific constrained-output modes."""

    JSON_SCHEMA = "json_schema"
    JSON_OBJECT = "json_object"
    GBNF = "gbnf"
    VLLM_STRUCTURED_CHOICE = "vllm_structured_choice"
    VLLM_JSON_SCHEMA = "vllm_json_schema"


class StructuredLLMReasoningEffort(StrEnum):
    """Provider reasoning-effort settings when supported by the endpoint."""

    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


class StructuredLLMTextVerbosity(StrEnum):
    """Provider text-verbosity settings when supported by the endpoint."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StructuredLLMThinkingMode(StrEnum):
    """Provider thinking-mode toggle when supported by the endpoint."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class StructuredLLMRouteReason(StrEnum):
    """Stable routing reasons for structured-provider selection."""

    PRIMARY_AVAILABLE = "primary_available"
    LOCAL_FALLBACK_AVAILABLE = "local_fallback_available"
    REMOTE_FALLBACK_ALLOWED = "remote_fallback_allowed"
    NO_FALLBACK_CONFIGURED = "no_fallback_configured"
    FALLBACK_UNAVAILABLE = "fallback_unavailable"
    REMOTE_POLICY_FORBIDDEN = "remote_policy_forbidden"
    REMOTE_EXPLICITLY_DENIED = "remote_explicitly_denied"
    REMOTE_CONSENT_MISSING = "remote_consent_missing"


class StructuredLLMPreflightFailureCode(StrEnum):
    """Stable preflight failure codes emitted before provider calls."""

    OVER_BUDGET = "over_budget"


class StructuredLLMBackendFailureCode(StrEnum):
    """Stable provider/backend failure codes for advisory completion reports."""

    PROVIDER_CONFIG_MISSING = "provider_config_missing"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_REQUEST_FAILED = "provider_request_failed"
    PROVIDER_HTTP_ERROR = "provider_http_error"
    PROVIDER_INVALID_JSON = "provider_invalid_json"
    PROVIDER_RESPONSE_NOT_OBJECT = "provider_response_not_object"
    PROVIDER_EMPTY_CONTENT = "provider_empty_content"
    PROVIDER_CONTENT_NOT_JSON = "provider_content_not_json"
    PROVIDER_SCHEMA_MISMATCH = "provider_schema_mismatch"
    PROVIDER_REFUSAL = "provider_refusal"


class StructuredLLMCaptureStatus(StrEnum):
    """Metadata-only capture statuses."""

    SUCCESS = "success"
    FAILED = "failed"
    MANUAL_FOLLOW_UP_REQUIRED = "manual_follow_up_required"


@dataclass(frozen=True)
class StructuredOutputSpec:
    """Operation-supplied schema or grammar for one structured decision."""

    schema_name: str
    schema_version: str
    json_schema: dict[str, JsonValue]
    strict: bool = True
    gbnf_grammar: str | None = None
    choice_values: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.schema_name.strip():
            raise ValueError("Structured output schema_name must be non-empty.")
        if not self.schema_version.strip():
            raise ValueError("Structured output schema_version must be non-empty.")
        if self.json_schema.get("type") != "object":
            raise ValueError("Structured output JSON Schema must describe an object.")
        if self.strict and self.json_schema.get("additionalProperties") is not False:
            raise ValueError(
                "Strict structured output schemas must set additionalProperties=false."
            )
        if any(not choice.strip() for choice in self.choice_values):
            raise ValueError("Structured output choice values must be non-empty.")


@dataclass(frozen=True)
class StructuredLLMProviderCapabilities:
    """Declared constrained-output capabilities for one provider profile."""

    supports_json_schema: bool
    supports_gbnf: bool
    supports_vllm_structured_choice: bool
    supports_json_object: bool = False
    supports_multimodal_vision: bool = False


@dataclass(frozen=True)
class StructuredLLMProviderProfile:
    """Metadata and capability profile for one configured provider."""

    provider_id: str
    model: str
    endpoint_kind: StructuredLLMEndpointKind
    output_mode: StructuredLLMOutputMode
    is_remote: bool
    context_window_tokens: int
    max_output_tokens: int
    capabilities: StructuredLLMProviderCapabilities
    temperature: float = 0.0
    reasoning_effort: StructuredLLMReasoningEffort | None = None
    text_verbosity: StructuredLLMTextVerbosity | None = None
    thinking_mode: StructuredLLMThinkingMode | None = None

    def __post_init__(self) -> None:
        if not self.provider_id.strip():
            raise ValueError("Structured provider_id must be non-empty.")
        if not self.model.strip():
            raise ValueError("Structured provider model must be non-empty.")
        if self.context_window_tokens <= 0:
            raise ValueError("Structured provider context_window_tokens must be positive.")
        if self.max_output_tokens <= 0:
            raise ValueError("Structured provider max_output_tokens must be positive.")
        if self.max_output_tokens >= self.context_window_tokens:
            raise ValueError(
                "Structured provider max_output_tokens must be below context_window_tokens."
            )
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError("Structured provider temperature must be between 0 and 2.")
        if self.output_mode == StructuredLLMOutputMode.JSON_SCHEMA:
            if not self.capabilities.supports_json_schema:
                raise ValueError("Provider profile selects JSON Schema without capability.")
        if self.output_mode == StructuredLLMOutputMode.JSON_OBJECT:
            if not self.capabilities.supports_json_object:
                raise ValueError("Provider profile selects JSON object without capability.")
        if self.output_mode == StructuredLLMOutputMode.VLLM_JSON_SCHEMA:
            if not self.capabilities.supports_json_schema:
                raise ValueError("Provider profile selects vLLM JSON Schema without capability.")
        if self.output_mode == StructuredLLMOutputMode.GBNF:
            if not self.capabilities.supports_gbnf:
                raise ValueError("Provider profile selects GBNF without capability.")
        if self.output_mode == StructuredLLMOutputMode.VLLM_STRUCTURED_CHOICE:
            if not self.capabilities.supports_vllm_structured_choice:
                raise ValueError(
                    "Provider profile selects vLLM structured choice without capability."
                )


@dataclass(frozen=True)
class StructuredChatProviderSet:
    """Primary plus optional fallback provider profiles."""

    primary: StructuredLLMProviderProfile
    fallback: StructuredLLMProviderProfile | None = None


@dataclass(frozen=True)
class StructuredLLMRoutePolicy:
    """Execution policy for local-first provider routing."""

    remote_providers_enabled: bool
    remote_fallback_policy_authorized: bool
    allow_remote_fallback: bool | None


@dataclass(frozen=True)
class StructuredLLMRouteDecision:
    """Selected provider slot or a blocked routing decision."""

    provider_slot: StructuredLLMProviderSlot | None
    provider_id: str | None
    reason: StructuredLLMRouteReason

    @property
    def blocked(self) -> bool:
        """Whether the route cannot call a provider."""

        return self.provider_slot is None


@dataclass(frozen=True)
class StructuredLLMTokenBudget:
    """Resolved prompt/output token budget for one provider call."""

    context_window_tokens: int
    max_output_tokens: int
    safety_margin_tokens: int

    @property
    def available_input_tokens(self) -> int:
        """Prompt token budget remaining after output and safety reserves."""

        return self.context_window_tokens - self.max_output_tokens - self.safety_margin_tokens


@dataclass(frozen=True)
class StructuredLLMPromptPreflightResult:
    """Budget preflight result produced before any provider call."""

    fits: bool
    estimated_input_tokens: int
    available_input_tokens: int
    failure_code: StructuredLLMPreflightFailureCode | None = None


@dataclass(frozen=True)
class StructuredLLMTextContentPart:
    """One text part in a multimodal Chat Completions user message."""

    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("Structured LLM text content part must be non-empty.")


@dataclass(frozen=True)
class StructuredLLMImageURLContentPart:
    """One image URL part in a multimodal Chat Completions user message."""

    url: str

    def __post_init__(self) -> None:
        if not self.url.strip():
            raise ValueError("Structured LLM image URL content part must be non-empty.")


StructuredLLMUserContentPart = StructuredLLMTextContentPart | StructuredLLMImageURLContentPart


@dataclass(frozen=True)
class StructuredLLMRequest:
    """Single-turn item-local structured-output request."""

    job_id: str
    item_id: str
    item_type: str
    prompt_template_version: str
    system_prompt: str
    user_payload: str
    output_spec: StructuredOutputSpec
    estimated_input_tokens: int
    max_output_tokens: int
    allow_remote_fallback: bool | None
    user_content_parts: tuple[StructuredLLMUserContentPart, ...] = ()

    def __post_init__(self) -> None:
        if not self.job_id.strip():
            raise ValueError("Structured LLM job_id must be non-empty.")
        if not self.item_id.strip():
            raise ValueError("Structured LLM item_id must be non-empty.")
        if not self.item_type.strip():
            raise ValueError("Structured LLM item_type must be non-empty.")
        if not self.prompt_template_version.strip():
            raise ValueError("Structured LLM prompt_template_version must be non-empty.")
        if not self.system_prompt.strip():
            raise ValueError("Structured LLM system_prompt must be non-empty.")
        if not self.user_payload.strip():
            raise ValueError("Structured LLM user_payload must be non-empty.")
        if self.estimated_input_tokens < 0:
            raise ValueError("Structured LLM estimated_input_tokens cannot be negative.")
        if self.max_output_tokens <= 0:
            raise ValueError("Structured LLM max_output_tokens must be positive.")
        if self.user_content_parts:
            if not isinstance(self.user_content_parts[0], StructuredLLMTextContentPart):
                raise ValueError("Multimodal user content must start with a text part.")


@dataclass(frozen=True)
class StructuredLLMUsage:
    """Optional bounded usage metadata returned by a provider."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class StructuredLLMResponse:
    """Provider response after JSON parsing and backend validation."""

    content: dict[str, JsonValue]
    finish_reason: str | None
    usage: StructuredLLMUsage = StructuredLLMUsage()


class StructuredLLMProviderError(Exception):
    """Typed provider failure that never stores raw prompts or responses."""

    def __init__(
        self,
        *,
        failure_code: StructuredLLMBackendFailureCode,
        message: str,
        provider_id: str,
        status_code: int | None = None,
        diagnostic: llm_diag.StructuredLLMProviderErrorDiagnostic | None = None,
    ) -> None:
        super().__init__(message)
        self.failure_code = failure_code
        self.provider_id = provider_id
        self.status_code = status_code
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class StructuredLLMCaptureMetadata:
    """Normal production capture record without raw prompt or model content."""

    job_id: str
    item_id: str
    item_type: str
    provider_profile_id: str
    remote_used: bool
    schema_name: str
    schema_version: str
    prompt_template_version: str
    status: StructuredLLMCaptureStatus
    backend_failure_code: str | None = None


class StructuredChatProviderProtocol(Protocol):
    """Protocol for provider adapters that return structured decision objects."""

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse: ...


def decide_structured_llm_route(
    *,
    provider_set: StructuredChatProviderSet,
    policy: StructuredLLMRoutePolicy,
    primary_available: bool,
    fallback_available: bool,
) -> StructuredLLMRouteDecision:
    """Select a provider with local-first and explicit remote-consent semantics."""

    if primary_available:
        return StructuredLLMRouteDecision(
            provider_slot="primary",
            provider_id=provider_set.primary.provider_id,
            reason=StructuredLLMRouteReason.PRIMARY_AVAILABLE,
        )

    if provider_set.fallback is None:
        return StructuredLLMRouteDecision(
            provider_slot=None,
            provider_id=None,
            reason=StructuredLLMRouteReason.NO_FALLBACK_CONFIGURED,
        )
    if not fallback_available:
        return StructuredLLMRouteDecision(
            provider_slot=None,
            provider_id=None,
            reason=StructuredLLMRouteReason.FALLBACK_UNAVAILABLE,
        )
    if not provider_set.fallback.is_remote:
        return StructuredLLMRouteDecision(
            provider_slot="fallback",
            provider_id=provider_set.fallback.provider_id,
            reason=StructuredLLMRouteReason.LOCAL_FALLBACK_AVAILABLE,
        )
    if not policy.remote_providers_enabled or not policy.remote_fallback_policy_authorized:
        return StructuredLLMRouteDecision(
            provider_slot=None,
            provider_id=None,
            reason=StructuredLLMRouteReason.REMOTE_POLICY_FORBIDDEN,
        )
    if policy.allow_remote_fallback is False:
        return StructuredLLMRouteDecision(
            provider_slot=None,
            provider_id=None,
            reason=StructuredLLMRouteReason.REMOTE_EXPLICITLY_DENIED,
        )
    if policy.allow_remote_fallback is None:
        return StructuredLLMRouteDecision(
            provider_slot=None,
            provider_id=None,
            reason=StructuredLLMRouteReason.REMOTE_CONSENT_MISSING,
        )
    return StructuredLLMRouteDecision(
        provider_slot="fallback",
        provider_id=provider_set.fallback.provider_id,
        reason=StructuredLLMRouteReason.REMOTE_FALLBACK_ALLOWED,
    )


def resolve_structured_llm_token_budget(
    *,
    profile: StructuredLLMProviderProfile,
    requested_max_output_tokens: int,
    safety_margin_tokens: int,
) -> StructuredLLMTokenBudget:
    """Resolve provider budget for item-local structured prompts."""

    if requested_max_output_tokens <= 0:
        raise ValueError("requested_max_output_tokens must be positive.")
    if safety_margin_tokens < 0:
        raise ValueError("safety_margin_tokens cannot be negative.")
    if requested_max_output_tokens > profile.max_output_tokens:
        raise ValueError("requested_max_output_tokens exceeds provider max_output_tokens.")
    budget = StructuredLLMTokenBudget(
        context_window_tokens=profile.context_window_tokens,
        max_output_tokens=requested_max_output_tokens,
        safety_margin_tokens=safety_margin_tokens,
    )
    if budget.available_input_tokens <= 0:
        raise ValueError("Resolved structured LLM input budget is empty.")
    return budget


def preflight_structured_llm_prompt(
    *,
    request: StructuredLLMRequest,
    budget: StructuredLLMTokenBudget,
) -> StructuredLLMPromptPreflightResult:
    """Check item-local prompt budget before any provider is called."""

    if request.estimated_input_tokens <= budget.available_input_tokens:
        return StructuredLLMPromptPreflightResult(
            fits=True,
            estimated_input_tokens=request.estimated_input_tokens,
            available_input_tokens=budget.available_input_tokens,
        )
    return StructuredLLMPromptPreflightResult(
        fits=False,
        estimated_input_tokens=request.estimated_input_tokens,
        available_input_tokens=budget.available_input_tokens,
        failure_code=StructuredLLMPreflightFailureCode.OVER_BUDGET,
    )


def build_structured_llm_capture_metadata(
    *,
    request: StructuredLLMRequest,
    profile: StructuredLLMProviderProfile,
    status: StructuredLLMCaptureStatus,
    backend_failure_code: str | None = None,
) -> StructuredLLMCaptureMetadata:
    """Build bounded production metadata while excluding prompt and response text."""

    return StructuredLLMCaptureMetadata(
        job_id=request.job_id,
        item_id=request.item_id,
        item_type=request.item_type,
        provider_profile_id=profile.provider_id,
        remote_used=profile.is_remote,
        schema_name=request.output_spec.schema_name,
        schema_version=request.output_spec.schema_version,
        prompt_template_version=request.prompt_template_version,
        status=status,
        backend_failure_code=backend_failure_code,
    )
