"""Story 58 live replay proof HTTP transport.

Purpose:
    Execute operator-declared Service API v2 proof requests while keeping
    request payloads and credentials out of retained evidence.

Relationships:
    - Used by the Story 58 proof orchestrator.
    - Depends only on `httpx` and manifest request descriptions, not Service API
      route implementation modules.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import IO, TypeAlias

import httpx

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import JsonObject
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_sensitive_inputs import (
    sensitive_request_headers,
)

ProofMultipartValue: TypeAlias = (
    tuple[str | None, IO[bytes] | bytes | str] | tuple[str | None, IO[bytes] | bytes | str, str]
)


def fetch_json(
    client: httpx.Client,
    *,
    path: str,
    api_key: str,
    correlation_id: str,
) -> tuple[int, JsonObject]:
    """Fetch a JSON object with proof-run authentication headers."""

    response = client.get(path, headers=_headers(api_key=api_key, correlation_id=correlation_id))
    return response.status_code, _json_payload(response)


def execute_manifest_request(
    *,
    client: httpx.Client,
    request_spec: JsonObject,
    manifest_root: Path,
    api_key: str,
    correlation_id: str,
) -> tuple[int, JsonObject]:
    """Execute one manifest-declared request and return status plus JSON payload."""

    method = _required_string(request_spec, "method").upper()
    path = _required_string(request_spec, "path")
    query = _string_map(request_spec.get("query"))
    headers = {
        **_headers(api_key=api_key, correlation_id=correlation_id),
        **_string_map(request_spec.get("headers")),
        **sensitive_request_headers(request_spec),
    }
    json_payload = _json_file_payload(
        manifest_root=manifest_root,
        value=request_spec.get("json_file"),
    )
    multipart = request_spec.get("multipart")
    if isinstance(multipart, dict):
        return _execute_multipart_request(
            client=client,
            method=method,
            path=path,
            query=query,
            headers=headers,
            manifest_root=manifest_root,
            multipart=multipart,
        )
    response = client.request(
        method,
        path,
        params=query,
        headers=headers,
        json=json_payload,
    )
    return response.status_code, _json_payload(response)


def _execute_multipart_request(
    *,
    client: httpx.Client,
    method: str,
    path: str,
    query: dict[str, str],
    headers: dict[str, str],
    manifest_root: Path,
    multipart: dict[object, object],
) -> tuple[int, JsonObject]:
    file_path = _path_from_value(manifest_root=manifest_root, value=multipart.get("file_path"))
    job_spec_path = _path_from_value(
        manifest_root=manifest_root,
        value=multipart.get("job_spec_file"),
    )
    content_type = multipart.get("content_type")
    file_content_type = (
        content_type if isinstance(content_type, str) else "application/octet-stream"
    )
    job_spec_text = job_spec_path.read_text(encoding="utf-8")
    with file_path.open("rb") as file_handle:
        files: dict[str, ProofMultipartValue] = {
            "file": (file_path.name, file_handle, file_content_type),
            "job_spec": (None, job_spec_text),
        }
        response = client.request(
            method,
            path,
            params=query,
            headers=headers,
            files=files,
        )
    return response.status_code, _json_payload(response)


def _headers(*, api_key: str, correlation_id: str) -> dict[str, str]:
    return {"X-API-Key": api_key, "X-Correlation-ID": correlation_id}


def _json_payload(response: httpx.Response) -> JsonObject:
    try:
        payload: object = response.json()
    except ValueError:
        return {"error": {"code": "non_json_response", "retryable": False}}
    if isinstance(payload, dict):
        return dict(payload)
    return {"error": {"code": "non_object_json_response", "retryable": False}}


def _json_file_payload(*, manifest_root: Path, value: object) -> object | None:
    if value is None:
        return None
    path = _path_from_value(manifest_root=manifest_root, value=value)
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
        return payload
    except ValueError as exc:
        raise SystemExit(f"request JSON file is not valid JSON: {path}") from exc


def _path_from_value(*, manifest_root: Path, value: object) -> Path:
    if not isinstance(value, str) or value.strip() == "":
        raise SystemExit("manifest request path value must be a non-empty string")
    path = Path(value)
    return path if path.is_absolute() else manifest_root / path


def _required_string(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise SystemExit(f"manifest request missing non-empty {key}")
    return value


def _string_map(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SystemExit("manifest map value must be an object")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not isinstance(item, str):
            raise SystemExit("manifest map keys and values must be strings")
        result[key] = item
    return result
