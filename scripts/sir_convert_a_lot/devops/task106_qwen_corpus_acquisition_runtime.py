"""Runtime helpers for Task 106 Hemma-only Qwen corpus acquisition.

Purpose:
    Stage revision-pinned Swedish corpus assets onto Hemma's bulk-data HDD tier
    using targeted, sequential Hugging Face downloads instead of broad snapshot
    fan-out or deprecated dataset-script loading.

Relationships:
    - Used by `run_task106_hemma_qwen_corpus_acquisition.py`.
    - Prepares raw corpus inputs for the Task 103 / Task 106 preprocessing
      adapters without downloading large datasets to the local workstation.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from huggingface_hub import HfApi, hf_hub_download
from huggingface_hub.errors import HfHubHTTPError

DEFAULT_HEMMA_HF_CACHE_ENV: Final[str] = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HEMMA_QWEN_DATA_ENV: Final[str] = "SIR_CONVERT_A_LOT_HEMMA_QWEN_CORPUS_DATA_PATH"
DEFAULT_HF_CACHE_DIR: Final[Path] = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_DATA_ROOT: Final[Path] = Path(
    "/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"
)
DEFAULT_OUTPUT_ROOT: Final[Path] = Path("build/reference/qwen3-tts-swedish-corpus/acquisition")
DEFAULT_FLEURS_SPLITS: Final[tuple[str, ...]] = ("dev", "test")
DEFAULT_RIXVOX_SPLITS: Final[tuple[str, ...]] = ("dev", "test")
DEFAULT_WAXHOLM_MAX_FILES: Final[int] = 64
DEFAULT_REQUEST_PAUSE_SECONDS: Final[float] = 0.25
DEFAULT_MAX_RETRIES: Final[int] = 5


@dataclass(frozen=True)
class Task106AcquisitionSettings:
    """Normalized settings for the Task 106 acquisition runner."""

    output_root: Path
    data_root: Path
    hf_cache_dir: Path
    fleurs_splits: tuple[str, ...]
    rixvox_splits: tuple[str, ...]
    waxholm_max_files: int
    request_pause_seconds: float
    max_retries: int


@dataclass(frozen=True)
class DownloadedFileRecord:
    """One staged dataset asset in the Task 106 acquisition report."""

    dataset: str
    revision: str
    filename: str
    cache_path: str
    staged_path: str


@dataclass(frozen=True)
class Task106AcquisitionReport:
    """Deterministic machine-readable report for one Task 106 acquisition pass."""

    data_root: str
    hf_cache_dir: str
    dataset_revisions: dict[str, str]
    downloaded_files: list[DownloadedFileRecord]
    counts_by_dataset: dict[str, int]


def default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for corpus acquisition."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_ENV, "").strip()
    return DEFAULT_HF_CACHE_DIR if configured_path == "" else Path(configured_path)


def default_data_root() -> Path:
    """Resolve the canonical Hemma raw-corpus root for Swedish Qwen acquisition."""
    configured_path = os.environ.get(DEFAULT_HEMMA_QWEN_DATA_ENV, "").strip()
    return DEFAULT_DATA_ROOT if configured_path == "" else Path(configured_path)


def ensure_data_disk_path(path: Path, *, label: str) -> None:
    """Require one configured path to live on a managed Hemma storage tier."""
    rendered = path.as_posix()
    if (
        rendered.startswith("/srv/scratch/")
        or rendered.startswith("/srv/storage/")
        or rendered.startswith("/home/paunchygent/.data/")
    ):
        return
    raise SystemExit(f"{label} must live on a managed Hemma storage tier, got `{rendered}`.")


def ensure_bulk_data_storage_path(path: Path, *, label: str) -> None:
    """Require one configured path to live on Hemma's HDD bulk-data tier."""
    rendered = path.as_posix()
    if rendered.startswith("/srv/storage/") or rendered.startswith("/home/paunchygent/.data/"):
        return
    raise SystemExit(f"{label} must live on Hemma's HDD bulk-data tier, got `{rendered}`.")


def resolve_dataset_revision(
    repo_id: str,
    *,
    max_retries: int,
    request_pause_seconds: float,
) -> str:
    """Resolve one dataset repository to a concrete commit SHA with retry/backoff."""
    api = HfApi()
    retry_delay_seconds = request_pause_seconds
    for attempt in range(1, max_retries + 1):
        try:
            dataset_info = api.dataset_info(repo_id)
            revision = dataset_info.sha
            if not isinstance(revision, str) or revision == "":
                raise SystemExit(f"dataset_info({repo_id}) did not return a valid revision SHA.")
            return revision
        except HfHubHTTPError as exc:
            _sleep_before_retry(
                exc=exc,
                attempt=attempt,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                label=f"dataset_info({repo_id})",
            )
            retry_delay_seconds *= 2.0
    raise SystemExit(
        f"Failed to resolve dataset revision for `{repo_id}` after {max_retries} attempts."
    )


def download_file_with_retry(
    *,
    repo_id: str,
    revision: str,
    filename: str,
    cache_dir: Path,
    max_retries: int,
    request_pause_seconds: float,
) -> Path:
    """Download one dataset file through targeted sequential acquisition with backoff."""
    retry_delay_seconds = request_pause_seconds
    for attempt in range(1, max_retries + 1):
        try:
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                repo_type="dataset",
                revision=revision,
                filename=filename,
                cache_dir=cache_dir.as_posix(),
            )
            time.sleep(request_pause_seconds)
            return Path(downloaded_path)
        except HfHubHTTPError as exc:
            _sleep_before_retry(
                exc=exc,
                attempt=attempt,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                label=f"hf_hub_download({repo_id}, {filename})",
            )
            retry_delay_seconds *= 2.0
    raise SystemExit(
        f"Failed to download `{filename}` from `{repo_id}` after {max_retries} attempts."
    )


def stage_downloaded_file(*, cached_path: Path, staged_path: Path) -> None:
    """Expose one cached dataset asset through a stable staged-root symlink."""
    staged_path.parent.mkdir(parents=True, exist_ok=True)
    if staged_path.is_symlink():
        if staged_path.resolve() == cached_path.resolve():
            return
        staged_path.unlink()
    elif staged_path.exists():
        raise SystemExit(f"Refusing to overwrite non-symlink staged path: {staged_path}")
    staged_path.symlink_to(cached_path)


def acquire_fleurs_assets(
    settings: Task106AcquisitionSettings,
) -> tuple[str, list[DownloadedFileRecord]]:
    """Stage the targeted Swedish FLEURS control assets on Hemma's HDD tier."""
    repo_id = "google/fleurs"
    revision = resolve_dataset_revision(
        repo_id,
        max_retries=settings.max_retries,
        request_pause_seconds=settings.request_pause_seconds,
    )
    records: list[DownloadedFileRecord] = []
    for split in settings.fleurs_splits:
        for filename in (
            f"data/sv_se/{split}.tsv",
            f"data/sv_se/audio/{split}.tar.gz",
        ):
            cached_path = download_file_with_retry(
                repo_id=repo_id,
                revision=revision,
                filename=filename,
                cache_dir=settings.hf_cache_dir,
                max_retries=settings.max_retries,
                request_pause_seconds=settings.request_pause_seconds,
            )
            staged_path = settings.data_root / "raw" / "google_fleurs" / filename
            stage_downloaded_file(cached_path=cached_path, staged_path=staged_path)
            records.append(
                DownloadedFileRecord(
                    dataset="google/fleurs",
                    revision=revision,
                    filename=filename,
                    cache_path=cached_path.as_posix(),
                    staged_path=staged_path.as_posix(),
                )
            )
    return revision, records


def acquire_rixvox_metadata_assets(
    settings: Task106AcquisitionSettings,
) -> tuple[str, list[DownloadedFileRecord]]:
    """Stage the targeted RixVox metadata parquet files on Hemma's HDD tier."""
    repo_id = "KBLab/rixvox"
    revision = resolve_dataset_revision(
        repo_id,
        max_retries=settings.max_retries,
        request_pause_seconds=settings.request_pause_seconds,
    )
    records: list[DownloadedFileRecord] = []
    for split in settings.rixvox_splits:
        filename = f"data/{split}_metadata.parquet"
        cached_path = download_file_with_retry(
            repo_id=repo_id,
            revision=revision,
            filename=filename,
            cache_dir=settings.hf_cache_dir,
            max_retries=settings.max_retries,
            request_pause_seconds=settings.request_pause_seconds,
        )
        staged_path = settings.data_root / "raw" / "kblab_rixvox" / filename
        stage_downloaded_file(cached_path=cached_path, staged_path=staged_path)
        records.append(
            DownloadedFileRecord(
                dataset="KBLab/rixvox",
                revision=revision,
                filename=filename,
                cache_path=cached_path.as_posix(),
                staged_path=staged_path.as_posix(),
            )
        )
    return revision, records


def acquire_waxholm_assets(
    settings: Task106AcquisitionSettings,
) -> tuple[str, list[DownloadedFileRecord]]:
    """Stage a bounded labeled Waxholm control subset on Hemma's HDD tier."""
    repo_id = "KTH/waxholm"
    revision = resolve_dataset_revision(
        repo_id,
        max_retries=settings.max_retries,
        request_pause_seconds=settings.request_pause_seconds,
    )
    records: list[DownloadedFileRecord] = []
    listing_filename = "alloktrainfiles"
    listing_cached_path = download_file_with_retry(
        repo_id=repo_id,
        revision=revision,
        filename=listing_filename,
        cache_dir=settings.hf_cache_dir,
        max_retries=settings.max_retries,
        request_pause_seconds=settings.request_pause_seconds,
    )
    listing_staged_path = settings.data_root / "raw" / "kth_waxholm" / listing_filename
    stage_downloaded_file(cached_path=listing_cached_path, staged_path=listing_staged_path)
    records.append(
        DownloadedFileRecord(
            dataset="KTH/waxholm",
            revision=revision,
            filename=listing_filename,
            cache_path=listing_cached_path.as_posix(),
            staged_path=listing_staged_path.as_posix(),
        )
    )
    listing_entries = [
        line.strip()
        for line in listing_cached_path.read_text(encoding="utf-8").splitlines()
        if line.strip() != ""
    ]
    for entry in listing_entries[: settings.waxholm_max_files]:
        base_stem = entry.removesuffix(".smp")
        speaker_dir = base_stem.split(".", 1)[0]
        for filename in (
            f"scenes_formatted/{speaker_dir}/{base_stem}.wav",
            f"scenes_formatted/{speaker_dir}/{base_stem}.smp.mix",
        ):
            cached_path = download_file_with_retry(
                repo_id=repo_id,
                revision=revision,
                filename=filename,
                cache_dir=settings.hf_cache_dir,
                max_retries=settings.max_retries,
                request_pause_seconds=settings.request_pause_seconds,
            )
            staged_path = settings.data_root / "raw" / "kth_waxholm" / filename
            stage_downloaded_file(cached_path=cached_path, staged_path=staged_path)
            records.append(
                DownloadedFileRecord(
                    dataset="KTH/waxholm",
                    revision=revision,
                    filename=filename,
                    cache_path=cached_path.as_posix(),
                    staged_path=staged_path.as_posix(),
                )
            )
    return revision, records


def run_task106_acquisition(settings: Task106AcquisitionSettings) -> Task106AcquisitionReport:
    """Run the bounded Hemma-only raw-corpus acquisition pass for Task 106."""
    ensure_bulk_data_storage_path(settings.data_root, label="Task 106 data_root")
    ensure_data_disk_path(settings.hf_cache_dir, label="Task 106 hf_cache_dir")
    settings.data_root.mkdir(parents=True, exist_ok=True)
    settings.hf_cache_dir.mkdir(parents=True, exist_ok=True)

    dataset_revisions: dict[str, str] = {}
    downloaded_files: list[DownloadedFileRecord] = []

    fleurs_revision, fleurs_records = acquire_fleurs_assets(settings)
    dataset_revisions["google/fleurs"] = fleurs_revision
    downloaded_files.extend(fleurs_records)

    waxholm_revision, waxholm_records = acquire_waxholm_assets(settings)
    dataset_revisions["KTH/waxholm"] = waxholm_revision
    downloaded_files.extend(waxholm_records)

    rixvox_revision, rixvox_records = acquire_rixvox_metadata_assets(settings)
    dataset_revisions["KBLab/rixvox"] = rixvox_revision
    downloaded_files.extend(rixvox_records)

    counts_by_dataset: dict[str, int] = {}
    for dataset_name in sorted({record.dataset for record in downloaded_files}):
        counts_by_dataset[dataset_name] = sum(
            1 for record in downloaded_files if record.dataset == dataset_name
        )

    return Task106AcquisitionReport(
        data_root=settings.data_root.as_posix(),
        hf_cache_dir=settings.hf_cache_dir.as_posix(),
        dataset_revisions=dataset_revisions,
        downloaded_files=downloaded_files,
        counts_by_dataset=counts_by_dataset,
    )


def _sleep_before_retry(
    *,
    exc: HfHubHTTPError,
    attempt: int,
    max_retries: int,
    retry_delay_seconds: float,
    label: str,
) -> None:
    """Sleep between retry attempts when the Hub responds with a transient failure."""
    response = getattr(exc, "response", None)
    status_code = None if response is None else response.status_code
    transient_status_codes = {429, 500, 502, 503, 504}
    if status_code not in transient_status_codes or attempt >= max_retries:
        raise SystemExit(f"{label} failed with status {status_code}: {exc}") from exc
    time.sleep(retry_delay_seconds)
