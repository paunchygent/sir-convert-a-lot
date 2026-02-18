"""Typed runtime models for v2 job orchestration.

Purpose:
    Centralize v2 runtime dataclasses so v2 orchestration logic can stay focused
    on behavior rather than data-shape declarations.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` as primary v2 runtime model types.
    - Mirrors v1 runtime model patterns in `infrastructure.runtime_models`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2


@dataclass
class StoredJobV2:
    """Internal mutable job state stored by the service v2 runtime."""

    job_id: str
    spec: JobSpecV2
    source_filename: str
    source_format: SourceFormatV2
    output_format: OutputFormatV2
    upload_path: Path
    resources_zip_path: Path | None
    reference_docx_path: Path | None
    artifact_path: Path
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    progress_stage: str
    last_heartbeat_at: datetime | None = None
    current_phase_started_at: datetime | None = None
    phase_timings_ms: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    artifact_sha256: str | None = None
    artifact_size_bytes: int | None = None
    pipeline_used: str | None = None
    backend_used: str | None = None
    acceleration_used: str | None = None
    options_fingerprint: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_retryable: bool = False
    failure_details: dict[str, object] | None = None
