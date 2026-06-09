"""Tests for structured LLM hot-routing settings.

Purpose:
    Prove HTML to PDF route5's hot-settings core is operator-gated, versioned, atomic, and
    metadata-only before it is wired to service HTTP routes.

Relationships:
    - Exercises `domain.structured_llm_hot_settings`.
    - Complements provider-profile tests without adding a public
      provider-route selector to the conversion job-spec contract.
"""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.domain.structured_llm_hot_settings import (
    StructuredLLMHotSettingsStore,
    StructuredLLMInternalRouteClass,
    StructuredLLMProviderRoutingSettings,
    StructuredLLMSettingsAuthoritySource,
    StructuredLLMSettingsErrorCode,
    StructuredLLMSettingsMutationAuthority,
    StructuredLLMSettingsMutationError,
)

LOCAL_PROVIDER_ID = "qwen36-llama-cpp-mtp"
OPENAI_PROVIDER_ID = "openai-gpt-5.4-mini-2026-03-17"


def test_hot_settings_replace_is_operator_authorized_and_audited() -> None:
    store = _store()

    event = store.replace_settings(
        new_settings=_settings(
            version=2,
            active_provider_profile_id=OPENAI_PROVIDER_ID,
            remote_provider_authorized=True,
            route_classes=frozenset({StructuredLLMInternalRouteClass.OPERATOR_API_ONLY}),
            rollout_label="openai-mini-eval",
        ),
        authority=_operator_authority(),
        timestamp="2026-05-18T12:00:00Z",
        correlation_id="corr-openai-hot-settings",
    )

    assert store.active_settings.version == 2
    assert store.active_settings.active_provider_profile_id == OPENAI_PROVIDER_ID
    assert event.success is True
    assert event.previous_settings_version == 1
    assert event.active_settings_version == 2
    assert event.selected_provider_profile == OPENAI_PROVIDER_ID
    assert event.allowed_internal_route_classes == ("operator_api_only",)
    assert event.remote_provider_authorized is True
    assert event.failure_code is None


def test_hot_settings_reject_unsigned_public_mutation_and_preserve_last_valid() -> None:
    store = _store()

    with pytest.raises(StructuredLLMSettingsMutationError) as exc_info:
        store.replace_settings(
            new_settings=_settings(
                version=2,
                active_provider_profile_id=OPENAI_PROVIDER_ID,
                remote_provider_authorized=True,
            ),
            authority=StructuredLLMSettingsMutationAuthority(
                actor_id="public-api-key-caller",
                authority_source=StructuredLLMSettingsAuthoritySource.INTERNAL_IDENTITY,
                internal_identity_verified=False,
            ),
            timestamp="2026-05-18T12:00:00Z",
            correlation_id="corr-public-denied",
        )

    assert exc_info.value.failure_code == StructuredLLMSettingsErrorCode.UNAUTHORIZED
    assert store.active_settings.version == 1
    assert store.active_settings.active_provider_profile_id == LOCAL_PROVIDER_ID
    failure_event = store.audit_events[-1]
    assert failure_event.success is False
    assert failure_event.active_settings_version == 1
    assert failure_event.failure_code == StructuredLLMSettingsErrorCode.UNAUTHORIZED


def test_hot_settings_reject_stale_version_and_unknown_provider() -> None:
    store = _store()

    with pytest.raises(StructuredLLMSettingsMutationError) as stale_exc:
        store.replace_settings(
            new_settings=_settings(version=1, active_provider_profile_id=LOCAL_PROVIDER_ID),
            authority=_operator_authority(),
            timestamp="2026-05-18T12:00:00Z",
            correlation_id="corr-stale",
        )

    assert stale_exc.value.failure_code == StructuredLLMSettingsErrorCode.STALE_VERSION
    assert store.active_settings.version == 1

    with pytest.raises(StructuredLLMSettingsMutationError) as unknown_exc:
        store.replace_settings(
            new_settings=_settings(version=2, active_provider_profile_id="missing-provider"),
            authority=_operator_authority(),
            timestamp="2026-05-18T12:00:01Z",
            correlation_id="corr-unknown",
        )

    assert unknown_exc.value.failure_code == (
        StructuredLLMSettingsErrorCode.UNKNOWN_PROVIDER_PROFILE
    )
    assert store.active_settings.version == 1


def test_hot_settings_reject_remote_profile_without_remote_authorization() -> None:
    store = _store()

    with pytest.raises(StructuredLLMSettingsMutationError) as exc_info:
        store.replace_settings(
            new_settings=_settings(
                version=2,
                active_provider_profile_id=OPENAI_PROVIDER_ID,
                remote_provider_authorized=False,
            ),
            authority=_operator_authority(),
            timestamp="2026-05-18T12:00:00Z",
            correlation_id="corr-remote-denied",
        )

    assert exc_info.value.failure_code == StructuredLLMSettingsErrorCode.REMOTE_PROVIDER_FORBIDDEN
    assert store.active_settings.active_provider_profile_id == LOCAL_PROVIDER_ID


def test_hot_settings_allow_deployment_operator_authority() -> None:
    store = _store()

    store.replace_settings(
        new_settings=_settings(
            version=2,
            active_provider_profile_id=LOCAL_PROVIDER_ID,
            route_classes=frozenset({StructuredLLMInternalRouteClass.OPERATOR_LOCAL_ONLY}),
        ),
        authority=StructuredLLMSettingsMutationAuthority(
            actor_id="deploy-script",
            authority_source=StructuredLLMSettingsAuthoritySource.DEPLOYMENT_OPERATOR,
            internal_identity_verified=False,
        ),
        timestamp="2026-05-18T12:00:00Z",
        correlation_id="corr-deploy",
    )

    assert store.active_settings.version == 2
    assert store.audit_events[-1].authority_source == (
        StructuredLLMSettingsAuthoritySource.DEPLOYMENT_OPERATOR
    )


def _store() -> StructuredLLMHotSettingsStore:
    return StructuredLLMHotSettingsStore(
        initial_settings=_settings(
            version=1,
            active_provider_profile_id=LOCAL_PROVIDER_ID,
            route_classes=frozenset({StructuredLLMInternalRouteClass.OPERATOR_DEFAULT}),
            rollout_label="local-default",
        ),
        known_provider_profile_ids=frozenset({LOCAL_PROVIDER_ID, OPENAI_PROVIDER_ID}),
        remote_provider_profile_ids=frozenset({OPENAI_PROVIDER_ID}),
    )


def _settings(
    *,
    version: int,
    active_provider_profile_id: str,
    route_classes: frozenset[StructuredLLMInternalRouteClass] = frozenset(
        {StructuredLLMInternalRouteClass.OPERATOR_DEFAULT}
    ),
    remote_provider_authorized: bool = False,
    rollout_label: str = "test-rollout",
) -> StructuredLLMProviderRoutingSettings:
    return StructuredLLMProviderRoutingSettings(
        version=version,
        active_provider_profile_id=active_provider_profile_id,
        allowed_internal_route_classes=route_classes,
        remote_provider_authorized=remote_provider_authorized,
        rollout_label=rollout_label,
    )


def _operator_authority() -> StructuredLLMSettingsMutationAuthority:
    return StructuredLLMSettingsMutationAuthority(
        actor_id="identity:v1:operator",
        authority_source=StructuredLLMSettingsAuthoritySource.INTERNAL_IDENTITY,
        internal_identity_verified=True,
    )
