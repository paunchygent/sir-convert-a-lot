"""Terminal artifact JSON loading through filesystem or object refs.

Purpose:
    Load terminal JSON artifacts after route authorization while preserving the
    object-store boundary for cold primary bundle manifests.

Relationships:
    - Supports routes that expose JSON terminal artifacts.
    - Delegates object reads to `TerminalArtifactStore` without exposing SDK
      details to route handlers.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.object_store_models import TerminalArtifactStore
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


class TerminalArtifactJsonInvalidError(Exception):
    """Raised when a terminal JSON artifact cannot be decoded as an object."""


def load_terminal_artifact_json_v2(
    *,
    object_store: TerminalArtifactStore,
    job: StoredJobV2,
    artifact_key: str,
    filesystem_path: Path,
) -> dict[str, object]:
    """Load a terminal JSON object from local storage or its object ref."""
    payload = _read_terminal_artifact_bytes(
        object_store=object_store,
        job=job,
        artifact_key=artifact_key,
        filesystem_path=filesystem_path,
    )
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TerminalArtifactJsonInvalidError() from exc
    if not isinstance(decoded, dict):
        raise TerminalArtifactJsonInvalidError()
    return {str(key): value for key, value in decoded.items()}


def _read_terminal_artifact_bytes(
    *,
    object_store: TerminalArtifactStore,
    job: StoredJobV2,
    artifact_key: str,
    filesystem_path: Path,
) -> bytes:
    if filesystem_path.exists():
        try:
            return filesystem_path.read_bytes()
        except OSError as exc:
            raise TerminalArtifactJsonInvalidError() from exc
    ref = job.terminal_artifact_object_refs.get(artifact_key)
    if ref is None:
        ref = job.terminal_artifact_object_refs.get("primary")
    if ref is None:
        raise TerminalArtifactJsonInvalidError()
    read = object_store.read_artifact(ref)
    return read.content
