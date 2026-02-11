"""Sir Convert-a-Lot compatibility model exports.

Purpose:
    Preserve stable imports for model symbols while delegating definitions to
    DDD-structured `domain` and `application` layers.

Relationships:
    - Re-exports from `domain.specs` and `application.contracts`.
    - Used by legacy imports in service/client/tests during migration.
"""

from scripts.sir_convert_a_lot.application.contracts import (
    ArtifactMetadata,
    CliManifest,
    CliManifestEntry,
    ConversionMetadata,
    ErrorBody,
    ErrorEnvelope,
    JobLinks,
    JobPendingResultResponse,
    JobProgress,
    JobRecordData,
    JobRecordResponse,
    JobResultResponse,
    ResultPayload,
)
from scripts.sir_convert_a_lot.domain.specs import (
    TERMINAL_JOB_STATUSES,
    AccelerationPolicy,
    BackendStrategy,
    ConversionSpec,
    ExecutionSpec,
    JobSpec,
    JobStatus,
    NormalizeMode,
    OcrMode,
    Priority,
    RetentionSpec,
    SourceKind,
    SourceSpec,
    TableMode,
)

__all__ = [
    "AccelerationPolicy",
    "ArtifactMetadata",
    "BackendStrategy",
    "CliManifest",
    "CliManifestEntry",
    "ConversionMetadata",
    "ConversionSpec",
    "ErrorBody",
    "ErrorEnvelope",
    "ExecutionSpec",
    "JobLinks",
    "JobPendingResultResponse",
    "JobProgress",
    "JobRecordData",
    "JobRecordResponse",
    "JobResultResponse",
    "JobSpec",
    "JobStatus",
    "NormalizeMode",
    "OcrMode",
    "Priority",
    "ResultPayload",
    "RetentionSpec",
    "SourceKind",
    "SourceSpec",
    "TERMINAL_JOB_STATUSES",
    "TableMode",
]
