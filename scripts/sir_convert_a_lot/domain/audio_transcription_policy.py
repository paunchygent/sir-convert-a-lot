"""Speech-to-text audio route policy and sidecar capability contracts.

Purpose:
    Define the domain boundary for audio transcription admission, route-level
    capacity caps, public option rejection, and STT sidecar readiness parsing.

Relationships:
    - Implements the policy slice authorized by the governed STT backlog lane
      and ADR-0013.
    - Complements `service_routes_v2` by keeping audio admission decisions
      provider-neutral before sidecar execution is wired.
    - Supplies deterministic public error codes for future HTTP and sidecar
      integration layers without importing codec, model, or infrastructure
      dependencies.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    DAY_ONE_LANGUAGE_VALUES,
    DAY_ONE_MEDIA_CONTAINERS,
    DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    FORBIDDEN_SIDECAR_CAPABILITY_KEYS,
    MAX_AUDIO_DURATION_SECONDS,
    MAX_AUDIO_UPLOAD_BYTES,
    STT_SIDECAR_CONTRACT_VERSION,
    AudioAdmissionQueueBehavior,
    AudioDiarizationMode,
    AudioDiarizationOptions,
    AudioInputProtocol,
    AudioProbeEvidence,
    AudioTranscriptionCapacitySnapshot,
    AudioTranscriptionCaps,
    AudioTranscriptionErrorCode,
    AudioTranscriptionPolicyDecision,
    AudioTranscriptionPublicOptions,
    AudioTranscriptionRouteRequest,
    SttSidecarReadinessDecision,
)
from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy

_PROFILE_LABEL_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
_NORMALIZED_AUDIO_CONTAINER = "wav"
_NORMALIZED_AUDIO_SAMPLE_RATE_HZ = 16_000
_NORMALIZED_AUDIO_CHANNELS = 1
_NORMALIZED_AUDIO_SAMPLE_FORMAT = "s16"

__all__ = (
    "DEFAULT_AUDIO_TRANSCRIPTION_CAPS",
    "AudioAdmissionQueueBehavior",
    "AudioDiarizationMode",
    "AudioDiarizationOptions",
    "AudioInputProtocol",
    "AudioProbeEvidence",
    "AudioTranscriptionCapacitySnapshot",
    "AudioTranscriptionCaps",
    "AudioTranscriptionErrorCode",
    "AudioTranscriptionPolicyDecision",
    "AudioTranscriptionPublicOptions",
    "AudioTranscriptionRouteRequest",
    "SttSidecarReadinessDecision",
    "evaluate_audio_transcription_route_policy",
    "evaluate_stt_sidecar_readiness",
    "required_audio_transcription_public_error_codes",
)


def evaluate_audio_transcription_route_policy(
    *,
    request: AudioTranscriptionRouteRequest,
    probe: AudioProbeEvidence,
    capacity: AudioTranscriptionCapacitySnapshot,
    caps: AudioTranscriptionCaps,
) -> AudioTranscriptionPolicyDecision:
    """Evaluate admission rules for the audio route."""

    if not request.route_enabled:
        return _reject(AudioTranscriptionErrorCode.ROUTE_DISABLED)
    if request.input_protocol != AudioInputProtocol.LOCAL_UPLOAD:
        return _reject(
            AudioTranscriptionErrorCode.INPUT_PROTOCOL_UNSUPPORTED,
            protocol=request.input_protocol.value,
        )
    option_failure = request.public_options.validation_failure()
    if option_failure is not None:
        code, details = option_failure
        return AudioTranscriptionPolicyDecision(
            accepted=False,
            error_code=code,
            details=details,
        )
    if request.acceleration_policy != AccelerationPolicy.GPU_REQUIRED:
        return _reject(
            AudioTranscriptionErrorCode.GPU_REQUIRED_UNAVAILABLE,
            acceleration_policy=request.acceleration_policy.value,
        )
    if request.retention_pin:
        return _reject(AudioTranscriptionErrorCode.RETENTION_PIN_UNSUPPORTED)
    if probe.upload_size_bytes > MAX_AUDIO_UPLOAD_BYTES:
        return _reject(
            AudioTranscriptionErrorCode.UPLOAD_SIZE_EXCEEDED,
            limit_bytes=str(MAX_AUDIO_UPLOAD_BYTES),
        )
    if not probe.has_audio_stream:
        return _reject(AudioTranscriptionErrorCode.STREAM_MISSING)
    normalized_container = probe.container.strip().lower().lstrip(".")
    if normalized_container not in DAY_ONE_MEDIA_CONTAINERS:
        return _reject(
            AudioTranscriptionErrorCode.CONTAINER_UNSUPPORTED,
            container=normalized_container,
        )
    effective_duration_limit_seconds = request.public_options.max_duration_seconds
    if probe.duration_seconds > effective_duration_limit_seconds:
        return _reject(
            AudioTranscriptionErrorCode.DURATION_EXCEEDED,
            limit_seconds=str(effective_duration_limit_seconds),
        )
    exhausted_cap = capacity.exhausted_by(caps)
    if exhausted_cap is not None:
        return _reject(caps.capacity_error_code, exhausted_cap=exhausted_cap)
    return AudioTranscriptionPolicyDecision(accepted=True)


def evaluate_stt_sidecar_readiness(
    *,
    health_payload: Mapping[str, object],
    capability_payload: Mapping[str, object],
) -> SttSidecarReadinessDecision:
    """Parse STT sidecar health/capability truth and fail closed on drift."""

    health_failure = _evaluate_health_payload(health_payload)
    if health_failure is not None:
        return health_failure
    if _contains_forbidden_capability_key(capability_payload):
        return _sidecar_unavailable("forbidden_backend_native_capability_key")

    if _string_at(capability_payload, "adapter_contract_version") != STT_SIDECAR_CONTRACT_VERSION:
        return _sidecar_unavailable("capability_contract_version_mismatch")

    runtime = _mapping_at(capability_payload, "runtime")
    if runtime is None:
        return _sidecar_unavailable("runtime_missing")
    runtime_failure = _evaluate_runtime_capability(runtime)
    if runtime_failure is not None:
        return runtime_failure

    media = _mapping_at(capability_payload, "media")
    if media is None:
        return _sidecar_unavailable("media_missing")
    media_failure = _evaluate_media_capability(media)
    if media_failure is not None:
        return media_failure

    transcription = _mapping_at(capability_payload, "transcription")
    diarization = _mapping_at(capability_payload, "diarization")
    if transcription is None or diarization is None:
        return _sidecar_unavailable("profile_sections_missing")
    profile_failure = _evaluate_profile_capabilities(
        transcription=transcription,
        diarization=diarization,
    )
    if profile_failure is not None:
        return profile_failure

    cache = _mapping_at(capability_payload, "cache")
    if cache is None:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_CACHE_UNAVAILABLE,
            reason="cache_missing",
        )
    cache_failure = _evaluate_cache_capability(cache)
    if cache_failure is not None:
        return cache_failure

    secrets = _mapping_at(capability_payload, "secrets")
    if secrets is None:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED,
            reason="secrets_missing",
        )
    secrets_failure = _evaluate_secret_capability(secrets)
    if secrets_failure is not None:
        return secrets_failure

    stt_profile = _string_at(transcription, "profile_label")
    diarization_profile = _string_at(diarization, "profile_label")
    if stt_profile is None or diarization_profile is None:
        return _sidecar_unavailable("profile_labels_missing")
    return SttSidecarReadinessDecision(
        ready=True,
        profile_labels={
            "stt_profile": stt_profile,
            "diarization_profile": diarization_profile,
        },
    )


def required_audio_transcription_public_error_codes() -> frozenset[AudioTranscriptionErrorCode]:
    """Return the public error-code authority for the audio route."""

    return frozenset(AudioTranscriptionErrorCode)


def _evaluate_health_payload(
    payload: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    if _string_at(payload, "status") != "ok":
        return _sidecar_unavailable("health_status_not_ok")
    if _bool_at(payload, "ready") is not True:
        return _sidecar_unavailable("health_not_ready")
    if _bool_at(payload, "gpu_ready") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.GPU_REQUIRED_UNAVAILABLE,
            reason="gpu_not_ready",
        )
    if _string_at(payload, "capability_version") != STT_SIDECAR_CONTRACT_VERSION:
        return _sidecar_unavailable("health_capability_version_mismatch")
    if _string_at(payload, "backend_profile_id") is None:
        return _sidecar_unavailable("health_backend_profile_missing")
    if _string_at(payload, "backend_version") is None:
        return _sidecar_unavailable("health_backend_version_missing")
    return None


def _evaluate_runtime_capability(
    runtime: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    if _string_at(runtime, "network_scope") != "internal_only":
        return _sidecar_unavailable("network_scope_not_internal_only")
    if _bool_at(runtime, "published_port_allowed") is not False:
        return _sidecar_unavailable("published_port_exposure")
    if _bool_at(runtime, "gpu_required") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.GPU_REQUIRED_UNAVAILABLE,
            reason="gpu_not_required_by_profile",
        )
    if _bool_at(runtime, "acceleration_ready") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.GPU_REQUIRED_UNAVAILABLE,
            reason="acceleration_not_ready",
        )
    if _string_at(runtime, "acceleration_family") is None:
        return _sidecar_unavailable("acceleration_family_missing")
    return None


def _evaluate_media_capability(
    media: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    max_upload_bytes = _int_at(media, "max_upload_bytes")
    if max_upload_bytes is None:
        return _sidecar_unavailable("max_upload_bytes_unsafe")
    if max_upload_bytes < MAX_AUDIO_UPLOAD_BYTES:
        return _sidecar_unavailable("max_upload_bytes_below_route_contract")
    max_duration_seconds = _int_at(media, "max_duration_seconds")
    if max_duration_seconds is None:
        return _sidecar_unavailable("max_duration_seconds_unsafe")
    if max_duration_seconds < MAX_AUDIO_DURATION_SECONDS:
        return _sidecar_unavailable("max_duration_seconds_below_route_contract")
    accepted_containers = _string_sequence_at(media, "accepted_containers")
    if accepted_containers is None:
        return _sidecar_unavailable("accepted_containers_missing")
    accepted_container_set = frozenset(accepted_containers)
    if not accepted_container_set.issubset(DAY_ONE_MEDIA_CONTAINERS):
        return _sidecar_unavailable("accepted_containers_not_bounded")
    if not DAY_ONE_MEDIA_CONTAINERS.issubset(accepted_container_set):
        return _sidecar_unavailable("accepted_containers_below_route_contract")
    input_protocols = _string_sequence_at(media, "input_protocols")
    if input_protocols != (AudioInputProtocol.LOCAL_UPLOAD.value,):
        return _sidecar_unavailable("input_protocols_not_local_upload_only")
    normalized_audio = _mapping_at(media, "normalized_audio")
    if normalized_audio is None:
        return _sidecar_unavailable("normalized_audio_missing")
    normalized_audio_failure = _evaluate_normalized_audio_capability(normalized_audio)
    if normalized_audio_failure is not None:
        return normalized_audio_failure
    return None


def _evaluate_normalized_audio_capability(
    normalized_audio: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    if _string_at(normalized_audio, "container") != _NORMALIZED_AUDIO_CONTAINER:
        return _sidecar_unavailable("normalized_audio_container_unsupported")
    if _int_at(normalized_audio, "sample_rate_hz") != _NORMALIZED_AUDIO_SAMPLE_RATE_HZ:
        return _sidecar_unavailable("normalized_audio_sample_rate_unsupported")
    if _int_at(normalized_audio, "channels") != _NORMALIZED_AUDIO_CHANNELS:
        return _sidecar_unavailable("normalized_audio_channels_unsupported")
    if _string_at(normalized_audio, "sample_format") != _NORMALIZED_AUDIO_SAMPLE_FORMAT:
        return _sidecar_unavailable("normalized_audio_sample_format_unsupported")
    return None


def _evaluate_profile_capabilities(
    *,
    transcription: Mapping[str, object],
    diarization: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    stt_profile = _string_at(transcription, "profile_label")
    diarization_profile = _string_at(diarization, "profile_label")
    if not _is_provider_neutral_label(stt_profile):
        return _sidecar_unavailable("transcription_profile_label_not_bounded")
    if not _is_provider_neutral_label(diarization_profile):
        return _sidecar_unavailable("diarization_profile_label_not_bounded")
    languages = _string_sequence_at(transcription, "languages")
    if languages is None or not DAY_ONE_LANGUAGE_VALUES.issubset(frozenset(languages)):
        return _sidecar_unavailable("day_one_languages_missing")
    modes = _string_sequence_at(diarization, "modes")
    if modes is None or not {
        AudioDiarizationMode.AUTO.value,
        AudioDiarizationMode.KNOWN_SPEAKER_COUNT.value,
        AudioDiarizationMode.SPEAKER_RANGE.value,
    }.issubset(frozenset(modes)):
        return _sidecar_unavailable("diarization_modes_missing")
    if _bool_at(diarization, "required_for_success") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.DIARIZATION_BACKEND_UNAVAILABLE,
            reason="diarization_not_required_for_success",
        )
    if _bool_at(diarization, "exclusive_speaker_segments_supported") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.DIARIZATION_BACKEND_UNAVAILABLE,
            reason="exclusive_speaker_segments_not_supported",
        )
    return None


def _evaluate_cache_capability(
    cache: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    for required_key in ("cache_family", "host_root", "container_root"):
        if _string_at(cache, required_key) is None:
            return _reject_readiness(
                AudioTranscriptionErrorCode.MODEL_CACHE_UNAVAILABLE,
                reason=f"{required_key}_missing",
            )
    if _bool_at(cache, "cache_roots_ready") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_CACHE_UNAVAILABLE,
            reason="cache_roots_not_ready",
        )
    if _bool_at(cache, "model_artifacts_present") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_CACHE_UNAVAILABLE,
            reason="model_artifacts_missing",
        )
    return None


def _evaluate_secret_capability(
    secrets: Mapping[str, object],
) -> SttSidecarReadinessDecision | None:
    required_secret_names = _string_sequence_at(secrets, "required_secret_names")
    if required_secret_names is None or not required_secret_names:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED,
            reason="required_secret_names_missing",
        )
    if _bool_at(secrets, "required_secrets_present") is not True:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED,
            reason="required_secrets_missing",
        )
    if _bool_at(secrets, "values_exposed") is not False:
        return _reject_readiness(
            AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED,
            reason="secret_values_exposed",
        )
    return None


def _reject(
    error_code: AudioTranscriptionErrorCode,
    **details: str,
) -> AudioTranscriptionPolicyDecision:
    return AudioTranscriptionPolicyDecision(
        accepted=False,
        error_code=error_code,
        details=dict(details),
    )


def _reject_readiness(
    error_code: AudioTranscriptionErrorCode,
    *,
    reason: str,
) -> SttSidecarReadinessDecision:
    return SttSidecarReadinessDecision(
        ready=False,
        error_code=error_code,
        details={"reason": reason},
    )


def _sidecar_unavailable(reason: str) -> SttSidecarReadinessDecision:
    return _reject_readiness(
        AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE,
        reason=reason,
    )


def _mapping_at(payload: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        return None
    normalized: dict[str, object] = {}
    for nested_key, nested_value in value.items():
        if not isinstance(nested_key, str):
            return None
        normalized[nested_key] = nested_value
    return normalized


def _string_at(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _bool_at(payload: Mapping[str, object], key: str) -> bool | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    return None


def _int_at(payload: Mapping[str, object], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _string_sequence_at(payload: Mapping[str, object], key: str) -> tuple[str, ...] | None:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        return None
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or item.strip() == "":
            return None
        normalized.append(item)
    return tuple(normalized)


def _contains_forbidden_capability_key(value: object) -> bool:
    if isinstance(value, Mapping):
        for nested_key, nested_value in value.items():
            if isinstance(nested_key, str) and nested_key in FORBIDDEN_SIDECAR_CAPABILITY_KEYS:
                return True
            if _contains_forbidden_capability_key(nested_value):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return any(_contains_forbidden_capability_key(item) for item in value)
    return False


def _is_provider_neutral_label(value: str | None) -> bool:
    if value is None:
        return False
    return _PROFILE_LABEL_PATTERN.fullmatch(value) is not None
