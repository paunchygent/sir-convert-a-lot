"""Story 58 live replay proof request context.

Purpose:
    Own metadata-only extraction and interpolation for dependent Story 58 proof
    requests, using only redacted response payload fields.

Relationships:
    - Used by the Story 58 proof orchestrator between redaction and later HTTP
      transport calls.
    - Does not import Service API runtime modules or retain raw response
      payloads, request bodies, credentials, or secret header values.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import JsonObject

VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
PATH_TOKEN_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)])?")


@dataclass
class Story58ProofContext:
    """Metadata context captured from redacted proof responses."""

    _values: dict[str, str] = field(default_factory=dict)

    def interpolated_request(self, request_spec: JsonObject) -> JsonObject:
        """Return a request spec with path, query, and header values interpolated."""

        resolved = dict(request_spec)
        path = request_spec.get("path")
        if isinstance(path, str):
            resolved["path"] = self.interpolate(path)
        query = request_spec.get("query")
        if query is not None:
            resolved["query"] = self._interpolated_string_map(query, field_name="query")
        headers = request_spec.get("headers")
        if headers is not None:
            resolved["headers"] = self._interpolated_string_map(headers, field_name="headers")
        return resolved

    def capture(self, *, request_spec: JsonObject, redacted_payload: JsonObject) -> None:
        """Capture declared variables from a redacted response payload."""

        extract = request_spec.get("extract")
        if extract is None:
            return
        if not isinstance(extract, dict):
            raise SystemExit("request extract value must be an object")
        for variable, path in extract.items():
            if not isinstance(variable, str) or VARIABLE_NAME_PATTERN.fullmatch(variable) is None:
                raise SystemExit("extract variable names must be non-empty identifiers")
            if variable in self._values:
                raise SystemExit(f"extract variable already exists: {variable}")
            if not isinstance(path, str) or path.strip() == "":
                raise SystemExit(f"extract path for {variable} must be a non-empty string")
            value = _value_at_path(redacted_payload, path)
            if value is None:
                raise SystemExit(f"missing extraction for {variable}: {path}")
            if not isinstance(value, (str, int, bool)):
                raise SystemExit(f"extraction for {variable} did not resolve to a scalar")
            self._values[variable] = str(value)

    def interpolate(self, value: str) -> str:
        """Interpolate placeholders from captured metadata, failing closed."""

        unresolved: list[str] = []

        def replace(match: re.Match[str]) -> str:
            variable = match.group(1)
            resolved = self._values.get(variable)
            if resolved is None:
                unresolved.append(variable)
                return match.group(0)
            return resolved

        result = PLACEHOLDER_PATTERN.sub(replace, value)
        if unresolved:
            names = ", ".join(sorted(set(unresolved)))
            raise SystemExit(f"unresolved manifest interpolation: {names}")
        if "{" in result or "}" in result:
            raise SystemExit("unresolved manifest interpolation: malformed placeholder")
        return result

    def _interpolated_string_map(self, value: object, *, field_name: str) -> dict[str, str]:
        if not isinstance(value, dict):
            raise SystemExit(f"manifest {field_name} value must be an object")
        result: dict[str, str] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not isinstance(item, str):
                raise SystemExit(f"manifest {field_name} keys and values must be strings")
            result[key] = self.interpolate(item)
        return result


def _value_at_path(payload: JsonObject, path: str) -> object:
    current: object = payload
    for token in path.split("."):
        if token.strip() == "":
            raise SystemExit(f"invalid extraction path: {path}")
        match = PATH_TOKEN_PATTERN.fullmatch(token)
        if match is None:
            raise SystemExit(f"invalid extraction path: {path}")
        if not isinstance(current, dict):
            return None
        current = current.get(match.group(1))
        index = match.group(2)
        if index is not None:
            if not isinstance(current, list):
                return None
            item_index = int(index)
            if item_index >= len(current):
                return None
            current = current[item_index]
    return current
