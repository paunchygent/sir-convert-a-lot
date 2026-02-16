"""Docling layout model resolution helpers.

Purpose:
    Centralize service-side layout model mapping and fallback candidate
    resolution for Docling conversion runs.

Relationships:
    - Imported by `infrastructure.docling_backend` for converter construction
      and ordering fallback sequencing.
    - Exposes deterministic env-controlled model selection behavior used by
      backend tests and runtime configuration.
"""

from __future__ import annotations

import os

from docling.datamodel.layout_model_specs import (
    DOCLING_LAYOUT_EGRET_LARGE,
    DOCLING_LAYOUT_EGRET_MEDIUM,
    DOCLING_LAYOUT_EGRET_XLARGE,
    DOCLING_LAYOUT_HERON,
    DOCLING_LAYOUT_HERON_101,
    DOCLING_LAYOUT_V2,
    LayoutModelConfig,
)

from scripts.sir_convert_a_lot.infrastructure.conversion_backend import BackendExecutionError

DOCLING_LAYOUT_MODEL_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_LAYOUT_MODEL"
DOCLING_LAYOUT_FALLBACK_MODELS_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_LAYOUT_FALLBACK_MODELS"
DOCLING_ORDERING_PATCH_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_ORDERING_PATCH"
DOCLING_ORDERING_QUALITY_GATE_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_ORDERING_QUALITY_GATE"
DEFAULT_LAYOUT_MODEL_KEY = "docling_layout_egret_large"
LAYOUT_MODEL_BY_KEY: dict[str, LayoutModelConfig] = {
    "docling_layout_v2": DOCLING_LAYOUT_V2,
    "docling_layout_heron": DOCLING_LAYOUT_HERON,
    "docling_layout_heron_101": DOCLING_LAYOUT_HERON_101,
    "docling_layout_egret_medium": DOCLING_LAYOUT_EGRET_MEDIUM,
    "docling_layout_egret_large": DOCLING_LAYOUT_EGRET_LARGE,
    "docling_layout_egret_xlarge": DOCLING_LAYOUT_EGRET_XLARGE,
}
DEFAULT_LAYOUT_FALLBACKS_BY_PRIMARY: dict[str, tuple[str, ...]] = {
    "docling_layout_egret_large": ("docling_layout_heron",),
    "docling_layout_egret_xlarge": ("docling_layout_egret_large", "docling_layout_heron"),
}


def is_env_flag_enabled(*, env_var: str, default: bool) -> bool:
    """Resolve a boolean env setting with deterministic fallback."""
    raw = os.getenv(env_var)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def resolve_layout_model_key() -> str:
    """Resolve configured primary Docling layout model key."""
    raw_value = os.getenv(DOCLING_LAYOUT_MODEL_ENV_VAR)
    requested_key = (
        raw_value.strip().lower()
        if raw_value is not None and raw_value.strip() != ""
        else DEFAULT_LAYOUT_MODEL_KEY
    )
    if requested_key not in LAYOUT_MODEL_BY_KEY:
        supported = ", ".join(sorted(LAYOUT_MODEL_BY_KEY))
        raise BackendExecutionError(
            f"Unsupported Docling layout model '{requested_key}'. Use one of: {supported}."
        )
    return requested_key


def resolve_layout_model_config(*, layout_model_key: str | None = None) -> LayoutModelConfig:
    """Resolve a concrete layout model config by key."""
    resolved_key = resolve_layout_model_key() if layout_model_key is None else layout_model_key
    if resolved_key not in LAYOUT_MODEL_BY_KEY:
        supported = ", ".join(sorted(LAYOUT_MODEL_BY_KEY))
        raise BackendExecutionError(
            f"Unsupported Docling layout model '{resolved_key}'. Use one of: {supported}."
        )
    return LAYOUT_MODEL_BY_KEY[resolved_key].model_copy(deep=True)


def resolve_layout_model_candidate_keys() -> tuple[str, ...]:
    """Resolve deterministic layout-model sequence for source-order fallback."""
    primary_key = resolve_layout_model_key()
    raw_fallback = os.getenv(DOCLING_LAYOUT_FALLBACK_MODELS_ENV_VAR)
    if raw_fallback is None or raw_fallback.strip() == "":
        fallback_keys = DEFAULT_LAYOUT_FALLBACKS_BY_PRIMARY.get(primary_key, ())
    else:
        fallback_keys = tuple(
            item.strip().lower() for item in raw_fallback.split(",") if item.strip() != ""
        )

    ordered: list[str] = [primary_key]
    for key in fallback_keys:
        if key not in LAYOUT_MODEL_BY_KEY:
            supported = ", ".join(sorted(LAYOUT_MODEL_BY_KEY))
            raise BackendExecutionError(
                f"Unsupported Docling fallback layout model '{key}'. Use one of: {supported}."
            )
        if key not in ordered:
            ordered.append(key)
    return tuple(ordered)
