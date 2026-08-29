"""Lease-aware decorator for structured answer-key provider attempts."""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderProtocol,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_token_lease import (
    FilesystemAnswerKeyTokenLeaseLedger,
)


class LeasedStructuredChatProvider:
    """Reserve one non-refundable lease around every delegated provider attempt."""

    def __init__(
        self,
        *,
        provider: StructuredChatProviderProtocol,
        lease_ledger: FilesystemAnswerKeyTokenLeaseLedger,
    ) -> None:
        self._provider = provider
        self._lease_ledger = lease_ledger

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        """Delegate after send-state persistence and reconcile usable success usage."""

        lease = self._lease_ledger.reserve(
            estimated_input_tokens=request.estimated_input_tokens,
            max_output_tokens=request.max_output_tokens,
        )
        self._lease_ledger.mark_sent(lease=lease)
        response = await self._provider.complete_structured_chat(
            request=request,
            profile=profile,
        )
        actual_tokens = _usable_usage_tokens(response.usage)
        if actual_tokens is not None:
            self._lease_ledger.reconcile(lease=lease, actual_tokens=actual_tokens)
        return response


def _usable_usage_tokens(usage: StructuredLLMUsage) -> int | None:
    if usage.total_tokens is not None and usage.total_tokens >= 0:
        return usage.total_tokens
    if (
        usage.prompt_tokens is not None
        and usage.completion_tokens is not None
        and usage.prompt_tokens >= 0
        and usage.completion_tokens >= 0
    ):
        return usage.prompt_tokens + usage.completion_tokens
    return None
