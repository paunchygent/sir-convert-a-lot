"""Sir Convert-a-Lot domain specifications.

Purpose:
    Define the core conversion domain language and invariants for v1 jobs,
    independent of transport and infrastructure concerns.

Relationships:
    - Imported by `application.contracts` for typed API payloads.
    - Imported by `infrastructure.runtime_engine` for execution policy enforcement.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceKind(StrEnum):
    """Supported source kinds for v1 conversion requests."""

    UPLOAD = "upload"


class BackendStrategy(StrEnum):
    """Backend strategy values supported by v1."""

    AUTO = "auto"
    DOCLING = "docling"
    PYMUPDF = "pymupdf"


class OcrMode(StrEnum):
    """OCR mode values supported by v1."""

    AUTO = "auto"
    OFF = "off"
    FORCE = "force"


class TableMode(StrEnum):
    """Table extraction modes supported by v1."""

    FAST = "fast"
    ACCURATE = "accurate"


class NormalizeMode(StrEnum):
    """Normalization modes supported by v1."""

    NONE = "none"
    STANDARD = "standard"
    STRICT = "strict"


class AccelerationPolicy(StrEnum):
    """Execution acceleration policies supported by v1."""

    GPU_REQUIRED = "gpu_required"
    GPU_PREFER = "gpu_prefer"
    CPU_ONLY = "cpu_only"


class Priority(StrEnum):
    """Execution priority values supported by v1."""

    NORMAL = "normal"
    HIGH = "high"


class JobStatus(StrEnum):
    """Job status lifecycle states."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


TERMINAL_JOB_STATUSES: frozenset[JobStatus] = frozenset(
    {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}
)


class SourceSpec(BaseModel):
    """Source section of the v1 job specification."""

    model_config = ConfigDict(extra="forbid")

    kind: SourceKind
    filename: str = Field(min_length=1)


class ConversionSpec(BaseModel):
    """Conversion section of the v1 job specification."""

    model_config = ConfigDict(extra="forbid")

    output_format: Literal["md"]
    backend_strategy: BackendStrategy
    ocr_mode: OcrMode
    table_mode: TableMode
    normalize: NormalizeMode


class ExecutionSpec(BaseModel):
    """Execution section of the v1 job specification."""

    model_config = ConfigDict(extra="forbid")

    acceleration_policy: AccelerationPolicy
    priority: Priority = Priority.NORMAL
    document_timeout_seconds: int = Field(default=1800, ge=30, le=7200)


class RetentionSpec(BaseModel):
    """Retention section of the v1 job specification."""

    model_config = ConfigDict(extra="forbid")

    pin: bool = False


class JobSpec(BaseModel):
    """Complete v1 job specification."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v1"]
    source: SourceSpec
    conversion: ConversionSpec
    execution: ExecutionSpec
    retention: RetentionSpec = Field(default_factory=RetentionSpec)
