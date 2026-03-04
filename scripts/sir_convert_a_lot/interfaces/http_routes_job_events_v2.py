"""SSE lifecycle-event routes for Sir Convert-a-Lot service API v2.

Purpose:
    Provide the v2 `/events/stream` HTTP surface for replay + live lifecycle
    updates using Server-Sent Events.

Relationships:
    - Included by `interfaces.http_api`.
    - Reads runtime state from `interfaces.http_app_state`.
    - Streams events emitted by `infrastructure.job_store_v2_core`.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    JobEventProgressV2,
    JobEventRouteV2,
    JobEventSseMetricsV2,
    JobLifecycleEventV2,
)
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES
from scripts.sir_convert_a_lot.infrastructure.filesystem_journal import utc_now
from scripts.sir_convert_a_lot.infrastructure.job_events_v2 import (
    CursorExpiredErrorV2,
    CursorValidationErrorV2,
    JobLifecycleEventRecordV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request


def _require_api_key(request: Request, *, service_started_at: str) -> None:
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    api_key = request.headers.get("X-API-Key")
    if api_key != runtime.config.api_key:
        raise ServiceError(
            status_code=401,
            code="auth_invalid_api_key",
            message="Missing or invalid X-API-Key.",
            retryable=False,
        )


def _event_payload(
    *,
    record: JobLifecycleEventRecordV2,
    sent_at: datetime,
) -> JobLifecycleEventV2:
    emit_to_send_ms = max(0, int((sent_at - record.occurred_at).total_seconds() * 1000))
    return JobLifecycleEventV2(
        event_id=record.event_id,
        event_type=record.event_type,
        sequence=record.sequence,
        occurred_at=record.occurred_at,
        job_id=record.job_id,
        status=record.status,
        route=JobEventRouteV2(
            source_format=record.source_format,
            target_format=record.target_format,
        ),
        progress=JobEventProgressV2(
            stage=record.stage,
            last_heartbeat_at=record.last_heartbeat_at,
            total_pages=record.total_pages,
            processed_pages=record.processed_pages,
            failed_pages=record.failed_pages,
            percent_complete=record.percent_complete,
            pages_per_minute=record.pages_per_minute,
            eta_seconds=record.eta_seconds,
        ),
        sse_metrics=JobEventSseMetricsV2(sent_at=sent_at, emit_to_send_ms=emit_to_send_ms),
    )


def _sse_frame(payload: JobLifecycleEventV2) -> str:
    body = json.dumps(payload.model_dump(mode="json"), separators=(",", ":"))
    return f"id: {payload.event_id}\nevent: {payload.event_type}\ndata: {body}\n\n"


def build_job_events_router_v2(*, service_started_at: str) -> APIRouter:
    """Build v2 SSE lifecycle-event router with stable app-state wiring."""
    router = APIRouter()

    @router.get("/v2/convert/jobs/{job_id}/events/stream")
    async def stream_job_events(
        job_id: str,
        request: Request,
        cursor: str | None = Query(default=None),
        last_event_id: str | None = Query(default=None),
    ) -> StreamingResponse:
        _require_api_key(request, service_started_at=service_started_at)
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        if not runtime.config.enable_sse_stream:
            raise ServiceError(
                status_code=503,
                code="push_disabled",
                message="SSE streaming is disabled by runtime feature flag.",
                retryable=False,
                details={"surface": "sse_stream"},
            )

        try:
            after_sequence = runtime.resolve_sse_resume_sequence(
                job_id=job_id,
                cursor=cursor,
                last_event_id=last_event_id,
            )
        except CursorExpiredErrorV2 as exc:
            raise ServiceError(
                status_code=410,
                code="cursor_expired",
                message="Replay cursor is outside the retention horizon.",
                retryable=False,
                details={
                    "replay_horizon_hours": exc.replay_horizon_hours,
                    "latest_cursor": exc.latest_cursor,
                },
            ) from exc
        except CursorValidationErrorV2 as exc:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Invalid SSE replay pointer.",
                retryable=False,
                details={"reason": exc.message},
            ) from exc

        async def _event_stream() -> AsyncIterator[str]:
            last_sequence = after_sequence
            started = time.monotonic()
            max_runtime = max(0.1, runtime.config.sse_stream_max_seconds)
            poll_interval = max(0.01, runtime.config.sse_poll_interval_seconds)
            while True:
                events = runtime.get_sse_events(
                    job_id=job_id,
                    after_sequence=last_sequence,
                )
                terminal_seen = False
                for record in events:
                    sent_at = utc_now()
                    payload = _event_payload(record=record, sent_at=sent_at)
                    yield _sse_frame(payload)
                    last_sequence = record.sequence
                    if record.status in TERMINAL_JOB_STATUSES:
                        terminal_seen = True
                if terminal_seen:
                    return
                if time.monotonic() - started >= max_runtime:
                    return
                await asyncio.sleep(poll_interval)

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(
            _event_stream(),
            media_type="text/event-stream",
            headers=headers,
        )

    return router
