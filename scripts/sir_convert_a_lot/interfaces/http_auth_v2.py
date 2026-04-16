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


@dataclass(frozen=True)
class AuthContextV2:
    """Resolved authentication context for one v2 HTTP request."""

    api_key: str
    owner_api_key_scope: str


class JobOwnedResourceV2(Protocol):
    """Protocol for job resources guarded by API-key owner scope."""

    job_id: str
    owner_api_key_scope: str


_JobOwnedResourceT = TypeVar("_JobOwnedResourceT", bound=JobOwnedResourceV2)


def build_owner_scope_v2() -> str:
    """Return the stable persisted owner scope for the single v2 service key."""

    return "service-api-key"


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
) -> _JobOwnedResourceT:
    """Require that the authenticated caller owns the target job."""

    if job is None:
        raise _job_not_found_error()
    if job.owner_api_key_scope != auth_context.owner_api_key_scope:
        raise _job_not_found_error()
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
