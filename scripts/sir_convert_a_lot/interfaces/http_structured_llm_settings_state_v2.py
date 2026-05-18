"""HTTP app-state access for structured LLM hot settings.

Purpose:
    Provide one FastAPI app-state helper for the running structured-provider
    routing store so operator mutation routes and conversion-job admission share
    the same hot settings instance.

Relationships:
    - Uses `interfaces.http_app_state.runtime_v2_for_request` to reach the
      running service config.
    - Uses `infrastructure.structured_llm_hot_settings_runtime` for store
      creation from immutable provider catalog configuration.
"""

from __future__ import annotations

from fastapi import Request

from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMHotSettingsStore,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_hot_settings_runtime import (
    structured_llm_hot_settings_store_from_config,
)
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request


def structured_llm_hot_settings_store_for_request(
    request: Request,
    *,
    service_started_at: str,
) -> StructuredLLMHotSettingsStore:
    """Return the shared hot-settings store for this FastAPI app."""

    store = getattr(request.app.state, "structured_llm_hot_settings_store", None)
    if isinstance(store, StructuredLLMHotSettingsStore):
        return store
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    startup_lock = getattr(request.app.state, "startup_lock", None)
    if startup_lock is None:
        raise RuntimeError("missing startup lock for structured LLM hot settings")
    with startup_lock:
        store = getattr(request.app.state, "structured_llm_hot_settings_store", None)
        if isinstance(store, StructuredLLMHotSettingsStore):
            return store
        created = structured_llm_hot_settings_store_from_config(runtime.config)
        request.app.state.structured_llm_hot_settings_store = created
        return created
