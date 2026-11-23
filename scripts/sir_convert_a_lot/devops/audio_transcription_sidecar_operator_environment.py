"""Audio transcription sidecar operator environment.

Purpose:
    Load repo-local operator environment values for the speech-to-text sidecar
    benchmark lane while keeping secret values out of generated reports and
    subprocess command text.

Relationships:
    - Used by the live-observation producer before launching host or Docker
      runtime probes.
    - Never overwrites a variable already set in the process environment with a
      `.env` value, so a secret injected through
      `agent-secrets run --set sir-convert-a-lot-operator` always wins.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path


def merged_operator_environment(
    base_environment: Mapping[str, str],
    *,
    env_file: Path,
) -> dict[str, str]:
    """Return process environment extended with repo-local operator values."""

    merged = dict(base_environment)
    if env_file.is_file():
        for key, value in _parse_env_file(env_file).items():
            merged.setdefault(key, value)
    return merged


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key or not _valid_env_name(normalized_key):
            continue
        values[normalized_key] = _unquote_value(value.strip())
    return values


def _valid_env_name(value: str) -> bool:
    first = value[0]
    if not (first == "_" or first.isalpha()):
        return False
    return all(character == "_" or character.isalnum() for character in value)


def _unquote_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
