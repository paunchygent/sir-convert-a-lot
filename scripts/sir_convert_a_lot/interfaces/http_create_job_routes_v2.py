"""Create-job route registry for Sir Convert-a-Lot service API v2.

Purpose:
    Keep route-specific create-job policy, companion upload handling, and
    target validation behind a typed registry keyed by v2 source/output format.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2` for `POST /v2/convert/jobs`.
    - Uses route metadata from `domain.service_routes_v2` as the route
      authority.
    - Delegates DigiExam migration companion checks to
      `interfaces.http_digiexam_migration_request_v2`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    DAY_ONE_MEDIA_CONTAINERS,
    DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    MAX_AUDIO_UPLOAD_BYTES,
    AudioTranscriptionCapacitySnapshot,
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
    DIGIEXAM_MIGRATION_ROUTE_KEY_V2,
    RouteKeyV2,
    RoutePolicyV2,
    route_key_for_spec_v2,
    route_policy_for_key_v2,
    supported_route_keys_v2,
)
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.interfaces.http_digiexam_migration_request_v2 import (
    read_digiexam_migration_companions_v2,
)
from scripts.sir_convert_a_lot.interfaces.http_jobs_v2_request_validation import (
    validate_create_job_route_constraints,
)


@dataclass(frozen=True)
class CreateJobCompanionPartsV2:
    """UploadFile handles for optional multipart parts on create-job requests."""

    resources: UploadFile | None
    reference_docx: UploadFile | None
    graded_result_pdf: UploadFile | None
    parity_pdf: UploadFile | None
    digiexam_ingestion_overlay: UploadFile | None
    form_part_names: frozenset[str]


@dataclass(frozen=True)
class PreparedCreateJobRouteV2:
    """Route-prepared companion bytes and digests for v2 job creation."""

    resources_zip_bytes: bytes | None = None
    resources_sha256: str | None = None
    reference_docx_bytes: bytes | None = None
    reference_docx_sha256: str | None = None
    graded_result_pdf_bytes: bytes | None = None
    graded_result_pdf_sha256: str | None = None
    parity_pdf_bytes: bytes | None = None
    parity_pdf_sha256: str | None = None
    digiexam_ingestion_overlay_bytes: bytes | None = None
    digiexam_ingestion_overlay_sha256: str | None = None


DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2: tuple[RouteKeyV2, ...] = (
    RouteKeyV2(source_format=SourceFormatV2.PDF, output_format=OutputFormatV2.MD),
    RouteKeyV2(source_format=SourceFormatV2.DOCX, output_format=OutputFormatV2.MD),
    RouteKeyV2(source_format=SourceFormatV2.HTML, output_format=OutputFormatV2.MD),
    RouteKeyV2(source_format=SourceFormatV2.DOCX, output_format=OutputFormatV2.PDF),
    RouteKeyV2(source_format=SourceFormatV2.MD, output_format=OutputFormatV2.PDF),
    RouteKeyV2(source_format=SourceFormatV2.MD, output_format=OutputFormatV2.DOCX),
    RouteKeyV2(source_format=SourceFormatV2.HTML, output_format=OutputFormatV2.PDF),
    RouteKeyV2(source_format=SourceFormatV2.HTML, output_format=OutputFormatV2.DOCX),
    RouteKeyV2(source_format=SourceFormatV2.PDF, output_format=OutputFormatV2.DOCX),
)

_AUDIO_SOURCE_SUFFIXES_V2 = frozenset(
    {
        ".aac",
        ".aiff",
        ".flac",
        ".m4a",
        ".mkv",
        ".mov",
        ".mp3",
        ".mp4",
        ".ogg",
        ".opus",
        ".wav",
        ".webm",
    }
)


class CreateJobRouteHandlerV2(Protocol):
    """Handler contract for route-specific create-job preparation."""

    policy: RoutePolicyV2

    async def prepare(
        self,
        *,
        spec: JobSpecV2,
        config: ServiceConfig,
        primary_payload_size: int,
        parts: CreateJobCompanionPartsV2,
    ) -> PreparedCreateJobRouteV2:
        """Validate and read route-specific companion parts."""


class AudioCapacityJobSubjectV2(Protocol):
    """Stored job fields needed for audio route-capacity checks."""

    source_format: SourceFormatV2
    output_format: OutputFormatV2
    status: JobStatus


class AudioCapacityJobStoreV2(Protocol):
    """Job-store operations needed for audio route-capacity checks."""

    def list_job_ids(self) -> list[str]:
        """Return all visible v2 job ids."""


class AudioCapacityRuntimeV2(Protocol):
    """Runtime operations needed for audio route-capacity checks."""

    @property
    def job_store(self) -> AudioCapacityJobStoreV2:
        """Return the v2 job store backing the runtime."""
        ...

    def get_job(self, job_id: str) -> AudioCapacityJobSubjectV2 | None:
        """Return a visible job or `None` when the id is not available."""


class DefaultCreateJobRouteHandlerV2:
    """Create-job preparation for generic document conversion routes."""

    def __init__(self, *, policy: RoutePolicyV2) -> None:
        self.policy = policy

    async def prepare(
        self,
        *,
        spec: JobSpecV2,
        config: ServiceConfig,
        primary_payload_size: int,
        parts: CreateJobCompanionPartsV2,
    ) -> PreparedCreateJobRouteV2:
        del primary_payload_size
        _reject_digiexam_companions_for_default_route(parts)
        resources_bytes = await _read_optional_resources(
            upload=parts.resources,
            config=config,
        )
        reference_docx_bytes = await _read_optional_reference_docx(
            upload=parts.reference_docx,
            config=config,
        )
        validate_create_job_route_constraints(
            spec=spec,
            resources_uploaded=resources_bytes is not None,
            reference_docx_uploaded=reference_docx_bytes is not None,
        )
        return PreparedCreateJobRouteV2(
            resources_zip_bytes=resources_bytes,
            resources_sha256=_sha256(resources_bytes),
            reference_docx_bytes=reference_docx_bytes,
            reference_docx_sha256=_sha256(reference_docx_bytes),
        )


class DigiExamMigrationCreateJobRouteHandlerV2:
    """Create-job preparation for DigiExam migration bundle routes."""

    def __init__(self, *, policy: RoutePolicyV2) -> None:
        self.policy = policy

    async def prepare(
        self,
        *,
        spec: JobSpecV2,
        config: ServiceConfig,
        primary_payload_size: int,
        parts: CreateJobCompanionPartsV2,
    ) -> PreparedCreateJobRouteV2:
        companions = await read_digiexam_migration_companions_v2(
            spec=spec,
            config=config,
            primary_payload_size=primary_payload_size,
            form_part_names=set(parts.form_part_names),
            resources_uploaded=parts.resources is not None,
            reference_docx_uploaded=parts.reference_docx is not None,
            graded_result_pdf=parts.graded_result_pdf,
            parity_pdf=parts.parity_pdf,
            digiexam_ingestion_overlay=parts.digiexam_ingestion_overlay,
        )
        return PreparedCreateJobRouteV2(
            graded_result_pdf_bytes=companions.graded_result_pdf_bytes,
            graded_result_pdf_sha256=companions.graded_result_pdf_sha256,
            parity_pdf_bytes=companions.parity_pdf_bytes,
            parity_pdf_sha256=companions.parity_pdf_sha256,
            digiexam_ingestion_overlay_bytes=companions.digiexam_ingestion_overlay_bytes,
            digiexam_ingestion_overlay_sha256=companions.digiexam_ingestion_overlay_sha256,
        )


class AudioTranscriptionAdmissionCreateJobRouteHandlerV2:
    """Admission-only create-job preparation for audio transcript bundle routes."""

    def __init__(self, *, policy: RoutePolicyV2) -> None:
        self.policy = policy

    async def prepare(
        self,
        *,
        spec: JobSpecV2,
        config: ServiceConfig,
        primary_payload_size: int,
        parts: CreateJobCompanionPartsV2,
    ) -> PreparedCreateJobRouteV2:
        del config
        _reject_audio_companions_for_audio_route(parts)
        if primary_payload_size > MAX_AUDIO_UPLOAD_BYTES:
            raise ServiceError(
                status_code=413,
                code=AudioTranscriptionErrorCode.UPLOAD_SIZE_EXCEEDED.value,
                message="Uploaded audio media exceeds the audio route size limit.",
                retryable=False,
                details={"limit_bytes": MAX_AUDIO_UPLOAD_BYTES},
            )
        container = Path(spec.source.filename).suffix.lower().lstrip(".")
        if container not in DAY_ONE_MEDIA_CONTAINERS:
            raise ServiceError(
                status_code=415,
                code=AudioTranscriptionErrorCode.CONTAINER_UNSUPPORTED.value,
                message="Uploaded media container is not supported by the audio route.",
                retryable=False,
                details={"container": container},
            )
        return PreparedCreateJobRouteV2()


class ServiceRouteRegistryV2:
    """Fail-closed create-job route handler registry for service API v2."""

    def __init__(self, handlers: tuple[CreateJobRouteHandlerV2, ...]) -> None:
        self._handlers = {handler.policy.key: handler for handler in handlers}

    def require_handler(self, key: RouteKeyV2) -> CreateJobRouteHandlerV2:
        """Return the handler for a supported route or raise a typed service error."""

        handler = self._handlers.get(key)
        if handler is None:
            raise ServiceError(
                status_code=422,
                code="unsupported_v2_route",
                message=(
                    f"Unsupported v2 route: {key.source_format.value} -> {key.output_format.value}"
                ),
                retryable=False,
                details={
                    "source_format": key.source_format.value,
                    "output_format": key.output_format.value,
                },
            )
        return handler

    def require_handler_for_spec(self, spec: JobSpecV2) -> CreateJobRouteHandlerV2:
        """Return the handler for a validated v2 job spec."""

        return self.require_handler(route_key_for_spec_v2(spec))

    def registered_route_keys(self) -> tuple[RouteKeyV2, ...]:
        """Return registered route keys in stable policy order."""

        return tuple(key for key in supported_route_keys_v2() if key in self._handlers)


def build_create_job_route_registry_v2() -> ServiceRouteRegistryV2:
    """Build the default create-job registry for current production routes."""

    handlers: list[CreateJobRouteHandlerV2] = []
    for key in DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2:
        handlers.append(DefaultCreateJobRouteHandlerV2(policy=_required_route_policy_v2(key)))
    handlers.append(
        DigiExamMigrationCreateJobRouteHandlerV2(
            policy=_required_route_policy_v2(DIGIEXAM_MIGRATION_ROUTE_KEY_V2)
        )
    )
    handlers.append(
        AudioTranscriptionAdmissionCreateJobRouteHandlerV2(
            policy=_required_route_policy_v2(AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2)
        )
    )
    return ServiceRouteRegistryV2(tuple(handlers))


def infer_source_format_from_filename_v2(filename: str) -> SourceFormatV2 | None:
    """Infer the broad v2 source format from an uploaded filename."""

    suffix = Path(filename).suffix.lower()
    if suffix in _AUDIO_SOURCE_SUFFIXES_V2:
        return SourceFormatV2.AUDIO
    if suffix == ".pdf":
        return SourceFormatV2.PDF
    if suffix in {".md", ".markdown"}:
        return SourceFormatV2.MD
    if suffix in {".html", ".htm"}:
        return SourceFormatV2.HTML
    if suffix == ".docx":
        return SourceFormatV2.DOCX
    if suffix == ".dxe":
        return SourceFormatV2.DIGIEXAM_DXE
    return None


def enforce_audio_transcription_route_capacity_v2(
    *,
    spec: JobSpecV2,
    runtime: AudioCapacityRuntimeV2,
) -> None:
    """Reject new audio transcript work when route-level admission caps are full."""

    if not _is_audio_transcript_bundle_spec_v2(spec):
        return
    snapshot = AudioTranscriptionCapacitySnapshot(
        active_stt_jobs=_active_audio_transcript_job_count_v2(runtime),
        active_probe_normalization_workers=0,
        active_sidecar_transcription_requests=0,
        gpu_slots_in_use=0,
    )
    exhausted_cap = snapshot.exhausted_by(DEFAULT_AUDIO_TRANSCRIPTION_CAPS)
    if exhausted_cap is None:
        return
    raise ServiceError(
        status_code=429,
        code=DEFAULT_AUDIO_TRANSCRIPTION_CAPS.capacity_error_code.value,
        message="Audio transcription route capacity is exhausted.",
        retryable=True,
        details={"exhausted_cap": exhausted_cap},
    )


def _required_route_policy_v2(key: RouteKeyV2) -> RoutePolicyV2:
    policy = route_policy_for_key_v2(key)
    if policy is None:
        raise RuntimeError(
            "create-job route handler registered without route-policy metadata: "
            f"{key.source_format.value} -> {key.output_format.value}"
        )
    return policy


def _active_audio_transcript_job_count_v2(runtime: AudioCapacityRuntimeV2) -> int:
    active_count = 0
    for job_id in runtime.job_store.list_job_ids():
        try:
            job = runtime.get_job(job_id)
        except ServiceError as exc:
            if exc.status_code == 404:
                continue
            raise
        if job is not None and _is_active_audio_transcript_job_v2(job):
            active_count += 1
    return active_count


def _is_active_audio_transcript_job_v2(job: AudioCapacityJobSubjectV2) -> bool:
    return (
        job.source_format == SourceFormatV2.AUDIO
        and job.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE
        and job.status in {JobStatus.QUEUED, JobStatus.RUNNING}
    )


def _is_audio_transcript_bundle_spec_v2(spec: JobSpecV2) -> bool:
    return (
        spec.source.format == SourceFormatV2.AUDIO
        and spec.conversion.output_format == OutputFormatV2.TRANSCRIPT_BUNDLE
    )


def _reject_digiexam_companions_for_default_route(parts: CreateJobCompanionPartsV2) -> None:
    unsupported_parts = []
    if parts.graded_result_pdf is not None:
        unsupported_parts.append("graded_result_pdf")
    if parts.parity_pdf is not None:
        unsupported_parts.append("parity_pdf")
    if parts.digiexam_ingestion_overlay is not None:
        unsupported_parts.append("digiexam_ingestion_overlay")
    if unsupported_parts:
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam companion uploads are only accepted by the migration bundle route.",
            retryable=False,
            details={"unsupported_parts": unsupported_parts},
        )


def _reject_audio_companions_for_audio_route(parts: CreateJobCompanionPartsV2) -> None:
    unsupported_parts = []
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
            code=AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED.value,
            message="Audio transcript jobs accept only the primary uploaded media file.",
            retryable=False,
            details={"unsupported_parts": unsupported_parts},
        )


async def _read_optional_resources(
    *,
    upload: UploadFile | None,
    config: ServiceConfig,
) -> bytes | None:
    if upload is None:
        return None
    payload = await upload.read()
    if len(payload) > config.max_upload_bytes:
        raise ServiceError(
            status_code=413,
            code="payload_too_large",
            message="Uploaded resources zip exceeds configured size limit.",
            retryable=False,
        )
    return payload


async def _read_optional_reference_docx(
    *,
    upload: UploadFile | None,
    config: ServiceConfig,
) -> bytes | None:
    if upload is None:
        return None
    if upload.filename is None or upload.filename.strip() == "":
        raise ServiceError(
            status_code=400,
            code="validation_error",
            message="Uploaded reference_docx must include a filename.",
            retryable=False,
            details={"field": "reference_docx.filename"},
        )
    if not Path(upload.filename).name.lower().endswith(".docx"):
        raise ServiceError(
            status_code=415,
            code="unsupported_media_type",
            message="reference_docx must be a .docx file.",
            retryable=False,
        )
    payload = await upload.read()
    if len(payload) > config.max_upload_bytes:
        raise ServiceError(
            status_code=413,
            code="payload_too_large",
            message="Uploaded reference_docx exceeds configured size limit.",
            retryable=False,
        )
    return payload


def _sha256(payload: bytes | None) -> str | None:
    if payload is None:
        return None
    return hashlib.sha256(payload).hexdigest()
