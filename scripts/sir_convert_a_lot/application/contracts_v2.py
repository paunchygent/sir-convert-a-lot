"""Sir Convert-a-Lot application contracts for multi-format service API v2.

Purpose:
    Define typed service API v2 response payloads (job records, results, and
    binary artifact metadata) exchanged between HTTP interfaces and the v2
    runtime.

Relationships:
    - Used by `scripts.sir_convert_a_lot.interfaces` v2 routes for response
      serialization.
    - Coexists with v1 contracts in `scripts.sir_convert_a_lot.application.contracts`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.application.contracts import ErrorBody
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2


class JobProgressV2(BaseModel):
    """Progress metadata for running v2 jobs."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    last_heartbeat_at: datetime | None = None
    current_phase_started_at: datetime | None = None
    phase_timings_ms: dict[str, int] = Field(default_factory=dict)


class JobLinksV2(BaseModel):
    """Hypermedia links included in v2 job status payloads."""

    model_config = ConfigDict(extra="forbid")

    self: str
    result: str
    artifact: str
    cancel: str


class JobRecordDataV2(BaseModel):
    """Job details payload embedded in v2 job record responses."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    source_filename: str
    source_format: SourceFormatV2
    output_format: OutputFormatV2
    progress: JobProgressV2
    links: JobLinksV2


class JobRecordResponseV2(BaseModel):
    """Response payload for v2 job status endpoints."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    job: JobRecordDataV2


class ArtifactMetadataV2(BaseModel):
    """Artifact metadata for successful v2 job results."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    format: OutputFormatV2
    size_bytes: int
    sha256: str
    content_type: str


class ConversionMetadataV2(BaseModel):
    """Execution metadata for successful v2 conversion jobs."""

    model_config = ConfigDict(extra="forbid")

    pipeline_used: str
    backend_used: str | None = None
    acceleration_used: str | None = None
    options_fingerprint: str


class ResultPayloadV2(BaseModel):
    """Result payload for successful v2 conversion jobs."""

    model_config = ConfigDict(extra="forbid")

    artifact: ArtifactMetadataV2
    conversion_metadata: ConversionMetadataV2
    warnings: list[str] = Field(default_factory=list)


class JobResultResponseV2(BaseModel):
    """Response payload for v2 successful result retrieval."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    job_id: str
    status: Literal[JobStatus.SUCCEEDED] = JobStatus.SUCCEEDED
    result: ResultPayloadV2


class JobPendingResultResponseV2(BaseModel):
    """Response payload when a v2 result request is made before completion."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    job_id: str
    status: JobStatus


class ErrorEnvelopeV2(BaseModel):
    """Top-level error envelope for v2 responses."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    error: ErrorBody
