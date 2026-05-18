"""Structured LLM hot-routing settings.

Purpose:
    Define the versioned runtime settings that let operators switch structured
    answer-key provider routing for newly admitted work without changing public
    job-spec contracts.

Relationships:
    - Supports ADR-0010 and Task 325 provider routing while staying below the
      conversion API contract surface.
    - Consumes provider profile IDs produced by the structured LLM catalog and
      OpenAI/local provider profile modules.
    - Emits metadata-only audit records that can be attached to service logs or
      operator reports without retaining prompts, item text, responses, or
      secrets.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from threading import Lock


class StructuredLLMInternalRouteClass(StrEnum):
    """Operator-internal route classes for structured provider routing."""

    OPERATOR_DEFAULT = "operator_default"
    OPERATOR_LOCAL_ONLY = "operator_local_only"
    OPERATOR_API_ONLY = "operator_api_only"
    OPERATOR_LOCAL_FIRST = "operator_local_first"


class StructuredLLMSettingsAuthoritySource(StrEnum):
    """Authority sources allowed to mutate hot provider routing settings."""

    INTERNAL_IDENTITY = "internal_identity"
    DEPLOYMENT_OPERATOR = "deployment_operator"


class StructuredLLMSettingsErrorCode(StrEnum):
    """Typed failures for hot settings mutations."""

    UNAUTHORIZED = "unauthorized"
    STALE_VERSION = "stale_version"
    UNKNOWN_PROVIDER_PROFILE = "unknown_provider_profile"
    REMOTE_PROVIDER_FORBIDDEN = "remote_provider_forbidden"
    INVALID_SETTINGS = "invalid_settings"


@dataclass(frozen=True)
class StructuredLLMSettingsMutationAuthority:
    """Resolved operator authority for one settings mutation attempt."""

    actor_id: str
    authority_source: StructuredLLMSettingsAuthoritySource
    internal_identity_verified: bool

    def __post_init__(self) -> None:
        if not self.actor_id.strip():
            raise ValueError("Structured LLM settings actor_id must be non-empty.")

    @property
    def can_mutate(self) -> bool:
        """Whether this authority can mutate hot provider routing settings."""

        if self.authority_source == StructuredLLMSettingsAuthoritySource.DEPLOYMENT_OPERATOR:
            return True
        return self.internal_identity_verified


@dataclass(frozen=True)
class StructuredLLMProviderRoutingSettings:
    """Versioned runtime route state for newly admitted structured LLM work."""

    version: int
    active_provider_profile_id: str
    allowed_internal_route_classes: frozenset[StructuredLLMInternalRouteClass]
    remote_provider_authorized: bool
    rollout_label: str
    operator_notes: str | None = None

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("Structured LLM settings version must be positive.")
        if not self.active_provider_profile_id.strip():
            raise ValueError("Structured LLM active provider profile must be non-empty.")
        if not self.allowed_internal_route_classes:
            raise ValueError("Structured LLM settings need at least one internal route class.")
        if not self.rollout_label.strip():
            raise ValueError("Structured LLM settings rollout_label must be non-empty.")


@dataclass(frozen=True)
class StructuredLLMSettingsAuditEvent:
    """Metadata-only audit event for a hot settings mutation attempt."""

    actor_id: str
    authority_source: StructuredLLMSettingsAuthoritySource
    previous_settings_version: int
    requested_settings_version: int
    active_settings_version: int
    selected_provider_profile: str
    allowed_internal_route_classes: tuple[str, ...]
    remote_provider_authorized: bool
    rollout_label: str
    timestamp: str
    correlation_id: str
    success: bool
    failure_code: StructuredLLMSettingsErrorCode | None = None


class StructuredLLMSettingsMutationError(Exception):
    """Settings mutation failure that leaves the active settings unchanged."""

    def __init__(
        self,
        *,
        failure_code: StructuredLLMSettingsErrorCode,
        message: str,
    ) -> None:
        super().__init__(message)
        self.failure_code = failure_code


class StructuredLLMHotSettingsStore:
    """Thread-safe in-memory holder for the active provider routing settings."""

    def __init__(
        self,
        *,
        initial_settings: StructuredLLMProviderRoutingSettings,
        known_provider_profile_ids: frozenset[str],
        remote_provider_profile_ids: frozenset[str],
    ) -> None:
        if initial_settings.active_provider_profile_id not in known_provider_profile_ids:
            raise ValueError("Initial structured LLM settings reference an unknown provider.")
        self._settings = initial_settings
        self._known_provider_profile_ids = known_provider_profile_ids
        self._remote_provider_profile_ids = remote_provider_profile_ids
        self._audit_events: list[StructuredLLMSettingsAuditEvent] = []
        self._lock = Lock()

    @property
    def active_settings(self) -> StructuredLLMProviderRoutingSettings:
        """Return the current active settings snapshot."""

        with self._lock:
            return self._settings

    @property
    def audit_events(self) -> tuple[StructuredLLMSettingsAuditEvent, ...]:
        """Return metadata-only settings mutation audit events."""

        with self._lock:
            return tuple(self._audit_events)

    def replace_settings(
        self,
        *,
        new_settings: StructuredLLMProviderRoutingSettings,
        authority: StructuredLLMSettingsMutationAuthority,
        timestamp: str,
        correlation_id: str,
    ) -> StructuredLLMSettingsAuditEvent:
        """Atomically replace active settings or fail closed with audit evidence."""

        with self._lock:
            previous = self._settings
            failure_code = self._validate_mutation(
                previous=previous,
                new_settings=new_settings,
                authority=authority,
            )
            if failure_code is not None:
                event = _audit_event(
                    previous=previous,
                    requested=new_settings,
                    active=previous,
                    authority=authority,
                    timestamp=timestamp,
                    correlation_id=correlation_id,
                    success=False,
                    failure_code=failure_code,
                )
                self._audit_events.append(event)
                raise StructuredLLMSettingsMutationError(
                    failure_code=failure_code,
                    message=f"Structured LLM settings mutation failed: {failure_code.value}.",
                )
            self._settings = new_settings
            event = _audit_event(
                previous=previous,
                requested=new_settings,
                active=new_settings,
                authority=authority,
                timestamp=timestamp,
                correlation_id=correlation_id,
                success=True,
                failure_code=None,
            )
            self._audit_events.append(event)
            return event

    def _validate_mutation(
        self,
        *,
        previous: StructuredLLMProviderRoutingSettings,
        new_settings: StructuredLLMProviderRoutingSettings,
        authority: StructuredLLMSettingsMutationAuthority,
    ) -> StructuredLLMSettingsErrorCode | None:
        if not authority.can_mutate:
            return StructuredLLMSettingsErrorCode.UNAUTHORIZED
        if new_settings.version <= previous.version:
            return StructuredLLMSettingsErrorCode.STALE_VERSION
        if new_settings.active_provider_profile_id not in self._known_provider_profile_ids:
            return StructuredLLMSettingsErrorCode.UNKNOWN_PROVIDER_PROFILE
        if (
            new_settings.active_provider_profile_id in self._remote_provider_profile_ids
            and not new_settings.remote_provider_authorized
        ):
            return StructuredLLMSettingsErrorCode.REMOTE_PROVIDER_FORBIDDEN
        return None


def _audit_event(
    *,
    previous: StructuredLLMProviderRoutingSettings,
    requested: StructuredLLMProviderRoutingSettings,
    active: StructuredLLMProviderRoutingSettings,
    authority: StructuredLLMSettingsMutationAuthority,
    timestamp: str,
    correlation_id: str,
    success: bool,
    failure_code: StructuredLLMSettingsErrorCode | None,
) -> StructuredLLMSettingsAuditEvent:
    return StructuredLLMSettingsAuditEvent(
        actor_id=authority.actor_id,
        authority_source=authority.authority_source,
        previous_settings_version=previous.version,
        requested_settings_version=requested.version,
        active_settings_version=active.version,
        selected_provider_profile=requested.active_provider_profile_id,
        allowed_internal_route_classes=tuple(
            sorted(route_class.value for route_class in requested.allowed_internal_route_classes)
        ),
        remote_provider_authorized=requested.remote_provider_authorized,
        rollout_label=requested.rollout_label,
        timestamp=timestamp,
        correlation_id=correlation_id,
        success=success,
        failure_code=failure_code,
    )
