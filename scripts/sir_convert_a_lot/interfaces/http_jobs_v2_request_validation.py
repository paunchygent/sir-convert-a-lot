"""Request validation helpers for v2 create-job HTTP endpoint.

Purpose:
    Keep v2 create-job route validations focused and deterministic, including
    route-option guards and DOCX template selector checks.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2`.
    - Uses template resolver from `infrastructure.docx_template_catalog_v2`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.docx_template_catalog_v2 import (
    DocxTemplateCatalogLoadError,
    DocxTemplateNotFoundError,
    DocxTemplateUnavailableError,
    DocxTemplateVersionNotFoundError,
    load_default_docx_template_catalog,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError


def validate_create_job_route_constraints(
    *,
    spec: JobSpecV2,
    resources_uploaded: bool,
    reference_docx_uploaded: bool,
) -> None:
    """Validate route-level upload constraints and template selectors for create-job."""

    if reference_docx_uploaded and spec.conversion.output_format != OutputFormatV2.DOCX:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message=(
                "reference_docx upload is only supported for v2 routes with output_format='docx'."
            ),
            retryable=False,
            details={
                "field": "reference_docx",
                "output_format": spec.conversion.output_format.value,
            },
        )

    if spec.conversion.output_format == OutputFormatV2.MD:
        if resources_uploaded and spec.source.format != SourceFormatV2.HTML:
            raise ServiceError(
                status_code=422,
                code="validation_error",
                message=(
                    "resources upload is only supported for v2 html -> md routes with "
                    "output_format='md'."
                ),
                retryable=False,
                details={"field": "resources", "output_format": "md"},
            )

    template_selector = spec.conversion.template
    if template_selector is None:
        return

    try:
        catalog = load_default_docx_template_catalog()
    except DocxTemplateCatalogLoadError as exc:
        raise ServiceError(
            status_code=500,
            code="template_catalog_invalid",
            message=exc.message,
            retryable=False,
        ) from exc

    try:
        catalog.resolve(
            template_id=template_selector.template_id,
            version=template_selector.version,
        )
    except DocxTemplateNotFoundError as exc:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message="Unknown DOCX template id.",
            retryable=False,
            details={
                "field": "conversion.template.template_id",
                "template_id": exc.template_id,
            },
        ) from exc
    except DocxTemplateVersionNotFoundError as exc:
        raise ServiceError(
            status_code=422,
            code="validation_error",
            message="Unknown DOCX template version.",
            retryable=False,
            details={
                "field": "conversion.template.version",
                "template_id": exc.template_id,
                "version": exc.version,
            },
        ) from exc
    except DocxTemplateUnavailableError as exc:
        raise ServiceError(
            status_code=409,
            code="template_unavailable",
            message="Requested DOCX template is currently unavailable.",
            retryable=False,
            details={
                "template_id": exc.template_id,
                "version": exc.version,
                "status": exc.status.value,
            },
        ) from exc
