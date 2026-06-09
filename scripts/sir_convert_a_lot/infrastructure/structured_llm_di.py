"""Dishka composition for structured LLM providers.

Purpose:
    Compose the structured LLM provider harness structured-provider harness from service-loaded
    runtime configuration, HTTP client lifecycle, and provider adapter types.

Relationships:
    - Consumes `infrastructure.structured_llm_config.StructuredLLMRuntimeConfig`.
    - Provides `infrastructure.structured_llm_provider.HttpStructuredChatProvider`
      for later advisory answer-key services.
    - Remains opt-in and is not invoked by parser, renderer, or HTTP artifact
      routes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide

from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)


class StructuredLLMProviderComposition(Provider):
    """Dishka provider for structured LLM runtime dependencies."""

    def __init__(
        self,
        *,
        config: StructuredLLMRuntimeConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__()
        self._config = config
        self._client = client

    @provide(scope=Scope.APP)
    def runtime_config(self) -> StructuredLLMRuntimeConfig:
        """Provide service-loaded structured LLM config."""

        return self._config

    @provide(scope=Scope.APP)
    async def http_client(self) -> AsyncIterator[httpx.AsyncClient]:
        """Provide the HTTP client used by structured-provider adapters."""

        if self._client is not None:
            yield self._client
            return
        async with httpx.AsyncClient() as client:
            yield client

    @provide(scope=Scope.APP)
    def provider(
        self,
        client: httpx.AsyncClient,
        config: StructuredLLMRuntimeConfig,
    ) -> HttpStructuredChatProvider:
        """Provide the structured chat adapter with configured connections."""

        return HttpStructuredChatProvider(client=client, connections=config.connections)


def create_structured_llm_async_container(
    *,
    config: StructuredLLMRuntimeConfig,
    client: httpx.AsyncClient | None = None,
) -> AsyncContainer:
    """Create the opt-in Dishka container for structured-provider services."""

    return make_async_container(StructuredLLMProviderComposition(config=config, client=client))
