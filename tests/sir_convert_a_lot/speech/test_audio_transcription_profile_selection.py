"""Behavioral tests for audio transcription benchmark profile selection.

Purpose:
    Prove that speech-to-text profile selection depends on content-safe Hemma
    benchmark evidence rather than backend-native model identifiers or silent
    runtime fallbacks.

Relationships:
    - Exercises the audio transcription benchmark profile-selection boundary.
    - Protects ADR-0013 and the audio converter contract before route execution
      or transcript artifact persistence is implemented.
"""

from __future__ import annotations

from dataclasses import replace

from scripts.sir_convert_a_lot.domain.audio_transcription_benchmark_profiles import (
    AudioBenchmarkContentSafetyEvidence,
    AudioBenchmarkEvidence,
    AudioBenchmarkLanguageEvidence,
    AudioBenchmarkProfileLabels,
    AudioBenchmarkRuntimeEvidence,
    AudioBenchmarkSpeakerHintEvidence,
    AudioBenchmarkSyntheticDurationEvidence,
    BenchmarkBackendFamily,
    BenchmarkProfileSelectionStatus,
    build_content_safe_audio_benchmark_report,
    evaluate_audio_benchmark_profile_selection,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)


def valid_evidence() -> AudioBenchmarkEvidence:
    """Return a complete profile-selection evidence fixture."""

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
            required_secret_names=("HUGGINGFACE_TOKEN",),
            required_secret_values_exposed=False,
            private_cache_paths=(
                "/srv/scratch/sir-convert-a-lot/cache/huggingface",
                "/home/paunchygent/.cache/private",
            ),
        ),
        language_evidence=(
            AudioBenchmarkLanguageEvidence(
                fixture_label="operator_sv_fixture",
                language="sv",
                detected_language="sv",
                diarized_segment_count=18,
                exclusive_speaker_segments=True,
                alignment_suitable=True,
                word_timestamps_available=True,
                transcript_text_retained=False,
                transcript_text_samples=("hej detta ska inte synas",),
            ),
            AudioBenchmarkLanguageEvidence(
                fixture_label="operator_en_fixture",
                language="en",
                detected_language="en",
                diarized_segment_count=21,
                exclusive_speaker_segments=True,
                alignment_suitable=True,
                word_timestamps_available=True,
                transcript_text_retained=False,
                transcript_text_samples=("hello this must not render",),
            ),
        ),
        speaker_hints=AudioBenchmarkSpeakerHintEvidence(
            exact_speaker_count_supported=True,
            exact_speaker_count_exercised=True,
            min_max_speaker_range_supported=True,
            min_max_speaker_range_exercised=True,
        ),
        duration=AudioBenchmarkSyntheticDurationEvidence(
            proof_kind="synthetic_duration",
            duration_seconds=7200.0,
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


def test_profile_selection_accepts_complete_content_safe_gpu_evidence() -> None:
    decision = evaluate_audio_benchmark_profile_selection(valid_evidence())

    assert decision.status == BenchmarkProfileSelectionStatus.SELECTED
    assert decision.stt_profile == "stt_sv_en_primary"
    assert decision.diarization_profile == "diarization_sv_en_primary"
    assert decision.rejection_reasons == ()


def test_profile_selection_rejects_silent_cpu_fallback() -> None:
    evidence = valid_evidence().with_runtime(cpu_fallback_observed=True)

    decision = evaluate_audio_benchmark_profile_selection(evidence)

    assert decision.status == BenchmarkProfileSelectionStatus.REJECTED
    assert "cpu_fallback_observed" in decision.rejection_reasons


def test_profile_selection_rejects_missing_model_access_failure_evidence() -> None:
    evidence = valid_evidence().with_runtime(missing_model_access_failure_code=None)

    decision = evaluate_audio_benchmark_profile_selection(evidence)

    assert decision.status == BenchmarkProfileSelectionStatus.REJECTED
    assert "missing_model_access_failure_not_proven" in decision.rejection_reasons


def test_profile_selection_rejects_unproven_speaker_hint_modes() -> None:
    evidence = valid_evidence().with_speaker_hints(
        min_max_speaker_range_exercised=False,
    )

    decision = evaluate_audio_benchmark_profile_selection(evidence)

    assert decision.status == BenchmarkProfileSelectionStatus.REJECTED
    assert "speaker_range_hint_not_exercised" in decision.rejection_reasons


def test_profile_selection_rejects_incomplete_120_minute_proof_shape() -> None:
    evidence = valid_evidence().with_duration(duration_seconds=7199.0)

    decision = evaluate_audio_benchmark_profile_selection(evidence)

    assert decision.status == BenchmarkProfileSelectionStatus.REJECTED
    assert "120_minute_feasibility_not_proven" in decision.rejection_reasons


def test_profile_selection_rejects_unbounded_public_profile_labels() -> None:
    evidence = valid_evidence().with_profiles(stt_profile="provider/raw-model-large-v3")

    decision = evaluate_audio_benchmark_profile_selection(evidence)

    assert decision.status == BenchmarkProfileSelectionStatus.REJECTED
    assert "stt_profile_label_not_bounded" in decision.rejection_reasons


def test_content_safe_report_excludes_transcript_text_model_ids_tokens_and_private_paths() -> None:
    evidence = valid_evidence()

    report = build_content_safe_audio_benchmark_report(evidence)
    rendered = str(report)

    assert report["profiles"] == {
        "stt_profile": "stt_sv_en_primary",
        "diarization_profile": "diarization_sv_en_primary",
        "stt_backend_family": "faster_whisper",
        "diarization_backend_family": "pyannote_audio",
    }
    assert "provider/private-stt-model" not in rendered
    assert "provider/private-diarization-model" not in rendered
    assert "hej detta ska inte synas" not in rendered
    assert "hello this must not render" not in rendered
    assert "/srv/scratch" not in rendered
    assert "/home/paunchygent" not in rendered
    assert "secret_value" not in rendered
    assert report["fixtures"] == [
        {
            "detected_language": "sv",
            "diarized_segment_count": 18,
            "exclusive_speaker_segments": True,
            "fixture_label": "operator_sv_fixture",
            "language": "sv",
            "alignment_suitable": True,
            "word_timestamps_available": True,
        },
        {
            "detected_language": "en",
            "diarized_segment_count": 21,
            "exclusive_speaker_segments": True,
            "fixture_label": "operator_en_fixture",
            "language": "en",
            "alignment_suitable": True,
            "word_timestamps_available": True,
        },
    ]


def test_profile_selection_rejects_missing_word_timestamps() -> None:
    language_evidence = (
        valid_evidence().language_evidence[0],
        AudioBenchmarkLanguageEvidence(
            fixture_label="operator_en_fixture",
            language="en",
            detected_language="en",
            diarized_segment_count=21,
            exclusive_speaker_segments=True,
            alignment_suitable=True,
            word_timestamps_available=False,
            transcript_text_retained=False,
            transcript_text_samples=(),
        ),
    )
    evidence = replace(valid_evidence(), language_evidence=language_evidence)

    decision = evaluate_audio_benchmark_profile_selection(evidence)

    assert decision.status == BenchmarkProfileSelectionStatus.REJECTED
    assert "en_word_timestamps_missing" in decision.rejection_reasons
