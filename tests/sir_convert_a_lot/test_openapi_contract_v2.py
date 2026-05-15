"""OpenAPI contract tests for Sir Convert-a-Lot service API v2.

Purpose:
    Keep the generated v2 OpenAPI snapshot synchronized with the FastAPI app
    and verify that DigiExam migration multipart contracts expose typed schemas
    for downstream consumer generation.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.openapi_export_v2`.
    - Protects Story 48 / Task 304 consumer contract publication.
"""

from __future__ import annotations

import json

from scripts.sir_convert_a_lot.domain.digiexam_schema_versions import (
    ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
    DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
    DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION,
    TARGET_READINESS_REPORT_SCHEMA_VERSION,
    digiexam_schema_version_extension,
)
from scripts.sir_convert_a_lot.openapi_export_v2 import (
    DEFAULT_OPENAPI_CONTRACT_PATH,
    build_openapi_contract_v2,
    openapi_contract_bytes_v2,
)


def _mapping(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return {str(key): item for key, item in value.items()}


def test_openapi_v2_snapshot_matches_runtime_export() -> None:
    expected = json.loads(DEFAULT_OPENAPI_CONTRACT_PATH.read_text(encoding="utf-8"))
    actual = json.loads(openapi_contract_bytes_v2().decode("utf-8"))

    assert actual == expected


def test_create_job_openapi_contract_exposes_typed_multipart_json_parts() -> None:
    schema = build_openapi_contract_v2()
    paths = _mapping(schema["paths"])
    create_job = _mapping(_mapping(paths["/v2/convert/jobs"])["post"])
    responses = _mapping(create_job["responses"])
    response_200 = _mapping(_mapping(_mapping(responses["200"])["content"])["application/json"])
    response_202 = _mapping(_mapping(_mapping(responses["202"])["content"])["application/json"])

    assert response_200["schema"] == {"$ref": "#/components/schemas/JobCreateResponseV2"}
    assert response_202["schema"] == {"$ref": "#/components/schemas/JobCreateResponseV2"}
    assert create_job["x-sir-convert-contract-components"] == {
        "job_spec": "#/components/schemas/JobSpecV2",
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
    assert create_job["x-sir-convert-digiexam-schema-versions"] == (
        digiexam_schema_version_extension()
    )

    request_body = _mapping(create_job["requestBody"])
    content = _mapping(request_body["content"])
    multipart = _mapping(content["multipart/form-data"])
    multipart_schema = _mapping(multipart["schema"])
    body_schema_ref = str(multipart_schema["$ref"]).removeprefix("#/components/schemas/")
    schemas = _mapping(_mapping(schema["components"])["schemas"])
    body_schema = _mapping(schemas[body_schema_ref])
    properties = _mapping(body_schema["properties"])

    assert _mapping(properties["job_spec"])["$ref"] == "#/components/schemas/JobSpecV2"
    assert _mapping(properties["digiexam_ingestion_overlay"])["$ref"] == (
        "#/components/schemas/DigiExamIngestionOverlay"
    )
    assert multipart["encoding"] == {
        "job_spec": {"contentType": "application/json"},
        "digiexam_ingestion_overlay": {"contentType": "application/json"},
    }


def test_digiexam_consumer_components_are_published() -> None:
    schema = build_openapi_contract_v2()
    schemas = _mapping(_mapping(schema["components"])["schemas"])

    for component_name in (
        "JobSpecV2",
        "DigiExamMigrationOptionsV2",
        "DigiExamIngestionOverlay",
        "DigiExamMigrationBundleManifestV2",
        "DigiExamTargetReadinessReportV1",
        "DigiExamEffectiveExamV1",
        "DigiExamIngestionOverlayReportV1",
        "DigiExamAnswerKeyCompletionReportV1",
    ):
        assert component_name in schemas

    readiness_report = _mapping(schemas["DigiExamTargetReadinessReportV1"])
    readiness_properties = _mapping(readiness_report["properties"])
    readiness_schema_version = _mapping(readiness_properties["schema_version"])
    assert readiness_schema_version["const"] == TARGET_READINESS_REPORT_SCHEMA_VERSION
    effective_exam = _mapping(schemas["DigiExamEffectiveExamV1"])
    effective_properties = _mapping(effective_exam["properties"])
    effective_schema_version = _mapping(effective_properties["schema_version"])
    assert effective_schema_version["const"] == DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION
    ingestion_overlay = _mapping(schemas["DigiExamIngestionOverlay"])
    ingestion_properties = _mapping(ingestion_overlay["properties"])
    ingestion_schema_version = _mapping(ingestion_properties["schema_version"])
    assert ingestion_schema_version["const"] == DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION
    completion_report = _mapping(schemas["DigiExamAnswerKeyCompletionReportV1"])
    completion_properties = _mapping(completion_report["properties"])
    completion_schema_version = _mapping(completion_properties["schema_version"])
    assert completion_schema_version["const"] == ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION
    assert "DigiExamOverlayMatchingPair" not in schemas
    assert "DigiExamOverlayMatchingManualAnswerKey" not in schemas
    assert "DigiExamOverlayMatchingItemPatch" not in schemas

    effective_answer_key = _mapping(schemas["DigiExamEffectiveAnswerKeyV1"])
    effective_answer_key_properties = _mapping(effective_answer_key["properties"])
    assert "correct_matching_pairs" not in effective_answer_key_properties

    effective_patch_summary = _mapping(schemas["DigiExamEffectiveItemPatchSummaryV1"])
    effective_patch_summary_properties = _mapping(effective_patch_summary["properties"])
    assert "patched_matching_left_indices" not in effective_patch_summary_properties
    assert "patched_matching_right_indices" not in effective_patch_summary_properties
