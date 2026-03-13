"""Data contracts for the Qwen preprocessing pipeline.

Purpose:
    Define the typed row, manifest, report, and runtime-setting contracts used
    by the staged Swedish Qwen preprocessing pipeline.

Relationships:
    - Consumes base families and heartbeats from `ml.qwen.common.models`.
    - Imported by the preprocessing pipeline facade and stage-oriented modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, TypedDict

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    CANONICAL_MANIFEST_FAMILIES,
    FinalizationHeartbeat,
    ManifestFamily,
    RowProcessingHeartbeat,
)

# --- Preprocessing Specific Constants ---
HIGH_TRUST_WER_MAX = 0.15
MEDIUM_TRUST_WER_MAX = 0.20

QualityTier = Literal["high_trust", "medium_trust", "rejected"]
SpeakerQualityGate = Literal["speaker_from_id", "manual_review", "rejected_multi_speaker"]
AdmissionDecision = Literal["admit", "reject"]
PreprocessingStage = Literal["all", "source-selection", "row-processing", "finalization", "reports"]


class RawManifestRow(TypedDict):
    """Raw Qwen manifest row emitted before `audio_codes` are generated."""

    audio: str
    text: str
    ref_audio: str
    speaker_id: str
    dataset: str
    source_split: str
    quality_tier: QualityTier


@dataclass(frozen=True)
class InventoryRow:
    """One deterministic inventory row before curation."""

    dataset: str
    source_split: str
    dataset_row_id: str
    source_audio_path: str
    source_sample_rate_hz: int
    duration_seconds: float
    text_raw: str
    text_normalized: str
    speaker_id: str
    speaker_name: str
    speaker_from_id: bool
    speaker_total_hours: float
    language: str
    has_label_files: bool
    speaker_audio_meta_ok: bool
    boilerplate_group: str | None
    notes: str | None


@dataclass(frozen=True)
class CuratedRow:
    """One deterministic curated row after filtering and scoring."""

    dataset: str
    source_split: str
    dataset_row_id: str
    speaker_id: str
    speaker_name: str
    speaker_from_id: bool
    source_audio_path: str
    audio_24k_path: str
    duration_seconds: float
    text_normalized: str
    reference_audio_24k_path: str
    asr_model: str
    asr_revision: str
    asr_transcript: str
    asr_wer: float
    quality_tier: QualityTier
    speaker_quality_gate: SpeakerQualityGate
    dedup_applied: bool
    admission_decision: AdmissionDecision
    manifest_target: ManifestFamily


@dataclass(frozen=True)
class PreparedManifestRow:
    """One Qwen-ready prepared manifest row with `audio_codes`."""

    audio: str
    text: str
    ref_audio: str
    speaker_id: str
    dataset: str
    source_split: str
    quality_tier: QualityTier
    audio_codes: list[list[int]]


@dataclass(frozen=True)
class SpoolRow:
    """One durable row-processing result used by later finalization."""

    dataset: str
    source_split: str
    dataset_row_id: str
    speaker_id: str
    speaker_name: str
    speaker_from_id: bool
    source_audio_path: str
    audio_24k_path: str
    duration_seconds: float
    text_normalized: str
    reference_audio_24k_paths: dict[ManifestFamily, str]
    asr_model: str
    asr_revision: str
    asr_transcript: str
    asr_wer: float
    quality_tier: QualityTier
    speaker_quality_gate: SpeakerQualityGate
    dedup_applied: bool
    admission_decision: AdmissionDecision
    manifest_targets: tuple[ManifestFamily, ...]


@dataclass(frozen=True)
class AudioCodesRuntimeSettings:
    """Settings for the in-container audio-code generation batch."""

    dockerfile_path: Path = Path("containers/qwen-finetune-hemma/Dockerfile")
    image: str = "qwen-finetune-hemma:latest"
    build_image: bool = False
    hf_cache_dir: Path = Path("/srv/storage/sir-convert-a-lot/cache/huggingface")
    hf_cache_home_mount: Path = Path("/home/paunchygent/cache/huggingface")


@dataclass(frozen=True)
class PreprocessingSettings:
    """Normalized preprocessing runtime settings."""

    output_root: Path
    asr_model: str
    asr_revision: str
    tokenizer_model: str
    stage: PreprocessingStage = "all"
    finalization_families: tuple[ManifestFamily, ...] = CANONICAL_MANIFEST_FAMILIES
    audio_codes_chunk_size: int = 8
    audio_codes_runtime: AudioCodesRuntimeSettings = field(
        default_factory=AudioCodesRuntimeSettings
    )
    row_worker_count: int = 1
    gpu_asr_worker_count: int = 1
    resume_row_processing: bool = False


@dataclass(frozen=True)
class PreprocessingReport:
    """Top-level report for one preprocessing pass."""

    output_root: str
    datasets: list[str]
    asr_model: str
    asr_revision: str
    tokenizer_model: str
    inventory_rows: int
    curated_rows: int
    admitted_rows: int
    prepared_rows: int
    speaker_ids: list[str]
    manifest_counts: dict[ManifestFamily, int]


RowHeartbeatCallback = Callable[[RowProcessingHeartbeat], None]
FinalizationHeartbeatCallback = Callable[[FinalizationHeartbeat], None]
