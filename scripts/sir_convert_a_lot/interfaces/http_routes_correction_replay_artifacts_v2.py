"""Nested correction replay artifact HTTP route for Service API v2.

Purpose:
    Serve request-scoped correction replay artifacts only when the caller
    presents the artifact-set id, artifact key, and content hash advertised by
    the correction apply response.

Relationships:
    - Registered by `interfaces.http_routes_job_artifacts_v2`.
    - Resolves immutable artifact sets through
      `infrastructure.correction_replay_artifact_writer`.
    - Reuses the v2 job access helpers and runtime lookup used by named
      artifact routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2
from scripts.sir_convert_a_lot.infrastructure.correction_replay_artifact_writer import (
    resolve_exam_authoring_correction_replay_artifact,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import (
    auth_context_for_job_access_v2,
    require_job_access_v2,
)


def register_correction_replay_artifact_routes_v2(
    *,
    router: APIRouter,
    service_started_at: str,
) -> None:
    """Register nested correction replay artifact routes."""

    @router.get(
        "/v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}",
    )
    async def get_correction_replay_artifact(
        job_id: str,
        artifact_set_id: str,
        artifact_key: str,
        content_sha256: str,
        request: Request,
    ) -> FileResponse:
        runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
        job = runtime.get_job(job_id)
        auth_context = auth_context_for_job_access_v2(
            request,
            service_started_at=service_started_at,
            job=job,
            required_grant="sir-convert:artifacts:read-own",
        )
        job = require_job_access_v2(
            auth_context=auth_context,
            job=job,
            required_grant="sir-convert:artifacts:read-own",
            access_denied_code="artifact_access_denied",
        )
        if job.output_format != OutputFormatV2.EXAMNET_MIGRATION_BUNDLE:
            raise ServiceError(
                status_code=409,
                code="correction_replay_artifacts_not_supported",
                message="Correction replay artifacts are only supported for Exam Converter jobs.",
                retryable=False,
                details={"output_format": job.output_format.value},
            )
        if job.status not in TERMINAL_JOB_STATUSES:
            raise ServiceError(
                status_code=409,
                code="correction_replay_artifact_set_not_available",
                message="Correction replay artifacts are only available for terminal jobs.",
                retryable=True,
                details={"status": job.status.value},
            )
        if job.status != JobStatus.SUCCEEDED:
            raise ServiceError(
                status_code=409,
                code="job_not_succeeded",
                message="Job is terminal but has no successful conversion result.",
                retryable=False,
                details={"status": job.status.value},
            )
        resolved = resolve_exam_authoring_correction_replay_artifact(
            job=job,
            artifact_set_id=artifact_set_id,
            artifact_key=artifact_key,
            content_sha256=content_sha256,
        )
        return FileResponse(
            path=resolved.path.as_posix(),
            media_type=resolved.content_type,
            filename=resolved.filename,
        )
