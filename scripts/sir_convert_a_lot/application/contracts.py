"""Sir Convert-a-Lot application contracts.

Purpose:
    Define typed API/CLI data contracts exchanged between interfaces and
    application/infrastructure services.

Relationships:
    - Imported by HTTP and CLI interfaces for response/manifest validation.
    - Imported by infrastructure runtime for conversion metadata typing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from scripts.sir_convert_a_lot.domain.specs import JobStatus, TableMode


class JobProgress(BaseModel):
    """Progress metadata for running jobs."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    pages_total: int | None = None
    pages_processed: int | None = None


class JobLinks(BaseModel):
    """Hypermedia links included in job status payloads."""

    model_config = ConfigDict(extra="forbid")

    self: str
    result: str
    cancel: str


class JobRecordData(BaseModel):
    """Job details payload embedded in job record responses."""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    source_filename: str
    progress: JobProgress
    links: JobLinks


class JobRecordResponse(BaseModel):
    """Response payload for job status endpoints."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    job: JobRecordData


class ArtifactMetadata(BaseModel):
    """Artifact metadata for successful job results."""

    model_config = ConfigDict(extra="forbid")

    markdown_filename: str
    size_bytes: int
    sha256: str


class ConversionMetadata(BaseModel):
    """Execution metadata for successful conversion jobs."""

    model_config = ConfigDict(extra="forbid")

    backend_used: str
    acceleration_used: str
    ocr_enabled: bool
    table_mode: TableMode
    options_fingerprint: str


class ResultPayload(BaseModel):
    """Result payload for successful conversion jobs."""

    model_config = ConfigDict(extra="forbid")

    artifact: ArtifactMetadata
    conversion_metadata: ConversionMetadata
    warnings: list[str] = Field(default_factory=list)
    markdown_content: str | None = None


class JobResultResponse(BaseModel):
    """Response payload for successful result retrieval."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    job_id: str
    status: Literal[JobStatus.SUCCEEDED] = JobStatus.SUCCEEDED
    result: ResultPayload


class JobPendingResultResponse(BaseModel):
    """Response payload when a result request is made before completion."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    job_id: str
    status: JobStatus


class ErrorBody(BaseModel):
    """Standard error payload shape for all non-2xx responses."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None = None
    correlation_id: str


class ErrorEnvelope(BaseModel):
    """Top-level error envelope for v1 responses."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    error: ErrorBody


class CliManifestEntry(BaseModel):
    """Deterministic manifest entry emitted by the convert-a-lot CLI."""

    model_config = ConfigDict(extra="forbid")

    source_file_path: str
    job_id: str | None
    status: JobStatus
    output_path: str | None
    error_code: str | None


class CliManifest(BaseModel):
    """Batch manifest emitted by the convert-a-lot CLI."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"] = "v1"
    tool_name: Literal["sir-convert-a-lot"] = "sir-convert-a-lot"
    generated_at: datetime
    source_root: str
    output_root: str
    entries: list[CliManifestEntry]
