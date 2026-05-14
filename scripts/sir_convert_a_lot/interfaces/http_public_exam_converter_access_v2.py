"""HTTP adapter for public Exam Converter access.

Purpose:
    Bridge FastAPI requests to the public Exam Converter contract, token codec,
    and pure policy decisions while keeping route handlers thin.

Relationships:
    - Used by v2 job and artifact routes.
    - Maps public grant and artifact-read policy decisions into service error
      envelopes at the web boundary.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Request
from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.public_exam_converter_access_policy_v2 import (
    PublicGrantRejectionV2,
    PublicOwnedJobSnapshotV2,
    VerifiedPublicConversionGrantV2,
    evaluate_public_artifact_read_lease_v2,
    evaluate_public_conversion_grant_v2,
    is_public_owner_scope_v2,
    public_artifact_read_lease_exp_seconds_v2,
    verified_public_conversion_grant_v2,
)
from scripts.sir_convert_a_lot.application.public_exam_converter_contract_v2 import (
    BUNDLE_MANIFEST_ARTIFACT_KEY,
    PUBLIC_ARTIFACT_READ_LEASE_HEADER,
    PUBLIC_CONVERSION_GRANT_HEADER,
    PUBLIC_EXAM_CONVERTER_ROUTE_KEY,
    PUBLIC_EXAM_CONVERTER_SOURCE_APP,
    PublicArtifactReadLeaseResponseV2,
    PublicArtifactReadLeaseV1,
    PublicConversionGrantV1,
)
from scripts.sir_convert_a_lot.infrastructure.public_token_codec_v2 import (
    PublicTokenCodecError,
    read_hs256_public_token_v2,
    read_rs256_public_token_v2,
    sign_hs256_public_token_v2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import (
    PublicExamConverterRuntimeAccessConfig,
    ServiceError,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_auth_v2 import require_api_key_v2


def public_conversion_grant_header_present_v2(request: Request) -> bool:
    """Return whether the request carries a public conversion grant header."""

    value = request.headers.get(PUBLIC_CONVERSION_GRANT_HEADER)
    return value is not None and value.strip() != ""


def public_bundle_manifest_artifact_key_v2() -> str:
    """Return the public artifact key used for bundle manifest leases."""

    return BUNDLE_MANIFEST_ARTIFACT_KEY


def is_public_job_v2(job: StoredJobV2 | None) -> bool:
    """Return whether the job is owned by a public conversion grant."""

    return job is not None and is_public_owner_scope_v2(job.owner_api_key_scope)


def require_public_create_access_v2(
    *,
    request: Request,
    service_started_at: str,
    requested_targets: frozenset[str],
) -> VerifiedPublicConversionGrantV2:
    """Require API key transport and a valid public conversion grant for create."""

    require_api_key_v2(request, service_started_at=service_started_at)
    return _verified_grant_from_request(
        request=request,
        service_started_at=service_started_at,
        requested_targets=requested_targets,
    )


def require_public_job_access_v2(
    *,
    request: Request,
    service_started_at: str,
    job: StoredJobV2,
) -> VerifiedPublicConversionGrantV2:
    """Require that the request's public grant owns the stored public job."""

    require_api_key_v2(request, service_started_at=service_started_at)
    verified_grant = _verified_grant_from_request(
        request=request,
        service_started_at=service_started_at,
        requested_targets=None,
    )
    if verified_grant.owner_scope != job.owner_api_key_scope:
        raise ServiceError(
            status_code=403,
            code="public_grant_ownership_required",
            message="Verified public conversion grant does not own this job.",
            retryable=False,
        )
    return verified_grant


def issue_public_artifact_read_lease_fragment_v2(
    *,
    request: Request,
    service_started_at: str,
    verified_grant: VerifiedPublicConversionGrantV2,
    job: StoredJobV2,
    artifact_key: str,
) -> dict[str, object]:
    """Issue one public artifact-read lease response fragment."""

    access = _public_access_config(request=request, service_started_at=service_started_at)
    secret = _artifact_read_secret(access)
    now_ts = int(time.time())
    job_snapshot = _public_job_snapshot(job)
    exp = public_artifact_read_lease_exp_seconds_v2(
        profile=access.profile,
        grant=verified_grant.grant,
        job=job_snapshot,
        now_ts=now_ts,
    )
    if exp <= now_ts:
        raise ServiceError(
            status_code=401,
            code="public_artifact_read_lease_denied",
            message="Public artifact-read lease cannot outlive artifact retention.",
            retryable=False,
            details={"reason": "public_artifact_retention_expired"},
        )
    token = sign_hs256_public_token_v2(
        payload=_artifact_read_lease_payload(
            verified_grant=verified_grant,
            job=job,
            artifact_key=artifact_key,
            issuer=access.profile.artifact_read_lease_issuer,
            audience=access.profile.artifact_read_lease_audience,
            issued_at=now_ts,
            expires_at=exp,
        ),
        secret=secret,
    )
    fragment = PublicArtifactReadLeaseResponseV2(
        token=token,
        artifact_key=artifact_key,
        expires_at=datetime.fromtimestamp(exp, tz=UTC),
    )
    return fragment.model_dump(mode="json")


def require_public_artifact_read_lease_v2(
    *,
    request: Request,
    service_started_at: str,
    verified_grant: VerifiedPublicConversionGrantV2,
    job: StoredJobV2,
    artifact_key: str,
) -> None:
    """Require a valid public artifact-read lease for one requested artifact."""

    raw_lease = request.headers.get(PUBLIC_ARTIFACT_READ_LEASE_HEADER)
    if raw_lease is None or raw_lease.strip() == "":
        raise ServiceError(
            status_code=401,
            code="public_artifact_read_lease_required",
            message="Public artifact reads require a signed artifact-read lease.",
            retryable=False,
        )
    access = _public_access_config(request=request, service_started_at=service_started_at)
    try:
        claims = read_hs256_public_token_v2(
            token=raw_lease.strip(),
            secret=_artifact_read_secret(access),
        )
        lease = PublicArtifactReadLeaseV1.model_validate(claims)
    except PublicTokenCodecError as exc:
        raise _artifact_read_lease_denied(exc.reason) from exc
    except ValidationError as exc:
        raise _artifact_read_lease_denied(
            "invalid_public_artifact_read_lease_payload",
            validation_error=exc.errors(include_context=False),
        ) from exc

    rejection = evaluate_public_artifact_read_lease_v2(
        lease=lease,
        profile=access.profile,
        verified_grant=verified_grant,
        job=_public_job_snapshot(job),
        artifact_key=artifact_key,
        now_ts=int(time.time()),
    )
    if rejection is not None:
        raise _artifact_read_lease_denied(rejection.value)


def _verified_grant_from_request(
    *,
    request: Request,
    service_started_at: str,
    requested_targets: frozenset[str] | None,
) -> VerifiedPublicConversionGrantV2:
    raw_grant = request.headers.get(PUBLIC_CONVERSION_GRANT_HEADER)
    if raw_grant is None or raw_grant.strip() == "":
        raise ServiceError(
            status_code=401,
            code="public_grant_required",
            message="Public Exam Converter requests require a HuleEdu grant.",
            retryable=False,
        )
    access = _public_access_config(request=request, service_started_at=service_started_at)
    try:
        claims = read_rs256_public_token_v2(
            token=raw_grant.strip(),
            public_keys=access.grant_public_keys,
        )
        grant = PublicConversionGrantV1.model_validate(claims)
    except PublicTokenCodecError as exc:
        raise _public_grant_untrusted(exc.reason) from exc
    except ValidationError as exc:
        raise _public_grant_untrusted(
            "invalid_public_grant_payload",
            validation_error=exc.errors(include_context=False),
        ) from exc

    evaluation = evaluate_public_conversion_grant_v2(
        grant=grant,
        profile=access.profile,
        requested_targets=requested_targets,
        now_ts=int(time.time()),
    )
    if evaluation.rejection is not None:
        raise _public_grant_rejected(evaluation.rejection)
    if evaluation.owner_digest is None or evaluation.owner_scope is None:
        raise _public_grant_untrusted("missing_public_grant_owner_digest")
    return verified_public_conversion_grant_v2(
        grant=grant,
        owner_digest=evaluation.owner_digest,
        owner_scope=evaluation.owner_scope,
    )


def _public_access_config(
    *,
    request: Request,
    service_started_at: str,
) -> PublicExamConverterRuntimeAccessConfig:
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    access = runtime.config.public_exam_converter_access
    if access is None:
        raise ServiceError(
            status_code=503,
            code="public_exam_converter_access_not_configured",
            message="Public Exam Converter access is not configured.",
            retryable=True,
        )
    return access


def _public_grant_rejected(rejection: PublicGrantRejectionV2) -> ServiceError:
    code = _public_grant_error_code(rejection)
    status_code = 401 if code in {"public_grant_untrusted", "public_grant_expired"} else 403
    return ServiceError(
        status_code=status_code,
        code=code,
        message="Missing, invalid, or unauthorized public conversion grant.",
        retryable=False,
        details={"reason": rejection.value},
    )


def _public_grant_error_code(rejection: PublicGrantRejectionV2) -> str:
    if rejection == PublicGrantRejectionV2.EXPIRED:
        return "public_grant_expired"
    if rejection == PublicGrantRejectionV2.WRONG_AUDIENCE:
        return "public_grant_wrong_audience"
    if rejection == PublicGrantRejectionV2.WRONG_CAPABILITY:
        return "public_grant_wrong_capability"
    if rejection in {
        PublicGrantRejectionV2.BLANK_TARGET,
        PublicGrantRejectionV2.DUPLICATE_TARGET,
        PublicGrantRejectionV2.UNSUPPORTED_TARGET,
        PublicGrantRejectionV2.REQUESTED_TARGET_NOT_COVERED,
    }:
        return "public_grant_target_not_allowed"
    if rejection in {
        PublicGrantRejectionV2.WRONG_ROUTE,
        PublicGrantRejectionV2.WRONG_SOURCE_APP,
        PublicGrantRejectionV2.WRONG_POLICY_VERSION,
    }:
        return "public_grant_wrong_route"
    return "public_grant_untrusted"


def _public_grant_untrusted(
    reason: str,
    *,
    validation_error: object | None = None,
) -> ServiceError:
    details: dict[str, object] = {"reason": reason}
    if validation_error is not None:
        details["validation_error"] = validation_error
    return ServiceError(
        status_code=401,
        code="public_grant_untrusted",
        message="Signed public conversion grant is invalid.",
        retryable=False,
        details=details,
    )


def _artifact_read_lease_denied(
    reason: str,
    *,
    validation_error: object | None = None,
) -> ServiceError:
    details: dict[str, object] = {"reason": reason}
    if validation_error is not None:
        details["validation_error"] = validation_error
    return ServiceError(
        status_code=403,
        code="public_artifact_read_lease_denied",
        message="Public artifact-read lease does not authorize this artifact read.",
        retryable=False,
        details=details,
    )


def _artifact_read_secret(access: PublicExamConverterRuntimeAccessConfig) -> str:
    secret = access.artifact_read_lease_secret
    if secret is None or secret.strip() == "":
        raise ServiceError(
            status_code=503,
            code="public_artifact_read_lease_not_configured",
            message="Public artifact-read lease signing is not configured.",
            retryable=True,
        )
    return secret.strip()


def _public_job_snapshot(job: StoredJobV2) -> PublicOwnedJobSnapshotV2:
    return PublicOwnedJobSnapshotV2(
        job_id=job.job_id,
        owner_scope=job.owner_api_key_scope,
        expires_at=job.expires_at,
    )


def _artifact_read_lease_payload(
    *,
    verified_grant: VerifiedPublicConversionGrantV2,
    job: StoredJobV2,
    artifact_key: str,
    issuer: str,
    audience: str,
    issued_at: int,
    expires_at: int,
) -> dict[str, object]:
    return {
        "lease_version": 1,
        "iss": issuer,
        "aud": audience,
        "parent_grant_jti": verified_grant.grant.jti,
        "job_id": job.job_id,
        "artifact_key": artifact_key,
        "owner_digest": verified_grant.owner_digest,
        "route_key": PUBLIC_EXAM_CONVERTER_ROUTE_KEY,
        "source_app": PUBLIC_EXAM_CONVERTER_SOURCE_APP,
        "allowed_targets_snapshot": list(verified_grant.grant.allowed_targets),
        "policy_version": verified_grant.grant.policy_version,
        "iat": issued_at,
        "exp": expires_at,
        "jti": f"parl_{uuid4().hex}",
        "correlation_id": verified_grant.grant.correlation_id,
    }
