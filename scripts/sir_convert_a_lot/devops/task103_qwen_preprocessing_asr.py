"""ASR and transcript-quality helpers for the staged Qwen preprocessing lane.

Purpose:
    Encapsulate Swedish transcript normalization, WER scoring, admission-tier
    logic, and the lazy Whisper-based ASR scorer used during row-processing.

Relationships:
    - Used by the row-processing stage to score admitted audio rows.
    - Kept separate from orchestration so ASR policy and runtime concerns do
      not live in one monolithic preprocessing module.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    HIGH_TRUST_WER_MAX,
    MEDIUM_TRUST_WER_MAX,
    AdmissionDecision,
    QualityTier,
    SpeakerQualityGate,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import SourceRecord


class TorchTensorProtocol(Protocol):
    """Minimal tensor surface needed by the local ASR helper."""

    def to(self, *args: object, **kwargs: object) -> "TorchTensorProtocol":
        """Move one tensor to the requested device and dtype."""


class ProcessorOutputProtocol(Protocol):
    """Minimal processor output surface used by the local ASR helper."""

    input_features: TorchTensorProtocol
    attention_mask: TorchTensorProtocol | None


class WhisperProcessorProtocol(Protocol):
    """Minimal processor surface used by the local ASR helper."""

    feature_extractor: "WhisperFeatureExtractorProtocol"

    def __call__(
        self,
        waveform: object,
        *,
        sampling_rate: int,
        return_tensors: str,
        return_attention_mask: bool,
    ) -> ProcessorOutputProtocol:
        """Encode one waveform into input features."""

    def batch_decode(self, sequences: object, *, skip_special_tokens: bool) -> list[str]:
        """Decode generated token ids into text."""


class WhisperFeatureExtractorProtocol(Protocol):
    """Minimal feature extractor metadata used by the local ASR helper."""

    sampling_rate: int


class TorchDeviceProtocol(Protocol):
    """Minimal device surface used by the local ASR helper."""

    type: str


class WhisperModelProtocol(Protocol):
    """Minimal seq2seq model surface used by the local ASR helper."""

    def to(self, device: TorchDeviceProtocol) -> "WhisperModelProtocol":
        """Move the model to one target device."""

    def eval(self) -> None:
        """Set the model to evaluation mode."""

    def generate(
        self,
        input_features: TorchTensorProtocol,
        *,
        attention_mask: TorchTensorProtocol | None = None,
        max_new_tokens: int,
        task: str,
    ) -> object:
        """Generate one transcription token sequence."""


def normalize_text(text: str) -> str:
    """Normalize one Swedish transcript into the repo's canonical orthography form."""
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\u00a0", " ").replace("’", "'").replace("`", "'")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized == "":
        raise ValueError("Transcript normalization produced an empty string.")
    if normalized[-1] not in ".!?":
        normalized = f"{normalized}."
    return normalized


def normalize_for_wer(text: str) -> str:
    """Normalize text into a WER-friendly token space."""
    lowered = normalize_text(text).lower()
    without_punctuation = re.sub(r"[^\w\såäöÅÄÖ]", " ", lowered, flags=re.UNICODE)
    return re.sub(r"\s+", " ", without_punctuation).strip()


def word_error_rate(reference_text: str, hypothesis_text: str) -> float:
    """Compute deterministic word error rate without external runtime dependencies."""
    reference_words = normalize_for_wer(reference_text).split()
    hypothesis_words = normalize_for_wer(hypothesis_text).split()
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0

    previous_row = list(range(len(hypothesis_words) + 1))
    for row_index, reference_word in enumerate(reference_words, start=1):
        current_row = [row_index]
        for column_index, hypothesis_word in enumerate(hypothesis_words, start=1):
            substitution_cost = 0 if reference_word == hypothesis_word else 1
            current_row.append(
                min(
                    previous_row[column_index] + 1,
                    current_row[column_index - 1] + 1,
                    previous_row[column_index - 1] + substitution_cost,
                )
            )
        previous_row = current_row
    return round(previous_row[-1] / len(reference_words), 6)


def quality_tier_for_wer(asr_wer: float) -> QualityTier:
    """Assign the fixed T102/T103 quality tier for one WER score."""
    if asr_wer <= HIGH_TRUST_WER_MAX:
        return "high_trust"
    if asr_wer <= MEDIUM_TRUST_WER_MAX:
        return "medium_trust"
    return "rejected"


def speaker_quality_gate_for_source(source_record: SourceRecord) -> SpeakerQualityGate:
    """Assign one speaker-quality gate from the dataset-native source metadata."""
    if source_record.speaker_from_id and source_record.speaker_audio_meta_ok:
        return "speaker_from_id"
    return "manual_review"


def admission_decision_for_source(
    quality_tier: QualityTier,
    speaker_quality_gate: SpeakerQualityGate,
) -> AdmissionDecision:
    """Map quality and speaker gates to one bounded pilot admission decision."""
    if quality_tier in {"high_trust", "medium_trust"} and speaker_quality_gate == "speaker_from_id":
        return "admit"
    return "reject"


@dataclass
class WhisperStrictScorer:
    """Lazy Swedish ASR scorer backed by `KBLab/kb-whisper-large` strict."""

    model_id: str
    revision: str
    _model: WhisperModelProtocol | None = None
    _processor: WhisperProcessorProtocol | None = None
    _device: TorchDeviceProtocol | None = None
    _dtype: object | None = None

    def _ensure_loaded(self) -> None:
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

        if self._model is not None and self._processor is not None and self._device is not None:
            return
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.float16 if device.type == "cuda" else torch.float32
        processor = AutoProcessor.from_pretrained(self.model_id, revision=self.revision)
        model_load_kwargs: dict[str, object] = {
            "revision": self.revision,
            "dtype": dtype,
        }
        if device.type == "cuda":
            # Official Whisper examples load on GPU through `device_map`
            # instead of calling `.to(...)` on a potentially meta-backed model.
            model_load_kwargs["device_map"] = "auto"
        model = AutoModelForSpeechSeq2Seq.from_pretrained(self.model_id, **model_load_kwargs)
        if device.type != "cuda":
            model.to(device)
        model.eval()
        self._model = model
        self._processor = processor
        self._device = device
        self._dtype = dtype

    def transcribe(self, audio_path: "Path") -> str:
        """Transcribe one canonical 24 kHz audio artifact into Swedish text."""
        import librosa
        import numpy as np
        import soundfile
        import torch

        self._ensure_loaded()
        if self._model is None or self._processor is None or self._device is None:
            raise RuntimeError("ASR scorer failed to initialize its model state.")
        waveform, sample_rate_hz = soundfile.read(audio_path.as_posix(), dtype="float32")
        if getattr(waveform, "ndim", 1) > 1:
            waveform = waveform.mean(axis=1)
        target_sample_rate_hz = int(self._processor.feature_extractor.sampling_rate)
        if sample_rate_hz != target_sample_rate_hz:
            waveform = librosa.resample(
                np.asarray(waveform, dtype=np.float32),
                orig_sr=sample_rate_hz,
                target_sr=target_sample_rate_hz,
            )
            sample_rate_hz = target_sample_rate_hz
        processed = self._processor(
            waveform,
            sampling_rate=sample_rate_hz,
            return_tensors="pt",
            return_attention_mask=True,
        )
        input_features = processed.input_features.to(self._device)
        attention_mask = processed.attention_mask
        if attention_mask is not None:
            attention_mask = attention_mask.to(self._device)
        if self._device.type == "cuda":
            input_features = input_features.to(dtype=self._dtype)
        with torch.inference_mode():
            predicted_ids = self._model.generate(
                input_features,
                attention_mask=attention_mask,
                max_new_tokens=256,
                task="transcribe",
            )
        decoded = self._processor.batch_decode(predicted_ids, skip_special_tokens=True)
        if not decoded:
            raise RuntimeError(f"ASR transcription returned no text for {audio_path}.")
        return decoded[0].strip()
