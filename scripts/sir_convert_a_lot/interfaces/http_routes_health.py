"""Health/readiness HTTP routes for Sir Convert-a-Lot.

Purpose:
    Provide liveness (`/healthz`) and fail-closed readiness (`/readyz`)
    surfaces as a dedicated router.

Relationships:
    - Included by `interfaces.http_api` app factory.
    - Uses app-state helpers from `interfaces.http_app_state`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, generate_latest

from scripts.sir_convert_a_lot.application.contracts import (
    ServiceHealthResponse,
    ServiceReadinessReason,
    ServiceReadinessResponse,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    ObjectStoreReadiness,
    TerminalArtifactStore,
)
from scripts.sir_convert_a_lot.interfaces.http_app_state import (
    ensure_runtime_state_v2,
    metadata_for_app,
    resolve_prod_root_from_env,
)


def build_health_router(*, app: FastAPI, service_started_at: str) -> APIRouter:
    """Build health router bound to app-state helpers."""
    router = APIRouter()

    @router.get("/healthz")
    async def healthcheck() -> ServiceHealthResponse:
        metadata = metadata_for_app(app, utc_now_iso=service_started_at)
        return ServiceHealthResponse(
            status="ok",
            service_revision=metadata.service_revision,
            started_at=metadata.started_at,
            data_root=metadata.data_root.as_posix(),
            service_profile=metadata.service_profile,
        )

    @router.get("/readyz")
    async def readycheck() -> JSONResponse:
        metadata = metadata_for_app(app, utc_now_iso=service_started_at)
        expected_revision_obj = getattr(
            app.state, "expected_service_revision", metadata.service_revision
        )
        expected_revision = (
            expected_revision_obj
            if isinstance(expected_revision_obj, str)
            else metadata.service_revision
        )
        expected_profile_obj = getattr(
            app.state, "expected_service_profile", metadata.service_profile
        )
        expected_profile = (
            expected_profile_obj
            if isinstance(expected_profile_obj, str)
            else metadata.service_profile
        )
        prod_root = resolve_prod_root_from_env()
        local_scratch = _local_scratch_readiness(metadata.data_root)
        runtime_v2 = ensure_runtime_state_v2(app, utc_now_iso=service_started_at)
        object_store = _object_store_readiness(
            app=app, api_store=runtime_v2.terminal_artifact_store
        )

        reasons: list[ServiceReadinessReason] = []
        if local_scratch["ready"] is not True:
            reasons.append(
                ServiceReadinessReason(
                    code="local_scratch_unavailable",
                    message="Local scratch data root is not writable.",
                )
            )
        if object_store["config_ready"] is not True or object_store["reachable"] is not True:
            reasons.append(
                ServiceReadinessReason(
                    code="object_store_unavailable",
                    message="Configured object store is not ready.",
                )
            )
        if metadata.service_revision == "unknown":
            reasons.append(
                ServiceReadinessReason(
                    code="unknown_service_revision",
                    message="Service revision is unknown; readiness cannot be guaranteed.",
                )
            )
        if expected_revision == "unknown":
            reasons.append(
                ServiceReadinessReason(
                    code="unknown_expected_revision",
                    message="Expected revision is unknown; readiness cannot be guaranteed.",
                )
            )
        elif metadata.service_revision != expected_revision:
            reasons.append(
                ServiceReadinessReason(
                    code="stale_revision",
                    message="Service revision does not match expected repository revision.",
                    details={
                        "service_revision": metadata.service_revision,
                        "expected_revision": expected_revision,
                    },
                )
            )
        if metadata.service_profile != expected_profile:
            reasons.append(
                ServiceReadinessReason(
                    code="profile_mismatch",
                    message="Service profile does not match configured entrypoint profile.",
                    details={
                        "service_profile": metadata.service_profile,
                        "expected_profile": expected_profile,
                    },
                )
            )
        if metadata.data_root != prod_root:
            reasons.append(
                ServiceReadinessReason(
                    code="data_root_profile_mismatch",
                    message="Service data root does not match configured canonical data root.",
                    details={
                        "service_data_root": metadata.data_root.as_posix(),
                        "expected_data_root": prod_root.as_posix(),
                    },
                )
            )

        is_ready = len(reasons) == 0
        payload = ServiceReadinessResponse(
            status="ready" if is_ready else "not_ready",
            ready=is_ready,
            service_revision=metadata.service_revision,
            expected_revision=expected_revision,
            service_profile=metadata.service_profile,
            expected_service_profile=expected_profile,
            started_at=metadata.started_at,
            data_root=metadata.data_root.as_posix(),
            local_scratch=local_scratch,
            object_store=object_store,
            reasons=reasons,
        )
        status_code = 200 if is_ready else 503
        return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))

    @router.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> PlainTextResponse:
        registry_obj = getattr(app.state, "metrics_registry", None)
        if not isinstance(registry_obj, CollectorRegistry):
            return PlainTextResponse(content="metrics registry unavailable", status_code=500)
        metrics_data = generate_latest(registry_obj)
        return PlainTextResponse(content=metrics_data, media_type=CONTENT_TYPE_LATEST)

    return router


def _local_scratch_readiness(data_root: Path) -> dict[str, object]:
    try:
        data_root.mkdir(parents=True, exist_ok=True)
        probe = data_root / ".readyz-local-scratch"
        probe.write_text("readyz", encoding="utf-8")
        content = probe.read_text(encoding="utf-8")
    except OSError as exc:
        return {"ready": False, "reason": exc.__class__.__name__}
    return {"ready": content == "readyz"}


def _object_store_readiness(
    *,
    app: FastAPI,
    api_store: TerminalArtifactStore,
) -> dict[str, object]:
    api_readiness = api_store.readiness()
    worker_store_obj = getattr(app.state, "worker_terminal_artifact_store", None)
    if not isinstance(worker_store_obj, TerminalArtifactStore):
        if api_readiness.backend == "r2":
            return ObjectStoreReadiness(
                backend=api_readiness.backend,
                config_ready=api_readiness.config_ready,
                reachable=False,
                api_access=api_readiness.api_access,
                worker_access="not_configured",
                secret_sources=api_readiness.secret_sources,
                reason=_join_readiness_reasons(
                    api_readiness.reason,
                    "worker_probe_not_configured",
                ),
            ).to_json()
        return api_readiness.to_json()

    worker_readiness = worker_store_obj.readiness()
    return ObjectStoreReadiness(
        backend=api_readiness.backend,
        config_ready=api_readiness.config_ready and worker_readiness.config_ready,
        reachable=api_readiness.reachable and worker_readiness.reachable,
        api_access=api_readiness.api_access,
        worker_access=worker_readiness.api_access,
        secret_sources={
            **api_readiness.secret_sources,
            **{f"worker:{key}": value for key, value in worker_readiness.secret_sources.items()},
        },
        reason=_join_readiness_reasons(api_readiness.reason, worker_readiness.reason),
    ).to_json()


def _join_readiness_reasons(first: str | None, second: str | None) -> str | None:
    reasons = tuple(reason for reason in (first, second) if reason is not None)
    if not reasons:
        return None
    return "; ".join(reasons)
