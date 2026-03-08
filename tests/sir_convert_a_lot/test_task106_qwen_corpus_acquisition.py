"""Tests for the Task 106 Hemma-only Qwen corpus acquisition surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task106_hemma_qwen_corpus_acquisition import (
    _parse_args,
    main,
)
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    DEFAULT_FLEURS_SPLITS,
    DEFAULT_RIXVOX_SPLITS,
    DEFAULT_WAXHOLM_MAX_FILES,
    DownloadedFileRecord,
    Task106AcquisitionReport,
    Task106AcquisitionSettings,
    ensure_data_disk_path,
    run_task106_acquisition,
    stage_downloaded_file,
)


def test_task106_parse_args_defaults() -> None:
    """The Task 106 runner should expose deterministic defaults."""
    settings = _parse_args([])

    assert settings.fleurs_splits == DEFAULT_FLEURS_SPLITS
    assert settings.rixvox_splits == DEFAULT_RIXVOX_SPLITS
    assert settings.waxholm_max_files == DEFAULT_WAXHOLM_MAX_FILES


def test_ensure_data_disk_path_rejects_non_data_disk_path(tmp_path: Path) -> None:
    """Task 106 should reject paths that do not live on managed Hemma tiers."""
    with pytest.raises(SystemExit, match="managed Hemma storage tier"):
        ensure_data_disk_path(tmp_path / "not-data-root", label="test path")


def test_stage_downloaded_file_creates_stable_symlink(tmp_path: Path) -> None:
    """The staged corpus root should expose cached files through stable symlinks."""
    cached_path = tmp_path / "cache/file.txt"
    staged_path = tmp_path / "data/file.txt"
    cached_path.parent.mkdir(parents=True, exist_ok=True)
    cached_path.write_text("hej\n", encoding="utf-8")

    stage_downloaded_file(cached_path=cached_path, staged_path=staged_path)

    assert staged_path.is_symlink()
    assert staged_path.resolve() == cached_path.resolve()


def test_run_task106_acquisition_aggregates_targeted_download_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 106 runtime should aggregate staged files from all datasets."""
    settings = Task106AcquisitionSettings(
        output_root=tmp_path / "build/reference/qwen3-tts-swedish-corpus/acquisition",
        data_root=Path("/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"),
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        fleurs_splits=("dev", "test"),
        rixvox_splits=("dev", "test"),
        waxholm_max_files=4,
        request_pause_seconds=0.0,
        max_retries=2,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime.ensure_data_disk_path",
        lambda path, label: None,
    )
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=True, exist_ok=True: None)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime.acquire_fleurs_assets",
        lambda task_settings: (
            "rev-fleurs",
            [
                DownloadedFileRecord(
                    dataset="google/fleurs",
                    revision="rev-fleurs",
                    filename="data/sv_se/dev.tsv",
                    cache_path="/srv/cache/dev.tsv",
                    staged_path="/srv/data/dev.tsv",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime.acquire_waxholm_assets",
        lambda task_settings: (
            "rev-waxholm",
            [
                DownloadedFileRecord(
                    dataset="KTH/waxholm",
                    revision="rev-waxholm",
                    filename="alloktrainfiles",
                    cache_path="/srv/cache/alloktrainfiles",
                    staged_path="/srv/data/alloktrainfiles",
                )
            ],
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime.acquire_rixvox_metadata_assets",
        lambda task_settings: (
            "rev-rixvox",
            [
                DownloadedFileRecord(
                    dataset="KBLab/rixvox",
                    revision="rev-rixvox",
                    filename="data/dev_metadata.parquet",
                    cache_path="/srv/cache/dev_metadata.parquet",
                    staged_path="/srv/data/dev_metadata.parquet",
                )
            ],
        ),
    )

    report = run_task106_acquisition(settings)

    assert report.dataset_revisions["google/fleurs"] == "rev-fleurs"
    assert report.dataset_revisions["KTH/waxholm"] == "rev-waxholm"
    assert report.dataset_revisions["KBLab/rixvox"] == "rev-rixvox"
    assert report.counts_by_dataset == {
        "KBLab/rixvox": 1,
        "KTH/waxholm": 1,
        "google/fleurs": 1,
    }


def test_task106_runner_main_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Task 106 runner should write the acquisition report and print JSON."""
    expected_report = Task106AcquisitionReport(
        data_root="/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus",
        hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        dataset_revisions={"google/fleurs": "rev-fleurs"},
        downloaded_files=[
            DownloadedFileRecord(
                dataset="google/fleurs",
                revision="rev-fleurs",
                filename="data/sv_se/dev.tsv",
                cache_path="/srv/cache/dev.tsv",
                staged_path="/srv/data/dev.tsv",
            )
        ],
        counts_by_dataset={"google/fleurs": 1},
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task106_hemma_qwen_corpus_acquisition.run_task106_acquisition",
        lambda settings: expected_report,
    )

    exit_code = main(["--output-root", str(tmp_path / "out")])

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["counts_by_dataset"]["google/fleurs"] == 1
    assert (tmp_path / "out/report.json").is_file()
