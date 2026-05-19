"""HTTP app-state and lifecycle helpers for Sir Convert-a-Lot.

Purpose:
    Centralize FastAPI app-state initialization and runtime ownership so route
    modules can stay focused on HTTP contract behavior.

Relationships:
    - Used by `interfaces.http_api` for app factory and lifespan hooks.
    - Used by route modules to access initialized `ServiceRuntime` and metadata.
"""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from prometheus_client import CollectorRegistry, Counter, Histogram

from scripts.sir_convert_a_lot.infrastructure.runtime_engine import (
    ServiceConfig,
    ServiceRuntime,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceRuntimeMetadata
from scripts.sir_convert_a_lot.infrastructure.runtime_telemetry_v2 import RuntimeTelemetrySinkV2

BAKED_EXPECTED_REVISION_PATH = Path("/opt/sir-convert-a-lot/expected_revision")
BAKED_EXPECTED_REVISION_PATH_ENV = "SIR_CONVERT_A_LOT_BAKED_EXPECTED_REVISION_PATH"
BAKED_SERVICE_REVISION_PATH = Path("/opt/sir-convert-a-lot/service_revision")
BAKED_SERVICE_REVISION_PATH_ENV = "SIR_CONVERT_A_LOT_BAKED_SERVICE_REVISION_PATH"


def resolve_repo_head_revision() -> str:
    """Resolve current repository HEAD revision."""
    repo_root = Path(__file__).resolve().parents[3]
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return output if output != "" else "unknown"


def _configured_revision(env_key: str) -> str | None:
    configured_revision = os.getenv(env_key)
    if configured_revision is None:
        return None
    cleaned = configured_revision.strip()
    if cleaned == "" or cleaned == "unknown":
        return None
    return cleaned


def _read_baked_revision(*, default_path: Path, path_env_key: str) -> str | None:
    raw_path = os.getenv(path_env_key)
    path = Path(raw_path) if raw_path is not None and raw_path.strip() != "" else default_path
    try:
        cleaned = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if cleaned == "" or cleaned == "unknown":
        return None
    return cleaned


def resolve_service_revision() -> str:
    """Resolve service revision from override or repository metadata."""
    configured_revision = _configured_revision("SIR_CONVERT_A_LOT_SERVICE_REVISION")
    if configured_revision is not None:
        return configured_revision
    baked_revision = _read_baked_revision(
        default_path=BAKED_SERVICE_REVISION_PATH,
        path_env_key=BAKED_SERVICE_REVISION_PATH_ENV,
    )
    if baked_revision is not None:
        return baked_revision
    return resolve_repo_head_revision()


def resolve_expected_revision(*, default_revision: str) -> str:
    """Resolve expected service revision for readiness verification."""
    configured_revision = _configured_revision("SIR_CONVERT_A_LOT_EXPECTED_REVISION")
    if configured_revision is not None:
        return configured_revision
    baked_revision = _read_baked_revision(
        default_path=BAKED_EXPECTED_REVISION_PATH,
        path_env_key=BAKED_EXPECTED_REVISION_PATH_ENV,
    )
    if baked_revision is not None:
        return baked_revision
    if default_revision.strip() != "":
        return default_revision
    return "unknown"


def resolve_prod_root_from_env() -> Path:
    """Resolve configured production data root."""
    raw = (
        os.getenv("CONVERTER_STORAGE_ROOT")
        or os.getenv("SIR_CONVERT_A_LOT_DATA_DIR")
        or "build/sir_convert_a_lot"
    )
    return Path(raw).resolve()


def initialize_service_state(
    app: FastAPI,
    *,
    runtime_config: ServiceConfig,
    service_profile: str,
    expected_service_profile: str,
    expected_service_revision: str,
    service_revision: str,
    metrics_registry: CollectorRegistry,
    request_counter: Counter,
    request_duration: Histogram,
    runtime_telemetry_v2: RuntimeTelemetrySinkV2,
) -> None:
    """Attach deterministic service state required for runtime initialization."""
    app.state.service_config = runtime_config
    app.state.service_profile = service_profile
    app.state.expected_service_profile = expected_service_profile
    app.state.expected_service_revision = expected_service_revision
    app.state.service_revision = service_revision
    app.state.metrics_registry = metrics_registry
    app.state.request_counter = request_counter
    app.state.request_duration = request_duration
    app.state.runtime_telemetry_v2 = runtime_telemetry_v2
    app.state.startup_lock = threading.Lock()


def ensure_runtime_state(
    app: FastAPI, *, utc_now_iso: str
) -> tuple[ServiceRuntime, ServiceRuntimeMetadata]:
    """Initialize runtime and metadata exactly once per app instance."""
    runtime_obj = getattr(app.state, "runtime", None)
    metadata_obj = getattr(app.state, "service_metadata", None)
    if isinstance(runtime_obj, ServiceRuntime) and isinstance(metadata_obj, ServiceRuntimeMetadata):
        return runtime_obj, metadata_obj

    startup_lock = getattr(app.state, "startup_lock", None)
    if startup_lock is None:
        raise RuntimeError("missing startup lock for service app state initialization")
    with startup_lock:
        runtime_obj = getattr(app.state, "runtime", None)
        metadata_obj = getattr(app.state, "service_metadata", None)
        if isinstance(runtime_obj, ServiceRuntime) and isinstance(
            metadata_obj, ServiceRuntimeMetadata
        ):
            return runtime_obj, metadata_obj

        runtime_config = getattr(app.state, "service_config", None)
        service_profile_obj = getattr(app.state, "service_profile", None)
        service_revision_obj = getattr(app.state, "service_revision", None)
        if not isinstance(runtime_config, ServiceConfig):
            raise RuntimeError("missing service config for runtime initialization")
        if not isinstance(service_profile_obj, str) or service_profile_obj.strip() == "":
            raise RuntimeError("missing service profile for runtime initialization")
        if not isinstance(service_revision_obj, str) or service_revision_obj.strip() == "":
            raise RuntimeError("missing service revision for runtime initialization")

        runtime = ServiceRuntime(runtime_config)
        metadata = ServiceRuntimeMetadata(
            service_profile=service_profile_obj,
            service_revision=service_revision_obj,
            started_at=utc_now_iso,
            data_root=runtime.config.data_root.resolve(),
        )
        app.state.runtime = runtime
        app.state.service_metadata = metadata
        return runtime, metadata


def runtime_for_request(request: Request, *, utc_now_iso: str) -> ServiceRuntime:
    """Return initialized runtime for an incoming request."""
    runtime_obj, _ = ensure_runtime_state(request.app, utc_now_iso=utc_now_iso)
    return runtime_obj


def ensure_runtime_state_v2(app: FastAPI, *, utc_now_iso: str) -> ServiceRuntimeV2:
    """Initialize v2 runtime exactly once per app instance."""
    # Ensure shared metadata + canonical runtime exist first.
    ensure_runtime_state(app, utc_now_iso=utc_now_iso)

    runtime_obj = getattr(app.state, "runtime_v2", None)
    if isinstance(runtime_obj, ServiceRuntimeV2):
        return runtime_obj

    startup_lock = getattr(app.state, "startup_lock", None)
    if startup_lock is None:
        raise RuntimeError("missing startup lock for service app state initialization")
    with startup_lock:
        runtime_obj = getattr(app.state, "runtime_v2", None)
        if isinstance(runtime_obj, ServiceRuntimeV2):
            return runtime_obj

        runtime_config = getattr(app.state, "service_config", None)
        runtime_telemetry_obj = getattr(app.state, "runtime_telemetry_v2", None)
        if not isinstance(runtime_config, ServiceConfig):
            raise RuntimeError("missing service config for runtime initialization")
        if not isinstance(runtime_telemetry_obj, RuntimeTelemetrySinkV2):
            raise RuntimeError("missing v2 runtime telemetry sink for runtime initialization")

        runtime_v2 = ServiceRuntimeV2(runtime_config, telemetry_sink=runtime_telemetry_obj)
        app.state.runtime_v2 = runtime_v2
        return runtime_v2


def runtime_v2_for_request(request: Request, *, utc_now_iso: str) -> ServiceRuntimeV2:
    """Return initialized v2 runtime for an incoming request."""
    return ensure_runtime_state_v2(request.app, utc_now_iso=utc_now_iso)


def metadata_for_app(app: FastAPI, *, utc_now_iso: str) -> ServiceRuntimeMetadata:
    """Return initialized service metadata for health/readiness checks."""
    _, metadata_obj = ensure_runtime_state(app, utc_now_iso=utc_now_iso)
    return metadata_obj


def shutdown_runtime_state(app: FastAPI) -> None:
    """Shutdown runtime resources if runtime was initialized."""
    runtime_obj = getattr(app.state, "runtime", None)
    if isinstance(runtime_obj, ServiceRuntime):
        runtime_obj.shutdown()
    runtime_v2_obj = getattr(app.state, "runtime_v2", None)
    if isinstance(runtime_v2_obj, ServiceRuntimeV2):
        runtime_v2_obj.shutdown()
