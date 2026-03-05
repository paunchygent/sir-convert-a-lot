"""Runtime configuration and fingerprint helpers.

Purpose:
    Keep environment-based runtime configuration resolution and request
    fingerprint logic separate from runtime orchestration concerns.

Relationships:
    - Imported by `infrastructure.runtime_engine`.
    - Produces `ServiceConfig` and idempotency fingerprint inputs used by HTTP API.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig

CPU_UNLOCK_ENV_VARS: tuple[str, str] = (
    "SIR_CONVERT_A_LOT_ALLOW_CPU_ONLY",
    "SIR_CONVERT_A_LOT_ALLOW_CPU_FALLBACK",
)

_BOOL_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_BOOL_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _parse_bool_env(*, name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _BOOL_TRUE_VALUES:
        return True
    if normalized in _BOOL_FALSE_VALUES:
        return False
    raise ValueError(
        f"Invalid boolean value for {name}: {raw!r}. Use one of: 1/0, true/false, yes/no, on/off."
    )


def _parse_bounded_int_env(
    *,
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid integer value for {name}: {raw!r}.") from exc
    if value < minimum or value > maximum:
        raise ValueError(
            f"Invalid value for {name}: {value}. Expected range [{minimum}, {maximum}]."
        )
    return value


def fingerprint_for_request(spec_payload: dict[str, object], file_sha256: str) -> str:
    """Create deterministic idempotency fingerprint for a create-job request."""
    normalized = json.dumps(spec_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{normalized}:{file_sha256}".encode("utf-8")).hexdigest()


def service_config_from_env() -> ServiceConfig:
    """Load runtime configuration from environment variables."""
    api_key = os.getenv("SIR_CONVERT_A_LOT_API_KEY", "dev-only-key")
    data_root = Path(
        os.getenv("CONVERTER_STORAGE_ROOT")
        or os.getenv("SIR_CONVERT_A_LOT_DATA_DIR")
        or "build/sir_convert_a_lot"
    )
    gpu_available = os.getenv("SIR_CONVERT_A_LOT_GPU_AVAILABLE", "1") == "1"
    max_workers = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_MAX_WORKERS",
        default=1,
        minimum=1,
        maximum=64,
    )
    enable_parallel_pdf_chunks = _parse_bool_env(
        name="SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS",
        default=False,
    )
    max_chunk_workers = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS",
        default=1,
        minimum=1,
        maximum=32,
    )
    pdf_chunk_size_pages = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES",
        default=10,
        minimum=1,
        maximum=500,
    )
    gpu_stage_max_concurrency = _parse_bounded_int_env(
        name="SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY",
        default=max_workers,
        minimum=1,
        maximum=64,
    )
    enable_sse_stream = os.getenv("SIR_CONVERT_A_LOT_ENABLE_SSE_STREAM", "0") == "1"
    sse_replay_horizon_seconds = int(
        os.getenv("SIR_CONVERT_A_LOT_SSE_REPLAY_HORIZON_SECONDS", str(24 * 3600))
    )
    sse_poll_interval_seconds = float(
        os.getenv("SIR_CONVERT_A_LOT_SSE_POLL_INTERVAL_SECONDS", "0.05")
    )
    sse_stream_max_seconds = float(os.getenv("SIR_CONVERT_A_LOT_SSE_STREAM_MAX_SECONDS", "15.0"))
    enable_webhook_onboarding = os.getenv("SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_ONBOARDING", "0") == "1"
    webhook_secret_overlap_seconds = int(
        os.getenv("SIR_CONVERT_A_LOT_WEBHOOK_SECRET_OVERLAP_SECONDS", str(24 * 3600))
    )
    enable_webhook_delivery = os.getenv("SIR_CONVERT_A_LOT_ENABLE_WEBHOOK_DELIVERY", "0") == "1"

    enabled_unlock_envs = [name for name in CPU_UNLOCK_ENV_VARS if os.getenv(name) == "1"]
    if enabled_unlock_envs:
        joined_names = ", ".join(enabled_unlock_envs)
        raise ValueError(
            "CPU unlock env vars are disabled during GPU-first rollout lock: "
            f"{joined_names}. Use explicit ServiceConfig test overrides instead."
        )

    return ServiceConfig(
        api_key=api_key,
        data_root=data_root,
        max_workers=max_workers,
        enable_parallel_pdf_chunks=enable_parallel_pdf_chunks,
        max_chunk_workers=max_chunk_workers,
        pdf_chunk_size_pages=pdf_chunk_size_pages,
        gpu_stage_max_concurrency=gpu_stage_max_concurrency,
        gpu_available=gpu_available,
        enable_sse_stream=enable_sse_stream,
        sse_replay_horizon_seconds=sse_replay_horizon_seconds,
        sse_poll_interval_seconds=sse_poll_interval_seconds,
        sse_stream_max_seconds=sse_stream_max_seconds,
        enable_webhook_onboarding=enable_webhook_onboarding,
        webhook_secret_overlap_seconds=webhook_secret_overlap_seconds,
        enable_webhook_delivery=enable_webhook_delivery,
    )
