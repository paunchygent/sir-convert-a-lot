"""DOCX template discovery HTTP routes for service API v2.

Purpose:
    Provide read-only template catalog endpoints used by downstream GUI domains
    to discover selectable DOCX templates and version metadata.

Relationships:
    - Included by `interfaces.http_api` as part of the v2 API surface.
    - Uses template catalog loading from
      `infrastructure.docx_template_catalog_v2`.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from scripts.sir_convert_a_lot.application.contracts_v2 import (
    DocxTemplateDetailResponseV2,
    DocxTemplateListResponseV2,
    DocxTemplateSummaryV2,
    DocxTemplateVersionDataV2,
    DocxTemplateVersionResponseV2,
)
from scripts.sir_convert_a_lot.infrastructure.docx_template_catalog_v2 import (
    DocxTemplateCatalogLoadError,
    DocxTemplateCatalogV2,
    DocxTemplateNotFoundError,
    DocxTemplateVersionNotFoundError,
    ResolvedDocxTemplateV2,
    load_default_docx_template_catalog,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import require_api_key_v2


def _as_version_data(resolved: ResolvedDocxTemplateV2) -> DocxTemplateVersionDataV2:
    metadata = resolved.metadata
    return DocxTemplateVersionDataV2(
        template_id=metadata.template_id,
        version=metadata.version,
        name=metadata.name,
        description=metadata.description,
        domain_tags=list(metadata.domain_tags),
        language_tags=list(metadata.language_tags),
        status=metadata.status.value,
        artifact_sha256=metadata.artifact_sha256,
        artifact_size_bytes=metadata.artifact_size_bytes,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at,
    )


def _load_catalog_or_raise() -> DocxTemplateCatalogV2:
    try:
        return load_default_docx_template_catalog()
    except DocxTemplateCatalogLoadError as exc:
        raise ServiceError(
            status_code=500,
            code="template_catalog_invalid",
            message=exc.message,
            retryable=False,
        ) from exc


def build_templates_router_v2(*, service_started_at: str) -> APIRouter:
    """Build v2 template discovery router with stable app-state wiring."""

    router = APIRouter()

    @router.get("/v2/templates/docx")
    async def list_docx_templates(request: Request) -> JSONResponse:
        require_api_key_v2(request, service_started_at=service_started_at)
        catalog = _load_catalog_or_raise()
        summaries = [
            DocxTemplateSummaryV2(
                template_id=summary.template_id,
                name=summary.name,
                description=summary.description,
                domain_tags=list(summary.domain_tags),
                latest_active_version=summary.latest_active_version,
                versions=list(summary.versions),
                statuses=[status.value for status in summary.statuses],
            )
            for summary in catalog.list_template_summaries()
        ]
        payload = DocxTemplateListResponseV2(templates=summaries)
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.get("/v2/templates/docx/{template_id}")
    async def get_docx_template(template_id: str, request: Request) -> JSONResponse:
        require_api_key_v2(request, service_started_at=service_started_at)
        catalog = _load_catalog_or_raise()
        try:
            versions = catalog.list_versions(template_id=template_id)
        except DocxTemplateNotFoundError as exc:
            raise ServiceError(
                status_code=404,
                code="template_not_found",
                message="DOCX template was not found.",
                retryable=False,
                details={"template_id": exc.template_id},
            ) from exc

        payload = DocxTemplateDetailResponseV2(
            template_id=template_id,
            versions=[_as_version_data(item) for item in versions],
        )
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    @router.get("/v2/templates/docx/{template_id}/versions/{version}")
    async def get_docx_template_version(
        template_id: str,
        version: str,
        request: Request,
    ) -> JSONResponse:
        require_api_key_v2(request, service_started_at=service_started_at)
        catalog = _load_catalog_or_raise()
        try:
            resolved = catalog.resolve(template_id=template_id, version=version)
        except DocxTemplateNotFoundError as exc:
            raise ServiceError(
                status_code=404,
                code="template_not_found",
                message="DOCX template was not found.",
                retryable=False,
                details={"template_id": exc.template_id},
            ) from exc
        except DocxTemplateVersionNotFoundError as exc:
            raise ServiceError(
                status_code=404,
                code="template_version_not_found",
                message="Requested DOCX template version was not found.",
                retryable=False,
                details={"template_id": exc.template_id, "version": exc.version},
            ) from exc

        payload = DocxTemplateVersionResponseV2(template=_as_version_data(resolved))
        return JSONResponse(status_code=200, content=payload.model_dump(mode="json"))

    return router
