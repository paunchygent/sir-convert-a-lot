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

DocxTemplateStatusV2 = Literal["active", "deprecated", "disabled"]


class JobProgressV2(BaseModel):
    """Progress metadata for running v2 jobs."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    last_heartbeat_at: datetime | None = None
    current_phase_started_at: datetime | None = None
    phase_timings_ms: dict[str, int] = Field(
        default_factory=dict,
        description=("Canonical stage timings map. See v2 converter docs for key contract."),
    )
    total_pages: int | None = Field(default=None, ge=0)
    processed_pages: int | None = Field(default=None, ge=0)
    failed_pages: int | None = Field(default=None, ge=0)
    percent_complete: float | None = Field(default=None, ge=0.0, le=100.0)
    pages_per_minute: float | None = Field(default=None, ge=0.0)
    eta_seconds: int | None = Field(default=None, ge=0)


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
    acceleration_policy_requested: str | None = None
    gpu_runtime_kind: str | None = None
    gpu_device_count: int | None = Field(default=None, ge=0)
    gpu_busy_percent: int | None = Field(default=None, ge=0, le=100)
    gpu_memory_used_percent: int | None = Field(default=None, ge=0, le=100)
    options_fingerprint: str
    template_id: str | None = None
    template_version: str | None = None
    template_artifact_sha256: str | None = None
    parallel_enabled: bool | None = None
    max_chunk_workers: int | None = Field(default=None, ge=1)
    chunk_size_pages: int | None = Field(default=None, ge=1)
    effective_gpu_stage_limit: int | None = Field(default=None, ge=1)
    scheduling_mode: str | None = None


class DocxTemplateSummaryV2(BaseModel):
    """Selection-ready template summary in v2 template listing responses."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    name: str
    description: str
    domain_tags: list[str] = Field(default_factory=list)
    latest_active_version: str | None = None
    versions: list[str] = Field(default_factory=list)
    statuses: list[DocxTemplateStatusV2] = Field(default_factory=list)


class DocxTemplateVersionDataV2(BaseModel):
    """One template-version metadata record returned from v2 template APIs."""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    version: str
    name: str
    description: str
    domain_tags: list[str] = Field(default_factory=list)
    language_tags: list[str] = Field(default_factory=list)
    status: DocxTemplateStatusV2
    artifact_sha256: str
    artifact_size_bytes: int
    created_at: datetime
    updated_at: datetime


class DocxTemplateListResponseV2(BaseModel):
    """Response payload for `GET /v2/templates/docx`."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    templates: list[DocxTemplateSummaryV2] = Field(default_factory=list)


class DocxTemplateDetailResponseV2(BaseModel):
    """Response payload for `GET /v2/templates/docx/{template_id}`."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    template_id: str
    versions: list[DocxTemplateVersionDataV2] = Field(default_factory=list)


class DocxTemplateVersionResponseV2(BaseModel):
    """Response payload for one resolved template version record."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    template: DocxTemplateVersionDataV2


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


class JobEventRouteV2(BaseModel):
    """Route metadata included in v2 lifecycle event payloads."""

    model_config = ConfigDict(extra="forbid")

    source_format: SourceFormatV2
    target_format: OutputFormatV2


class JobEventProgressV2(BaseModel):
    """Progress metadata included in v2 lifecycle event payloads."""

    model_config = ConfigDict(extra="forbid")

    stage: str
    last_heartbeat_at: datetime | None = None
    total_pages: int | None = Field(default=None, ge=0)
    processed_pages: int | None = Field(default=None, ge=0)
    failed_pages: int | None = Field(default=None, ge=0)
    percent_complete: float | None = Field(default=None, ge=0.0, le=100.0)
    pages_per_minute: float | None = Field(default=None, ge=0.0)
    eta_seconds: int | None = Field(default=None, ge=0)


class JobEventSseMetricsV2(BaseModel):
    """Transient SSE instrumentation fields emitted with stream payloads."""

    model_config = ConfigDict(extra="forbid")

    sent_at: datetime
    emit_to_send_ms: int


class JobLifecycleEventV2(BaseModel):
    """Event payload emitted by the v2 SSE stream surface."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    event_id: str
    event_type: Literal[
        "job.queued",
        "job.running",
        "job.succeeded",
        "job.failed",
        "job.canceled",
    ]
    sequence: int
    occurred_at: datetime
    job_id: str
    status: JobStatus
    route: JobEventRouteV2
    progress: JobEventProgressV2
    sse_metrics: JobEventSseMetricsV2 | None = None


WebhookEventTypeContractV2 = Literal[
    "job.queued",
    "job.running",
    "job.succeeded",
    "job.failed",
    "job.canceled",
]
WebhookSecretVersionContractV2 = Literal["active", "next"]


class WebhookSubscriptionCreateRequestV2(BaseModel):
    """Request payload for webhook subscription creation."""

    model_config = ConfigDict(extra="forbid")

    callback_url: str
    event_types: list[WebhookEventTypeContractV2]
    enabled: bool = True


class WebhookSubscriptionUpdateRequestV2(BaseModel):
    """Request payload for webhook subscription update."""

    model_config = ConfigDict(extra="forbid")

    callback_url: str | None = None
    event_types: list[WebhookEventTypeContractV2] | None = None
    enabled: bool | None = None


class WebhookSecretRotateRequestV2(BaseModel):
    """Request payload for webhook secret rotation."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = None


class WebhookSecretRevokeRequestV2(BaseModel):
    """Request payload for webhook secret revocation."""

    model_config = ConfigDict(extra="forbid")

    version: WebhookSecretVersionContractV2 | None = None


class WebhookSubscriptionDataV2(BaseModel):
    """Non-secret webhook subscription payload used in read/list responses."""

    model_config = ConfigDict(extra="forbid")

    subscription_id: str
    callback_url: str
    event_types: list[WebhookEventTypeContractV2]
    enabled: bool
    created_at: datetime
    updated_at: datetime


class WebhookSecretRevealV2(BaseModel):
    """Secret material revealed once at create/rotate time."""

    model_config = ConfigDict(extra="forbid")

    version: WebhookSecretVersionContractV2
    value: str
    revealed_once: Literal[True] = True


class WebhookSecretOverlapV2(BaseModel):
    """Secret overlap metadata emitted by rotate/revoke operations."""

    model_config = ConfigDict(extra="forbid")

    active_and_next_valid: bool
    overlap_expires_at: datetime | None = None
    overlap_hours: int


class WebhookSubscriptionCreateResponseV2(BaseModel):
    """Response payload for webhook subscription create operation."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    subscription: WebhookSubscriptionDataV2
    secret: WebhookSecretRevealV2


class WebhookSubscriptionListResponseV2(BaseModel):
    """Response payload for webhook subscription listing."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    subscriptions: list[WebhookSubscriptionDataV2] = Field(default_factory=list)


class WebhookSubscriptionGetResponseV2(BaseModel):
    """Response payload for one webhook subscription read."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    subscription: WebhookSubscriptionDataV2


class WebhookSecretRotateResponseV2(BaseModel):
    """Response payload for webhook secret rotation."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    subscription_id: str
    secret: WebhookSecretRevealV2
    overlap: WebhookSecretOverlapV2


class WebhookSecretRevokeResponseV2(BaseModel):
    """Response payload for webhook secret revocation."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    subscription_id: str
    revoked_version: WebhookSecretVersionContractV2
    overlap: WebhookSecretOverlapV2


class ErrorEnvelopeV2(BaseModel):
    """Top-level error envelope for v2 responses."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"] = "v2"
    error: ErrorBody
