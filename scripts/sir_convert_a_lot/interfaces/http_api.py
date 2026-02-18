"""Sir Convert-a-Lot HTTP app factory.

Purpose:
    Build the FastAPI application shell (middleware, error handlers, lifespan,
    and routers) for the v1 conversion API.

Relationships:
    - Uses runtime/lifecycle helpers from `interfaces.http_app_state`.
    - Includes routers from `interfaces.http_routes_jobs` and
      `interfaces.http_routes_health`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_client import CollectorRegistry, Counter, Histogram

from scripts.sir_convert_a_lot.application.contracts import (
    ErrorBody,
    ErrorEnvelope,
)
from scripts.sir_convert_a_lot.application.contracts_v2 import ErrorEnvelopeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_engine import (
    ServiceConfig,
    ServiceError,
    service_config_from_env,
)
from scripts.sir_convert_a_lot.interfaces.http_app_state import (
    ensure_runtime_state,
    initialize_service_state,
    resolve_expected_revision,
    resolve_service_revision,
    shutdown_runtime_state,
)
from scripts.sir_convert_a_lot.interfaces.http_routes_health import build_health_router
from scripts.sir_convert_a_lot.interfaces.http_routes_jobs import build_job_router
from scripts.sir_convert_a_lot.interfaces.http_routes_jobs_v2 import build_job_router_v2


def _utc_now_iso() -> str:
    """Return current UTC timestamp as RFC3339 string."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _error_envelope(
    *,
    api_version: str,
    correlation_id: str,
    code: str,
    message: str,
    retryable: bool,
    details: dict[str, object] | None = None,
) -> ErrorEnvelope | ErrorEnvelopeV2:
    error_body = ErrorBody(
        code=code,
        message=message,
        retryable=retryable,
        details=details,
        correlation_id=correlation_id,
    )
    if api_version == "v2":
        return ErrorEnvelopeV2(error=error_body)
    return ErrorEnvelope(error=error_body)


def create_app(
    config: ServiceConfig | None = None,
    *,
    service_profile: str = "prod",
    expected_service_profile: str | None = None,
) -> FastAPI:
    """Create a FastAPI app instance for the Sir Convert-a-Lot v1 API."""
    runtime_config = config or service_config_from_env()
    service_revision = resolve_service_revision()
    expected_service_revision = resolve_expected_revision(default_revision=service_revision)
    service_started_at = _utc_now_iso()

    resolved_expected_profile = expected_service_profile or service_profile
    metrics_registry = CollectorRegistry()
    request_counter = Counter(
        "sir_convert_a_lot_http_requests_total",
        "Total HTTP requests by method, normalized path, and status code.",
        ["method", "path", "status_code"],
        registry=metrics_registry,
    )
    request_duration = Histogram(
        "sir_convert_a_lot_http_request_duration_seconds",
        "HTTP request duration in seconds by method and normalized path.",
        ["method", "path"],
        registry=metrics_registry,
    )

    @asynccontextmanager
    async def _lifespan(lifespan_app: FastAPI):
        ensure_runtime_state(lifespan_app, utc_now_iso=service_started_at)
        try:
            yield
        finally:
            shutdown_runtime_state(lifespan_app)

    app = FastAPI(title="Sir Convert-a-Lot API", version="1.0.0", lifespan=_lifespan)
    initialize_service_state(
        app,
        runtime_config=runtime_config,
        service_profile=service_profile,
        expected_service_profile=resolved_expected_profile,
        expected_service_revision=expected_service_revision,
        service_revision=service_revision,
        metrics_registry=metrics_registry,
        request_counter=request_counter,
        request_duration=request_duration,
    )

    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        started_at = perf_counter()
        incoming = request.headers.get("X-Correlation-ID")
        correlation_id = incoming if incoming else f"corr_{uuid4().hex}"
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        route_obj = request.scope.get("route")
        path_template = request.url.path
        if route_obj is not None:
            route_path = getattr(route_obj, "path", None)
            if isinstance(route_path, str) and route_path.strip() != "":
                path_template = route_path
        duration_seconds = max(0.0, perf_counter() - started_at)
        request_duration.labels(request.method, path_template).observe(duration_seconds)
        request_counter.labels(request.method, path_template, str(response.status_code)).inc()
        return response

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", f"corr_{uuid4().hex}")
        api_version = "v2" if request.url.path.startswith("/v2/") else "v1"
        envelope = _error_envelope(
            api_version=api_version,
            correlation_id=correlation_id,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )
        return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", f"corr_{uuid4().hex}")
        api_version = "v2" if request.url.path.startswith("/v2/") else "v1"
        envelope = _error_envelope(
            api_version=api_version,
            correlation_id=correlation_id,
            code="validation_error",
            message="Request validation failed.",
            retryable=False,
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=envelope.model_dump(mode="json"))

    app.include_router(build_health_router(app=app, service_started_at=service_started_at))
    app.include_router(build_job_router(service_started_at=service_started_at))
    app.include_router(build_job_router_v2(service_started_at=service_started_at))
    return app
