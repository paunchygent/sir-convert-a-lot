"""Evaluation-only Sir Convert-a-Lot service entrypoint.

Purpose:
    Provide an isolated runtime profile for scientific-corpus backend A/B
    evaluation without changing production-lock startup semantics.

Relationships:
    - Reuses `interfaces.http_api.create_app` for the canonical v1 API surface.
    - Reuses `infrastructure.runtime_engine.ServiceConfig` with explicit eval
      overrides for CPU-compatible backend experiments.
"""

from __future__ import annotations

import os
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.runtime_engine import ServiceConfig
from scripts.sir_convert_a_lot.interfaces.http_api import app as _default_app
from scripts.sir_convert_a_lot.interfaces.http_api import create_app


def _bool_env(name: str, *, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def eval_service_config_from_env() -> ServiceConfig:
    """Build evaluation-only runtime config from environment variables."""
    api_key = os.getenv("SIR_CONVERT_A_LOT_API_KEY", "dev-only-key")
    gpu_available = _bool_env("SIR_CONVERT_A_LOT_GPU_AVAILABLE", default=True)
    allow_cpu_only = _bool_env("SIR_CONVERT_A_LOT_EVAL_ALLOW_CPU_ONLY", default=True)
    allow_cpu_fallback = _bool_env("SIR_CONVERT_A_LOT_EVAL_ALLOW_CPU_FALLBACK", default=False)
    max_upload_bytes = int(os.getenv("SIR_CONVERT_A_LOT_MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    inline_max_bytes = int(os.getenv("SIR_CONVERT_A_LOT_INLINE_MAX_BYTES", str(2 * 1024 * 1024)))
    data_root_raw = os.getenv("SIR_CONVERT_A_LOT_EVAL_DATA_DIR", "build/sir_convert_a_lot_eval")
    data_root = Path(data_root_raw)
    return ServiceConfig(
        api_key=api_key,
        data_root=data_root,
        max_upload_bytes=max_upload_bytes,
        inline_max_bytes=inline_max_bytes,
        gpu_available=gpu_available,
        allow_cpu_only=allow_cpu_only,
        allow_cpu_fallback=allow_cpu_fallback,
    )


app = create_app(eval_service_config_from_env())

__all__ = ["app", "create_app", "eval_service_config_from_env", "_default_app"]
