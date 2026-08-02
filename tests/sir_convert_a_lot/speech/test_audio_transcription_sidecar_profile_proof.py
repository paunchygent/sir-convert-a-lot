"""Audio transcription sidecar profile-proof behavior.

Purpose:
    Prove that live speech-to-text sidecar benchmark evidence is complete,
    content-safe, and route-safe before profile selection can unblock audio
    transcript execution.

Relationships:
    - Exercises the devops profile-proof reporting boundary for Hemma STT
      benchmark evidence.
    - Reuses the domain profile-selection evidence model without importing
      speech-to-text, diarization, Hugging Face, FFmpeg, or sidecar runtimes.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

import pytest

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_contracts import (
    AudioTranscriptionBackendDependencyEvidence,
    AudioTranscriptionBatchLifecycleEvidence,
    AudioTranscriptionCodecBoundaryEvidence,
    AudioTranscriptionHuggingFaceReadinessEvidence,
    AudioTranscriptionSidecarLaunchEvidence,
    AudioTranscriptionSidecarProfileProofEvidence,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_proof import (
    build_live_profile_proof_report,
    write_live_profile_proof_report,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_benchmark_profiles import (
    AudioBenchmarkContentSafetyEvidence,
    AudioBenchmarkEvidence,
    AudioBenchmarkLanguageEvidence,
    AudioBenchmarkProfileLabels,
    AudioBenchmarkRuntimeEvidence,
    AudioBenchmarkSpeakerHintEvidence,
    AudioBenchmarkSyntheticDurationEvidence,
    BenchmarkBackendFamily,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)


def test_live_profile_proof_accepts_complete_sanitized_sidecar_evidence(
    tmp_path: Path,
) -> None:
    evidence = complete_sidecar_profile_proof()

    report = build_live_profile_proof_report(evidence)
    json_path, markdown_path = write_live_profile_proof_report(report, output_root=tmp_path)

    assert report["schema_version"] == "audio_transcription_sidecar_profile_proof_v1"
    assert report["proof_ready"] is True
    assert report["profile_selection"] == {
        "selected": True,
        "stt_profile": "stt_sv_en_primary",
        "diarization_profile": "diarization_sv_en_primary",
        "rejection_reasons": (),
    }
    assert report["required_evidence"] == {
        "live_hemma_evidence": True,
        "sidecar_launch": True,
        "codec_boundary": True,
        "backend_dependencies": True,
        "huggingface_readiness": True,
        "swedish_fixture": True,
        "english_fixture": True,
        "exact_speaker_count": True,
        "min_max_speaker_range": True,
        "gpu_required_execution": True,
        "batch_lifecycle": True,
        "content_safety": True,
        "route_unregistered": True,
    }
    assert report["sidecar_launch"]["image_name"] == "sir-convert-a-lot-stt-sidecar"
    assert report["sidecar_launch"]["build_contract"] == "buildkit"
    assert report["codec_boundary"]["supported_audio_codecs"] == (
        "aac",
        "flac",
        "m4a",
        "mp3",
        "ogg",
        "opus",
        "wav",
    )
    assert report["route_registration"]["audio_transcript_bundle_registered"] is False

    persisted_text = json_path.read_text(encoding="utf-8")
    persisted_text += markdown_path.read_text(encoding="utf-8")
    parsed = json.loads(json_path.read_text(encoding="utf-8"))

    assert parsed["proof_ready"] is True
    assert json_path == tmp_path / "profile-proof.json"
    assert markdown_path == tmp_path / "profile-proof.md"
    assert "hf_private_token_value" not in persisted_text
    assert "provider/private-stt-model" not in persisted_text
    assert "provider/private-diarization-model" not in persisted_text
    assert "hej detta ska inte synas" not in persisted_text
    assert "hello this must not render" not in persisted_text
    assert "/srv/scratch" not in persisted_text
    assert "/home/paunchygent" not in persisted_text
    assert "/tmp/operator-fixture.wav" not in persisted_text


@pytest.mark.parametrize(
    ("mutate", "expected_reason"),
    (
        pytest.param(
            lambda proof: replace(proof, evidence_mode="projection"),
            "live_hemma_evidence_missing",
            id="projection-mode",
        ),
        pytest.param(
            lambda proof: replace(
                proof,
                codec_boundary=replace(proof.codec_boundary, bad_media_fails_closed=False),
            ),
            "codec_boundary_not_proven",
            id="codec-boundary",
        ),
        pytest.param(
            lambda proof: replace(
                proof,
                backend_dependencies=replace(
                    proof.backend_dependencies,
                    faster_whisper_importable=False,
                ),
            ),
            "backend_dependencies_not_ready",
            id="backend-dependencies",
        ),
        pytest.param(
            lambda proof: replace(
                proof,
                huggingface_readiness=replace(
                    proof.huggingface_readiness,
                    cache_roots_ready=False,
                ),
            ),
            "huggingface_readiness_not_ready",
            id="huggingface-readiness",
        ),
        pytest.param(
            lambda proof: _with_benchmark_languages(
                proof,
                _english_language_evidence(),
            ),
            "sv_language_fixture_missing",
            id="swedish-fixture",
        ),
        pytest.param(
            lambda proof: _with_benchmark_languages(
                proof,
                _swedish_language_evidence(),
            ),
            "en_language_fixture_missing",
            id="english-fixture",
        ),
        pytest.param(
            lambda proof: _with_benchmark_speaker_hints(
                proof,
                exact_speaker_count_exercised=False,
            ),
            "exact_speaker_count_hint_not_exercised",
            id="exact-speaker-count",
        ),
        pytest.param(
            lambda proof: _with_benchmark_speaker_hints(
                proof,
                min_max_speaker_range_exercised=False,
            ),
            "speaker_range_hint_not_exercised",
            id="speaker-range",
        ),
        pytest.param(
            lambda proof: replace(
                proof,
                batch_lifecycle=replace(
                    proof.batch_lifecycle,
                    duration_seconds=7_199.0,
                ),
            ),
            "120_minute_lifecycle_not_proven",
            id="batch-lifecycle",
        ),
        pytest.param(
            lambda proof: _with_benchmark_runtime(
                proof,
                gpu_execution_confirmed=False,
            ),
            "gpu_required_execution_not_proven",
            id="gpu-required-execution",
        ),
        pytest.param(
            lambda proof: _with_content_safety(
                proof,
                transcript_text_in_report=True,
            ),
            "content_safety_not_proven",
            id="content-safety",
        ),
        pytest.param(
            lambda proof: _with_benchmark_languages(
                proof,
                _swedish_language_evidence(),
                replace(_english_language_evidence(), word_timestamps_available=False),
            ),
            "en_word_timestamps_missing",
            id="word-timestamps",
        ),
        pytest.param(
            lambda proof: replace(proof, audio_transcript_route_registered=True),
            "route_registration_observed",
            id="route-registration",
        ),
    ),
)
def test_live_profile_proof_rejects_each_missing_required_evidence(
    mutate: Callable[
        [AudioTranscriptionSidecarProfileProofEvidence],
        AudioTranscriptionSidecarProfileProofEvidence,
    ],
    expected_reason: str,
) -> None:
    report = build_live_profile_proof_report(mutate(complete_sidecar_profile_proof()))

    assert report["proof_ready"] is False
    assert report["profile_selection"]["selected"] is False
    assert expected_reason in report["profile_selection"]["rejection_reasons"]


def test_live_profile_proof_report_redacts_leak_samples_even_when_rejected(
    tmp_path: Path,
) -> None:
    evidence = replace(
        complete_sidecar_profile_proof(),
        huggingface_readiness=replace(
            complete_sidecar_profile_proof().huggingface_readiness,
            secret_values_exposed=True,
            private_cache_paths_exposed=True,
        ),
    )

    report = build_live_profile_proof_report(evidence)
    json_path, markdown_path = write_live_profile_proof_report(report, output_root=tmp_path)
    persisted_text = json_path.read_text(encoding="utf-8")
    persisted_text += markdown_path.read_text(encoding="utf-8")

    assert report["proof_ready"] is False
    assert "content_safety_not_proven" in report["profile_selection"]["rejection_reasons"]
    assert "hf_private_token_value" not in persisted_text
    assert "/srv/scratch/sir-convert-a-lot/cache/huggingface" not in persisted_text
    assert "provider/private-stt-model" not in persisted_text
    assert "hej detta ska inte synas" not in persisted_text


def test_profile_proof_records_historical_route_unregistered_evidence() -> None:
    report = build_live_profile_proof_report(complete_sidecar_profile_proof())

    assert report["required_evidence"]["route_unregistered"] is True
    assert report["route_registration"]["audio_transcript_bundle_registered"] is False


def complete_sidecar_profile_proof() -> AudioTranscriptionSidecarProfileProofEvidence:
    """Return complete live-proof evidence for the STT benchmark boundary."""

    return AudioTranscriptionSidecarProfileProofEvidence(
        evidence_mode="live_hemma",
        sidecar_launch=AudioTranscriptionSidecarLaunchEvidence(
            image_name="sir-convert-a-lot-stt-sidecar",
            image_tag="benchmark",
            compose_service="stt-sidecar-benchmark",
            build_contract="buildkit",
            launch_observed=True,
            isolated_runtime_marker=True,
            required_system_tools=("ffmpeg", "ffprobe"),
            required_python_packages=(
                "faster-whisper",
                "huggingface_hub",
                "pyannote.audio",
                "torch",
                "torchaudio",
                "torchcodec",
            ),
            gpu_acceleration_required=True,
            hf_token_env_var_names=("HF_TOKEN",),
            hf_cache_env_var_names=("HF_HOME", "HF_HUB_CACHE"),
            environment_values_exposed=False,
            private_paths_exposed=False,
            raw_model_identifiers_exposed=False,
        ),
        codec_boundary=AudioTranscriptionCodecBoundaryEvidence(
            ffmpeg_available=True,
            ffprobe_available=True,
            supported_audio_codecs=("aac", "flac", "m4a", "mp3", "ogg", "opus", "wav"),
            valid_audio_probe_exercised=True,
            bad_media_fails_closed=True,
            no_audio_fails_closed=True,
            unsupported_media_fails_closed=True,
            bounded_metadata_projected=True,
            source_media_paths=("/tmp/operator-fixture.wav",),
        ),
        backend_dependencies=AudioTranscriptionBackendDependencyEvidence(
            faster_whisper_importable=True,
            pyannote_audio_importable=True,
            huggingface_hub_importable=True,
            torch_importable=True,
            torchaudio_importable=True,
            torchcodec_audio_decoder_importable=True,
            miopen_hiprtc_headers_available=True,
            sidecar_runtime_isolated=True,
            main_service_dependency_change_observed=False,
        ),
        huggingface_readiness=AudioTranscriptionHuggingFaceReadinessEvidence(
            token_env_var_names=("HF_TOKEN",),
            token_env_vars_present=True,
            cache_roots_ready=True,
            cache_status="scratch_backed",
            model_access_status="ready",
            secret_values_exposed=False,
            private_cache_paths_exposed=False,
            raw_model_identifiers_exposed=False,
            token_value_samples=("hf_private_token_value",),
            private_cache_paths=("/srv/scratch/sir-convert-a-lot/cache/huggingface",),
        ),
        benchmark_evidence=complete_audio_benchmark_evidence(),
        batch_lifecycle=AudioTranscriptionBatchLifecycleEvidence(
            duration_seconds=7_200.0,
            chunk_count=12,
            max_chunk_duration_seconds=600.0,
            progress_updates_observed=True,
            checkpoints_observed=True,
            detached_status_capable=True,
            cancel_semantics_observed=True,
            retry_semantics_observed=True,
        ),
        audio_transcript_route_registered=False,
    )


def complete_audio_benchmark_evidence() -> AudioBenchmarkEvidence:
    """Return complete content-safe profile-selection evidence."""

    return AudioBenchmarkEvidence(
        profiles=AudioBenchmarkProfileLabels(
            stt_profile="stt_sv_en_primary",
            diarization_profile="diarization_sv_en_primary",
            stt_backend_family=BenchmarkBackendFamily.FASTER_WHISPER,
            diarization_backend_family=BenchmarkBackendFamily.PYANNOTE_AUDIO,
            raw_model_identifiers=(
                "provider/private-stt-model",
                "provider/private-diarization-model",
            ),
        ),
        runtime=AudioBenchmarkRuntimeEvidence(
            acceleration_family="rocm",
            gpu_execution_confirmed=True,
            cpu_fallback_observed=False,
            cache_family="huggingface",
            cache_reuse_observed=True,
            cache_roots_ready=True,
            missing_model_access_failure_code=AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED,
            required_secret_names=("HF_TOKEN",),
            required_secret_values_exposed=False,
            private_cache_paths=("/home/paunchygent/.cache/private",),
        ),
        language_evidence=(
            _swedish_language_evidence(),
            _english_language_evidence(),
        ),
        speaker_hints=AudioBenchmarkSpeakerHintEvidence(
            exact_speaker_count_supported=True,
            exact_speaker_count_exercised=True,
            min_max_speaker_range_supported=True,
            min_max_speaker_range_exercised=True,
        ),
        duration=AudioBenchmarkSyntheticDurationEvidence(
            proof_kind="synthetic_duration",
            duration_seconds=7_200.0,
            chunk_count=12,
            max_chunk_duration_seconds=600.0,
            lifecycle_assumptions_exercised=True,
        ),
        content_safety=AudioBenchmarkContentSafetyEvidence(
            transcript_text_in_report=False,
            raw_model_ids_in_report=False,
            secret_values_in_report=False,
            private_paths_in_report=False,
            generated_artifacts_in_repo=False,
        ),
    )


def _swedish_language_evidence() -> AudioBenchmarkLanguageEvidence:
    return AudioBenchmarkLanguageEvidence(
        fixture_label="operator_sv_fixture",
        language="sv",
        detected_language="sv",
        diarized_segment_count=18,
        exclusive_speaker_segments=True,
        alignment_suitable=True,
        word_timestamps_available=True,
        transcript_text_retained=False,
        transcript_text_samples=("hej detta ska inte synas",),
    )


def _english_language_evidence() -> AudioBenchmarkLanguageEvidence:
    return AudioBenchmarkLanguageEvidence(
        fixture_label="operator_en_fixture",
        language="en",
        detected_language="en",
        diarized_segment_count=21,
        exclusive_speaker_segments=True,
        alignment_suitable=True,
        word_timestamps_available=True,
        transcript_text_retained=False,
        transcript_text_samples=("hello this must not render",),
    )


def _with_benchmark_languages(
    proof: AudioTranscriptionSidecarProfileProofEvidence,
    *language_evidence: AudioBenchmarkLanguageEvidence,
) -> AudioTranscriptionSidecarProfileProofEvidence:
    return replace(
        proof,
        benchmark_evidence=replace(
            proof.benchmark_evidence,
            language_evidence=language_evidence,
        ),
    )


def _with_benchmark_speaker_hints(
    proof: AudioTranscriptionSidecarProfileProofEvidence,
    *,
    exact_speaker_count_exercised: bool | None = None,
    min_max_speaker_range_exercised: bool | None = None,
) -> AudioTranscriptionSidecarProfileProofEvidence:
    return replace(
        proof,
        benchmark_evidence=proof.benchmark_evidence.with_speaker_hints(
            exact_speaker_count_exercised=exact_speaker_count_exercised,
            min_max_speaker_range_exercised=min_max_speaker_range_exercised,
        ),
    )


def _with_benchmark_runtime(
    proof: AudioTranscriptionSidecarProfileProofEvidence,
    *,
    gpu_execution_confirmed: bool | None = None,
) -> AudioTranscriptionSidecarProfileProofEvidence:
    return replace(
        proof,
        benchmark_evidence=proof.benchmark_evidence.with_runtime(
            gpu_execution_confirmed=gpu_execution_confirmed,
        ),
    )


def _with_content_safety(
    proof: AudioTranscriptionSidecarProfileProofEvidence,
    *,
    transcript_text_in_report: bool,
) -> AudioTranscriptionSidecarProfileProofEvidence:
    return replace(
        proof,
        benchmark_evidence=replace(
            proof.benchmark_evidence,
            content_safety=replace(
                proof.benchmark_evidence.content_safety,
                transcript_text_in_report=transcript_text_in_report,
            ),
        ),
    )
