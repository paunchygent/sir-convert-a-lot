"""Terminal artifact object-store persistence for v2 jobs.

Purpose:
    Persist primary terminal artifacts and route-owned named terminal bundle
    artifacts behind the Sir-owned object-store adapter during successful job
    finalization.

Relationships:
    - Called by `job_store_v2.JobStoreV2.mark_succeeded`.
    - Keeps route-specific artifact selection out of generic job-state code.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    ARTIFACT_DEFINITIONS,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2
from scripts.sir_convert_a_lot.domain.transcript_formatter_artifacts import (
    TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS,
)
from scripts.sir_convert_a_lot.infrastructure.audio_transcript_runtime_types import (
    TRANSCRIPT_JSON_ARTIFACT_KEY,
)
from scripts.sir_convert_a_lot.infrastructure.object_store_models import (
    TerminalArtifactObjectRef,
    TerminalArtifactStore,
    TerminalArtifactWriteRequest,
)


def persist_terminal_artifact_objects_v2(
    *,
    object_store: TerminalArtifactStore,
    job_id: str,
    owner_api_key_scope: str,
    source_format_value: str,
    output_format: OutputFormatV2,
    artifact_path: Path,
    primary_content_type: str,
    primary_payload: bytes,
) -> dict[str, TerminalArtifactObjectRef]:
    """Persist Task 381-approved terminal artifacts and return refs by artifact key."""
    route_key = f"{source_format_value}_to_{output_format.value}"
    owner_scope_sha256 = hashlib.sha256(owner_api_key_scope.encode("utf-8")).hexdigest()
    refs: dict[str, TerminalArtifactObjectRef] = {
        "primary": object_store.put_artifact(
            TerminalArtifactWriteRequest(
                job_id=job_id,
                route_key=route_key,
                owner_scope_sha256=owner_scope_sha256,
                artifact_class="primary_terminal",
                artifact_key="primary",
                filename=artifact_path.name,
                content_type=primary_content_type,
                payload=primary_payload,
            )
        )
    }
    if output_format == OutputFormatV2.EXAMNET_MIGRATION_BUNDLE:
        refs["bundle_manifest"] = refs["primary"]
        refs.update(
            _persist_digiexam_named_artifacts(
                object_store=object_store,
                job_id=job_id,
                route_key=route_key,
                owner_scope_sha256=owner_scope_sha256,
                artifacts_dir=artifact_path.parent,
            )
        )
    if output_format == OutputFormatV2.TRANSCRIPT_BUNDLE:
        refs[TRANSCRIPT_JSON_ARTIFACT_KEY] = refs["primary"]
        refs.update(
            _persist_transcript_named_artifacts(
                object_store=object_store,
                job_id=job_id,
                route_key=route_key,
                owner_scope_sha256=owner_scope_sha256,
                artifacts_dir=artifact_path.parent,
            )
        )
    return refs


def _persist_digiexam_named_artifacts(
    *,
    object_store: TerminalArtifactStore,
    job_id: str,
    route_key: str,
    owner_scope_sha256: str,
    artifacts_dir: Path,
) -> dict[str, TerminalArtifactObjectRef]:
    refs: dict[str, TerminalArtifactObjectRef] = {}
    for artifact_key, definition in ARTIFACT_DEFINITIONS.items():
        if artifact_key.value == "bundle_manifest":
            continue
        path = artifacts_dir / definition.filename
        if not path.exists():
            continue
        refs[artifact_key.value] = object_store.put_artifact(
            TerminalArtifactWriteRequest(
                job_id=job_id,
                route_key=route_key,
                owner_scope_sha256=owner_scope_sha256,
                artifact_class="terminal_bundle",
                artifact_key=artifact_key.value,
                filename=definition.filename,
                content_type=definition.content_type,
                payload=path.read_bytes(),
            )
        )
    return refs


def _persist_transcript_named_artifacts(
    *,
    object_store: TerminalArtifactStore,
    job_id: str,
    route_key: str,
    owner_scope_sha256: str,
    artifacts_dir: Path,
) -> dict[str, TerminalArtifactObjectRef]:
    refs: dict[str, TerminalArtifactObjectRef] = {}
    for definition in TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS:
        path = artifacts_dir / definition.filename
        if not path.exists():
            continue
        refs[definition.artifact_key] = object_store.put_artifact(
            TerminalArtifactWriteRequest(
                job_id=job_id,
                route_key=route_key,
                owner_scope_sha256=owner_scope_sha256,
                artifact_class="terminal_bundle",
                artifact_key=definition.artifact_key,
                filename=definition.filename,
                content_type=definition.content_type,
                payload=path.read_bytes(),
            )
        )
    return refs
