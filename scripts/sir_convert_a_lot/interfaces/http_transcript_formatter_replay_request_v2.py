"""Transcript formatter replay create-job admission helpers.

Purpose:
    Validate the Service API v2 create-job upload boundary for stateless
    formatter replay over saved canonical transcript JSON.

Relationships:
    - Imported by `interfaces.http_create_job_routes_v2` for route registry
      wiring.
    - Leaves canonical JSON schema validation to the replay runtime before any
      formatter artifacts are generated.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.sir_convert_a_lot.domain.service_routes_v2 import RoutePolicyV2
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError

if TYPE_CHECKING:
    from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
        CreateJobCompanionPartsV2,
        PreparedCreateJobRouteV2,
    )


@dataclass(slots=True)
class TranscriptFormatterReplayCreateJobRouteHandlerV2:
    """Create-job preparation for transcript formatter replay routes."""

    policy: RoutePolicyV2

    async def prepare(
        self,
        *,
        spec: JobSpecV2,
        config: ServiceConfig,
        primary_payload_size: int,
        parts: "CreateJobCompanionPartsV2",
    ) -> "PreparedCreateJobRouteV2":
        from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
            PreparedCreateJobRouteV2,
        )

        _reject_replay_companions(parts)
        if primary_payload_size > config.max_upload_bytes:
            raise ServiceError(
                status_code=413,
                code="payload_too_large",
                message="Uploaded transcript JSON exceeds configured size limit.",
                retryable=False,
            )
        if Path(spec.source.filename).suffix.lower() != ".json":
            raise ServiceError(
                status_code=415,
                code="unsupported_media_type",
                message="Transcript formatter replay accepts only .json uploads.",
                retryable=False,
            )
        return PreparedCreateJobRouteV2()


def _reject_replay_companions(parts: "CreateJobCompanionPartsV2") -> None:
    unsupported_parts: list[str] = []
    if parts.resources is not None:
        unsupported_parts.append("resources")
    if parts.reference_docx is not None:
        unsupported_parts.append("reference_docx")
    if parts.graded_result_pdf is not None:
        unsupported_parts.append("graded_result_pdf")
    if parts.parity_pdf is not None:
        unsupported_parts.append("parity_pdf")
    if parts.digiexam_ingestion_overlay is not None:
        unsupported_parts.append("digiexam_ingestion_overlay")
    if unsupported_parts:
        raise ServiceError(
            status_code=422,
            code="transcript_formatter_replay_companion_unsupported",
            message="Transcript formatter replay accepts only the primary JSON upload.",
            retryable=False,
            details={"unsupported_parts": unsupported_parts},
        )
