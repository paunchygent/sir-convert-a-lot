"""FasterWhisper and pyannote runtime for the STT sidecar.

Purpose:
    Execute local-upload audio transcription and diarization inside the isolated
    STT sidecar image, returning only provider-neutral health, capability, and
    transcript payloads to the main service.

Relationships:
    - Implements `stt_sidecar.contracts.SttSidecarBackend`.
    - Shares route constants with `domain.audio_transcription_contracts` so
      readiness truth matches the Service API v2 audio runtime.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    DAY_ONE_MEDIA_CONTAINERS,
    MAX_AUDIO_DURATION_SECONDS,
    MAX_AUDIO_UPLOAD_BYTES,
    STT_SIDECAR_CONTRACT_VERSION,
)
from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError
from scripts.sir_convert_a_lot.stt_sidecar.media import (
    NORMALIZATION_PROFILE,
    NORMALIZED_CHANNELS,
    NORMALIZED_SAMPLE_RATE_HZ,
    duration_seconds,
    normalize_audio,
    trim_normalized_audio,
)
from scripts.sir_convert_a_lot.stt_sidecar.model_lifecycle import (
    BatchedWhisperModelLike,
    DiarizationPipelineLike,
    SttModelLifecycle,
    cache_root_ready,
    model_artifacts_present,
)
from scripts.sir_convert_a_lot.stt_sidecar.normalized_audio import NormalizedAudioStore
from scripts.sir_convert_a_lot.stt_sidecar.request_parsing import (
    language_option,
    mapping_at,
    optional_int,
    required_float,
    required_string,
    source_path,
)
from scripts.sir_convert_a_lot.stt_sidecar.segments import (
    SpeakerSegment,
    TranscriptSegment,
    confidence,
    detected_language,
    float_attr,
    speaker_segments,
    string_attr,
)
from scripts.sir_convert_a_lot.stt_sidecar.settings import SttSidecarSettings


class SttSidecarRuntime:
    """Production STT sidecar runtime backed by FasterWhisper and pyannote."""

    def __init__(self, settings: SttSidecarSettings) -> None:
        self._settings = settings
        self._model_lifecycle = SttModelLifecycle(settings)
        self._ready = False
        self._gpu_ready = False
        self._lock = threading.Lock()
        self._canceled_handles: set[str] = set()
        self._normalized_audio = NormalizedAudioStore(
            Path(gettempdir()) / "sir-convert-a-lot-stt-sidecar"
        )

    def startup(self) -> None:
        """Prepare GPU-only STT sidecar capability without loading models."""
        self._gpu_ready = self._model_lifecycle.gpu_ready()
        if not self._gpu_ready:
            raise RuntimeError("GPU runtime is required for the STT sidecar.")
        if not self._model_lifecycle.required_secret_present():
            raise RuntimeError("HF token is required for the STT sidecar diarization profile.")
        self._ready = True

    def shutdown(self) -> None:
        """Drop resident STT and diarization model references."""
        self._model_lifecycle.shutdown()

    def health(self) -> Mapping[str, object]:
        """Return sanitized readiness truth for the main service."""
        self.unload_idle_models()
        residency = self._model_lifecycle.snapshot()
        return {
            "status": "ok" if self._ready and self._gpu_ready else "degraded",
            "ready": self._ready,
            "backend_profile_id": self._settings.backend_profile_id,
            "backend_version": self._settings.backend_version,
            "gpu_ready": self._gpu_ready,
            "capability_version": STT_SIDECAR_CONTRACT_VERSION,
            "models_resident": residency["models_resident"],
        }

    def capabilities(self) -> Mapping[str, object]:
        """Return sanitized capability truth for the main service."""
        self.unload_idle_models()
        residency = self._model_lifecycle.snapshot()
        cache_ready = cache_root_ready(self._settings.hf_cache_container_root)
        artifacts_present = model_artifacts_present(self._settings)
        return {
            "adapter_contract_version": STT_SIDECAR_CONTRACT_VERSION,
            "runtime": {
                "network_scope": "internal_only",
                "published_port_allowed": False,
                "gpu_required": True,
                "acceleration_family": self._settings.acceleration_family,
                "acceleration_ready": self._gpu_ready,
            },
            "media": {
                "max_upload_bytes": MAX_AUDIO_UPLOAD_BYTES,
                "max_duration_seconds": MAX_AUDIO_DURATION_SECONDS,
                "accepted_containers": sorted(DAY_ONE_MEDIA_CONTAINERS),
                "input_protocols": ["local_upload"],
                "normalized_audio": {
                    "container": "wav",
                    "sample_rate_hz": NORMALIZED_SAMPLE_RATE_HZ,
                    "channels": NORMALIZED_CHANNELS,
                    "sample_format": "s16",
                },
            },
            "transcription": {
                "profile_label": self._settings.stt_profile_label,
                "backend_family": "faster_whisper",
                "batch_size": self._settings.batch_size,
                "languages": ["auto", "sv", "en"],
                "word_timestamps_supported": True,
            },
            "diarization": {
                "profile_label": self._settings.diarization_profile_label,
                "backend_family": "pyannote_audio",
                "required_for_success": True,
                "modes": ["auto", "known_speaker_count", "speaker_range"],
                "exclusive_speaker_segments_supported": True,
            },
            "cache": {
                "cache_family": "huggingface",
                "host_root": self._settings.hf_cache_host_label,
                "container_root": self._settings.hf_cache_container_label,
                "cache_roots_ready": cache_ready,
                "model_artifacts_present": artifacts_present,
                "models_resident": residency["models_resident"],
                "active_model_uses": residency["active_model_uses"],
                "idle_unload_seconds": residency["idle_unload_seconds"],
            },
            "secrets": {
                "required_secret_names": [self._settings.hf_token_env_name],
                "required_secrets_present": (
                    os.environ.get(self._settings.hf_token_env_name, "").strip() != ""
                ),
                "values_exposed": False,
            },
        }

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Probe and normalize one local-upload audio request."""
        self._require_ready()
        request_handle = required_string(request, "request_handle")
        self._raise_if_canceled(request_handle)
        input_path = source_path(request)
        options = mapping_at(request, "options")
        duration = duration_seconds(input_path)
        _enforce_duration_limit(duration_seconds=duration, options=options)
        normalized_path = self._normalized_audio.path_for(
            request_handle=request_handle,
            source_path=input_path,
        )
        normalize_audio(
            source_path=input_path,
            target_path=normalized_path,
            media_duration_seconds=duration,
        )
        normalized_audio = self._normalized_audio.remember(
            request_handle=request_handle,
            normalized_path=normalized_path,
        )
        return {
            "status": "succeeded",
            "media": {
                "duration_seconds": duration,
                "normalized_audio_sha256": normalized_audio.sha256,
                "normalized_audio_handle": normalized_audio.handle,
            },
            "runtime_metadata": {
                "acceleration_used": self._settings.acceleration_family,
                "normalization_profile": NORMALIZATION_PROFILE,
            },
            "warnings": [],
        }

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Run global diarization for one normalized audio request."""
        self._require_ready()
        request_handle = required_string(request, "request_handle")
        self._raise_if_canceled(request_handle)
        normalized_audio = self._normalized_audio.resolve(request)
        options = mapping_at(request, "options")
        with self._model_lifecycle.use_models() as models:
            speakers = self._diarize_segments(
                normalized_path=normalized_audio.path,
                options=options,
                diarization_pipeline=models.diarization_pipeline,
            )
        self._raise_if_canceled(request_handle)
        return {
            "status": "succeeded",
            "diarization": {
                "status": "succeeded",
                "mode_used": required_string(mapping_at(options, "diarization"), "mode"),
                "windows": [
                    {
                        "window_id": f"speaker-window-{index:04d}",
                        "start_seconds": speaker.start_seconds,
                        "end_seconds": speaker.end_seconds,
                        "speaker_label": speaker.speaker_label,
                    }
                    for index, speaker in enumerate(speakers, start=1)
                ],
            },
            "warnings": [],
        }

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Transcribe one deterministic normalized audio chunk."""
        self._require_ready()
        request_handle = required_string(request, "request_handle")
        self._raise_if_canceled(request_handle)
        normalized_audio = self._normalized_audio.resolve(request)
        options = mapping_at(request, "options")
        language = language_option(options)
        chunk = mapping_at(request, "chunk")
        chunk_index = optional_int(chunk, "chunk_index")
        if chunk_index is None:
            raise SttSidecarRequestError(
                code="invalid_request",
                message="chunk_index is required.",
                status_code=422,
            )
        start_seconds = required_float(chunk, "start_seconds")
        end_seconds = required_float(chunk, "end_seconds")
        if end_seconds <= start_seconds:
            raise SttSidecarRequestError(
                code="invalid_request",
                message="chunk end_seconds must be greater than start_seconds.",
                status_code=422,
            )
        with TemporaryDirectory(prefix="sir-stt-chunk-") as temp_dir:
            chunk_path = Path(temp_dir) / "chunk.wav"
            trim_normalized_audio(
                source_path=normalized_audio.path,
                target_path=chunk_path,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
            )
            with self._model_lifecycle.use_models() as models:
                segments = self._transcribe_segments(
                    normalized_path=chunk_path,
                    language=language,
                    stt_model=models.stt_model,
                    start_offset_seconds=start_seconds,
                    segment_id_prefix=f"chunk-{chunk_index}-seg",
                )
        self._raise_if_canceled(request_handle)
        if not segments:
            raise SttSidecarRequestError(
                code="audio_transcription_failed",
                message="No transcript segments were produced.",
                status_code=502,
            )
        return {
            "status": "succeeded",
            "chunk_index": chunk_index,
            "segments": [
                {
                    "segment_id": segment.segment_id,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "text": segment.text,
                    "language": segment.language,
                    "confidence": segment.confidence,
                }
                for segment in segments
            ],
            "language": {
                "detected": detected_language(segments, requested=language),
                "confidence": None,
            },
            "warnings": [],
        }

    def cancel(self, request_handle: str) -> Mapping[str, object]:
        """Record cancellation for a request handle."""
        with self._lock:
            self._canceled_handles.add(request_handle)
        self.finalize(request_handle)
        return {"status": "cancel_requested", "request_handle": request_handle}

    def finalize(self, request_handle: str) -> Mapping[str, object]:
        """Remove sidecar-owned normalized media for one terminal request."""

        removed = self._normalized_audio.finalize(request_handle)
        return {
            "status": "finalized",
            "request_handle": request_handle,
            "removed_normalized_media": removed,
        }

    def unload_idle_models(self) -> Mapping[str, object]:
        """Drop resident model references after the configured idle timeout."""
        return self._model_lifecycle.unload_idle_models()

    def _transcribe_segments(
        self,
        *,
        normalized_path: Path,
        language: str | None,
        stt_model: BatchedWhisperModelLike,
        start_offset_seconds: float = 0.0,
        segment_id_prefix: str = "seg",
    ) -> list[TranscriptSegment]:
        segment_iterable, info = stt_model.transcribe(
            normalized_path.as_posix(),
            beam_size=self._settings.beam_size,
            batch_size=self._settings.batch_size,
            word_timestamps=True,
            language=language,
        )
        language_label = string_attr(info, "language", fallback=language or "auto")
        parsed: list[TranscriptSegment] = []
        for index, segment_obj in enumerate(segment_iterable, start=1):
            text = string_attr(segment_obj, "text", fallback="").strip()
            if text == "":
                continue
            parsed.append(
                TranscriptSegment(
                    segment_id=f"{segment_id_prefix}-{index:04d}",
                    start_seconds=start_offset_seconds + float_attr(segment_obj, "start"),
                    end_seconds=start_offset_seconds + float_attr(segment_obj, "end"),
                    speaker_label="SPEAKER_PENDING",
                    text=text,
                    language=language_label,
                    confidence=confidence(segment_obj),
                )
            )
        return parsed

    def _require_ready(self) -> None:
        if not self._ready or not self._gpu_ready:
            raise SttSidecarRequestError(
                code="audio_sidecar_unavailable",
                message="STT sidecar runtime is not ready.",
                status_code=503,
            )

    def _diarize_segments(
        self,
        *,
        normalized_path: Path,
        options: Mapping[str, object],
        diarization_pipeline: DiarizationPipelineLike,
    ) -> list[SpeakerSegment]:
        diarization_options = mapping_at(options, "diarization")
        output = diarization_pipeline(
            normalized_path.as_posix(),
            num_speakers=optional_int(diarization_options, "num_speakers"),
            min_speakers=optional_int(diarization_options, "min_speakers"),
            max_speakers=optional_int(diarization_options, "max_speakers"),
        )
        diarization = getattr(output, "exclusive_speaker_diarization", None)
        if diarization is None:
            diarization = getattr(output, "speaker_diarization", None)
        if diarization is None:
            raise SttSidecarRequestError(
                code="audio_diarization_failed",
                message="Diarization output did not contain speaker segments.",
                status_code=502,
            )
        speakers = speaker_segments(diarization)
        if not speakers:
            raise SttSidecarRequestError(
                code="audio_diarization_failed",
                message="Diarization output did not contain speaker segments.",
                status_code=502,
            )
        return speakers

    def _raise_if_canceled(self, request_handle: str) -> None:
        with self._lock:
            canceled = request_handle in self._canceled_handles
        if canceled:
            raise SttSidecarRequestError(
                code="audio_sidecar_canceled",
                message="Audio transcription request was canceled.",
                status_code=409,
            )


def _enforce_duration_limit(
    *,
    duration_seconds: float,
    options: Mapping[str, object],
) -> None:
    max_duration = optional_int(options, "max_duration_seconds")
    if max_duration is None:
        max_duration = MAX_AUDIO_DURATION_SECONDS
    effective_max_duration = min(max_duration, MAX_AUDIO_DURATION_SECONDS)
    if duration_seconds > float(effective_max_duration):
        raise SttSidecarRequestError(
            code="audio_duration_exceeded",
            message="Uploaded audio exceeds the configured duration limit.",
            status_code=422,
        )
