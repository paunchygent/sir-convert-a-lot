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
