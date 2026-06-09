"""Runtime helpers for bounded RixVox train staging on Hemma.

Purpose:
    Stage revision-pinned `KBLab/rixvox` train metadata and a bounded set of
    train audio archives onto Hemma's HDD bulk-data tier so the Qwen
    preprocessing lane can move from metadata-only inventory to real
    audio-backed train rows.

Relationships:
    - Used by `cli.ml.qwen_rixvox_train_staging`.
    - Reuses the revision-pinned Hugging Face download helpers from
      `ml.qwen.preprocessing.acquisition`.
    - Feeds later preprocessing work through `ml.qwen.preprocessing.public_corpus`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.preprocessing.acquisition import (
    DownloadedFileRecord,
    download_file_with_retry,
    ensure_bulk_data_storage_path,
    ensure_data_disk_path,
    resolve_dataset_revision,
    stage_downloaded_file,
)

RIXVOX_DATASET_ID = "KBLab/rixvox"


@dataclass(frozen=True)
class RixvoxTrainStagingSettings:
    """Normalized settings for the bounded RixVox train-staging surface."""

    output_root: Path
    data_root: Path
    hf_cache_dir: Path
    train_audio_shards: tuple[int, ...]
    request_pause_seconds: float
    max_retries: int


@dataclass(frozen=True)
class RixvoxTrainStagingReport:
    """Deterministic report contract for one bounded RixVox staging pass."""

    data_root: str
    hf_cache_dir: str
    dataset_revision: str
    train_audio_shards: list[int]
    downloaded_files: list[DownloadedFileRecord]
    train_metadata_staged: bool
    train_audio_archive_count: int


def normalize_train_audio_shards(train_audio_shards: tuple[int, ...]) -> tuple[int, ...]:
    """Normalize one bounded list of RixVox train shard ids."""
    if not train_audio_shards:
        raise SystemExit("Rixvox staging requires at least one `train_audio_shard`.")
    normalized_shards = tuple(sorted(set(train_audio_shards)))
    if any(shard < 0 for shard in normalized_shards):
        raise SystemExit("Rixvox staging train audio shards must be non-negative integers.")
    return normalized_shards


def run_rixvox_train_staging(
    settings: RixvoxTrainStagingSettings,
) -> RixvoxTrainStagingReport:
    """Stage train metadata and bounded train audio archives for RixVox."""
    ensure_bulk_data_storage_path(settings.data_root, label="Rixvox staging data_root")
    ensure_data_disk_path(settings.hf_cache_dir, label="Rixvox staging hf_cache_dir")
    settings.data_root.mkdir(parents=True, exist_ok=True)
    settings.hf_cache_dir.mkdir(parents=True, exist_ok=True)

    normalized_shards = normalize_train_audio_shards(settings.train_audio_shards)
    revision = resolve_dataset_revision(
        RIXVOX_DATASET_ID,
        max_retries=settings.max_retries,
        request_pause_seconds=settings.request_pause_seconds,
    )

    filenames = [
        "data/train_metadata.parquet",
        *[f"data/train/train_{shard}.tar.gz" for shard in normalized_shards],
    ]
    downloaded_files: list[DownloadedFileRecord] = []
    for filename in filenames:
        cached_path = download_file_with_retry(
            repo_id=RIXVOX_DATASET_ID,
            revision=revision,
            filename=filename,
            cache_dir=settings.hf_cache_dir,
            max_retries=settings.max_retries,
            request_pause_seconds=settings.request_pause_seconds,
        )
        staged_path = settings.data_root / "raw" / "kblab_rixvox" / filename
        stage_downloaded_file(cached_path=cached_path, staged_path=staged_path)
        downloaded_files.append(
            DownloadedFileRecord(
                dataset=RIXVOX_DATASET_ID,
                revision=revision,
                filename=filename,
                cache_path=cached_path.as_posix(),
                staged_path=staged_path.as_posix(),
            )
        )

    return RixvoxTrainStagingReport(
        data_root=settings.data_root.as_posix(),
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        dataset_revision=revision,
        train_audio_shards=list(normalized_shards),
        downloaded_files=downloaded_files,
        train_metadata_staged=True,
        train_audio_archive_count=len(normalized_shards),
    )
