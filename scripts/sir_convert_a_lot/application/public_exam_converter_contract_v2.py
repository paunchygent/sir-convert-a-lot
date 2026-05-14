"""Public Exam Converter grant and artifact lease contracts.

Purpose:
    Define JSON payload shapes for the narrow public Exam Converter grant lane
    without embedding token verification, route policy, or HTTP error mapping.

Relationships:
    - Used by public Exam Converter access policy and HTTP adapters.
    - Mirrors HuleEdu `PublicConversionGrantV1` and Sir Convert
      `PublicArtifactReadLeaseV1` docs-as-code contracts.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

PUBLIC_CONVERSION_GRANT_HEADER = "X-Public-Conversion-Grant"
PUBLIC_ARTIFACT_READ_LEASE_HEADER = "X-Public-Artifact-Read-Lease"
PUBLIC_OWNER_SCOPE_PREFIX = "public_grant:v1:sha256:"
BUNDLE_MANIFEST_ARTIFACT_KEY = "bundle_manifest"

PUBLIC_EXAM_CONVERTER_SOURCE_APP = "skriptoteket"
PUBLIC_EXAM_CONVERTER_CAPABILITY = "documents.conversion_hub.exam_converter"
PUBLIC_EXAM_CONVERTER_ROUTE_KEY = "digiexam_dxe_to_examnet_migration_bundle"
PUBLIC_EXAM_CONVERTER_SOURCE_FORMAT = "digiexam_dxe"
PUBLIC_EXAM_CONVERTER_OUTPUT_FORMAT = "examnet_migration_bundle"
PUBLIC_EXAM_CONVERTER_TARGETS = frozenset({"examnet_pdf", "qti_package"})


class PublicConversionGrantV1(BaseModel):
    """HuleEdu-signed public conversion grant payload."""

    model_config = ConfigDict(extra="forbid")

    grant_version: int
    iss: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    source_app: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    route_key: str = Field(min_length=1)
    source_format: str = Field(min_length=1)
    output_format: str = Field(min_length=1)
    allowed_targets: list[str] = Field(min_length=1)
    upload_digest: str = Field(min_length=8)
    policy_version: str = Field(min_length=1)
    policy_profile_id: str = Field(min_length=1)
    max_upload_bytes: int = Field(gt=0)
    allowed_mime_types: list[str] = Field(min_length=1)
    request_time_budget_seconds: int = Field(gt=0)
    artifact_ttl_seconds: int = Field(gt=0)
    artifact_read_lease_seconds: int = Field(gt=0)
    rate_limit_profile_id: str = Field(min_length=1)
    concurrency_profile_id: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)
    iat: int
    exp: int
    jti: str = Field(min_length=1)


class PublicArtifactReadLeaseV1(BaseModel):
    """Sir Convert-signed public artifact-read lease payload."""

    model_config = ConfigDict(extra="forbid")

    lease_version: int
    iss: str = Field(min_length=1)
    aud: str = Field(min_length=1)
    parent_grant_jti: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    artifact_key: str = Field(min_length=1)
    owner_digest: str = Field(min_length=64, max_length=64)
    route_key: str = Field(min_length=1)
    source_app: str = Field(min_length=1)
    allowed_targets_snapshot: list[str] = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    iat: int
    exp: int
    jti: str = Field(min_length=1)
    correlation_id: str = Field(min_length=1)


class PublicArtifactReadLeaseResponseV2(BaseModel):
    """Response fragment carrying a server-to-server artifact-read lease."""

    token: str = Field(min_length=1)
    artifact_key: str = Field(min_length=1)
    expires_at: datetime
