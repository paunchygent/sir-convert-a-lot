"""Script-free RixVox metadata adapter for the Task 106 Qwen corpus lane.

Purpose:
    Ingest `KBLab/rixvox` metadata from parquet files so the preprocessing
    pipeline can inventory and reason about real Swedish training rows without
    depending on deprecated dataset scripts.

Relationships:
    - Consumed by `task103_qwen_preprocessing_core.py` for inventory and future
      curation of real Swedish parliamentary speech.
    - Uses `huggingface_hub` for raw parquet acquisition and emits
      `SourceRecord` rows from `task103_qwen_source_models.py`.
"""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import Final, Mapping, Sequence

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import AudioLocator, SourceRecord

RIXVOX_DATASET_ID: Final[str] = "KBLab/rixvox"
RIXVOX_ALLOWED_SPLITS: Final[tuple[str, ...]] = ("train", "dev", "test")
RIXVOX_SOURCE_SAMPLE_RATE_HZ: Final[int] = 16_000


def download_rixvox_metadata_file(
    *,
    split: str,
    revision: str | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Download one revision-pinned RixVox metadata parquet file."""
    if split not in RIXVOX_ALLOWED_SPLITS:
        raise ValueError(f"Unsupported RixVox split for Task 106: {split}")
    parquet_path = hf_hub_download(
        repo_id=RIXVOX_DATASET_ID,
        repo_type="dataset",
        revision=revision,
        filename=f"data/{split}_metadata.parquet",
        cache_dir=None if cache_dir is None else cache_dir.as_posix(),
    )
    return Path(parquet_path)


def rixvox_source_records_from_parquet(parquet_path: Path, *, split: str) -> list[SourceRecord]:
    """Parse inventory-capable RixVox rows from one metadata parquet file."""
    return rixvox_source_records_from_parquet_with_audio_locators(
        parquet_path,
        split=split,
        audio_locators_by_source_path=None,
    )


def rixvox_source_records_from_parquet_with_audio_locators(
    parquet_path: Path,
    *,
    split: str,
    audio_locators_by_source_path: Mapping[str, AudioLocator] | None,
) -> list[SourceRecord]:
    """Parse RixVox rows with optional staged audio-locator resolution."""
    if split not in RIXVOX_ALLOWED_SPLITS:
        raise ValueError(f"Unsupported RixVox split for Task 106: {split}")
    parquet_file = pq.ParquetFile(parquet_path)
    source_records: list[SourceRecord] = []
    for batch in parquet_file.iter_batches():
        for row in batch.to_pylist():
            intressent_id = str(row["intressent_id"]).strip()
            speaker_slug = (
                intressent_id
                if intressent_id != ""
                else _slugify_speaker(str(row["speaker"]))
            )
            dataset_row_id = f"{row['dokid']}-{row['anforande_nummer']}-{row['observation_nr']}"
            bleu_score = float(row["bleu_score"])
            speaker_audio_meta = str(row["speaker_audio_meta"]).strip()
            filename = str(row["filename"]).strip()
            source_audio_locator = None
            if audio_locators_by_source_path is not None:
                source_audio_locator = audio_locators_by_source_path.get(filename)
            source_records.append(
                SourceRecord(
                    dataset="rixvox",
                    source_split=split,
                    dataset_row_id=dataset_row_id,
                    speaker_id=f"rixvox_{speaker_slug}",
                    speaker_name=str(row["speaker"]).strip(),
                    speaker_from_id=bool(row["speaker_from_id"]),
                    source_audio_path=filename,
                    source_audio_locator=source_audio_locator,
                    text_raw=str(row["text"]).strip(),
                    language="sv-SE",
                    speaker_total_hours=round(float(row["speaker_total_hours"]), 6),
                    has_label_files=False,
                    speaker_audio_meta_ok=speaker_audio_meta != "",
                    source_sample_rate_hz=RIXVOX_SOURCE_SAMPLE_RATE_HZ,
                    duration_seconds=round(float(row["duration"]), 6),
                    notes=(
                        f"bleu_score={bleu_score:.6f};"
                        f"speaker_audio_meta={speaker_audio_meta}"
                    ),
                )
            )
    return source_records


def download_rixvox_source_records(
    *,
    splits: Sequence[str],
    revision: str | None = None,
    cache_dir: Path | None = None,
) -> list[SourceRecord]:
    """Download and parse one or more RixVox metadata parquet files."""
    source_records: list[SourceRecord] = []
    for split in splits:
        parquet_path = download_rixvox_metadata_file(
            split=split,
            revision=revision,
            cache_dir=cache_dir,
        )
        source_records.extend(rixvox_source_records_from_parquet(parquet_path, split=split))
    return source_records


def build_rixvox_audio_locator_index(archive_paths: Sequence[Path]) -> dict[str, AudioLocator]:
    """Index staged RixVox tar members by dataset-relative filename."""
    audio_locators_by_source_path: dict[str, AudioLocator] = {}
    for archive_path in archive_paths:
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = member.name.strip()
                if not member_name.endswith(".wav"):
                    continue
                audio_locators_by_source_path.setdefault(
                    member_name,
                    AudioLocator(path=archive_path, archive_member=member_name),
                )
    return audio_locators_by_source_path


def _slugify_speaker(speaker_name: str) -> str:
    """Build one stable fallback speaker slug from a human-readable speaker name."""
    letters_only = [
        character.lower() if character.isalnum() else "_"
        for character in speaker_name.strip()
    ]
    slug = "".join(letters_only).strip("_")
    return "_".join(part for part in slug.split("_") if part != "")
