"""OpenAPI contract tests for the retained generic service API v2."""

import json

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


def test_create_job_openapi_contract_exposes_typed_job_spec() -> None:
    schema = build_openapi_contract_v2()
    paths = _mapping(schema["paths"])
    create_job = _mapping(_mapping(paths["/v2/convert/jobs"])["post"])

    assert create_job["x-sir-convert-contract-components"] == {
        "job_spec": "#/components/schemas/JobSpecV2"
    }
    multipart = _mapping(_mapping(create_job["requestBody"])["content"])
    multipart_form = _mapping(multipart["multipart/form-data"])
    assert multipart_form["encoding"] == {"job_spec": {"contentType": "application/json"}}


def test_openapi_contains_no_retired_exam_surface() -> None:
    schema = build_openapi_contract_v2()
    paths = _mapping(schema["paths"])
    schemas = _mapping(_mapping(schema["components"])["schemas"])

    assert all("exam" not in path.lower() and "correction-replay" not in path for path in paths)
    assert all(
        "digiexam" not in name.lower() and "answerkey" not in name.lower() for name in schemas
    )
