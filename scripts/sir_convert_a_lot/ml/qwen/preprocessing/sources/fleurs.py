"""FLEURS Swedish source adapter for the Qwen corpus pipeline.

Purpose:
    Ingest `google/fleurs` Swedish (`sv_se`) rows from revision-pinned raw TSV
    files and audio tar archives.

Relationships:
    - Consumed by the preprocessing pipeline for real public-corpus source
      enumeration.
    - Uses `huggingface_hub` for snapshot acquisition and emits `SourceRecord`
      rows from `ml.qwen.common.models`.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Final, Sequence

from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.ml.qwen.common.models import AudioLocator, SourceRecord

FLEURS_DATASET_ID: Final[str] = "google/fleurs"
FLEURS_SV_CONFIG: Final[str] = "sv_se"
FLEURS_SAMPLE_RATE_HZ: Final[int] = 16_000
FLEURS_ALLOWED_SPLITS: Final[tuple[str, ...]] = ("dev", "test")


def download_fleurs_sv_file(
    *,
    filename: str,
    revision: str | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Download one revision-pinned Swedish FLEURS file via targeted acquisition."""
    downloaded_path = hf_hub_download(
        repo_id=FLEURS_DATASET_ID,
        repo_type="dataset",
        revision=revision,
        filename=filename,
        cache_dir=None if cache_dir is None else cache_dir.as_posix(),
    )
    return Path(downloaded_path)


def fleurs_sv_source_records(
    snapshot_root: Path,
    *,
    splits: Sequence[str] = FLEURS_ALLOWED_SPLITS,
) -> list[SourceRecord]:
    """Parse `sv_se` FLEURS rows from one local snapshot root."""
    requested_splits = tuple(splits)
    invalid_splits = sorted(set(requested_splits) - set(FLEURS_ALLOWED_SPLITS))
    if invalid_splits:
        raise ValueError(f"Unsupported FLEURS splits: {invalid_splits}")

    parsed_rows: list[tuple[str, list[str]]] = []
    speaker_total_seconds: dict[str, float] = defaultdict(float)
    for split in requested_splits:
        tsv_path = snapshot_root / f"data/{FLEURS_SV_CONFIG}/{split}.tsv"
        if not tsv_path.is_file():
            raise FileNotFoundError(f"Missing FLEURS TSV file: {tsv_path}")
        for row in _iter_fleurs_tsv_rows(tsv_path):
            speaker_id_raw = row[0]
            sample_count = row[5]
            parsed_rows.append((split, row))
            duration_seconds = int(sample_count) / FLEURS_SAMPLE_RATE_HZ
            speaker_total_seconds[speaker_id_raw] += duration_seconds

    source_records: list[SourceRecord] = []
    for split, row in parsed_rows:
        speaker_id_raw, filename, text_raw, text_normalized, phones, sample_count, gender = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
        )
        del text_normalized
        del phones
        duration_seconds = round(int(sample_count) / FLEURS_SAMPLE_RATE_HZ, 6)
        archive_path = snapshot_root / f"data/{FLEURS_SV_CONFIG}/audio/{split}.tar.gz"
        if not archive_path.is_file():
            raise FileNotFoundError(f"Missing FLEURS audio archive: {archive_path}")
        speaker_total_hours = round(speaker_total_seconds[speaker_id_raw] / 3600.0, 6)
        speaker_id = f"fleurs_sv_se_{speaker_id_raw}"
        source_records.append(
            SourceRecord(
                dataset="fleurs_sv_se",
                source_split=split,
                dataset_row_id=f"{split}-{speaker_id_raw}-{filename.removesuffix('.wav')}",
                speaker_id=speaker_id,
                speaker_name=f"FLEURS speaker {speaker_id_raw}",
                speaker_from_id=True,
                source_audio_path=f"{archive_path.as_posix()}::{split}/{filename}",
                source_audio_locator=AudioLocator(
                    archive_path,
                    archive_member=f"{split}/{filename}",
                ),
                text_raw=text_raw,
                language="sv-SE",
                speaker_total_hours=speaker_total_hours,
                has_label_files=True,
                speaker_audio_meta_ok=True,
                source_sample_rate_hz=FLEURS_SAMPLE_RATE_HZ,
                duration_seconds=duration_seconds,
                notes=f"gender:{gender}",
            )
        )
    return source_records


def _iter_fleurs_tsv_rows(tsv_path: Path) -> list[list[str]]:
    """Parse one raw FLEURS TSV file without CSV quote semantics."""
    rows: list[list[str]] = []
    for raw_line in tsv_path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip() == "":
            continue
        row = raw_line.split("\t")
        if len(row) != 7:
            raise ValueError(f"Unexpected FLEURS TSV row width {len(row)} in {tsv_path}")
        rows.append(row)
    return rows
