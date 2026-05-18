"""OpenAPI schema wiring for Sir Convert-a-Lot service API v2.

Purpose:
    Keep the runtime `/openapi.json` and the generated contract snapshot aligned
    with consumer-facing v2 DTOs, including multipart JSON parts that FastAPI
    cannot infer from `UploadFile` and `Form` parameters alone.

Relationships:
    - Called by `interfaces.http_api.create_app`.
    - Uses application-level OpenAPI DTOs from `application.openapi_contracts_v2`.
    - Exported by `openapi_export_v2` for Skriptoteket contract generation.
"""

from __future__ import annotations

from collections.abc import MutableMapping

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from scripts.sir_convert_a_lot.application.openapi_contracts_v2 import (
    OPENAPI_CONTRACT_COMPONENT_MODELS,
)
from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    digiexam_schema_version_extension,
)

JsonObject = dict[str, object]


def configure_openapi_contract_v2(app: FastAPI) -> None:
    """Install the v2 OpenAPI generator used by runtime and snapshot exports."""

    def custom_openapi() -> JsonObject:
        if app.openapi_schema is not None:
            return _as_json_object(app.openapi_schema)
        schema = _as_json_object(
            get_openapi(
                title=app.title,
                version=app.version,
                routes=app.routes,
                description=app.description,
            )
        )
        _inject_component_models(schema, OPENAPI_CONTRACT_COMPONENT_MODELS)
        _patch_create_job_multipart_contract(schema)
        app.openapi_schema = schema
        return schema

    setattr(app, "openapi", custom_openapi)


def _inject_component_models(
    schema: MutableMapping[str, object], models: tuple[type[BaseModel], ...]
) -> None:
    component_schemas = _component_schemas(schema)
    for model in models:
        model_schema = _as_json_object(
            model.model_json_schema(ref_template="#/components/schemas/{model}")
        )
        defs = model_schema.pop("$defs", {})
        if isinstance(defs, dict):
            for name, definition in defs.items():
                component_schemas[str(name)] = definition
        component_schemas[model.__name__] = model_schema


def _patch_create_job_multipart_contract(schema: MutableMapping[str, object]) -> None:
    post_operation = _path_operation(schema, "/v2/convert/jobs", "post")
    post_operation["x-sir-convert-contract-components"] = {
        "job_spec": "#/components/schemas/JobSpecV2",
        "exam_authoring_matching_manual_answer_key": (
            "#/components/schemas/ExamAuthoringMatchingManualAnswerKey"
        ),
        "digiexam_ingestion_overlay": "#/components/schemas/DigiExamIngestionOverlay",
        "digiexam_migration_bundle_manifest": (
            "#/components/schemas/DigiExamMigrationBundleManifestV2"
        ),
        "target_readiness_report": "#/components/schemas/DigiExamTargetReadinessReportV1",
        "effective_ir_json": "#/components/schemas/DigiExamEffectiveExamV1",
        "ingestion_overlay_report": "#/components/schemas/DigiExamIngestionOverlayReportV1",
        "answer_key_completion_report": (
            "#/components/schemas/DigiExamAnswerKeyCompletionReportV1"
        ),
    }
    post_operation["x-sir-convert-digiexam-schema-versions"] = digiexam_schema_version_extension()
    content = _multipart_content(post_operation)
    content["encoding"] = {
        "job_spec": {"contentType": "application/json"},
        "digiexam_ingestion_overlay": {"contentType": "application/json"},
    }
    body_schema = _create_job_body_schema(schema)
    properties = _ensure_mapping(body_schema, "properties")
    if "job_spec" in properties:
        properties["job_spec"] = {
            "$ref": "#/components/schemas/JobSpecV2",
            "description": "Multipart JSON part parsed as the v2 job specification.",
        }
    if "digiexam_ingestion_overlay" in properties:
        properties["digiexam_ingestion_overlay"] = {
            "$ref": "#/components/schemas/DigiExamIngestionOverlay",
            "description": (
                "Optional multipart JSON part carrying a source-bound teacher ingestion overlay."
            ),
        }


def _component_schemas(schema: MutableMapping[str, object]) -> MutableMapping[str, object]:
    components = _ensure_mapping(schema, "components")
    return _ensure_mapping(components, "schemas")


def _path_operation(
    schema: MutableMapping[str, object], path: str, method: str
) -> MutableMapping[str, object]:
    paths = _ensure_mapping(schema, "paths")
    path_item = _ensure_mapping(paths, path)
    return _ensure_mapping(path_item, method)


def _multipart_content(operation: MutableMapping[str, object]) -> MutableMapping[str, object]:
    request_body = _ensure_mapping(operation, "requestBody")
    content = _ensure_mapping(request_body, "content")
    return _ensure_mapping(content, "multipart/form-data")


def _create_job_body_schema(schema: MutableMapping[str, object]) -> MutableMapping[str, object]:
    schemas = _component_schemas(schema)
    return _ensure_mapping(schemas, "Body_create_job_v2_convert_jobs_post")


def _ensure_mapping(parent: MutableMapping[str, object], key: str) -> MutableMapping[str, object]:
    value = parent.get(key)
    if isinstance(value, dict):
        return value
    child: JsonObject = {}
    parent[key] = child
    return child


def _as_json_object(value: object) -> JsonObject:
    if not isinstance(value, dict):
        raise TypeError("OpenAPI schema value must be a JSON object")
    return {str(key): item for key, item in value.items()}
