"""Story 58 live proof sensitive request input resolution.

Purpose:
    Resolve operator-private request headers from environment variables and
    private JSON files while keeping secret values and paths out of retained
    Story 58 proof manifests and evidence.

Relationships:
    - Used by the Story 58 live proof HTTP transport before issuing manifest
      requests.
    - Depends only on manifest request descriptions and process environment,
      not Service API runtime modules.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import JsonObject


def sensitive_request_headers(request_spec: JsonObject) -> dict[str, str]:
    """Return headers loaded from private operator-controlled sources."""

    return {
        **_headers_from_env_map(request_spec.get("header_env")),
        **_headers_from_file_env(request_spec.get("headers_file_env")),
    }


def _headers_from_env_map(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SystemExit("manifest header_env value must be an object")
    headers: dict[str, str] = {}
    for header_name, env_name in value.items():
        if not isinstance(header_name, str) or header_name.strip() == "":
            raise SystemExit("manifest header_env header names must be non-empty strings")
        if not isinstance(env_name, str) or env_name.strip() == "":
            raise SystemExit("manifest header_env env names must be non-empty strings")
        headers[header_name] = _env_value(env_name)
    return headers


def _headers_from_file_env(value: object) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, str) or value.strip() == "":
        raise SystemExit("manifest headers_file_env value must be a non-empty string")
    path_value = _env_value(value)
    return _header_file(Path(path_value))


def _header_file(path: Path) -> dict[str, str]:
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit("private header JSON file could not be read") from exc
    except ValueError as exc:
        raise SystemExit("private header JSON file is not valid JSON") from exc
    return _string_map(payload, label="private header JSON file")


def _env_value(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise SystemExit(f"required private header env var is not set: {name}")
    return value


def _string_map(value: object, *, label: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must contain a JSON object")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or key.strip() == "":
            raise SystemExit(f"{label} header names must be non-empty strings")
        if not isinstance(item, str) or item.strip() == "":
            raise SystemExit(f"{label} header values must be non-empty strings")
        result[key] = item
    return result
