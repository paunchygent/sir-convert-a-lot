"""DigiExam migration create-job request validation for service API v2.

Purpose:
    Keep the route-specific multipart, companion-file, target, and filename
    checks for `digiexam_dxe -> examnet_migration_bundle` out of the generic
    v2 job router.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2` after generic v2 job-spec
      validation.
    - Emits companion upload bytes for `infrastructure.runtime_engine_v2`.
    - Enforces the API/artifact contract owned by DigiExam migration request contract and
      implemented by
      DigiExam migration bundle API.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from scripts.sir_convert_a_lot.domain.specs_v2 import (
    ExamMigrationTargetV2,
    JobSpecV2,
    normalized_exam_migration_targets_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError

_ALLOWED_DIGIEXAM_PART_NAMES = frozenset(
    {"file", "job_spec", "graded_result_pdf", "parity_pdf", "digiexam_ingestion_overlay"}
)
_DIGIEXAM_DXE_MAX_BYTES = 50 * 1024 * 1024
_COMPANION_PDF_MAX_BYTES = 100 * 1024 * 1024
_INGESTION_OVERLAY_MAX_BYTES = 2 * 1024 * 1024
_AGGREGATE_MAX_BYTES = 200 * 1024 * 1024


@dataclass(frozen=True)
class DigiExamMigrationCompanionUploadsV2:
    """Accepted companion upload bytes and digests for one DigiExam job."""

    graded_result_pdf_bytes: bytes | None
    graded_result_pdf_sha256: str | None
    parity_pdf_bytes: bytes | None
    parity_pdf_sha256: str | None
    digiexam_ingestion_overlay_bytes: bytes | None
    digiexam_ingestion_overlay_sha256: str | None


def normalized_digiexam_targets(spec: JobSpecV2) -> tuple[ExamMigrationTargetV2, ...]:
    """Return route targets, defaulting to the governed PDF and QTI artifacts."""

    return normalized_exam_migration_targets_v2(spec)


async def read_digiexam_migration_companions_v2(
    *,
    spec: JobSpecV2,
    config: ServiceConfig,
    primary_payload_size: int,
    form_part_names: set[str],
    resources_uploaded: bool,
    reference_docx_uploaded: bool,
    graded_result_pdf: UploadFile | None,
    parity_pdf: UploadFile | None,
    digiexam_ingestion_overlay: UploadFile | None,
) -> DigiExamMigrationCompanionUploadsV2:
    """Validate and read DigiExam migration companion uploads."""

    _validate_part_names(form_part_names)
    _reject_generic_companions(
        resources_uploaded=resources_uploaded,
        reference_docx_uploaded=reference_docx_uploaded,
    )
    _validate_source_payload_size(config=config, primary_payload_size=primary_payload_size)
    _validate_declared_targets(spec)

    options = spec.digiexam_migration_options
    graded_result_bytes = await _read_optional_pdf(
        upload=graded_result_pdf,
        declared_filename=options.graded_result_pdf_filename if options else None,
        field_name="graded_result_pdf",
        filename_field="digiexam_migration_options.graded_result_pdf_filename",
    )
    parity_bytes = await _read_optional_pdf(
        upload=parity_pdf,
        declared_filename=options.parity_pdf_filename if options else None,
        field_name="parity_pdf",
        filename_field="digiexam_migration_options.parity_pdf_filename",
    )
    overlay_bytes = await _read_optional_ingestion_overlay(
        upload=digiexam_ingestion_overlay,
        declared_filename=options.ingestion_overlay_filename if options else None,
    )
    total_size = (
        primary_payload_size
        + len(graded_result_bytes or b"")
        + len(parity_bytes or b"")
        + len(overlay_bytes or b"")
    )
    if total_size > min(config.max_upload_bytes * 4, _AGGREGATE_MAX_BYTES):
        raise ServiceError(
            status_code=413,
            code="digiexam_payload_too_large",
            message="DigiExam migration multipart payload exceeds the aggregate size limit.",
            retryable=False,
            details={"part": "aggregate", "limit_bytes": _AGGREGATE_MAX_BYTES},
        )
    return DigiExamMigrationCompanionUploadsV2(
        graded_result_pdf_bytes=graded_result_bytes,
        graded_result_pdf_sha256=_sha256(graded_result_bytes),
        parity_pdf_bytes=parity_bytes,
        parity_pdf_sha256=_sha256(parity_bytes),
        digiexam_ingestion_overlay_bytes=overlay_bytes,
        digiexam_ingestion_overlay_sha256=_sha256(overlay_bytes),
    )


def _validate_part_names(form_part_names: set[str]) -> None:
    unsupported = sorted(form_part_names - _ALLOWED_DIGIEXAM_PART_NAMES)
    if unsupported:
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam migration route received unsupported multipart parts.",
            retryable=False,
            details={"unsupported_parts": unsupported},
        )


def _reject_generic_companions(
    *,
    resources_uploaded: bool,
    reference_docx_uploaded: bool,
) -> None:
    if resources_uploaded or reference_docx_uploaded:
        rejected = []
        if resources_uploaded:
            rejected.append("resources")
        if reference_docx_uploaded:
            rejected.append("reference_docx")
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam migration route does not accept generic v2 companion uploads.",
            retryable=False,
            details={"unsupported_parts": rejected},
        )


def _validate_source_payload_size(*, config: ServiceConfig, primary_payload_size: int) -> None:
    limit = min(config.max_upload_bytes, _DIGIEXAM_DXE_MAX_BYTES)
    if primary_payload_size > limit:
        raise ServiceError(
            status_code=413,
            code="digiexam_payload_too_large",
            message="DigiExam `.dxe` upload exceeds the route size limit.",
            retryable=False,
            details={"part": "file", "limit_bytes": limit},
        )


def _validate_declared_targets(spec: JobSpecV2) -> None:
    targets = normalized_digiexam_targets(spec)
    if not targets:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message="DigiExam migration route requires at least one target artifact.",
            retryable=False,
            details={"field": "conversion.targets"},
        )


async def _read_optional_pdf(
    *,
    upload: UploadFile | None,
    declared_filename: str | None,
    field_name: str,
    filename_field: str,
) -> bytes | None:
    if upload is None:
        if declared_filename is not None:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Declared companion filename has no matching multipart upload.",
                retryable=False,
                details={"field": filename_field, "filename": declared_filename},
            )
        return None
    if upload.filename is None or upload.filename.strip() == "":
        raise ServiceError(
            status_code=400,
            code="validation_error",
            message="DigiExam companion upload must include a filename.",
            retryable=False,
            details={"field": f"{field_name}.filename"},
        )
    filename = Path(upload.filename).name
    if declared_filename is not None and filename != declared_filename:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message="DigiExam companion filename must match job spec declaration.",
            retryable=False,
            details={"field": filename_field, "declared": declared_filename, "upload": filename},
        )
    if not filename.lower().endswith(".pdf"):
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam companion uploads must be PDF files.",
            retryable=False,
            details={"field": field_name, "filename": filename},
        )
    payload = await upload.read()
    if len(payload) == 0:
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam companion upload is empty.",
            retryable=False,
            details={"field": field_name},
        )
    if len(payload) > _COMPANION_PDF_MAX_BYTES:
        raise ServiceError(
            status_code=413,
            code="digiexam_payload_too_large",
            message="DigiExam companion PDF exceeds the route size limit.",
            retryable=False,
            details={"part": field_name, "limit_bytes": _COMPANION_PDF_MAX_BYTES},
        )
    if not payload.startswith(b"%PDF"):
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam companion upload is not a readable PDF payload.",
            retryable=False,
            details={"field": field_name},
        )
    return payload


async def _read_optional_ingestion_overlay(
    *,
    upload: UploadFile | None,
    declared_filename: str | None,
) -> bytes | None:
    if upload is None:
        if declared_filename is not None:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message="Declared ingestion overlay filename has no matching multipart upload.",
                retryable=False,
                details={
                    "field": "digiexam_migration_options.ingestion_overlay_filename",
                    "filename": declared_filename,
                },
            )
        return None
    if upload.filename is None or upload.filename.strip() == "":
        raise ServiceError(
            status_code=400,
            code="validation_error",
            message="DigiExam ingestion overlay upload must include a filename.",
            retryable=False,
            details={"field": "digiexam_ingestion_overlay.filename"},
        )
    filename = Path(upload.filename).name
    if declared_filename is None or filename != declared_filename:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message="DigiExam ingestion overlay filename must match job spec declaration.",
            retryable=False,
            details={
                "field": "digiexam_migration_options.ingestion_overlay_filename",
                "declared": declared_filename,
                "upload": filename,
            },
        )
    if not filename.lower().endswith(".json"):
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam ingestion overlay must be a JSON file.",
            retryable=False,
            details={"field": "digiexam_ingestion_overlay", "filename": filename},
        )
    payload = await upload.read()
    if len(payload) == 0:
        raise ServiceError(
            status_code=422,
            code="digiexam_companion_unsupported",
            message="DigiExam ingestion overlay upload is empty.",
            retryable=False,
            details={"field": "digiexam_ingestion_overlay"},
        )
    if len(payload) > _INGESTION_OVERLAY_MAX_BYTES:
        raise ServiceError(
            status_code=413,
            code="digiexam_payload_too_large",
            message="DigiExam ingestion overlay exceeds the route size limit.",
            retryable=False,
            details={
                "part": "digiexam_ingestion_overlay",
                "limit_bytes": _INGESTION_OVERLAY_MAX_BYTES,
            },
        )
    return payload


def _sha256(payload: bytes | None) -> str | None:
    if payload is None:
        return None
    return hashlib.sha256(payload).hexdigest()
