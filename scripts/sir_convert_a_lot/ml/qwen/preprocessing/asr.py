"""ASR and transcript-quality helpers for the Qwen preprocessing pipeline.

Purpose:
    Encapsulate Swedish transcript normalization, WER scoring, admission-tier
    logic, and the lazy Whisper-based ASR scorer used during row-processing.

Relationships:
    - Used by the row-processing stage to score admitted audio rows.
    - Reuses contracts from `ml.qwen.common.models` and
      `ml.qwen.preprocessing.models`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Protocol, runtime_checkable

from scripts.sir_convert_a_lot.ml.qwen.common.models import SourceRecord
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    HIGH_TRUST_WER_MAX,
    MEDIUM_TRUST_WER_MAX,
    AdmissionDecision,
    QualityTier,
    SpeakerQualityGate,
)

_TRANSFORMERS_PIPELINE_IMPORT_LOCK = Lock()


@runtime_checkable
class WhisperPipelineProtocol(Protocol):
    """Minimal Hugging Face ASR pipeline surface used by the scorer."""

    def __call__(
        self,
        inputs: object,
        *,
        generate_kwargs: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Run ASR on one input and return the structured pipeline payload."""


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
    """Assign the fixed quality tier for one WER score."""
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
    """Map quality and speaker gates to one bounded admission decision."""
    if quality_tier in {"high_trust", "medium_trust"} and speaker_quality_gate == "speaker_from_id":
        return "admit"
    return "reject"


@dataclass
class WhisperStrictScorer:
    """Lazy Swedish ASR scorer backed by `KBLab/kb-whisper-large` strict."""

    model_id: str
    revision: str
    _pipeline: object | None = None
    _load_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def ensure_loaded(self) -> None:
        """Initialize the cached pipeline eagerly when a caller wants warm startup."""
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        import torch

        if self._pipeline is not None:
            return
        with self._load_lock:
            if self._pipeline is not None:
                return
            with _TRANSFORMERS_PIPELINE_IMPORT_LOCK:
                from transformers import pipeline

            dtype = torch.float16 if torch.cuda.is_available() else torch.float32
            device = 0 if torch.cuda.is_available() else -1
            self._pipeline = pipeline(
                task="automatic-speech-recognition",
                model=self.model_id,
                revision=self.revision,
                dtype=dtype,
                device=device,
            )

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe one canonical 24 kHz audio artifact into Swedish text."""
        self._ensure_loaded()
        if self._pipeline is None:
            raise RuntimeError("ASR scorer failed to initialize its pipeline state.")
        if not isinstance(self._pipeline, WhisperPipelineProtocol):
            raise RuntimeError("ASR scorer initialized an unexpected pipeline object.")
        payload = self._pipeline(
            audio_path.as_posix(),
            generate_kwargs={"task": "transcribe"},
        )
        rendered_text = payload.get("text")
        if not isinstance(rendered_text, str) or rendered_text.strip() == "":
            raise RuntimeError(f"ASR transcription returned no text for {audio_path}.")
        return rendered_text.strip()
