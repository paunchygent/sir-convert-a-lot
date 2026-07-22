"""Tests for the bounded RixVox train staging surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.cli.ml.qwen_rixvox_train_staging import (
    DEFAULT_TRAIN_AUDIO_SHARDS,
    _parse_args,
    main,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.acquisition import (
    DownloadedFileRecord,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.rixvox_train_staging import (
    RixvoxTrainStagingReport,
    RixvoxTrainStagingSettings,
    normalize_train_audio_shards,
    run_rixvox_train_staging,
)


def test_rixvox_train_staging_parse_args_defaults() -> None:
    """The train-staging runner should expose deterministic default shards."""
    settings = _parse_args([])

    assert settings.train_audio_shards == DEFAULT_TRAIN_AUDIO_SHARDS


def test_normalize_train_audio_shards_rejects_empty_tuple() -> None:
    """Rixvox staging should require at least one bounded train shard."""
    with pytest.raises(SystemExit, match="at least one"):
        normalize_train_audio_shards(())


def test_run_rixvox_train_staging_downloads_metadata_and_shards(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runtime should stage train metadata and bounded train archives."""
    settings = RixvoxTrainStagingSettings(
        output_root=tmp_path / "build/reference/qwen3-tts-swedish-corpus/rixvox-train-staging",
        data_root=Path("/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus"),
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        train_audio_shards=(0, 2),
        request_pause_seconds=0.0,
        max_retries=2,
    )
    staged_calls: list[tuple[Path, Path]] = []
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.rixvox_train_staging.ensure_data_disk_path",
        lambda path, label: None,
    )
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=True, exist_ok=True: None)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.rixvox_train_staging.resolve_dataset_revision",
        lambda repo_id, *, max_retries, request_pause_seconds: "rev-rixvox",
    )

    def _fake_download_file_with_retry(
        *,
        repo_id: str,
        revision: str,
        filename: str,
        cache_dir: Path,
        max_retries: int,
        request_pause_seconds: float,
    ) -> Path:
        assert repo_id == "KBLab/rixvox"
        assert revision == "rev-rixvox"
        return Path("/srv/cache") / filename

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.rixvox_train_staging.download_file_with_retry",
        _fake_download_file_with_retry,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.preprocessing.rixvox_train_staging.stage_downloaded_file",
        lambda *, cached_path, staged_path: staged_calls.append((cached_path, staged_path)),
    )

    report = run_rixvox_train_staging(settings)

    assert report.dataset_revision == "rev-rixvox"
    assert report.train_audio_shards == [0, 2]
    assert report.train_metadata_staged is True
    assert report.train_audio_archive_count == 2
    assert [record.filename for record in report.downloaded_files] == [
        "data/train_metadata.parquet",
        "data/train/train_0.tar.gz",
        "data/train/train_2.tar.gz",
    ]
    assert staged_calls[0][1] == Path(
        "/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus/raw/kblab_rixvox/data/train_metadata.parquet"
    )


def test_rixvox_train_staging_runner_main_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The runner should write the staging report and print JSON."""
    expected_report = RixvoxTrainStagingReport(
        data_root="/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus",
        hf_cache_dir="/srv/scratch/sir-convert-a-lot/cache/huggingface",
        dataset_revision="rev-rixvox",
        train_audio_shards=[0],
        downloaded_files=[
            DownloadedFileRecord(
                dataset="KBLab/rixvox",
                revision="rev-rixvox",
                filename="data/train_metadata.parquet",
                cache_path="/srv/cache/train_metadata.parquet",
                staged_path="/srv/data/train_metadata.parquet",
            )
        ],
        train_metadata_staged=True,
        train_audio_archive_count=1,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_rixvox_train_staging.run_rixvox_train_staging",
        lambda settings: expected_report,
    )

    exit_code = main(["--output-root", str(tmp_path / "out")])

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["dataset_revision"] == "rev-rixvox"
    assert (tmp_path / "out/report.json").is_file()
