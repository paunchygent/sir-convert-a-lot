"""HTTP responses for authorized terminal artifact downloads.

Purpose:
    Convert filesystem or object-backed terminal artifact references into
    Sir Convert-owned HTTP responses after route-level authorization has
    already succeeded.

Relationships:
    - Used by `http_routes_job_artifacts_v2`.
    - Delegates object reads to `ServiceRuntimeV2` instead of exposing storage
      SDK calls in route modules.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Response
from fastapi.responses import FileResponse, StreamingResponse

from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    ObjectStoreMissingError,
    ObjectStoreUnavailableError,
    TerminalArtifactObjectRef,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_engine_v2 import ServiceRuntimeV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def terminal_artifact_response_v2(
    *,
    runtime: ServiceRuntimeV2,
    job: StoredJobV2,
    artifact_key: str,
    filesystem_path: Path,
    content_type: str,
    filename: str,
) -> Response:
    """Return an authorized artifact response from object store or filesystem."""
    ref = job.terminal_artifact_object_refs.get(artifact_key)
    if ref is None:
        return FileResponse(
            path=filesystem_path.as_posix(),
            media_type=content_type,
            filename=filename,
        )
    return _object_streaming_response(
        runtime=runtime,
        ref=ref,
        content_type=content_type,
        filename=filename,
    )


def _object_streaming_response(
    *,
    runtime: ServiceRuntimeV2,
    ref: TerminalArtifactObjectRef,
    content_type: str,
    filename: str,
) -> StreamingResponse:
    try:
        read = runtime.read_terminal_artifact(ref)
    except ObjectStoreMissingError as exc:
        raise ServiceError(
            status_code=404,
            code="artifact_not_available",
            message="Artifact object is not available.",
            retryable=True,
        ) from exc
    except ObjectStoreUnavailableError as exc:
        raise ServiceError(
            status_code=503,
            code="artifact_store_unavailable",
            message="Artifact storage is temporarily unavailable.",
            retryable=True,
        ) from exc
    return StreamingResponse(
        read.iter_bytes(),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
