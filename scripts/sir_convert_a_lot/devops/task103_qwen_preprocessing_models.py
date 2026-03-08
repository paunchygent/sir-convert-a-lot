"""Contracts for the Task 103/T110 staged Qwen preprocessing pipeline.

Purpose:
    Define the typed row, manifest, report, and runtime-setting contracts used
    by the staged Swedish Qwen preprocessing pipeline.

Relationships:
    - Imported by the Task 103 core facade and the staged preprocessing
      modules.
    - Shared by row-processing, finalization, and reporting helpers so the
      pipeline can be modularized without duplicating schema definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import ManifestFamily

CANONICAL_SAMPLE_RATE_HZ = 24_000
HIGH_TRUST_WER_MAX = 0.15
MEDIUM_TRUST_WER_MAX = 0.20
CANONICAL_MANIFEST_FAMILIES: tuple[ManifestFamily, ...] = (
    "swedish_smoke_train",
    "swedish_pilot_train",
    "swedish_scaleup_train",
    "swedish_checkpoint_dev",
    "swedish_final_test",
    "swedish_waxholm_control",
)

QualityTier = Literal["high_trust", "medium_trust", "rejected"]
SpeakerQualityGate = Literal["speaker_from_id", "manual_review", "rejected_multi_speaker"]
AdmissionDecision = Literal["admit", "reject"]
Task103Stage = Literal["all", "row-processing", "finalization"]


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
class Task103PreprocessingSettings:
    """Normalized Task 103 runtime settings."""

    output_root: Path
    asr_model: str
    asr_revision: str
    tokenizer_model: str
    stage: Task103Stage = "all"
    finalization_families: tuple[ManifestFamily, ...] = CANONICAL_MANIFEST_FAMILIES
    audio_codes_chunk_size: int = 8


@dataclass(frozen=True)
class Task103PreprocessingReport:
    """Top-level report for one Task 103 preprocessing pass."""

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
