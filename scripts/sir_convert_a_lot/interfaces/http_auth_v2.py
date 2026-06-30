"""Shared v2 HTTP API key authentication helpers.

Purpose:
    Centralize v2 API-key authentication around the single supported service
    key so routes stay aligned with the simplified public/general conversion
    contract.

Relationships:
    - Imported by v2 HTTP route modules for request authentication.
    - Depends on `interfaces.http_app_state` to resolve the runtime config.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, TypeVar

from fastapi import Request

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request
from scripts.sir_convert_a_lot.interfaces.http_internal_identity_v2 import (
    INTERNAL_IDENTITY_CONTEXT_HEADER,
    INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER,
    INTERNAL_IDENTITY_KEY_ID_HEADER,
    INTERNAL_IDENTITY_SIGNATURE_HEADER,
    require_verified_internal_identity_v2,
)


@dataclass(frozen=True)
class AuthContextV2:
    """Resolved authentication context for one v2 HTTP request."""

    api_key: str
    owner_api_key_scope: str
    grants: frozenset[str] = frozenset()
    identity_context_verified: bool = False


class JobOwnedResourceV2(Protocol):
    """Protocol for job resources guarded by API-key owner scope."""

    job_id: str
    owner_api_key_scope: str


_JobOwnedResourceT = TypeVar("_JobOwnedResourceT", bound=JobOwnedResourceV2)


def build_owner_scope_v2() -> str:
    """Return the stable persisted owner scope for the single v2 service key."""

    return "service-api-key"


def internal_identity_headers_present_v2(request: Request) -> bool:
    """Return whether a request attempts signed internal identity authentication."""

    identity_headers = (
        INTERNAL_IDENTITY_CONTEXT_VERSION_HEADER,
        INTERNAL_IDENTITY_CONTEXT_HEADER,
        INTERNAL_IDENTITY_KEY_ID_HEADER,
        INTERNAL_IDENTITY_SIGNATURE_HEADER,
    )
    return any(request.headers.get(header_name) is not None for header_name in identity_headers)


def _job_not_found_error() -> ServiceError:
    return ServiceError(
        status_code=404,
        code="job_not_found",
        message="Job not found or expired.",
        retryable=False,
    )


def require_job_access_v2(
    *,
    auth_context: AuthContextV2,
    job: _JobOwnedResourceT | None,
    required_grant: str | None = None,
    access_denied_code: str = "job_access_denied",
) -> _JobOwnedResourceT:
    """Require that the authenticated caller owns the target job."""

    if job is None:
        raise _job_not_found_error()
    if job.owner_api_key_scope != auth_context.owner_api_key_scope:
        if (
            job.owner_api_key_scope.startswith("identity:v1:")
            or auth_context.identity_context_verified
        ):
            raise ServiceError(
                status_code=403,
                code=access_denied_code,
                message="Authenticated caller does not own this job.",
                retryable=False,
            )
        raise _job_not_found_error()
    if required_grant is not None and job.owner_api_key_scope.startswith("identity:v1:"):
        if required_grant not in auth_context.grants:
            raise ServiceError(
                status_code=403,
                code=access_denied_code,
                message="Authenticated caller is missing the required grant.",
                retryable=False,
                details={"required_grant": required_grant},
            )
    return job


def require_api_key_v2(
    request: Request,
    *,
    service_started_at: str,
) -> AuthContextV2:
    """Authenticate a v2 request against the single supported service key."""

    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    api_key = request.headers.get("X-API-Key")
    if api_key == runtime.config.api_key:
        return AuthContextV2(
            api_key=runtime.config.api_key,
            owner_api_key_scope=build_owner_scope_v2(),
        )

    raise ServiceError(
        status_code=401,
        code="auth_invalid_api_key",
        message="Missing or invalid X-API-Key.",
        retryable=False,
    )


def require_internal_identity_auth_context_v2(
    request: Request,
    *,
    service_started_at: str,
    required_grant: str,
    missing_grant_code: str = "auth_missing_internal_identity_grant",
) -> AuthContextV2:
    """Authenticate transport and signed HuleEdu identity for user-originated v2 work."""

    transport_context = require_api_key_v2(request, service_started_at=service_started_at)
    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    identity = require_verified_internal_identity_v2(
        headers=request.headers,
        config=runtime.config,
    )
    if required_grant not in identity.grants:
        raise ServiceError(
            status_code=403,
            code=missing_grant_code,
            message="Signed internal identity is missing the required Sir Convert grant.",
            retryable=False,
            details={"required_grant": required_grant},
        )
    return AuthContextV2(
        api_key=transport_context.api_key,
        owner_api_key_scope=identity.owner_scope,
        grants=identity.grants,
        identity_context_verified=True,
    )


def auth_context_for_job_access_v2(
    request: Request,
    *,
    service_started_at: str,
    job: JobOwnedResourceV2 | None,
    required_grant: str,
    missing_grant_code: str = "auth_missing_internal_identity_grant",
) -> AuthContextV2:
    """Resolve API-key or identity-derived auth according to persisted job ownership."""

    transport_context = require_api_key_v2(request, service_started_at=service_started_at)
    if job is None or not job.owner_api_key_scope.startswith("identity:v1:"):
        return transport_context
    return require_internal_identity_auth_context_v2(
        request,
        service_started_at=service_started_at,
        required_grant=required_grant,
        missing_grant_code=missing_grant_code,
    )
