"""RixVox metadata adapter for the Qwen corpus pipeline.

Purpose:
    Ingest `KBLab/rixvox` metadata from parquet files so the preprocessing
    pipeline can inventory and reason about Swedish parliamentary speech.

Relationships:
    - Consumed by the preprocessing pipeline for inventory and future
      curation.
    - Uses `huggingface_hub` for raw parquet acquisition and emits
      `SourceRecord` rows from `ml.qwen.common.models`.
"""

from __future__ import annotations

import tarfile
from dataclasses import replace
from pathlib import Path
from typing import Callable, Collection, Final, Mapping, Sequence

import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.ml.qwen.common.models import AudioLocator, SourceRecord

RIXVOX_DATASET_ID: Final[str] = "KBLab/rixvox"
RIXVOX_ALLOWED_SPLITS: Final[tuple[str, ...]] = ("train", "dev", "test")
RIXVOX_SOURCE_SAMPLE_RATE_HZ: Final[int] = 16_000
BatchProgressCallback = Callable[[int, int], None]
LocatorProgressCallback = Callable[[int, int], None]


def download_rixvox_metadata_file(
    *,
    split: str,
    revision: str | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Download one revision-pinned RixVox metadata parquet file."""
    if split not in RIXVOX_ALLOWED_SPLITS:
        raise ValueError(f"Unsupported RixVox split: {split}")
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
    include_metadata_only_rows: bool = True,
    max_rows: int | None = None,
    batch_progress_callback: BatchProgressCallback | None = None,
) -> list[SourceRecord]:
    """Parse RixVox rows with optional staged audio-locator resolution."""
    if split not in RIXVOX_ALLOWED_SPLITS:
        raise ValueError(f"Unsupported RixVox split: {split}")
    if max_rows is not None and max_rows <= 0:
        raise ValueError("`max_rows` must be positive when provided.")
    parquet_file = pq.ParquetFile(parquet_path)
    source_records: list[SourceRecord] = []
    for batch_index, batch in enumerate(parquet_file.iter_batches(), start=1):
        for row in batch.to_pylist():
            source_record = _source_record_from_parquet_row(
                row,
                split=split,
                audio_locators_by_source_path=audio_locators_by_source_path,
                include_metadata_only_rows=include_metadata_only_rows,
            )
            if source_record is None:
                continue
            source_records.append(source_record)
            if max_rows is not None and len(source_records) >= max_rows:
                if batch_progress_callback is not None:
                    batch_progress_callback(batch_index, len(source_records))
                return source_records
        if batch_progress_callback is not None:
            batch_progress_callback(batch_index, len(source_records))
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


def attach_audio_locators_to_source_records(
    source_records: Sequence[SourceRecord],
    *,
    audio_locators_by_source_path: Mapping[str, AudioLocator],
    include_metadata_only_rows: bool,
) -> list[SourceRecord]:
    """Attach one bounded audio-locator mapping to preselected source records."""
    attached_source_records: list[SourceRecord] = []
    for source_record in source_records:
        source_audio_locator = audio_locators_by_source_path.get(source_record.source_audio_path)
        if source_audio_locator is None and not include_metadata_only_rows:
            continue
        attached_source_records.append(
            replace(source_record, source_audio_locator=source_audio_locator)
        )
    return attached_source_records


def build_rixvox_audio_locator_index(
    archive_paths: Sequence[Path],
    *,
    required_source_paths: Collection[str] | None = None,
    progress_callback: LocatorProgressCallback | None = None,
) -> dict[str, AudioLocator]:
    """Index staged RixVox tar members by dataset-relative filename."""
    audio_locators_by_source_path: dict[str, AudioLocator] = {}
    unresolved_required_paths = (
        None if required_source_paths is None else set(required_source_paths)
    )
    required_count = 0 if unresolved_required_paths is None else len(unresolved_required_paths)
    for archive_path in archive_paths:
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = member.name.strip()
                if not member_name.endswith(".wav"):
                    continue
                if (
                    unresolved_required_paths is not None
                    and member_name not in unresolved_required_paths
                ):
                    continue
                audio_locators_by_source_path.setdefault(
                    member_name,
                    AudioLocator(path=archive_path, archive_member=member_name),
                )
                if unresolved_required_paths is not None:
                    unresolved_required_paths.discard(member_name)
                    if progress_callback is not None:
                        progress_callback(
                            required_count - len(unresolved_required_paths),
                            required_count,
                        )
                    if not unresolved_required_paths:
                        return audio_locators_by_source_path
    if progress_callback is not None and unresolved_required_paths is not None:
        progress_callback(required_count - len(unresolved_required_paths), required_count)
    return audio_locators_by_source_path


def _source_record_from_parquet_row(
    row: Mapping[str, object],
    *,
    split: str,
    audio_locators_by_source_path: Mapping[str, AudioLocator] | None,
    include_metadata_only_rows: bool,
) -> SourceRecord | None:
    """Build one typed source record from a parquet row payload."""
    intressent_id = str(row["intressent_id"]).strip()
    speaker_slug = intressent_id if intressent_id != "" else _slugify_speaker(str(row["speaker"]))
    dataset_row_id = f"{row['dokid']}-{row['anforande_nummer']}-{row['observation_nr']}"
    bleu_score = _required_float(row, "bleu_score")
    speaker_audio_meta = str(row["speaker_audio_meta"]).strip()
    filename = str(row["filename"]).strip()
    source_audio_locator = None
    if audio_locators_by_source_path is not None:
        source_audio_locator = audio_locators_by_source_path.get(filename)
        if source_audio_locator is None and not include_metadata_only_rows:
            return None
    return SourceRecord(
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
        speaker_total_hours=round(_required_float(row, "speaker_total_hours"), 6),
        has_label_files=False,
        speaker_audio_meta_ok=speaker_audio_meta != "",
        source_sample_rate_hz=RIXVOX_SOURCE_SAMPLE_RATE_HZ,
        duration_seconds=round(_required_float(row, "duration"), 6),
        notes=f"bleu_score={bleu_score:.6f};speaker_audio_meta={speaker_audio_meta}",
    )


def _required_float(row: Mapping[str, object], key: str) -> float:
    """Read one required numeric parquet field as float."""
    value = row[key]
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"Expected numeric RixVox field `{key}`, got {type(value).__name__}.")
    return float(value)


def _slugify_speaker(speaker_name: str) -> str:
    """Build one stable fallback speaker slug from a human-readable speaker name."""
    letters_only = [
        character.lower() if character.isalnum() else "_" for character in speaker_name.strip()
    ]
    slug = "".join(letters_only).strip("_")
    return "_".join(part for part in slug.split("_") if part != "")
