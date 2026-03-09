"""Source models for Task 103 and Task 106 Qwen Swedish corpus adapters.

Purpose:
    Define the adapter-facing source contracts used to inventory, curate, and
    materialize Swedish speech corpora for the Qwen preprocessing pipeline.

Relationships:
    - Produced by dataset adapters such as `task103_qwen_source_fleurs.py`,
      `task103_qwen_source_waxholm.py`, `task103_qwen_source_rixvox.py`, and
      `task103_qwen_source_repo_fixture.py`.
    - Consumed by `task103_qwen_preprocessing_core.py`, which owns family
      assignment, audio normalization, ASR scoring, and manifest output.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


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


def source_record_from_payload(payload: Mapping[str, object]) -> SourceRecord:
    """Parse one serialized source-record payload into the typed contract."""
    return SourceRecord(
        dataset=_required_str(payload, "dataset"),
        source_split=_required_str(payload, "source_split"),
        dataset_row_id=_required_str(payload, "dataset_row_id"),
        speaker_id=_required_str(payload, "speaker_id"),
        speaker_name=_required_str(payload, "speaker_name"),
        speaker_from_id=_required_bool(payload, "speaker_from_id"),
        source_audio_path=_required_str(payload, "source_audio_path"),
        text_raw=_required_str(payload, "text_raw"),
        language=_required_str(payload, "language"),
        speaker_total_hours=_optional_float(payload.get("speaker_total_hours")),
        has_label_files=_required_bool(payload, "has_label_files"),
        speaker_audio_meta_ok=_required_bool(payload, "speaker_audio_meta_ok"),
        source_audio_locator=audio_locator_from_payload(payload.get("source_audio_locator")),
        reference_audio_locator=audio_locator_from_payload(payload.get("reference_audio_locator")),
        source_sample_rate_hz=_optional_int(payload.get("source_sample_rate_hz")),
        duration_seconds=_optional_float(payload.get("duration_seconds")),
        boilerplate_group=_optional_str(payload.get("boilerplate_group")),
        notes=_optional_str(payload.get("notes")),
    )


def _required_str(payload: Mapping[str, object], key: str) -> str:
    """Return one required string field from a serialized source-record payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Source record payload must include string `{key}`.")
    return value


def _required_bool(payload: Mapping[str, object], key: str) -> bool:
    """Return one required boolean field from a serialized source-record payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Source record payload must include boolean `{key}`.")
    return value


def _optional_str(value: object) -> str | None:
    """Return one optional string field from a serialized source-record payload."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Optional source-record string field had the wrong type.")
    return value


def _optional_int(value: object) -> int | None:
    """Return one optional integer field from a serialized source-record payload."""
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValueError("Optional source-record integer field had the wrong type.")
    return value


def _optional_float(value: object) -> float | None:
    """Return one optional float-like field from a serialized source-record payload."""
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise ValueError("Optional source-record float field had the wrong type.")
    return float(value)
