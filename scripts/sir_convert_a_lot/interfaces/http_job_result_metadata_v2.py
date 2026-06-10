"""Result metadata mapping for service API v2 job artifacts.

Purpose:
    Build public v2 conversion metadata from stored runtime jobs, including
    route-specific bundle metadata and safe formula-authority decisions.

Relationships:
    - Used by `interfaces.http_routes_job_artifacts_v2`.
    - Consumes `infrastructure.runtime_models_v2.StoredJobV2`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    ConversionMetadataV2,
    DigiExamMigrationConversionMetadataV2,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_artifacts import (
    load_digiexam_migration_result_metadata,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


def conversion_metadata_for_job_v2(
    job: StoredJobV2,
) -> ConversionMetadataV2 | DigiExamMigrationConversionMetadataV2:
    """Build public conversion metadata for one succeeded v2 job."""
    if job.output_format == OutputFormatV2.EXAMNET_MIGRATION_BUNDLE:
        bundle_metadata = load_digiexam_migration_result_metadata(job=job)
        return DigiExamMigrationConversionMetadataV2(
            pipeline_used=_required_pipeline_used(job),
            backend_used=job.backend_used,
            acceleration_used=job.acceleration_used,
            ocr_enabled=job.ocr_enabled,
            ocr_engine_used=job.ocr_engine_used,
            ocr_languages_used=job.ocr_languages_used,
            acceleration_policy_requested=job.acceleration_policy_requested,
            gpu_runtime_kind=job.gpu_runtime_kind,
            gpu_device_count=job.gpu_device_count,
            gpu_busy_percent=job.gpu_busy_percent,
            gpu_memory_used_percent=job.gpu_memory_used_percent,
            options_fingerprint=_required_options_fingerprint(job),
            template_id=job.template_id,
            template_version=job.template_version,
            template_artifact_sha256=job.template_artifact_sha256,
            parallel_enabled=job.parallel_enabled,
            max_chunk_workers=job.max_chunk_workers,
            chunk_size_pages=job.chunk_size_pages,
            effective_gpu_stage_limit=job.effective_gpu_stage_limit,
            scheduling_mode=job.scheduling_mode,
            formula_authority=dict(job.formula_authority),
            route_key="digiexam_dxe_to_examnet_migration_bundle",
            bundle_schema_version=DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION,
            bundle_status=bundle_metadata.bundle_status,
            source_sha256=bundle_metadata.source_sha256,
            target_readiness_report_artifact_key=(
                bundle_metadata.target_readiness_report_artifact_key
            ),
            manual_follow_up_required=bundle_metadata.manual_follow_up_required,
            warning_count=bundle_metadata.warning_count,
            artifact_count=bundle_metadata.artifact_count,
        )
    return ConversionMetadataV2(
        pipeline_used=_required_pipeline_used(job),
        backend_used=job.backend_used,
        acceleration_used=job.acceleration_used,
        ocr_enabled=job.ocr_enabled,
        ocr_engine_used=job.ocr_engine_used,
        ocr_languages_used=job.ocr_languages_used,
        acceleration_policy_requested=job.acceleration_policy_requested,
        gpu_runtime_kind=job.gpu_runtime_kind,
        gpu_device_count=job.gpu_device_count,
        gpu_busy_percent=job.gpu_busy_percent,
        gpu_memory_used_percent=job.gpu_memory_used_percent,
        options_fingerprint=_required_options_fingerprint(job),
        template_id=job.template_id,
        template_version=job.template_version,
        template_artifact_sha256=job.template_artifact_sha256,
        parallel_enabled=job.parallel_enabled,
        max_chunk_workers=job.max_chunk_workers,
        chunk_size_pages=job.chunk_size_pages,
        effective_gpu_stage_limit=job.effective_gpu_stage_limit,
        scheduling_mode=job.scheduling_mode,
        formula_authority=dict(job.formula_authority),
    )


def _required_pipeline_used(job: StoredJobV2) -> str:
    if job.pipeline_used is None:
        raise ServiceError(
            status_code=500,
            code="result_missing_metadata",
            message="Successful job is missing conversion metadata.",
            retryable=False,
        )
    return job.pipeline_used


def _required_options_fingerprint(job: StoredJobV2) -> str:
    if job.options_fingerprint is None:
        raise ServiceError(
            status_code=500,
            code="result_missing_metadata",
            message="Successful job is missing conversion metadata.",
            retryable=False,
        )
    return job.options_fingerprint
