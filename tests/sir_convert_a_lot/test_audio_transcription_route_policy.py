"""Behavioral tests for audio transcription route admission.

Purpose:
    Prove the planned audio route rejects unsupported inputs, invalid public
    options, exhausted capacity, and runtime registration before execution
    stories enable the route.

Relationships:
    - Exercises the audio transcription route-admission domain boundary.
    - Protects ADR-0013 and the audio converter contract before runtime route
      implementation begins.
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    AudioAdmissionQueueBehavior,
    AudioDiarizationMode,
    AudioDiarizationOptions,
    AudioInputProtocol,
    AudioTranscriptionCapacitySnapshot,
    AudioTranscriptionErrorCode,
    evaluate_audio_transcription_route_policy,
    required_audio_transcription_public_error_codes,
)
from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    build_create_job_route_registry_v2,
)
from tests.sir_convert_a_lot.audio_transcription_test_support import (
    probe,
    public_options_with,
    route_request,
)


def test_audio_transcription_names_concrete_reject_only_route_capacity_caps() -> None:
    caps = DEFAULT_AUDIO_TRANSCRIPTION_CAPS

    assert caps.max_active_stt_jobs_per_instance == 2
    assert caps.max_active_probe_normalization_workers == 2
    assert caps.max_active_sidecar_transcription_requests == 1
    assert caps.gpu_slots_per_instance == 1
    assert caps.queue_behavior == AudioAdmissionQueueBehavior.REJECT
    assert caps.capacity_error_code == AudioTranscriptionErrorCode.ROUTE_CAPACITY_EXCEEDED


@pytest.mark.parametrize(
    ("request_patch", "probe_patch", "capacity", "expected_code", "expected_details"),
    [
        (
            {"route_enabled": False},
            {},
            AudioTranscriptionCapacitySnapshot.empty(),
            AudioTranscriptionErrorCode.ROUTE_DISABLED,
            {},
        ),
        (
            {"input_protocol": AudioInputProtocol.REMOTE_URL},
            {},
            AudioTranscriptionCapacitySnapshot.empty(),
            AudioTranscriptionErrorCode.INPUT_PROTOCOL_UNSUPPORTED,
            {"protocol": "remote_url"},
        ),
        (
            {},
            {"container": "exe"},
            AudioTranscriptionCapacitySnapshot.empty(),
            AudioTranscriptionErrorCode.CONTAINER_UNSUPPORTED,
            {"container": "exe"},
        ),
        (
            {},
            {"has_audio_stream": False},
            AudioTranscriptionCapacitySnapshot.empty(),
            AudioTranscriptionErrorCode.STREAM_MISSING,
            {},
        ),
        (
            {"acceleration_policy": AccelerationPolicy.CPU_ONLY},
            {},
            AudioTranscriptionCapacitySnapshot.empty(),
            AudioTranscriptionErrorCode.GPU_REQUIRED_UNAVAILABLE,
            {"acceleration_policy": "cpu_only"},
        ),
        (
            {"retention_pin": True},
            {},
            AudioTranscriptionCapacitySnapshot.empty(),
            AudioTranscriptionErrorCode.RETENTION_PIN_UNSUPPORTED,
            {},
        ),
    ],
)
def test_route_policy_rejects_fail_closed_audio_admission_cases(
    request_patch: Mapping[str, object],
    probe_patch: Mapping[str, object],
    capacity: AudioTranscriptionCapacitySnapshot,
    expected_code: AudioTranscriptionErrorCode,
    expected_details: Mapping[str, str],
) -> None:
    decision = evaluate_audio_transcription_route_policy(
        request=route_request(**request_patch),
        probe=probe(**probe_patch),
        capacity=capacity,
        caps=DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    )

    assert decision.accepted is False
    assert decision.error_code == expected_code
    assert decision.details == expected_details


@pytest.mark.parametrize(
    ("capacity", "expected_exhausted_cap"),
    [
        (
            AudioTranscriptionCapacitySnapshot(
                active_stt_jobs=2,
                active_probe_normalization_workers=0,
                active_sidecar_transcription_requests=0,
                gpu_slots_in_use=0,
            ),
            "max_active_stt_jobs_per_instance",
        ),
        (
            AudioTranscriptionCapacitySnapshot(
                active_stt_jobs=0,
                active_probe_normalization_workers=2,
                active_sidecar_transcription_requests=0,
                gpu_slots_in_use=0,
            ),
            "max_active_probe_normalization_workers",
        ),
        (
            AudioTranscriptionCapacitySnapshot(
                active_stt_jobs=0,
                active_probe_normalization_workers=0,
                active_sidecar_transcription_requests=1,
                gpu_slots_in_use=0,
            ),
            "max_active_sidecar_transcription_requests",
        ),
        (
            AudioTranscriptionCapacitySnapshot(
                active_stt_jobs=0,
                active_probe_normalization_workers=0,
                active_sidecar_transcription_requests=0,
                gpu_slots_in_use=1,
            ),
            "gpu_slots_per_instance",
        ),
    ],
)
def test_route_policy_rejects_each_exhausted_audio_capacity_cap(
    capacity: AudioTranscriptionCapacitySnapshot,
    expected_exhausted_cap: str,
) -> None:
    decision = evaluate_audio_transcription_route_policy(
        request=route_request(),
        probe=probe(),
        capacity=capacity,
        caps=DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    )

    assert decision.accepted is False
    assert decision.error_code == AudioTranscriptionErrorCode.ROUTE_CAPACITY_EXCEEDED
    assert decision.details == {"exhausted_cap": expected_exhausted_cap}


@pytest.mark.parametrize("max_duration_seconds", [0, -1])
def test_route_policy_rejects_non_positive_public_duration_guardrail(
    max_duration_seconds: int,
) -> None:
    decision = evaluate_audio_transcription_route_policy(
        request=route_request(
            public_options=public_options_with(
                max_duration_seconds=max_duration_seconds,
                raw_option_keys=frozenset({"language", "diarization", "max_duration_seconds"}),
            )
        ),
        probe=probe(duration_seconds=120.0),
        capacity=AudioTranscriptionCapacitySnapshot.empty(),
        caps=DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    )

    assert decision.accepted is False
    assert decision.error_code == AudioTranscriptionErrorCode.DURATION_EXCEEDED
    assert decision.details == {
        "minimum_seconds": "1",
        "reason": "max_duration_seconds_must_be_positive",
    }


def test_route_policy_rejects_probe_duration_above_public_request_guardrail() -> None:
    decision = evaluate_audio_transcription_route_policy(
        request=route_request(
            public_options=public_options_with(
                max_duration_seconds=300,
                raw_option_keys=frozenset({"language", "diarization", "max_duration_seconds"}),
            )
        ),
        probe=probe(duration_seconds=301.0),
        capacity=AudioTranscriptionCapacitySnapshot.empty(),
        caps=DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    )

    assert decision.accepted is False
    assert decision.error_code == AudioTranscriptionErrorCode.DURATION_EXCEEDED
    assert decision.details == {"limit_seconds": "300"}


@pytest.mark.parametrize(
    "diarization",
    [
        AudioDiarizationOptions(mode=AudioDiarizationMode.AUTO, num_speakers=2),
        AudioDiarizationOptions(
            mode=AudioDiarizationMode.KNOWN_SPEAKER_COUNT,
            min_speakers=1,
            max_speakers=3,
        ),
        AudioDiarizationOptions(mode=AudioDiarizationMode.SPEAKER_RANGE, num_speakers=2),
        AudioDiarizationOptions(
            mode=AudioDiarizationMode.SPEAKER_RANGE,
            min_speakers=4,
            max_speakers=2,
        ),
    ],
)
def test_route_policy_rejects_invalid_diarization_options(
    diarization: AudioDiarizationOptions,
) -> None:
    decision = evaluate_audio_transcription_route_policy(
        request=route_request(
            public_options=public_options_with(
                diarization=diarization,
                raw_option_keys=frozenset({"language", "diarization", "output_artifacts"}),
            )
        ),
        probe=probe(),
        capacity=AudioTranscriptionCapacitySnapshot.empty(),
        caps=DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    )

    assert decision.accepted is False
    assert decision.error_code == AudioTranscriptionErrorCode.DIARIZATION_OPTIONS_INVALID


@pytest.mark.parametrize("forbidden_key", ["model_id", "beam_size", "vad_filter"])
def test_route_policy_rejects_public_backend_native_options(forbidden_key: str) -> None:
    decision = evaluate_audio_transcription_route_policy(
        request=route_request(
            public_options=public_options_with(
                raw_option_keys=frozenset({"language", "diarization", forbidden_key})
            )
        ),
        probe=probe(),
        capacity=AudioTranscriptionCapacitySnapshot.empty(),
        caps=DEFAULT_AUDIO_TRANSCRIPTION_CAPS,
    )

    assert decision.accepted is False
    assert decision.error_code == AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED
    assert decision.details == {"unsupported_option": forbidden_key}


def test_audio_public_error_code_set_covers_route_and_pipeline_failures() -> None:
    required_codes = required_audio_transcription_public_error_codes()

    assert {
        AudioTranscriptionErrorCode.ROUTE_DISABLED,
        AudioTranscriptionErrorCode.ROUTE_CAPACITY_EXCEEDED,
        AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE,
        AudioTranscriptionErrorCode.PROBE_FAILED,
        AudioTranscriptionErrorCode.NORMALIZATION_FAILED,
        AudioTranscriptionErrorCode.DIARIZATION_FAILED,
        AudioTranscriptionErrorCode.SEGMENT_ALIGNMENT_FAILED,
    }.issubset(required_codes)


def test_audio_transcription_policy_does_not_register_live_create_job_route() -> None:
    registry = build_create_job_route_registry_v2()

    assert all(key.source_format.value != "audio" for key in registry.registered_route_keys())
    assert all(
        key.output_format.value != "transcript_bundle" for key in registry.registered_route_keys()
    )
