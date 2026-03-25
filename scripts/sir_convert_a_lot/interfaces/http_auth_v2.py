"""Shared v2 HTTP API key authentication helpers.

Purpose:
    Centralize v2 API-key authentication so routes consistently recognize the
    public service key and the explicit internal adapter key lane.

Relationships:
    - Imported by v2 HTTP route modules for request authentication.
    - Depends on `interfaces.http_app_state` to resolve the runtime config.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeVar

from fastapi import Request

from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_app_state import runtime_v2_for_request


class AuthLaneV2(StrEnum):
    """Supported API-key lanes for v2 HTTP requests."""

    PUBLIC = "public"
    INTERNAL = "internal"


@dataclass(frozen=True)
class AuthContextV2:
    """Resolved authentication context for one v2 HTTP request."""

    api_key: str
    lane: AuthLaneV2
    owner_api_key_scope: str

    @property
    def allows_trusted_app_bundle(self) -> bool:
        """Return whether this request can use trusted HTML bundle mode."""

        return self.lane is AuthLaneV2.INTERNAL


class JobOwnedResourceV2(Protocol):
    """Protocol for job resources guarded by API-key owner scope."""

    job_id: str
    owner_auth_lane: str
    owner_api_key_scope: str | None


_JobOwnedResourceT = TypeVar("_JobOwnedResourceT", bound=JobOwnedResourceV2)


def build_owner_scope_v2(*, lane: AuthLaneV2) -> str:
    """Return the stable persisted owner scope for one auth lane."""

    if lane is AuthLaneV2.PUBLIC:
        return "public-api-lane"
    return "internal-api-lane"


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
    if job.owner_api_key_scope is None:
        if auth_context.lane is AuthLaneV2.PUBLIC:
            return job
        raise _job_not_found_error()
    if job.owner_auth_lane != auth_context.lane.value:
        raise _job_not_found_error()
    if job.owner_api_key_scope != auth_context.owner_api_key_scope:
        raise _job_not_found_error()
    return job


def require_api_key_v2(
    request: Request,
    *,
    service_started_at: str,
    allow_internal_api_key: bool = False,
) -> AuthContextV2:
    """Authenticate a v2 request against the public or internal API-key lane."""

    runtime = runtime_v2_for_request(request, utc_now_iso=service_started_at)
    api_key = request.headers.get("X-API-Key")
    if api_key == runtime.config.api_key:
        return AuthContextV2(
            api_key=runtime.config.api_key,
            lane=AuthLaneV2.PUBLIC,
            owner_api_key_scope=build_owner_scope_v2(lane=AuthLaneV2.PUBLIC),
        )

    internal_api_key = runtime.config.internal_api_key
    if allow_internal_api_key and internal_api_key is not None and api_key == internal_api_key:
        return AuthContextV2(
            api_key=internal_api_key,
            lane=AuthLaneV2.INTERNAL,
            owner_api_key_scope=build_owner_scope_v2(lane=AuthLaneV2.INTERNAL),
        )

    raise ServiceError(
        status_code=401,
        code="auth_invalid_api_key",
        message="Missing or invalid X-API-Key.",
        retryable=False,
    )
