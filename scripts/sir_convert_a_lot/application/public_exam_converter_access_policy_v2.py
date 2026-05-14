"""Public Exam Converter access policy decisions.

Purpose:
    Evaluate public Exam Converter grant scope, ownership, and artifact-read
    authorization as pure decisions separate from token cryptography and HTTP.

Relationships:
    - Consumes public Exam Converter contract models from the application layer.
    - Produces decision objects for v2 HTTP adapters to map into route errors.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from scripts.sir_convert_a_lot.application.public_exam_converter_contract_v2 import (
    PUBLIC_EXAM_CONVERTER_CAPABILITY,
    PUBLIC_EXAM_CONVERTER_OUTPUT_FORMAT,
    PUBLIC_EXAM_CONVERTER_ROUTE_KEY,
    PUBLIC_EXAM_CONVERTER_SOURCE_APP,
    PUBLIC_EXAM_CONVERTER_SOURCE_FORMAT,
    PUBLIC_EXAM_CONVERTER_TARGETS,
    PUBLIC_OWNER_SCOPE_PREFIX,
    PublicArtifactReadLeaseV1,
    PublicConversionGrantV1,
)


class PublicGrantRejectionV2(StrEnum):
    """Stable public conversion grant rejection reasons."""

    UNSUPPORTED_VERSION = "unsupported_public_grant_version"
    INVALID_ISSUER = "invalid_public_grant_issuer"
    WRONG_AUDIENCE = "invalid_public_grant_audience"
    WRONG_CAPABILITY = "invalid_public_grant_capability"
    WRONG_ROUTE = "invalid_public_grant_route"
    WRONG_SOURCE_APP = "invalid_public_grant_source_app"
    WRONG_POLICY_VERSION = "invalid_public_grant_policy_version"
    BLANK_TARGET = "blank_public_grant_target"
    DUPLICATE_TARGET = "duplicate_public_grant_target"
    UNSUPPORTED_TARGET = "public_grant_contains_unsupported_target"
    REQUESTED_TARGET_NOT_COVERED = "public_grant_does_not_cover_requested_targets"
    INVALID_TIMESTAMPS = "invalid_public_grant_timestamps"
    TTL_EXCEEDED = "public_grant_ttl_exceeded"
    ISSUED_IN_FUTURE = "public_grant_issued_in_future"
    EXPIRED = "public_grant_expired"


class PublicArtifactLeaseRejectionV2(StrEnum):
    """Stable public artifact-read lease rejection reasons."""

    UNSUPPORTED_VERSION = "unsupported_public_artifact_read_lease_version"
    INVALID_ISSUER = "invalid_public_artifact_read_lease_issuer"
    WRONG_AUDIENCE = "invalid_public_artifact_read_lease_audience"
    PARENT_MISMATCH = "public_artifact_read_lease_parent_mismatch"
    JOB_MISMATCH = "public_artifact_read_lease_job_mismatch"
    ARTIFACT_MISMATCH = "public_artifact_read_lease_artifact_mismatch"
    OWNER_MISMATCH = "public_artifact_read_lease_owner_mismatch"
    PERSISTED_OWNER_MISMATCH = "public_artifact_read_lease_persisted_owner_mismatch"
    ROUTE_MISMATCH = "public_artifact_read_lease_route_mismatch"
    TARGET_SNAPSHOT_MISMATCH = "public_artifact_read_lease_target_snapshot_mismatch"
    POLICY_MISMATCH = "public_artifact_read_lease_policy_mismatch"
    INVALID_TIMESTAMPS = "invalid_public_artifact_read_lease_timestamps"
    ISSUED_IN_FUTURE = "public_artifact_read_lease_issued_in_future"
    EXPIRED = "public_artifact_read_lease_expired"


@dataclass(frozen=True)
class PublicExamConverterAccessProfileV2:
    """Policy profile for public Exam Converter grant and lease decisions."""

    grant_expected_issuer: str = "api_gateway_service"
    grant_expected_audience: str = "sir-convert-a-lot"
    grant_expected_policy_version: str = "public-exam-converter-2026-05-13"
    grant_max_ttl_seconds: int = 300
    allowed_clock_skew_seconds: int = 5
    artifact_read_lease_issuer: str = "sir-convert-a-lot"
    artifact_read_lease_audience: str = "sir-convert-public-artifact-read"
    artifact_read_lease_max_seconds: int = 1800


@dataclass(frozen=True)
class PublicOwnedJobSnapshotV2:
    """Small job ownership snapshot needed by public grant policy."""

    job_id: str
    owner_scope: str
    expires_at: datetime | None


@dataclass(frozen=True)
class PublicGrantEvaluationV2:
    """Public grant policy decision and derived ownership identity."""

    rejection: PublicGrantRejectionV2 | None
    owner_digest: str | None = None
    owner_scope: str | None = None


@dataclass(frozen=True)
class VerifiedPublicConversionGrantV2:
    """Verified public grant plus derived owner identity."""

    grant: PublicConversionGrantV1
    owner_digest: str
    owner_scope: str


@dataclass(frozen=True)
class _PublicGrantPolicyContext:
    grant: PublicConversionGrantV1
    profile: PublicExamConverterAccessProfileV2
    requested_targets: frozenset[str] | None
    now_ts: int


@dataclass(frozen=True)
class _PublicArtifactLeasePolicyContext:
    lease: PublicArtifactReadLeaseV1
    profile: PublicExamConverterAccessProfileV2
    verified_grant: VerifiedPublicConversionGrantV2
    job: PublicOwnedJobSnapshotV2
    artifact_key: str
    now_ts: int


def evaluate_public_conversion_grant_v2(
    *,
    grant: PublicConversionGrantV1,
    profile: PublicExamConverterAccessProfileV2,
    requested_targets: frozenset[str] | None,
    now_ts: int,
) -> PublicGrantEvaluationV2:
    """Evaluate grant policy without reading headers or raising HTTP errors."""

    context = _PublicGrantPolicyContext(
        grant=grant,
        profile=profile,
        requested_targets=requested_targets,
        now_ts=now_ts,
    )
    rejection = _first_grant_rejection(context)
    if rejection is not None:
        return PublicGrantEvaluationV2(rejection=rejection)
    owner_digest = public_owner_digest_v2(grant)
    return PublicGrantEvaluationV2(
        rejection=None,
        owner_digest=owner_digest,
        owner_scope=public_owner_scope_v2(owner_digest),
    )


def verified_public_conversion_grant_v2(
    *,
    grant: PublicConversionGrantV1,
    owner_digest: str,
    owner_scope: str,
) -> VerifiedPublicConversionGrantV2:
    """Create a verified grant value after policy evaluation succeeds."""

    return VerifiedPublicConversionGrantV2(
        grant=grant,
        owner_digest=owner_digest,
        owner_scope=owner_scope,
    )


def is_public_owner_scope_v2(owner_scope: str) -> bool:
    """Return whether a stored job owner scope belongs to a public grant."""

    return owner_scope.startswith(PUBLIC_OWNER_SCOPE_PREFIX)


def public_owner_scope_v2(owner_digest: str) -> str:
    """Return the persisted owner scope for a public owner digest."""

    return f"{PUBLIC_OWNER_SCOPE_PREFIX}{owner_digest}"


def evaluate_public_artifact_read_lease_v2(
    *,
    lease: PublicArtifactReadLeaseV1,
    profile: PublicExamConverterAccessProfileV2,
    verified_grant: VerifiedPublicConversionGrantV2,
    job: PublicOwnedJobSnapshotV2,
    artifact_key: str,
    now_ts: int,
) -> PublicArtifactLeaseRejectionV2 | None:
    """Evaluate whether one lease authorizes one public artifact read."""

    context = _PublicArtifactLeasePolicyContext(
        lease=lease,
        profile=profile,
        verified_grant=verified_grant,
        job=job,
        artifact_key=artifact_key,
        now_ts=now_ts,
    )
    return _first_lease_rejection(context)


def public_owner_digest_v2(grant: PublicConversionGrantV1) -> str:
    """Derive the deterministic public owner digest from verified grant fields."""

    owner_payload = {
        "owner_kind": "public_grant",
        "grant_version": grant.grant_version,
        "iss": grant.iss,
        "aud": grant.aud,
        "source_app": grant.source_app,
        "capability": grant.capability,
        "route_key": grant.route_key,
        "source_format": grant.source_format,
        "output_format": grant.output_format,
        "allowed_targets": sorted(grant.allowed_targets),
        "upload_digest": grant.upload_digest,
        "policy_version": grant.policy_version,
        "policy_profile_id": grant.policy_profile_id,
        "jti": grant.jti,
    }
    normalized = json.dumps(owner_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def public_artifact_read_lease_exp_seconds_v2(
    *,
    profile: PublicExamConverterAccessProfileV2,
    grant: PublicConversionGrantV1,
    job: PublicOwnedJobSnapshotV2,
    now_ts: int,
) -> int:
    """Return the lease expiry timestamp bounded by grant, job, and profile."""

    job_remaining_seconds = 86_400
    if job.expires_at is not None:
        job_remaining_seconds = int(job.expires_at.timestamp()) - now_ts
    lease_seconds = min(
        grant.artifact_read_lease_seconds,
        profile.artifact_read_lease_max_seconds,
        job_remaining_seconds,
    )
    return now_ts + max(lease_seconds, 0)


def _first_grant_rejection(
    context: _PublicGrantPolicyContext,
) -> PublicGrantRejectionV2 | None:
    for rule in (
        _grant_version_rejection,
        _grant_trust_rejection,
        _grant_route_rejection,
        _grant_target_rejection,
        _grant_timestamp_rejection,
    ):
        rejection = rule(context)
        if rejection is not None:
            return rejection
    return None


def _grant_version_rejection(
    context: _PublicGrantPolicyContext,
) -> PublicGrantRejectionV2 | None:
    if context.grant.grant_version != 1:
        return PublicGrantRejectionV2.UNSUPPORTED_VERSION
    return None


def _grant_trust_rejection(
    context: _PublicGrantPolicyContext,
) -> PublicGrantRejectionV2 | None:
    grant = context.grant
    profile = context.profile
    if grant.iss != profile.grant_expected_issuer:
        return PublicGrantRejectionV2.INVALID_ISSUER
    if grant.aud != profile.grant_expected_audience:
        return PublicGrantRejectionV2.WRONG_AUDIENCE
    if grant.policy_version != profile.grant_expected_policy_version:
        return PublicGrantRejectionV2.WRONG_POLICY_VERSION
    return None


def _grant_route_rejection(
    context: _PublicGrantPolicyContext,
) -> PublicGrantRejectionV2 | None:
    grant = context.grant
    if grant.capability != PUBLIC_EXAM_CONVERTER_CAPABILITY:
        return PublicGrantRejectionV2.WRONG_CAPABILITY
    if grant.source_app != PUBLIC_EXAM_CONVERTER_SOURCE_APP:
        return PublicGrantRejectionV2.WRONG_SOURCE_APP
    if not (
        grant.route_key == PUBLIC_EXAM_CONVERTER_ROUTE_KEY
        and grant.source_format == PUBLIC_EXAM_CONVERTER_SOURCE_FORMAT
        and grant.output_format == PUBLIC_EXAM_CONVERTER_OUTPUT_FORMAT
    ):
        return PublicGrantRejectionV2.WRONG_ROUTE
    return None


def _grant_target_rejection(
    context: _PublicGrantPolicyContext,
) -> PublicGrantRejectionV2 | None:
    normalized_targets = [target.strip() for target in context.grant.allowed_targets]
    if any(target == "" for target in normalized_targets):
        return PublicGrantRejectionV2.BLANK_TARGET
    if len(set(normalized_targets)) != len(normalized_targets):
        return PublicGrantRejectionV2.DUPLICATE_TARGET
    grant_targets = frozenset(normalized_targets)
    if not grant_targets.issubset(PUBLIC_EXAM_CONVERTER_TARGETS):
        return PublicGrantRejectionV2.UNSUPPORTED_TARGET
    if context.requested_targets is not None and not context.requested_targets.issubset(
        grant_targets
    ):
        return PublicGrantRejectionV2.REQUESTED_TARGET_NOT_COVERED
    return None


def _grant_timestamp_rejection(
    context: _PublicGrantPolicyContext,
) -> PublicGrantRejectionV2 | None:
    grant = context.grant
    profile = context.profile
    now_ts = context.now_ts
    if grant.exp < grant.iat:
        return PublicGrantRejectionV2.INVALID_TIMESTAMPS
    if grant.exp - grant.iat > profile.grant_max_ttl_seconds:
        return PublicGrantRejectionV2.TTL_EXCEEDED
    if grant.iat > now_ts + profile.allowed_clock_skew_seconds:
        return PublicGrantRejectionV2.ISSUED_IN_FUTURE
    if grant.exp <= now_ts - profile.allowed_clock_skew_seconds:
        return PublicGrantRejectionV2.EXPIRED
    return None


def _first_lease_rejection(
    context: _PublicArtifactLeasePolicyContext,
) -> PublicArtifactLeaseRejectionV2 | None:
    for rule in (
        _lease_token_identity_rejection,
        _lease_job_binding_rejection,
        _lease_route_policy_rejection,
        _lease_lifetime_rejection,
    ):
        rejection = rule(context)
        if rejection is not None:
            return rejection
    return None


def _lease_token_identity_rejection(
    context: _PublicArtifactLeasePolicyContext,
) -> PublicArtifactLeaseRejectionV2 | None:
    lease = context.lease
    profile = context.profile
    if lease.lease_version != 1:
        return PublicArtifactLeaseRejectionV2.UNSUPPORTED_VERSION
    if lease.iss != profile.artifact_read_lease_issuer:
        return PublicArtifactLeaseRejectionV2.INVALID_ISSUER
    if lease.aud != profile.artifact_read_lease_audience:
        return PublicArtifactLeaseRejectionV2.WRONG_AUDIENCE
    return None


def _lease_job_binding_rejection(
    context: _PublicArtifactLeasePolicyContext,
) -> PublicArtifactLeaseRejectionV2 | None:
    lease = context.lease
    verified_grant = context.verified_grant
    job = context.job
    if lease.parent_grant_jti != verified_grant.grant.jti:
        return PublicArtifactLeaseRejectionV2.PARENT_MISMATCH
    if lease.job_id != job.job_id:
        return PublicArtifactLeaseRejectionV2.JOB_MISMATCH
    if lease.artifact_key != context.artifact_key:
        return PublicArtifactLeaseRejectionV2.ARTIFACT_MISMATCH
    if lease.owner_digest != verified_grant.owner_digest:
        return PublicArtifactLeaseRejectionV2.OWNER_MISMATCH
    if public_owner_scope_v2(lease.owner_digest) != job.owner_scope:
        return PublicArtifactLeaseRejectionV2.PERSISTED_OWNER_MISMATCH
    return None


def _lease_route_policy_rejection(
    context: _PublicArtifactLeasePolicyContext,
) -> PublicArtifactLeaseRejectionV2 | None:
    lease = context.lease
    grant = context.verified_grant.grant
    if (
        lease.route_key != PUBLIC_EXAM_CONVERTER_ROUTE_KEY
        or lease.source_app != PUBLIC_EXAM_CONVERTER_SOURCE_APP
    ):
        return PublicArtifactLeaseRejectionV2.ROUTE_MISMATCH
    if frozenset(lease.allowed_targets_snapshot) != frozenset(grant.allowed_targets):
        return PublicArtifactLeaseRejectionV2.TARGET_SNAPSHOT_MISMATCH
    if lease.policy_version != grant.policy_version:
        return PublicArtifactLeaseRejectionV2.POLICY_MISMATCH
    return None


def _lease_lifetime_rejection(
    context: _PublicArtifactLeasePolicyContext,
) -> PublicArtifactLeaseRejectionV2 | None:
    lease = context.lease
    profile = context.profile
    now_ts = context.now_ts
    if lease.exp < lease.iat:
        return PublicArtifactLeaseRejectionV2.INVALID_TIMESTAMPS
    if lease.iat > now_ts + profile.allowed_clock_skew_seconds:
        return PublicArtifactLeaseRejectionV2.ISSUED_IN_FUTURE
    if lease.exp <= now_ts - profile.allowed_clock_skew_seconds:
        return PublicArtifactLeaseRejectionV2.EXPIRED
    return None
