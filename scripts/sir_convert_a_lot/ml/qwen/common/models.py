"""Shared data models for the Qwen ML pipeline infrastructure.

Purpose:
    Provide stable, SRP-aligned data contracts for Docker runtime, cache
    mounting, and image-build orchestration shared across preprocessing and
    training domains.

Relationships:
    - Consumed by `ml.qwen.common.runtime` and `ml.qwen.common.storage`.
    - Consumed by domain-specific orchestrators in `ml.qwen.preprocessing` and
      `ml.qwen.training`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Protocol


@dataclass(frozen=True)
class MountResolution:
    """Resolved host path used for one Docker-visible persistent cache."""

    canonical_root: Path
    effective_root: Path
    used_home_mount: bool


@dataclass(frozen=True)
class QwenImageBuildPlan:
    """Planned image-build state for one Qwen runtime image request."""

    image_present: bool
    existing_image_id: str | None
    build_required: bool


class QwenImageSettings(Protocol):
    """Minimal image-build settings shared across Qwen container runners."""

    @property
    def dockerfile_path(self) -> Path:
        """Return the Dockerfile path for the shared Qwen runtime image."""

    @property
    def image(self) -> str:
        """Return the image tag for the shared Qwen runtime image."""

    @property
    def build_image(self) -> bool:
        """Return whether the shared Qwen runtime image should be rebuilt."""


class QwenCacheSettings(Protocol):
    """Minimal cache-mount settings shared across Qwen container runners."""

    @property
    def image(self) -> str:
        """Return the image tag for Docker bind-mount cache probes."""

    @property
    def hf_cache_dir(self) -> Path:
        """Return the canonical Hugging Face cache root."""

    @property
    def hf_cache_home_mount(self) -> Path:
        """Return the home-backed fallback mount for the HF cache root."""


# --- Shared ML Domain Constants and Types ---

ManifestFamily = Literal[
    "swedish_smoke_train",
    "swedish_pilot_train",
    "swedish_scaleup_train",
    "swedish_checkpoint_dev",
    "swedish_final_test",
    "swedish_waxholm_control",
]

CANONICAL_MANIFEST_FAMILIES: tuple[ManifestFamily, ...] = (
    "swedish_smoke_train",
    "swedish_pilot_train",
    "swedish_scaleup_train",
    "swedish_checkpoint_dev",
    "swedish_final_test",
    "swedish_waxholm_control",
)


CANONICAL_SAMPLE_RATE_HZ = 24_000


@dataclass(frozen=True)
class AudioLocator:
    """Describe one locally available audio source or one audio member in an archive."""

    path: Path
    archive_member: str | None = None

    def render_source_path(self) -> str:
        """Render one stable source-path identifier for manifests and reports."""
        if self.archive_member is None:
            return self.path.as_posix()
        return f"{self.path.as_posix()}::{self.archive_member}"


@dataclass(frozen=True)
class SourceRecord:
    """Represent one dataset-native source row before family assignment."""

    dataset: str
    source_split: str
    dataset_row_id: str
    speaker_id: str
    speaker_name: str
    speaker_from_id: bool
    source_audio_path: str
    text_raw: str
    language: str
    speaker_total_hours: float | None
    has_label_files: bool
    speaker_audio_meta_ok: bool
    source_audio_locator: AudioLocator | None = None
    reference_audio_locator: AudioLocator | None = None
    source_sample_rate_hz: int | None = None
    duration_seconds: float | None = None
    boilerplate_group: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class RowProcessingHeartbeat:
    """Row-processing heartbeat for durable status updates."""

    processed_row_count: int
    total_row_count: int
    current_dataset_row_id: str


@dataclass(frozen=True)
class FinalizationHeartbeat:
    """Finalization heartbeat for family/chunk-aware status updates."""

    current_family: ManifestFamily
    completed_families: tuple[ManifestFamily, ...]
    current_chunk_index: int
    completed_chunk_count: int
    total_chunk_count: int


def audio_locator_to_payload(audio_locator: AudioLocator | None) -> dict[str, object] | None:
    """Render one optional audio locator into a JSON-serializable payload."""
    if audio_locator is None:
        return None
    return {
        "path": audio_locator.path.as_posix(),
        "archive_member": audio_locator.archive_member,
    }


def audio_locator_from_payload(payload: object) -> AudioLocator | None:
    """Parse one optional audio-locator payload back into the typed contract."""
    if payload is None:
        return None
    if not isinstance(payload, Mapping):
        raise ValueError("Audio locator payload must be a mapping or null.")
    path_value = payload.get("path")
    archive_member_value = payload.get("archive_member")
    if not isinstance(path_value, str):
        raise ValueError("Audio locator payload must include a string `path`.")
    if archive_member_value is not None and not isinstance(archive_member_value, str):
        raise ValueError("Audio locator `archive_member` must be a string or null.")
    return AudioLocator(path=Path(path_value), archive_member=archive_member_value)


def source_record_to_payload(source_record: SourceRecord) -> dict[str, object]:
    """Render one source record into a JSON-serializable payload."""
    return {
        "dataset": source_record.dataset,
        "source_split": source_record.source_split,
        "dataset_row_id": source_record.dataset_row_id,
        "speaker_id": source_record.speaker_id,
        "speaker_name": source_record.speaker_name,
        "speaker_from_id": source_record.speaker_from_id,
        "source_audio_path": source_record.source_audio_path,
        "text_raw": source_record.text_raw,
        "language": source_record.language,
        "speaker_total_hours": source_record.speaker_total_hours,
        "has_label_files": source_record.has_label_files,
        "speaker_audio_meta_ok": source_record.speaker_audio_meta_ok,
        "source_audio_locator": audio_locator_to_payload(source_record.source_audio_locator),
        "reference_audio_locator": audio_locator_to_payload(source_record.reference_audio_locator),
        "source_sample_rate_hz": source_record.source_sample_rate_hz,
        "duration_seconds": source_record.duration_seconds,
        "boilerplate_group": source_record.boilerplate_group,
        "notes": source_record.notes,
    }


def source_record_from_payload(payload: object) -> SourceRecord:
    """Parse one JSON source-record payload back into the typed contract."""
    if not isinstance(payload, Mapping):
        raise ValueError("Source record payload must be a mapping.")
    dataset = payload.get("dataset")
    source_split = payload.get("source_split")
    dataset_row_id = payload.get("dataset_row_id")
    speaker_id = payload.get("speaker_id")
    speaker_name = payload.get("speaker_name")
    speaker_from_id = payload.get("speaker_from_id")
    source_audio_path = payload.get("source_audio_path")
    text_raw = payload.get("text_raw")
    language = payload.get("language")
    has_label_files = payload.get("has_label_files")
    speaker_audio_meta_ok = payload.get("speaker_audio_meta_ok")
    speaker_total_hours = payload.get("speaker_total_hours")
    source_sample_rate_hz = payload.get("source_sample_rate_hz")
    duration_seconds = payload.get("duration_seconds")
    boilerplate_group = payload.get("boilerplate_group")
    notes = payload.get("notes")
    if not isinstance(dataset, str):
        raise ValueError("Source record `dataset` must be a string.")
    if not isinstance(source_split, str):
        raise ValueError("Source record `source_split` must be a string.")
    if not isinstance(dataset_row_id, str):
        raise ValueError("Source record `dataset_row_id` must be a string.")
    if not isinstance(speaker_id, str):
        raise ValueError("Source record `speaker_id` must be a string.")
    if not isinstance(speaker_name, str):
        raise ValueError("Source record `speaker_name` must be a string.")
    if not isinstance(speaker_from_id, bool):
        raise ValueError("Source record `speaker_from_id` must be a bool.")
    if not isinstance(source_audio_path, str):
        raise ValueError("Source record `source_audio_path` must be a string.")
    if not isinstance(text_raw, str):
        raise ValueError("Source record `text_raw` must be a string.")
    if not isinstance(language, str):
        raise ValueError("Source record `language` must be a string.")
    if not isinstance(has_label_files, bool):
        raise ValueError("Source record `has_label_files` must be a bool.")
    if not isinstance(speaker_audio_meta_ok, bool):
        raise ValueError("Source record `speaker_audio_meta_ok` must be a bool.")
    if speaker_total_hours is not None and not isinstance(speaker_total_hours, (int, float)):
        raise ValueError("Source record `speaker_total_hours` must be numeric or null.")
    if source_sample_rate_hz is not None and not isinstance(source_sample_rate_hz, int):
        raise ValueError("Source record `source_sample_rate_hz` must be an int or null.")
    if duration_seconds is not None and not isinstance(duration_seconds, (int, float)):
        raise ValueError("Source record `duration_seconds` must be numeric or null.")
    if boilerplate_group is not None and not isinstance(boilerplate_group, str):
        raise ValueError("Source record `boilerplate_group` must be a string or null.")
    if notes is not None and not isinstance(notes, str):
        raise ValueError("Source record `notes` must be a string or null.")
    return SourceRecord(
        dataset=dataset,
        source_split=source_split,
        dataset_row_id=dataset_row_id,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        speaker_from_id=speaker_from_id,
        source_audio_path=source_audio_path,
        text_raw=text_raw,
        language=language,
        speaker_total_hours=(None if speaker_total_hours is None else float(speaker_total_hours)),
        has_label_files=has_label_files,
        speaker_audio_meta_ok=speaker_audio_meta_ok,
        source_audio_locator=audio_locator_from_payload(payload.get("source_audio_locator")),
        reference_audio_locator=audio_locator_from_payload(payload.get("reference_audio_locator")),
        source_sample_rate_hz=source_sample_rate_hz,
        duration_seconds=None if duration_seconds is None else float(duration_seconds),
        boilerplate_group=boilerplate_group,
        notes=notes,
    )
