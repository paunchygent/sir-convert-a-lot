"""Preprocessing runner and orchestration tests.

Purpose:
    Cover the public preprocessing CLI, run-root orchestration, and source-selection
    coordination behavior without mixing in lower-level source-adapter or ASR
    implementation details.

Relationships:
    - Tests `qwen_preprocess`.
    - Reuses shared builders from `test_support`.
    - Complements the processing, source-adapter, and ASR test modules.
"""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Sequence

import pytest

from scripts.sir_convert_a_lot.cli.ml.qwen_preprocess import (
    DEFAULT_ASR_MODEL,
    DEFAULT_ASR_REVISION,
    DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    DEFAULT_FLEURS_SPLITS,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_RIXVOX_SPLITS,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SOURCE_MODE,
    DEFAULT_TOKENIZER_MODEL,
    PreprocessingRunnerSettings,
    _parse_args,
    _resolve_source_records,
    main,
)
from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    CANONICAL_MANIFEST_FAMILIES,
    RowProcessingHeartbeat,
    SourceRecord,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.acquisition import DEFAULT_DATA_ROOT
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    PreprocessingReport,
    PreprocessingSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.sharding import (
    SourceSelectionHeartbeat,
    SourceSelectionSummary,
    selected_source_records_path,
    source_record_to_payload,
    write_selected_source_records,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    write_jsonl,
)
from tests.sir_convert_a_lot.ml.qwen.preprocessing.test_support import (
    build_source_record,
    report_only_preprocessing_runner,
    write_test_wav,
)


def test_parse_args_defaults() -> None:
    """The preprocessing runner should expose deterministic defaults."""
    runner_settings = _parse_args([])

    assert runner_settings.preprocessing.output_root == DEFAULT_OUTPUT_ROOT
    assert runner_settings.preprocessing.asr_model == DEFAULT_ASR_MODEL
    assert runner_settings.preprocessing.asr_revision == DEFAULT_ASR_REVISION
    assert runner_settings.preprocessing.tokenizer_model == DEFAULT_TOKENIZER_MODEL
    assert runner_settings.preprocessing.stage == "row-processing"
    assert runner_settings.preprocessing.audio_codes_chunk_size == 8
    assert runner_settings.preprocessing.row_worker_count == 1
    assert runner_settings.preprocessing.gpu_asr_worker_count == 1
    assert runner_settings.source_mode == DEFAULT_SOURCE_MODE
    assert runner_settings.data_root == DEFAULT_DATA_ROOT
    assert runner_settings.fleurs_splits == DEFAULT_FLEURS_SPLITS
    assert runner_settings.fleurs_max_rows_per_split == DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT
    assert runner_settings.rixvox_splits == DEFAULT_RIXVOX_SPLITS
    assert runner_settings.rixvox_max_rows_per_split is None
    assert runner_settings.runs_root == DEFAULT_RUNS_ROOT
    assert runner_settings.run_id is None
    assert runner_settings.run_root is None
    assert runner_settings.promote_on_success is False


def test_parse_args_rejects_stage_all_without_explicit_override() -> None:
    """The public preprocessing runner should reject non-canonical `stage=all` use."""
    with pytest.raises(SystemExit, match="no longer treats `stage=all` as canonical"):
        _parse_args(["--stage", "all"])


def test_parse_args_staged_public_corpus_mode(tmp_path: Path) -> None:
    """The runner should parse the staged public-corpus settings explicitly."""
    runner_settings = _parse_args(
        [
            "--source-mode",
            "staged-public-corpus",
            "--data-root",
            tmp_path.as_posix(),
            "--fleurs-splits",
            "dev",
            "--fleurs-max-rows-per-split",
            "8",
            "--rixvox-splits",
            "test",
            "--rixvox-max-rows-per-split",
            "16",
        ]
    )

    assert runner_settings.source_mode == "staged-public-corpus"
    assert runner_settings.data_root == tmp_path
    assert runner_settings.fleurs_splits == ("dev",)
    assert runner_settings.fleurs_max_rows_per_split == 8
    assert runner_settings.rixvox_splits == ("test",)
    assert runner_settings.rixvox_max_rows_per_split == 16
    assert runner_settings.run_id is None
    assert runner_settings.run_root is None


def test_parse_args_selected_source_records_mode(tmp_path: Path) -> None:
    """The runner should parse the portable selected-source mode explicitly."""
    records_path = tmp_path / "selected_source_records.jsonl"
    runner_settings = _parse_args(
        [
            "--source-mode",
            "selected-source-records",
            "--selected-source-records-path",
            records_path.as_posix(),
        ]
    )

    assert runner_settings.source_mode == "selected-source-records"
    assert runner_settings.selected_source_records_path == records_path


def test_parse_args_resume_row_processing_flag() -> None:
    """The runner should parse explicit row-processing resume control."""
    runner_settings = _parse_args(
        [
            "--stage",
            "row-processing",
            "--resume-row-processing",
        ]
    )

    assert runner_settings.preprocessing.resume_row_processing is True


def test_parse_args_rejects_resume_outside_row_processing() -> None:
    """Resume-row-processing must only be legal for the row-processing stage."""
    with pytest.raises(SystemExit, match="only valid for the `row-processing` stage"):
        _parse_args(
            [
                "--stage",
                "reports",
                "--resume-row-processing",
            ]
        )


def test_parse_args_run_scoped_controls(tmp_path: Path) -> None:
    """The runner should parse explicit run-root and promotion controls."""
    runner_settings = _parse_args(
        [
            "--source-mode",
            "staged-public-corpus",
            "--run-id",
            "proof-run",
            "--runs-root",
            (tmp_path / "runs").as_posix(),
            "--stage",
            "reports",
            "--promote-on-success",
        ]
    )

    assert runner_settings.run_id == "proof-run"
    assert runner_settings.runs_root == tmp_path / "runs"
    assert runner_settings.promote_on_success is True


def test_selected_source_records_mode_resolves_portable_rixvox_locators(
    tmp_path: Path,
) -> None:
    """Portable selected-source rows should resolve local RixVox locators before row-processing."""
    data_root = tmp_path / "data_root"
    archive_root = data_root / "raw/kblab_rixvox/data/train"
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_path = archive_root / "train_0.tar.gz"
    audio_path = tmp_path / "needed.wav"
    write_test_wav(audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01KRU1/needed.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    records_path = tmp_path / "selected_source_records.jsonl"
    write_jsonl(
        records_path,
        [
            source_record_to_payload(
                SourceRecord(
                    dataset="rixvox",
                    source_split="train",
                    dataset_row_id="GR01KRU1-1-0",
                    speaker_id="rixvox_0556347007015",
                    speaker_name="Peter Pedersen",
                    speaker_from_id=True,
                    source_audio_path="GR01KRU1/needed.wav",
                    source_audio_locator=None,
                    text_raw="Hej från Sverige.",
                    language="sv-SE",
                    speaker_total_hours=1.0,
                    has_label_files=False,
                    speaker_audio_meta_ok=True,
                    source_sample_rate_hz=16_000,
                    duration_seconds=5.0,
                )
            )
        ],
    )

    runner_settings = _parse_args(
        [
            "--source-mode",
            "selected-source-records",
            "--selected-source-records-path",
            records_path.as_posix(),
            "--data-root",
            data_root.as_posix(),
        ]
    )

    source_records = _resolve_source_records(
        runner_settings,
        output_root=tmp_path / "run",
    )

    assert source_records is not None
    assert len(source_records) == 1
    assert source_records[0].source_audio_locator is not None
    assert source_records[0].source_audio_locator.path == archive_path
    assert source_records[0].source_audio_locator.archive_member == "GR01KRU1/needed.wav"


def test_runner_main_prints_report_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The preprocessing runner should print the completed report as JSON."""
    expected_report = PreprocessingReport(
        output_root="build/reference/qwen3-tts-swedish-corpus",
        datasets=["fleurs_sv_se", "waxholm"],
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=2,
        curated_rows=2,
        admitted_rows=2,
        prepared_rows=2,
        speaker_ids=["speaker_a", "speaker_b"],
        manifest_counts={"swedish_checkpoint_dev": 1, "swedish_waxholm_control": 1},
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        report_only_preprocessing_runner(expected_report),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        lambda settings, **kwargs: None,
    )

    exit_code = main([])

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["output_root"] == expected_report.output_root
    assert stdout_payload["prepared_rows"] == 2


def test_runner_main_uses_run_root_for_staged_public_corpus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The runner should allocate one immutable run root for staged public-corpus mode."""
    expected_run_root = tmp_path / "runs" / "proof-run"
    expected_report = PreprocessingReport(
        output_root=expected_run_root.as_posix(),
        datasets=["rixvox"],
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=1,
        curated_rows=1,
        admitted_rows=1,
        prepared_rows=1,
        speaker_ids=["speaker_a"],
        manifest_counts={"swedish_smoke_train": 1},
    )
    observed_output_root: Path | None = None

    def _fake_run_preprocessing(
        settings: PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> PreprocessingReport:
        nonlocal observed_output_root
        del source_records
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        observed_output_root = settings.output_root
        return expected_report

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        _fake_run_preprocessing,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        lambda settings, **kwargs: [],
    )

    exit_code = main(
        [
            "--source-mode",
            "staged-public-corpus",
            "--data-root",
            tmp_path.as_posix(),
            "--runs-root",
            (tmp_path / "runs").as_posix(),
            "--run-id",
            "proof-run",
        ]
    )

    assert exit_code == 0
    assert observed_output_root == expected_run_root
    assert (expected_run_root / "run.json").is_file()
    status_payload = json.loads((expected_run_root / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "completed"
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["output_root"] == expected_report.output_root


def test_runner_main_persists_row_processing_heartbeat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner should persist row-level progress into the run-scoped status file."""
    expected_run_root = tmp_path / "runs" / "proof-run"
    expected_report = PreprocessingReport(
        output_root=expected_run_root.as_posix(),
        datasets=["rixvox"],
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=2,
        curated_rows=2,
        admitted_rows=2,
        prepared_rows=0,
        speaker_ids=["speaker_a"],
        manifest_counts={"swedish_smoke_train": 0},
    )

    def _fake_run_preprocessing(
        settings: PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> PreprocessingReport:
        del settings
        del source_records
        del finalization_heartbeat_callback
        assert row_heartbeat_callback is not None
        row_heartbeat_callback(
            RowProcessingHeartbeat(
                processed_row_count=2,
                total_row_count=4,
                current_dataset_row_id="rixvox-train-0002",
            )
        )
        return expected_report

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        _fake_run_preprocessing,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        lambda settings, **kwargs: [],
    )

    exit_code = main(
        [
            "--source-mode",
            "staged-public-corpus",
            "--data-root",
            tmp_path.as_posix(),
            "--runs-root",
            (tmp_path / "runs").as_posix(),
            "--run-id",
            "proof-run",
        ]
    )

    assert exit_code == 0
    status_payload = json.loads((expected_run_root / "status.json").read_text(encoding="utf-8"))
    assert status_payload["processed_row_count"] == 2
    assert status_payload["total_row_count"] == 4
    assert status_payload["current_dataset_row_id"] == "rixvox-train-0002"


def test_runner_main_rejects_promotion_outside_reports_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner should only allow promotion from the reports stage."""
    promoted_root = tmp_path / "build/reference/qwen3-tts-swedish-corpus"
    expected_report = PreprocessingReport(
        output_root=(tmp_path / "runs" / "proof-run").as_posix(),
        datasets=["rixvox"],
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=1,
        curated_rows=1,
        admitted_rows=1,
        prepared_rows=1,
        speaker_ids=["speaker_a"],
        manifest_counts={"swedish_smoke_train": 1},
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        report_only_preprocessing_runner(expected_report),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        lambda settings, **kwargs: [],
    )

    with pytest.raises(SystemExit, match="promotion is only allowed for the `reports` stage"):
        main(
            [
                "--source-mode",
                "staged-public-corpus",
                "--data-root",
                tmp_path.as_posix(),
                "--runs-root",
                (tmp_path / "runs").as_posix(),
                "--run-id",
                "proof-run",
                "--output-root",
                promoted_root.as_posix(),
                "--promote-on-success",
            ]
        )


def test_runner_main_promotes_successful_reports_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reports stage should also promote a successful run when requested."""
    promoted_root = tmp_path / "build/reference/qwen3-tts-swedish-corpus"
    expected_run_root = tmp_path / "runs" / "proof-run"
    expected_report = PreprocessingReport(
        output_root=expected_run_root.as_posix(),
        datasets=["rixvox"],
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=1,
        curated_rows=1,
        admitted_rows=1,
        prepared_rows=1,
        speaker_ids=["speaker_a"],
        manifest_counts={"swedish_smoke_train": 1},
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        report_only_preprocessing_runner(expected_report),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        lambda settings, **kwargs: [],
    )

    exit_code = main(
        [
            "--source-mode",
            "staged-public-corpus",
            "--data-root",
            tmp_path.as_posix(),
            "--runs-root",
            (tmp_path / "runs").as_posix(),
            "--run-id",
            "proof-run",
            "--output-root",
            promoted_root.as_posix(),
            "--promote-on-success",
            "--stage",
            "reports",
        ]
    )

    assert exit_code == 0
    assert promoted_root.is_symlink()
    assert promoted_root.resolve() == expected_run_root.resolve()
    status_payload = json.loads((expected_run_root / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "promoted"


def test_runner_main_persists_traceback_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner should persist a full traceback in the run-scoped status payload."""
    expected_run_root = tmp_path / "runs" / "failing-run"

    def _boom(
        settings: PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> PreprocessingReport:
        del settings
        del source_records
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        raise RuntimeError("meta tensor exploded")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        _boom,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        lambda settings, **kwargs: [],
    )

    with pytest.raises(RuntimeError, match="meta tensor exploded"):
        main(
            [
                "--source-mode",
                "staged-public-corpus",
                "--data-root",
                tmp_path.as_posix(),
                "--runs-root",
                (tmp_path / "runs").as_posix(),
                "--run-id",
                "failing-run",
            ]
        )

    status_payload = json.loads((expected_run_root / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "failed"
    assert "RuntimeError: meta tensor exploded" in status_payload["error"]
    assert "Traceback" in status_payload["error"]


def test_source_selection_stage_persists_selected_source_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The explicit source-selection stage should persist bounded selected-source artifacts."""
    run_root = tmp_path / "run"
    source_record = SourceRecord(
        dataset="rixvox",
        source_split="train",
        dataset_row_id="GR01KRU1-1-0",
        speaker_id="rixvox_0556347007015",
        speaker_name="Peter Pedersen",
        speaker_from_id=True,
        source_audio_path="GR01KRU1/needed.wav",
        source_audio_locator=None,
        text_raw="Hej från Sverige.",
        language="sv-SE",
        speaker_total_hours=1.0,
        has_label_files=False,
        speaker_audio_meta_ok=True,
        source_sample_rate_hz=16_000,
        duration_seconds=5.0,
    )

    def _fake_staged_source_records(
        *_args: object,
        source_selection_heartbeat_callback=None,
        **_kwargs: object,
    ) -> list[SourceRecord]:
        if source_selection_heartbeat_callback is not None:
            source_selection_heartbeat_callback(
                SourceSelectionHeartbeat(
                    phase="resolving-source-records",
                    current_split="train",
                    selected_row_count=1,
                    target_row_cap=64,
                    current_parquet_batch_index=1,
                    resolved_audio_locator_count=None,
                    required_audio_locator_count=None,
                )
            )
        return [source_record]

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.staged_public_corpus_source_records",
        _fake_staged_source_records,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.ensure_bulk_data_storage_path",
        lambda path, *, label: None,
    )

    exit_code = main(
        [
            "--source-mode",
            "staged-public-corpus",
            "--stage",
            "source-selection",
            "--run-root",
            run_root.as_posix(),
            "--data-root",
            tmp_path.as_posix(),
            "--rixvox-splits",
            "train",
            "--rixvox-max-rows-per-split",
            "64",
        ]
    )

    assert exit_code == 0
    assert selected_source_records_path(run_root).is_file()
    status_payload = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    assert status_payload["status"] == "completed"
    assert status_payload["stage"] == "source-selection"
    assert status_payload["selected_row_count"] == 1
    assert status_payload["current_split"] == "train"


def test_row_processing_reuses_selected_source_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The row-processing stage should reuse persisted selected-source artifacts."""
    run_root = tmp_path / "run"
    source_record = SourceRecord(
        dataset="rixvox",
        source_split="train",
        dataset_row_id="GR01KRU1-1-0",
        speaker_id="rixvox_0556347007015",
        speaker_name="Peter Pedersen",
        speaker_from_id=True,
        source_audio_path="GR01KRU1/needed.wav",
        source_audio_locator=None,
        text_raw="Hej från Sverige.",
        language="sv-SE",
        speaker_total_hours=1.0,
        has_label_files=False,
        speaker_audio_meta_ok=True,
        source_sample_rate_hz=16_000,
        duration_seconds=5.0,
    )
    write_selected_source_records(
        run_root,
        source_records=[source_record],
        summary=SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=1,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=64,
        ),
    )

    captured_dataset_row_ids: list[str] = []

    def _fake_run_preprocessing(
        settings: PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> PreprocessingReport:
        del settings
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        assert source_records is not None
        captured_dataset_row_ids.extend(row.dataset_row_id for row in source_records)
        return PreprocessingReport(
            output_root=run_root.as_posix(),
            datasets=["rixvox"],
            asr_model=DEFAULT_ASR_MODEL,
            asr_revision=DEFAULT_ASR_REVISION,
            tokenizer_model=DEFAULT_TOKENIZER_MODEL,
            inventory_rows=1,
            curated_rows=0,
            admitted_rows=0,
            prepared_rows=0,
            speaker_ids=["rixvox_0556347007015"],
            manifest_counts={family: 0 for family in CANONICAL_MANIFEST_FAMILIES},
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        _fake_run_preprocessing,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.staged_public_corpus_source_records",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Should reuse selection artifact")
        ),
    )

    exit_code = main(
        [
            "--source-mode",
            "staged-public-corpus",
            "--stage",
            "row-processing",
            "--run-root",
            run_root.as_posix(),
            "--data-root",
            tmp_path.as_posix(),
            "--rixvox-splits",
            "train",
            "--rixvox-max-rows-per-split",
            "64",
        ]
    )

    assert exit_code == 0
    assert captured_dataset_row_ids == ["GR01KRU1-1-0"]


def test_runner_main_staged_public_corpus_passes_source_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The runner should resolve staged public-corpus records before core execution."""
    expected_report = PreprocessingReport(
        output_root="build/reference/qwen3-tts-swedish-corpus",
        datasets=["fleurs_sv_se", "rixvox", "waxholm"],
        asr_model=DEFAULT_ASR_MODEL,
        asr_revision=DEFAULT_ASR_REVISION,
        tokenizer_model=DEFAULT_TOKENIZER_MODEL,
        inventory_rows=3,
        curated_rows=2,
        admitted_rows=2,
        prepared_rows=2,
        speaker_ids=["speaker_a", "speaker_b", "speaker_c"],
        manifest_counts={"swedish_checkpoint_dev": 1, "swedish_waxholm_control": 1},
    )
    expected_source_records = [
        build_source_record(
            dataset="fleurs_sv_se",
            source_split="dev",
            dataset_row_id="fleurs-dev-001",
            speaker_id="speaker_a",
            speaker_name="Speaker A",
            source_audio_path=tmp_path / "speaker_a.wav",
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        )
    ]
    observed_runner_settings: list[PreprocessingRunnerSettings] = []
    observed_source_records: list[list[SourceRecord] | None] = []

    def _fake_resolve_source_records(
        settings: PreprocessingRunnerSettings,
        **kwargs: object,
    ) -> list[SourceRecord]:
        del kwargs
        observed_runner_settings.append(settings)
        return expected_source_records

    def _fake_run_preprocessing(
        settings: PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> PreprocessingReport:
        del settings
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        assert source_records is not None
        observed_source_records.append(list(source_records))
        return expected_report

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess._resolve_source_records",
        _fake_resolve_source_records,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess.run_preprocessing_pipeline",
        _fake_run_preprocessing,
    )

    exit_code = main(
        [
            "--source-mode",
            "staged-public-corpus",
            "--data-root",
            DEFAULT_DATA_ROOT.as_posix(),
            "--fleurs-splits",
            "dev",
            "--fleurs-max-rows-per-split",
            "8",
            "--rixvox-splits",
            "test",
            "--rixvox-max-rows-per-split",
            "32",
        ]
    )

    assert exit_code == 0
    assert observed_runner_settings[0].source_mode == "staged-public-corpus"
    assert observed_runner_settings[0].fleurs_max_rows_per_split == 8
    assert observed_runner_settings[0].rixvox_max_rows_per_split == 32
    assert observed_source_records == [expected_source_records]
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["datasets"] == ["fleurs_sv_se", "rixvox", "waxholm"]
