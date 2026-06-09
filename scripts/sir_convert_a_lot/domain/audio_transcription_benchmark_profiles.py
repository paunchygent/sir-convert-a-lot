"""Audio transcription benchmark profile-selection policy.

Purpose:
    Select or reject bounded speech-to-text and diarization runtime profiles
    from content-safe Hemma benchmark evidence.

Relationships:
    - Re-exports evidence data contracts from
      `domain.audio_transcription_benchmark_types` for the audio benchmark lane.
    - Consumes public error-code language from
      `domain.audio_transcription_contracts` without importing STT, diarization,
      Hugging Face, FFmpeg, or sidecar runtime dependencies.
    - Produces sanitized benchmark-report projections before route
      registration, transcript persistence, or formatter outputs exist.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.audio_transcription_benchmark_types import (
    AudioBenchmarkContentSafetyEvidence,
    AudioBenchmarkDurationReport,
    AudioBenchmarkEvidence,
    AudioBenchmarkFixtureReport,
    AudioBenchmarkLanguageEvidence,
    AudioBenchmarkProfileLabels,
    AudioBenchmarkProfileReport,
    AudioBenchmarkProfileSelectionDecision,
    AudioBenchmarkReport,
    AudioBenchmarkRuntimeEvidence,
    AudioBenchmarkRuntimeReport,
    AudioBenchmarkSpeakerHintEvidence,
    AudioBenchmarkSpeakerHintReport,
    AudioBenchmarkSyntheticDurationEvidence,
    BenchmarkBackendFamily,
    BenchmarkProfileSelectionStatus,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)

_REQUIRED_120_MINUTE_SECONDS = 7_200.0
_ALLOWED_STT_PROFILE_LABELS: frozenset[str] = frozenset({"stt_sv_en_primary"})
_ALLOWED_DIARIZATION_PROFILE_LABELS: frozenset[str] = frozenset({"diarization_sv_en_primary"})
_REQUIRED_LANGUAGE_VALUES: frozenset[str] = frozenset({"sv", "en"})
_ALLOWED_ACCELERATION_FAMILIES: frozenset[str] = frozenset({"rocm", "cuda"})
_ALLOWED_CACHE_FAMILIES: frozenset[str] = frozenset({"huggingface"})

__all__ = (
    "AudioBenchmarkContentSafetyEvidence",
    "AudioBenchmarkDurationReport",
    "AudioBenchmarkEvidence",
    "AudioBenchmarkFixtureReport",
    "AudioBenchmarkLanguageEvidence",
    "AudioBenchmarkProfileLabels",
    "AudioBenchmarkProfileReport",
    "AudioBenchmarkProfileSelectionDecision",
    "AudioBenchmarkReport",
    "AudioBenchmarkRuntimeEvidence",
    "AudioBenchmarkRuntimeReport",
    "AudioBenchmarkSpeakerHintEvidence",
    "AudioBenchmarkSpeakerHintReport",
    "AudioBenchmarkSyntheticDurationEvidence",
    "BenchmarkBackendFamily",
    "BenchmarkProfileSelectionStatus",
    "build_content_safe_audio_benchmark_report",
    "evaluate_audio_benchmark_profile_selection",
)


def evaluate_audio_benchmark_profile_selection(
    evidence: AudioBenchmarkEvidence,
) -> AudioBenchmarkProfileSelectionDecision:
    """Select bounded audio profiles only when all benchmark evidence is complete."""

    rejection_reasons = tuple(_profile_rejection_reasons(evidence))
    if rejection_reasons:
        return AudioBenchmarkProfileSelectionDecision(
            status=BenchmarkProfileSelectionStatus.REJECTED,
            stt_profile=None,
            diarization_profile=None,
            rejection_reasons=rejection_reasons,
        )
    return AudioBenchmarkProfileSelectionDecision(
        status=BenchmarkProfileSelectionStatus.SELECTED,
        stt_profile=evidence.profiles.stt_profile,
        diarization_profile=evidence.profiles.diarization_profile,
        rejection_reasons=(),
    )


def build_content_safe_audio_benchmark_report(
    evidence: AudioBenchmarkEvidence,
) -> AudioBenchmarkReport:
    """Build a sanitized report without transcript, model, token, or path data."""

    decision = evaluate_audio_benchmark_profile_selection(evidence)
    report: AudioBenchmarkReport = {
        "profiles": {
            "stt_profile": evidence.profiles.stt_profile,
            "diarization_profile": evidence.profiles.diarization_profile,
            "stt_backend_family": evidence.profiles.stt_backend_family.value,
            "diarization_backend_family": evidence.profiles.diarization_backend_family.value,
        },
        "runtime": {
            "acceleration_family": evidence.runtime.acceleration_family,
            "gpu_execution_confirmed": evidence.runtime.gpu_execution_confirmed,
            "cpu_fallback_observed": evidence.runtime.cpu_fallback_observed,
            "cache_family": evidence.runtime.cache_family,
            "cache_reuse_observed": evidence.runtime.cache_reuse_observed,
            "cache_roots_ready": evidence.runtime.cache_roots_ready,
            "missing_model_access_failure_code": (
                evidence.runtime.missing_model_access_failure_code.value
                if evidence.runtime.missing_model_access_failure_code is not None
                else ""
            ),
            "required_secret_names": evidence.runtime.required_secret_names,
        },
        "fixtures": [_fixture_report(language) for language in evidence.language_evidence],
        "speaker_hints": {
            "exact_speaker_count_supported": (evidence.speaker_hints.exact_speaker_count_supported),
            "exact_speaker_count_exercised": (evidence.speaker_hints.exact_speaker_count_exercised),
            "min_max_speaker_range_supported": (
                evidence.speaker_hints.min_max_speaker_range_supported
            ),
            "min_max_speaker_range_exercised": (
                evidence.speaker_hints.min_max_speaker_range_exercised
            ),
        },
        "duration": {
            "proof_kind": evidence.duration.proof_kind,
            "duration_seconds": evidence.duration.duration_seconds,
            "chunk_count": evidence.duration.chunk_count,
            "max_chunk_duration_seconds": evidence.duration.max_chunk_duration_seconds,
            "lifecycle_assumptions_exercised": (evidence.duration.lifecycle_assumptions_exercised),
        },
        "selected": decision.status is BenchmarkProfileSelectionStatus.SELECTED,
        "rejection_reasons": decision.rejection_reasons,
    }
    if evidence.hemma_evidence_path is not None:
        report["hemma_evidence_path"] = "recorded"
    return report


def _fixture_report(
    language: AudioBenchmarkLanguageEvidence,
) -> AudioBenchmarkFixtureReport:
    return {
        "detected_language": language.detected_language,
        "diarized_segment_count": language.diarized_segment_count,
        "exclusive_speaker_segments": language.exclusive_speaker_segments,
        "fixture_label": language.fixture_label,
        "language": language.language,
        "alignment_suitable": language.alignment_suitable,
    }


def _profile_rejection_reasons(evidence: AudioBenchmarkEvidence) -> list[str]:
    reasons: list[str] = []
    reasons.extend(_profile_label_rejection_reasons(evidence.profiles))
    reasons.extend(_runtime_rejection_reasons(evidence.runtime))
    reasons.extend(_language_rejection_reasons(evidence.language_evidence))
    reasons.extend(_speaker_hint_rejection_reasons(evidence.speaker_hints))
    reasons.extend(_duration_rejection_reasons(evidence.duration))
    reasons.extend(_content_safety_rejection_reasons(evidence.content_safety))
    return reasons


def _profile_label_rejection_reasons(profiles: AudioBenchmarkProfileLabels) -> list[str]:
    reasons: list[str] = []
    if profiles.stt_profile not in _ALLOWED_STT_PROFILE_LABELS:
        reasons.append("stt_profile_label_not_bounded")
    if profiles.diarization_profile not in _ALLOWED_DIARIZATION_PROFILE_LABELS:
        reasons.append("diarization_profile_label_not_bounded")
    if profiles.stt_backend_family is not BenchmarkBackendFamily.FASTER_WHISPER:
        reasons.append("stt_backend_family_not_selected")
    if profiles.diarization_backend_family is not BenchmarkBackendFamily.PYANNOTE_AUDIO:
        reasons.append("diarization_backend_family_not_selected")
    if not profiles.raw_model_identifiers:
        reasons.append("raw_model_access_targets_not_recorded")
    return reasons


def _runtime_rejection_reasons(runtime: AudioBenchmarkRuntimeEvidence) -> list[str]:
    reasons: list[str] = []
    if runtime.acceleration_family not in _ALLOWED_ACCELERATION_FAMILIES:
        reasons.append("gpu_acceleration_family_not_supported")
    if not runtime.gpu_execution_confirmed:
        reasons.append("gpu_execution_not_confirmed")
    if runtime.cpu_fallback_observed:
        reasons.append("cpu_fallback_observed")
    if runtime.cache_family not in _ALLOWED_CACHE_FAMILIES:
        reasons.append("cache_family_not_supported")
    if not runtime.cache_reuse_observed:
        reasons.append("cache_reuse_not_observed")
    if not runtime.cache_roots_ready:
        reasons.append("cache_roots_not_ready")
    if (
        runtime.missing_model_access_failure_code
        is not AudioTranscriptionErrorCode.MODEL_ACCESS_DENIED
    ):
        reasons.append("missing_model_access_failure_not_proven")
    if not runtime.required_secret_names:
        reasons.append("required_secret_names_not_recorded")
    if runtime.required_secret_values_exposed:
        reasons.append("secret_values_exposed")
    return reasons


def _language_rejection_reasons(
    language_evidence: tuple[AudioBenchmarkLanguageEvidence, ...],
) -> list[str]:
    reasons: list[str] = []
    by_language = {evidence.language: evidence for evidence in language_evidence}
    for required_language in sorted(_REQUIRED_LANGUAGE_VALUES):
        evidence = by_language.get(required_language)
        if evidence is None:
            reasons.append(f"{required_language}_language_fixture_missing")
            continue
        reasons.extend(_single_language_rejection_reasons(evidence, required_language))
    return reasons


def _single_language_rejection_reasons(
    evidence: AudioBenchmarkLanguageEvidence,
    required_language: str,
) -> list[str]:
    reasons: list[str] = []
    if evidence.detected_language != required_language:
        reasons.append(f"{required_language}_language_detection_not_proven")
    if evidence.diarized_segment_count <= 0:
        reasons.append(f"{required_language}_diarized_segments_missing")
    if not evidence.exclusive_speaker_segments:
        reasons.append(f"{required_language}_exclusive_diarization_not_proven")
    if not evidence.alignment_suitable:
        reasons.append(f"{required_language}_alignment_not_suitable")
    if evidence.transcript_text_retained:
        reasons.append(f"{required_language}_transcript_text_retained")
    return reasons


def _speaker_hint_rejection_reasons(
    speaker_hints: AudioBenchmarkSpeakerHintEvidence,
) -> list[str]:
    reasons: list[str] = []
    if not speaker_hints.exact_speaker_count_supported:
        reasons.append("exact_speaker_count_hint_not_supported")
    if not speaker_hints.exact_speaker_count_exercised:
        reasons.append("exact_speaker_count_hint_not_exercised")
    if not speaker_hints.min_max_speaker_range_supported:
        reasons.append("speaker_range_hint_not_supported")
    if not speaker_hints.min_max_speaker_range_exercised:
        reasons.append("speaker_range_hint_not_exercised")
    return reasons


def _duration_rejection_reasons(
    duration: AudioBenchmarkSyntheticDurationEvidence,
) -> list[str]:
    if (
        duration.duration_seconds >= _REQUIRED_120_MINUTE_SECONDS
        and duration.chunk_count > 0
        and duration.max_chunk_duration_seconds > 0
        and duration.lifecycle_assumptions_exercised
    ):
        return []
    return ["120_minute_feasibility_not_proven"]


def _content_safety_rejection_reasons(
    content_safety: AudioBenchmarkContentSafetyEvidence,
) -> list[str]:
    reasons: list[str] = []
    if content_safety.transcript_text_in_report:
        reasons.append("transcript_text_in_report")
    if content_safety.raw_model_ids_in_report:
        reasons.append("raw_model_ids_in_report")
    if content_safety.secret_values_in_report:
        reasons.append("secret_values_in_report")
    if content_safety.private_paths_in_report:
        reasons.append("private_paths_in_report")
    if content_safety.generated_artifacts_in_repo:
        reasons.append("generated_artifacts_in_repo")
    return reasons
