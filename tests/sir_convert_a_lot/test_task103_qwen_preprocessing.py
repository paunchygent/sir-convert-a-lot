"""Tests for the Task 103 and Task 106 Qwen Swedish preprocessing surfaces."""

from __future__ import annotations

import io
import json
import math
import sys
import tarfile
import threading
import wave
from pathlib import Path
from typing import Mapping, Sequence

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing import (
    DEFAULT_ASR_MODEL,
    DEFAULT_ASR_REVISION,
    DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT,
    DEFAULT_FLEURS_SPLITS,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_RIXVOX_SPLITS,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SOURCE_MODE,
    DEFAULT_TOKENIZER_MODEL,
    Task103RunnerSettings,
    _parse_args,
    _resolve_source_records,
    main,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import (
    manifest_target_for_source,
    manifest_targets_for_curated_source,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    CANONICAL_MANIFEST_FAMILIES,
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
    WhisperStrictScorer,
    run_task103_preprocessing,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    Task103RowProcessingHeartbeat,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_row_stage import (
    process_rows_to_spool,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    completed_row_keys_index_path,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_resume_index import (
    main as task103_resume_index_main,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_fleurs import fleurs_sv_source_records
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    AudioLocator,
    SourceRecord,
    source_record_to_payload,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox import (
    build_rixvox_audio_locator_index,
    rixvox_source_records_from_parquet,
    rixvox_source_records_from_parquet_with_audio_locators,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_selection import (
    Task103SourceSelectionHeartbeat,
    Task103SourceSelectionSummary,
    selected_source_records_path,
    write_selected_source_records,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_waxholm import (
    waxholm_labeled_source_records,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_staged_public_corpus import (
    staged_public_corpus_source_records,
)
from scripts.sir_convert_a_lot.devops.task106_qwen_corpus_acquisition_runtime import (
    DEFAULT_DATA_ROOT,
)


def _write_test_wav(path: Path, *, sample_rate_hz: int, duration_seconds: float) -> None:
    """Write one deterministic mono WAV fixture for the Task 103 tests."""
    frame_count = int(sample_rate_hz * duration_seconds)
    amplitude = 12_000
    frequency_hz = 220.0
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(path.as_posix(), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        frames = bytearray()
        for frame_index in range(frame_count):
            sample = int(
                amplitude * math.sin((2.0 * math.pi * frequency_hz * frame_index) / sample_rate_hz)
            )
            frames.extend(sample.to_bytes(length=2, byteorder="little", signed=True))
        handle.writeframes(bytes(frames))


def _build_source_record(
    *,
    dataset: str,
    source_split: str,
    dataset_row_id: str,
    speaker_id: str,
    speaker_name: str,
    source_audio_path: Path,
    reference_audio_path: Path | None,
    text_raw: str,
) -> SourceRecord:
    """Build one local audio source record for core preprocessing tests."""
    return SourceRecord(
        dataset=dataset,
        source_split=source_split,
        dataset_row_id=dataset_row_id,
        speaker_id=speaker_id,
        speaker_name=speaker_name,
        speaker_from_id=True,
        source_audio_path=source_audio_path.as_posix(),
        source_audio_locator=AudioLocator(source_audio_path),
        reference_audio_locator=(
            None if reference_audio_path is None else AudioLocator(reference_audio_path)
        ),
        text_raw=text_raw,
        language="sv-SE",
        speaker_total_hours=None,
        has_label_files=True,
        speaker_audio_meta_ok=True,
    )


def _report_only_preprocessing_runner(
    expected_report: Task103PreprocessingReport,
):
    """Return one stub Task 103 runner that simply returns the expected report."""

    def _runner(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        del settings
        del source_records
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        return expected_report

    return _runner


def test_task103_parse_args_defaults() -> None:
    """The Task 103 runner should expose deterministic defaults."""
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


def test_task103_parse_args_rejects_stage_all_without_explicit_override() -> None:
    """The public Task 103 runner should reject non-canonical `stage=all` use."""
    with pytest.raises(SystemExit, match="no longer treats `stage=all` as canonical"):
        _parse_args(["--stage", "all"])


def test_task103_parse_args_staged_public_corpus_mode(tmp_path: Path) -> None:
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


def test_task103_parse_args_selected_source_records_mode(tmp_path: Path) -> None:
    """The runner should parse the portable selected-source mode explicitly."""
    selected_source_records_path = tmp_path / "selected_source_records.jsonl"
    runner_settings = _parse_args(
        [
            "--source-mode",
            "selected-source-records",
            "--selected-source-records-path",
            selected_source_records_path.as_posix(),
        ]
    )

    assert runner_settings.source_mode == "selected-source-records"
    assert runner_settings.selected_source_records_path == selected_source_records_path


def test_task103_parse_args_resume_row_processing_flag() -> None:
    """The runner should parse explicit row-processing resume control."""
    runner_settings = _parse_args(
        [
            "--stage",
            "row-processing",
            "--resume-row-processing",
        ]
    )

    assert runner_settings.preprocessing.resume_row_processing is True


def test_task103_parse_args_rejects_resume_outside_row_processing() -> None:
    """Resume-row-processing must only be legal for the row-processing stage."""
    with pytest.raises(SystemExit, match="only valid for the `row-processing` stage"):
        _parse_args(
            [
                "--stage",
                "reports",
                "--resume-row-processing",
            ]
        )


def test_task103_parse_args_run_scoped_controls(tmp_path: Path) -> None:
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


def test_task103_selected_source_records_mode_resolves_portable_rixvox_locators(
    tmp_path: Path,
) -> None:
    """Portable selected-source rows should resolve local RixVox locators before row-processing."""
    data_root = tmp_path / "data_root"
    archive_root = data_root / "raw/kblab_rixvox/data/train"
    archive_root.mkdir(parents=True, exist_ok=True)
    archive_path = archive_root / "train_0.tar.gz"
    audio_path = tmp_path / "needed.wav"
    _write_test_wav(audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01KRU1/needed.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    selected_records_path = tmp_path / "selected_source_records.jsonl"
    write_jsonl(
        selected_records_path,
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
            selected_records_path.as_posix(),
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


def test_task103_preprocessing_emits_deterministic_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 103 core should emit inventory, curated, raw, and prepared layers."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    reference_audio_path = workspace_root / "fixtures/ref.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.25)
    _write_test_wav(reference_audio_path, sample_rate_hz=16_000, duration_seconds=6.0)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core._encode_audio_codes",
        lambda *, tokenizer_model, audio_paths: [[[11, 12, 13]] for _ in audio_paths],
    )

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=workspace_root / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        ),
        source_records=[
            _build_source_record(
                dataset="repo_fixture_sv",
                source_split="fixture",
                dataset_row_id="repo-fixture-test-001",
                speaker_id="speaker_test",
                speaker_name="Test Speaker",
                source_audio_path=source_audio_path,
                reference_audio_path=reference_audio_path,
                text_raw="Hej från Sverige.",
            )
        ],
    )

    assert report.datasets == ["repo_fixture_sv"]
    assert report.inventory_rows == 1
    assert report.curated_rows == 1
    assert report.admitted_rows == 1
    assert report.prepared_rows == 1
    assert report.manifest_counts["swedish_smoke_train"] == 1

    output_root = Path(report.output_root)
    inventory_path = output_root / "inventory/repo_fixture_sv-fixture.jsonl"
    curated_path = output_root / "curated/swedish_smoke_train.jsonl"
    raw_manifest_path = output_root / "manifests/swedish_smoke_train.raw.jsonl"
    prepared_manifest_path = output_root / "manifests/swedish_smoke_train.prepared.jsonl"
    manifest_summary_path = output_root / "reports/manifest_summary.json"
    report_json_path = output_root / "report.json"

    assert inventory_path.is_file()
    assert curated_path.is_file()
    assert raw_manifest_path.is_file()
    assert prepared_manifest_path.is_file()
    assert manifest_summary_path.is_file()
    assert report_json_path.is_file()

    inventory_row = json.loads(inventory_path.read_text(encoding="utf-8").splitlines()[0])
    curated_row = json.loads(curated_path.read_text(encoding="utf-8").splitlines()[0])
    prepared_row = json.loads(prepared_manifest_path.read_text(encoding="utf-8").splitlines()[0])
    manifest_summary = json.loads(manifest_summary_path.read_text(encoding="utf-8"))

    assert inventory_row["source_sample_rate_hz"] == 16_000
    assert curated_row["quality_tier"] == "high_trust"
    assert curated_row["admission_decision"] == "admit"
    assert prepared_row["audio_codes"] == [[11, 12, 13]]
    assert manifest_summary["manifest_counts"]["swedish_smoke_train"] == 1

    for family in CANONICAL_MANIFEST_FAMILIES:
        assert (output_root / f"curated/{family}.jsonl").is_file()
        assert (output_root / f"manifests/{family}.raw.jsonl").is_file()
        assert (output_root / f"manifests/{family}.prepared.jsonl").is_file()

    with wave.open((output_root / curated_row["audio_24k_path"]).as_posix(), "rb") as handle:
        assert handle.getframerate() == 24_000


def test_process_rows_to_spool_prewarms_scorers_before_worker_execution(
    tmp_path: Path,
) -> None:
    """Row processing should preload one ASR scorer per GPU worker slot."""
    source_audio_path = tmp_path / "fixtures/source.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    created_scorers: list["_FakeScorer"] = []

    class _FakeScorer:
        def __init__(self) -> None:
            self.ensure_loaded_calls = 0

        def ensure_loaded(self) -> None:
            self.ensure_loaded_calls += 1

        def transcribe(self, _: Path) -> str:
            return "Hej från Sverige."

    def _fake_factory(model_id: str, revision: str) -> _FakeScorer:
        assert model_id == "KBLab/kb-whisper-large"
        assert revision == "strict"
        scorer = _FakeScorer()
        created_scorers.append(scorer)
        return scorer

    process_rows_to_spool(
        Task103PreprocessingSettings(
            output_root=tmp_path / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            row_worker_count=2,
            gpu_asr_worker_count=2,
        ),
        output_root=tmp_path / "build/reference/qwen3-tts-swedish-corpus",
        source_records=[
            _build_source_record(
                dataset="repo_fixture_sv",
                source_split="fixture",
                dataset_row_id="repo-fixture-test-001",
                speaker_id="speaker_test",
                speaker_name="Test Speaker",
                source_audio_path=source_audio_path,
                reference_audio_path=None,
                text_raw="Hej från Sverige.",
            )
        ],
        scorer_factory=_fake_factory,
    )

    assert len(created_scorers) == 2
    assert [scorer.ensure_loaded_calls for scorer in created_scorers] == [1, 1]
    spool_rows = list(
        (
            tmp_path / "build/reference/qwen3-tts-swedish-corpus/spool/rows/repo_fixture_sv/fixture"
        ).rglob("*.json")
    )
    assert len(spool_rows) == 1


def test_task103_preprocessing_supports_multiple_manifest_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The adapter-driven core should populate multiple canonical families."""
    workspace_root = tmp_path / "workspace"
    fleurs_audio_path = workspace_root / "fixtures/fleurs.wav"
    waxholm_audio_path = workspace_root / "fixtures/waxholm.wav"
    _write_test_wav(fleurs_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)
    _write_test_wav(waxholm_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core._encode_audio_codes",
        lambda *, tokenizer_model, audio_paths: [[[21, 22]] for _ in audio_paths],
    )

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=workspace_root / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        ),
        source_records=[
            _build_source_record(
                dataset="fleurs_sv_se",
                source_split="dev",
                dataset_row_id="fleurs-dev-001",
                speaker_id="fleurs_sv_se_123",
                speaker_name="FLEURS speaker 123",
                source_audio_path=fleurs_audio_path,
                reference_audio_path=None,
                text_raw="Hej från Sverige.",
            ),
            _build_source_record(
                dataset="waxholm",
                source_split="control",
                dataset_row_id="waxholm-001",
                speaker_id="waxholm_fp2001",
                speaker_name="fp2001",
                source_audio_path=waxholm_audio_path,
                reference_audio_path=None,
                text_raw="Hej från Sverige.",
            ),
        ],
    )

    assert report.manifest_counts["swedish_checkpoint_dev"] == 1
    assert report.manifest_counts["swedish_waxholm_control"] == 1
    output_root = Path(report.output_root)
    checkpoint_row = json.loads(
        (output_root / "curated/swedish_checkpoint_dev.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    waxholm_row = json.loads(
        (output_root / "curated/swedish_waxholm_control.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    assert checkpoint_row["manifest_target"] == "swedish_checkpoint_dev"
    assert waxholm_row["manifest_target"] == "swedish_waxholm_control"


def test_manifest_targets_for_curated_source_route_rixvox_train_by_quality() -> None:
    """RixVox train rows should map into bounded train families by trust tier."""
    source_record = SourceRecord(
        dataset="rixvox",
        source_split="train",
        dataset_row_id="rixvox-train-001",
        speaker_id="rixvox_0584659199514",
        speaker_name="Göran Hägglund",
        speaker_from_id=True,
        source_audio_path="GR01BOU3/2442210220028601121_anf191_1_25.wav",
        text_raw="Hej från Sverige.",
        language="sv-SE",
        speaker_total_hours=1.0,
        has_label_files=False,
        speaker_audio_meta_ok=True,
    )

    assert manifest_targets_for_curated_source(
        source_record,
        quality_tier="high_trust",
        speaker_quality_gate="speaker_from_id",
    ) == (
        "swedish_smoke_train",
        "swedish_pilot_train",
        "swedish_scaleup_train",
    )
    assert manifest_targets_for_curated_source(
        source_record,
        quality_tier="medium_trust",
        speaker_quality_gate="speaker_from_id",
    ) == ("swedish_scaleup_train",)
    assert (
        manifest_targets_for_curated_source(
            source_record,
            quality_tier="rejected",
            speaker_quality_gate="speaker_from_id",
        )
        == ()
    )


def test_task103_preprocessing_routes_rixvox_train_into_train_manifest_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """High-trust RixVox train rows should populate smoke, pilot, and scale-up manifests."""
    workspace_root = tmp_path / "workspace"
    archive_path = workspace_root / "raw/train_0.tar.gz"
    source_audio_path = tmp_path / "rixvox_train_source.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=3.0)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01BOU3/2442210220028601121_anf191_1_25.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core._encode_audio_codes",
        lambda *, tokenizer_model, audio_paths: [[[31, 32]] for _ in audio_paths],
    )

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=workspace_root / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        ),
        source_records=[
            SourceRecord(
                dataset="rixvox",
                source_split="train",
                dataset_row_id="GR01BOU3-191-0",
                speaker_id="rixvox_0584659199514",
                speaker_name="Göran Hägglund",
                speaker_from_id=True,
                source_audio_path="GR01BOU3/2442210220028601121_anf191_1_25.wav",
                source_audio_locator=AudioLocator(
                    archive_path,
                    archive_member="GR01BOU3/2442210220028601121_anf191_1_25.wav",
                ),
                text_raw="Hej från Sverige.",
                language="sv-SE",
                speaker_total_hours=1.0,
                has_label_files=False,
                speaker_audio_meta_ok=True,
                source_sample_rate_hz=16_000,
                duration_seconds=3.0,
            )
        ],
    )

    assert report.manifest_counts["swedish_smoke_train"] == 1
    assert report.manifest_counts["swedish_pilot_train"] == 1
    assert report.manifest_counts["swedish_scaleup_train"] == 1


def test_task103_row_processing_stage_emits_spool_without_manifests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The row-processing stage should persist spool rows without final manifests."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    reference_audio_path = workspace_root / "fixtures/ref.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.25)
    _write_test_wav(reference_audio_path, sample_rate_hz=16_000, duration_seconds=6.0)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=workspace_root / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=[
            _build_source_record(
                dataset="repo_fixture_sv",
                source_split="fixture",
                dataset_row_id="repo-fixture-test-001",
                speaker_id="speaker_test",
                speaker_name="Test Speaker",
                source_audio_path=source_audio_path,
                reference_audio_path=reference_audio_path,
                text_raw="Hej från Sverige.",
            )
        ],
    )

    output_root = Path(report.output_root)
    assert report.inventory_rows == 1
    assert report.curated_rows == 0
    assert report.prepared_rows == 0
    assert (output_root / "spool/rows").is_dir()
    assert len(list((output_root / "spool/rows").rglob("*.json"))) == 1
    assert not (output_root / "manifests/swedish_smoke_train.prepared.jsonl").exists()


def test_task103_row_processing_resume_reuses_existing_spool_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resumed row-processing should skip source rows that already have spool artifacts."""
    workspace_root = tmp_path / "workspace"
    first_audio_path = workspace_root / "fixtures/first.wav"
    second_audio_path = workspace_root / "fixtures/second.wav"
    _write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    _write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    def _fake_transcribe(self: object, audio_path: Path) -> str:
        transcribed_paths.append(audio_path.name)
        return "Hej från Sverige."

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        _fake_transcribe,
    )

    source_records = [
        _build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-test-001",
            speaker_id="speaker_test",
            speaker_name="Test Speaker",
            source_audio_path=first_audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        ),
        _build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-test-002",
            speaker_id="speaker_test",
            speaker_name="Test Speaker",
            source_audio_path=second_audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        ),
    ]
    output_root = workspace_root / "build/reference/qwen3-tts-swedish-corpus"
    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=[source_records[0]],
    )
    transcribed_paths.clear()

    heartbeats: list[Task103RowProcessingHeartbeat] = []
    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
            resume_row_processing=True,
        ),
        source_records=source_records,
        row_heartbeat_callback=heartbeats.append,
    )

    assert transcribed_paths == ["repo-fixture-test-002.wav"]
    assert len(list((output_root / "spool/rows").rglob("*.json"))) == 2
    assert heartbeats[0].processed_row_count == 1
    assert heartbeats[-1].processed_row_count == 2
    assert heartbeats[-1].total_row_count == 2
    completed_row_index_rows = [
        json.loads(raw_line)
        for raw_line in completed_row_keys_index_path(output_root).read_text(
            encoding="utf-8"
        ).splitlines()
        if raw_line.strip() != ""
    ]
    assert len(completed_row_index_rows) == 2
    assert completed_row_index_rows[-1]["dataset_row_id"] == "repo-fixture-test-002"


def test_task103_row_processing_resume_rebuilds_missing_completed_row_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should rebuild the completed-row index from canonical spool rows."""
    workspace_root = tmp_path / "workspace"
    first_audio_path = workspace_root / "fixtures/first.wav"
    second_audio_path = workspace_root / "fixtures/second.wav"
    _write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    _write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    def _fake_transcribe(self: object, audio_path: Path) -> str:
        transcribed_paths.append(audio_path.name)
        return "Hej från Sverige."

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        _fake_transcribe,
    )

    source_records = [
        _build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-test-001",
            speaker_id="speaker_test",
            speaker_name="Test Speaker",
            source_audio_path=first_audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        ),
        _build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-test-002",
            speaker_id="speaker_test",
            speaker_name="Test Speaker",
            source_audio_path=second_audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        ),
    ]
    output_root = workspace_root / "build/reference/qwen3-tts-swedish-corpus"
    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=[source_records[0]],
    )
    completed_row_keys_index_path(output_root).unlink()
    transcribed_paths.clear()

    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
            resume_row_processing=True,
        ),
        source_records=source_records,
    )

    assert transcribed_paths == ["repo-fixture-test-002.wav"]
    rebuilt_index_rows = [
        json.loads(raw_line)
        for raw_line in completed_row_keys_index_path(output_root).read_text(
            encoding="utf-8"
        ).splitlines()
        if raw_line.strip() != ""
    ]
    assert len(rebuilt_index_rows) == 2


def test_task103_row_processing_resume_self_heals_stale_completed_row_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should skip expensive work when spool JSON exists ahead of the index."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    def _fake_transcribe(self: object, audio_path: Path) -> str:
        transcribed_paths.append(audio_path.name)
        return "Hej från Sverige."

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        _fake_transcribe,
    )

    source_record = _build_source_record(
        dataset="repo_fixture_sv",
        source_split="fixture",
        dataset_row_id="repo-fixture-test-001",
        speaker_id="speaker_test",
        speaker_name="Test Speaker",
        source_audio_path=source_audio_path,
        reference_audio_path=None,
        text_raw="Hej från Sverige.",
    )
    output_root = workspace_root / "build/reference/qwen3-tts-swedish-corpus"
    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=[source_record],
    )
    completed_row_keys_index_path(output_root).write_text("", encoding="utf-8")
    transcribed_paths.clear()

    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
            resume_row_processing=True,
        ),
        source_records=[source_record],
    )

    assert transcribed_paths == []
    healed_index_rows = [
        json.loads(raw_line)
        for raw_line in completed_row_keys_index_path(output_root).read_text(
            encoding="utf-8"
        ).splitlines()
        if raw_line.strip() != ""
    ]
    assert len(healed_index_rows) == 1
    assert healed_index_rows[0]["dataset_row_id"] == "repo-fixture-test-001"


def test_task103_row_processing_resume_ignores_empty_crash_artifact_spool_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resume should ignore zero-byte spool files left behind by a crash."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    def _fake_transcribe(self: object, audio_path: Path) -> str:
        transcribed_paths.append(audio_path.name)
        return "Hej från Sverige."

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        _fake_transcribe,
    )

    source_record = _build_source_record(
        dataset="repo_fixture_sv",
        source_split="fixture",
        dataset_row_id="repo-fixture-test-001",
        speaker_id="speaker_test",
        speaker_name="Test Speaker",
        source_audio_path=source_audio_path,
        reference_audio_path=None,
        text_raw="Hej från Sverige.",
    )
    output_root = workspace_root / "build/reference/qwen3-tts-swedish-corpus"
    corrupted_spool_path = (
        output_root
        / "spool/rows/repo_fixture_sv/fixture/speaker_test/repo-fixture-test-001.json"
    )
    corrupted_spool_path.parent.mkdir(parents=True, exist_ok=True)
    corrupted_spool_path.write_text("", encoding="utf-8")

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
            resume_row_processing=True,
        ),
        source_records=[source_record],
    )

    assert transcribed_paths == ["repo-fixture-test-001.wav"]
    assert report.inventory_rows == 1
    assert len(list((output_root / "spool/rows").rglob("*.json"))) == 1
    assert json.loads(corrupted_spool_path.read_text(encoding="utf-8"))["dataset_row_id"] == (
        "repo-fixture-test-001"
    )


def test_task103_resume_index_helper_rebuild_and_validate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The resume-index helper should rebuild and validate existing run roots."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )

    source_record = _build_source_record(
        dataset="repo_fixture_sv",
        source_split="fixture",
        dataset_row_id="repo-fixture-test-001",
        speaker_id="speaker_test",
        speaker_name="Test Speaker",
        source_audio_path=source_audio_path,
        reference_audio_path=None,
        text_raw="Hej från Sverige.",
    )
    output_root = workspace_root / "build/reference/qwen3-tts-swedish-corpus"
    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=[source_record],
    )
    completed_row_keys_index_path(output_root).unlink()
    capsys.readouterr()

    rebuild_exit_code = task103_resume_index_main(
        ["rebuild", "--run-root", output_root.as_posix()]
    )
    rebuild_payload = json.loads(capsys.readouterr().out)
    assert rebuild_exit_code == 0
    assert rebuild_payload["command"] == "rebuild"
    assert rebuild_payload["completed_row_count"] == 1

    validate_exit_code = task103_resume_index_main(
        ["validate", "--run-root", output_root.as_posix()]
    )
    validate_payload = json.loads(capsys.readouterr().out)
    assert validate_exit_code == 0
    assert validate_payload["command"] == "validate"
    assert validate_payload["completed_row_count"] == 1


def test_task103_finalization_stage_chunks_audio_code_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The finalization stage should bound `audio_codes` generation by chunk size."""
    workspace_root = tmp_path / "workspace"
    first_audio_path = workspace_root / "fixtures/first.wav"
    second_audio_path = workspace_root / "fixtures/second.wav"
    third_audio_path = workspace_root / "fixtures/third.wav"
    _write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    _write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    _write_test_wav(third_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core.WhisperStrictScorer.transcribe",
        lambda self, audio_path: "Hej från Sverige.",
    )

    source_records = [
        _build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id=f"repo-fixture-test-00{index}",
            speaker_id=f"speaker_{index}",
            speaker_name=f"Speaker {index}",
            source_audio_path=audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        )
        for index, audio_path in enumerate(
            (first_audio_path, second_audio_path, third_audio_path),
            start=1,
        )
    ]
    output_root = workspace_root / "build/reference/qwen3-tts-swedish-corpus"
    run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=source_records,
    )

    observed_chunk_sizes: list[int] = []

    def _fake_encode_audio_codes(
        *,
        tokenizer_model: str,
        audio_paths: list[Path],
    ) -> list[list[list[int]]]:
        observed_chunk_sizes.append(len(audio_paths))
        return [[[41, 42]] for _ in audio_paths]

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core._encode_audio_codes",
        _fake_encode_audio_codes,
    )

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=output_root,
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="finalization",
            finalization_families=("swedish_smoke_train",),
            audio_codes_chunk_size=2,
        ),
    )

    assert observed_chunk_sizes == [2, 1]
    assert report.manifest_counts["swedish_smoke_train"] == 3
    assert report.prepared_rows == 3


def test_task103_runner_main_prints_report_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Task 103 runner should print the completed report as JSON."""
    expected_report = Task103PreprocessingReport(
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
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _report_only_preprocessing_runner(expected_report),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
        lambda settings, **kwargs: None,
    )

    exit_code = main([])

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["output_root"] == expected_report.output_root
    assert stdout_payload["prepared_rows"] == 2


def test_task103_runner_main_uses_run_root_for_staged_public_corpus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The runner should allocate one immutable run root for staged public-corpus mode."""
    expected_run_root = tmp_path / "runs" / "proof-run"
    expected_report = Task103PreprocessingReport(
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

    def _fake_run_task103_preprocessing(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        nonlocal observed_output_root
        observed_output_root = settings.output_root
        return expected_report

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _fake_run_task103_preprocessing,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
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


def test_task103_runner_main_persists_row_processing_heartbeat(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner should persist row-level progress into the run-scoped status file."""
    expected_run_root = tmp_path / "runs" / "proof-run"
    expected_report = Task103PreprocessingReport(
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

    def _fake_run_task103_preprocessing(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        assert row_heartbeat_callback is not None
        row_heartbeat_callback(
            Task103RowProcessingHeartbeat(
                processed_row_count=2,
                total_row_count=4,
                current_dataset_row_id="rixvox-train-0002",
            )
        )
        return expected_report

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _fake_run_task103_preprocessing,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
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


def test_task103_runner_main_rejects_promotion_outside_reports_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner should only allow promotion from the reports stage."""
    promoted_root = tmp_path / "build/reference/qwen3-tts-swedish-corpus"
    expected_report = Task103PreprocessingReport(
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
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _report_only_preprocessing_runner(expected_report),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
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


def test_task103_runner_main_promotes_successful_reports_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reports stage should also promote a successful run when requested."""
    promoted_root = tmp_path / "build/reference/qwen3-tts-swedish-corpus"
    expected_run_root = tmp_path / "runs" / "proof-run"
    expected_report = Task103PreprocessingReport(
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
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _report_only_preprocessing_runner(expected_report),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
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


def test_task103_runner_main_persists_traceback_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runner should persist a full traceback in the run-scoped status payload."""
    expected_run_root = tmp_path / "runs" / "failing-run"

    def _boom(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        raise RuntimeError("meta tensor exploded")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _boom,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
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


def test_fleurs_source_records_parse_tsv_and_audio_archive(tmp_path: Path) -> None:
    """The FLEURS adapter should parse TSV rows and build tar-member audio locators."""
    snapshot_root = tmp_path / "fleurs_snapshot"
    tsv_path = snapshot_root / "data/sv_se/dev.tsv"
    archive_path = snapshot_root / "data/sv_se/audio/dev.tar.gz"
    source_audio_path = tmp_path / "tmp_audio.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)

    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tsv_path.write_text(
        "1641\t14347918279741910315.wav\tHej från Sverige.\thej från sverige\th e j\t24000\tMALE\n",
        encoding="utf-8",
    )
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="dev/14347918279741910315.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    source_records = fleurs_sv_source_records(snapshot_root, splits=("dev",))

    assert len(source_records) == 1
    source_record = source_records[0]
    assert source_record.dataset == "fleurs_sv_se"
    assert source_record.source_audio_locator is not None
    assert source_record.source_audio_locator.archive_member == "dev/14347918279741910315.wav"
    assert manifest_target_for_source(source_record) == "swedish_checkpoint_dev"
    assert source_record.speaker_total_hours == round(1.5 / 3600.0, 6)


def test_fleurs_source_records_parse_quoted_text_without_csv_semantics(tmp_path: Path) -> None:
    """The FLEURS adapter should preserve quoted text in raw TSV rows."""
    snapshot_root = tmp_path / "fleurs_snapshot"
    tsv_path = snapshot_root / "data/sv_se/test.tsv"
    archive_path = snapshot_root / "data/sv_se/audio/test.tar.gz"
    source_audio_path = tmp_path / "quoted_audio.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)

    tsv_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tsv_path.write_text(
        '1960\t7619464773135024428.wav\t"Han sa ""hej""."\t"han sa ""hej""."\th a n\t24000\tMALE\n',
        encoding="utf-8",
    )
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="test/7619464773135024428.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    source_records = fleurs_sv_source_records(snapshot_root, splits=("test",))

    assert len(source_records) == 1
    assert source_records[0].text_raw == '"Han sa ""hej""."'
    assert manifest_target_for_source(source_records[0]) == "swedish_final_test"


def test_waxholm_labeled_source_records_parse_text_and_audio(tmp_path: Path) -> None:
    """The Waxholm adapter should decode `.smp.mix` orthography into Swedish text."""
    snapshot_root = tmp_path / "waxholm_snapshot"
    listing_path = snapshot_root / "alloktrainfiles"
    speaker_dir = snapshot_root / "scenes_formatted/fp2001"
    wav_path = speaker_dir / "fp2001.1.01.wav"
    mix_path = speaker_dir / "fp2001.1.01.smp.mix"
    _write_test_wav(wav_path, sample_rate_hz=16_000, duration_seconds=2.0)
    listing_path.parent.mkdir(parents=True, exist_ok=True)
    listing_path.write_text("fp2001.1.01.smp\n", encoding="utf-8")
    mix_path.parent.mkdir(parents=True, exist_ok=True)
    mix_path.write_text(
        "\n".join(
            [
                "Waxholm dialog.",
                "TEXT:",
                "XsmackX jag vill }ka till str|mkajen .",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    source_records = waxholm_labeled_source_records(snapshot_root)

    assert len(source_records) == 1
    source_record = source_records[0]
    assert source_record.text_raw == "jag vill åka till strömkajen ."
    assert source_record.source_audio_locator is not None
    assert manifest_target_for_source(source_record) == "swedish_waxholm_control"


def test_rixvox_source_records_from_parquet_ingest_metadata_only(tmp_path: Path) -> None:
    """The RixVox adapter should ingest parquet metadata without audio materialization."""
    parquet_path = tmp_path / "dev_metadata.parquet"
    table = pa.Table.from_pylist(
        [
            {
                "dokid": "GR01KRU1",
                "anforande_nummer": 5,
                "observation_nr": 0,
                "speaker": "Peter Pedersen",
                "party": "V",
                "gender": "male",
                "debatedate": None,
                "electoral_district": "Örebro län",
                "birth_year": 1954,
                "intressent_id": "0556347007015",
                "speaker_from_id": True,
                "speaker_audio_meta": "Peter Pedersen (V)",
                "text": "Hej från Sverige.",
                "start": 0.64,
                "end": 27.0,
                "duration": 26.36,
                "bleu_score": 0.39,
                "filename": "GR01KRU1/2442210220028627521_anf5_1_27.wav",
                "speaker_total_hours": 5.026244444444444,
            }
        ]
    )
    pq.write_table(table, parquet_path)

    source_records = rixvox_source_records_from_parquet(parquet_path, split="dev")

    assert len(source_records) == 1
    source_record = source_records[0]
    assert source_record.source_audio_locator is None
    assert source_record.source_audio_path == "GR01KRU1/2442210220028627521_anf5_1_27.wav"
    assert source_record.duration_seconds == 26.36
    assert source_record.source_sample_rate_hz == 16_000
    assert manifest_target_for_source(source_record) == "swedish_checkpoint_dev"


def test_rixvox_source_records_from_parquet_attach_audio_locators(tmp_path: Path) -> None:
    """The RixVox adapter should attach tar-member locators when staged archives exist."""
    parquet_path = tmp_path / "train_metadata.parquet"
    archive_path = tmp_path / "train_0.tar.gz"
    source_audio_path = tmp_path / "rixvox_audio.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01KRU1/2442210220028627521_anf5_1_27.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))
    table = pa.Table.from_pylist(
        [
            {
                "dokid": "GR01KRU1",
                "anforande_nummer": 5,
                "observation_nr": 0,
                "speaker": "Peter Pedersen",
                "party": "V",
                "gender": "male",
                "debatedate": None,
                "electoral_district": "Örebro län",
                "birth_year": 1954,
                "intressent_id": "0556347007015",
                "speaker_from_id": True,
                "speaker_audio_meta": "Peter Pedersen (V)",
                "text": "Hej från Sverige.",
                "start": 0.64,
                "end": 27.0,
                "duration": 26.36,
                "bleu_score": 0.39,
                "filename": "GR01KRU1/2442210220028627521_anf5_1_27.wav",
                "speaker_total_hours": 5.026244444444444,
            }
        ]
    )
    pq.write_table(table, parquet_path)

    audio_index = build_rixvox_audio_locator_index([archive_path])
    source_records = rixvox_source_records_from_parquet_with_audio_locators(
        parquet_path,
        split="train",
        audio_locators_by_source_path=audio_index,
    )

    assert len(source_records) == 1
    assert source_records[0].source_audio_locator is not None
    assert source_records[0].source_audio_locator.path == archive_path
    assert source_records[0].source_audio_locator.archive_member == (
        "GR01KRU1/2442210220028627521_anf5_1_27.wav"
    )


def test_rixvox_source_records_from_parquet_stops_after_max_rows_during_iteration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bounded RixVox loader should stop iterating once the cap is satisfied."""
    sample_rows = [
        {
            "dokid": "GR01KRU1",
            "anforande_nummer": index,
            "observation_nr": 0,
            "speaker": "Peter Pedersen",
            "party": "V",
            "gender": "male",
            "debatedate": None,
            "electoral_district": "Örebro län",
            "birth_year": 1954,
            "intressent_id": "0556347007015",
            "speaker_from_id": True,
            "speaker_audio_meta": "Peter Pedersen (V)",
            "text": f"Hej från Sverige {index}.",
            "start": 0.0,
            "end": 5.0,
            "duration": 5.0,
            "bleu_score": 0.39,
            "filename": f"GR01KRU1/audio_{index}.wav",
            "speaker_total_hours": 5.026244444444444,
        }
        for index in range(1, 4)
    ]

    class _FakeBatch:
        def __init__(self, row: Mapping[str, object]) -> None:
            self._row = row

        def to_pylist(self) -> list[Mapping[str, object]]:
            return [self._row]

    class _FakeParquetFile:
        def __init__(self, _path: Path) -> None:
            self._batches = [_FakeBatch(row) for row in sample_rows]

        def iter_batches(self):  # noqa: ANN202
            return iter(self._batches)

    batch_events: list[tuple[int, int]] = []
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox.pq.ParquetFile",
        _FakeParquetFile,
    )

    source_records = rixvox_source_records_from_parquet_with_audio_locators(
        Path("/tmp/fake.parquet"),
        split="train",
        audio_locators_by_source_path=None,
        max_rows=2,
        batch_progress_callback=lambda batch_index, row_count: batch_events.append(
            (batch_index, row_count)
        ),
    )

    assert [row.dataset_row_id for row in source_records] == ["GR01KRU1-1-0", "GR01KRU1-2-0"]
    assert batch_events == [(1, 1), (2, 2)]


def test_build_rixvox_audio_locator_index_stops_after_required_paths_are_resolved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bounded locator index should not open later archives once all targets are found."""
    first_archive_path = tmp_path / "train_0.tar.gz"
    second_archive_path = tmp_path / "train_1.tar.gz"
    source_audio_path = tmp_path / "rixvox_audio.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    with tarfile.open(first_archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01KRU1/needed.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    original_tarfile_open = tarfile.open

    def _guarded_tarfile_open(
        name: str | Path,
        mode: str = "r",
        *args: object,
        **kwargs: object,
    ):
        del mode
        if Path(name) == second_archive_path:
            raise AssertionError(
                "Second archive should not be opened once all required files exist."
            )
        del args
        del kwargs
        return original_tarfile_open(name, "r:*")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox.tarfile.open",
        _guarded_tarfile_open,
    )

    audio_index = build_rixvox_audio_locator_index(
        [first_archive_path, second_archive_path],
        required_source_paths={"GR01KRU1/needed.wav"},
    )

    assert list(audio_index) == ["GR01KRU1/needed.wav"]


def test_task103_source_selection_stage_persists_selected_source_records(
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
                Task103SourceSelectionHeartbeat(
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
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.staged_public_corpus_source_records",
        _fake_staged_source_records,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.ensure_bulk_data_storage_path",
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


def test_task103_row_processing_reuses_selected_source_records(
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
        summary=Task103SourceSelectionSummary(
            source_mode="staged-public-corpus",
            total_selected_rows=1,
            datasets=["rixvox"],
            fleurs_splits=["dev", "test"],
            rixvox_splits=["train"],
            rixvox_max_rows_per_split=64,
        ),
    )

    captured_dataset_row_ids: list[str] = []

    def _fake_run_task103_preprocessing(
        _settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        del row_heartbeat_callback
        del finalization_heartbeat_callback
        assert source_records is not None
        captured_dataset_row_ids.extend(row.dataset_row_id for row in source_records)
        return Task103PreprocessingReport(
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
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _fake_run_task103_preprocessing,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.staged_public_corpus_source_records",
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


def test_staged_public_corpus_source_records_load_all_supported_inputs(tmp_path: Path) -> None:
    """The staged public-corpus loader should aggregate FLEURS, Waxholm, and RixVox."""
    data_root = tmp_path / "data_root"

    fleurs_root = data_root / "raw/google_fleurs"
    fleurs_tsv_path = fleurs_root / "data/sv_se/dev.tsv"
    fleurs_archive_path = fleurs_root / "data/sv_se/audio/dev.tar.gz"
    fleurs_audio_path = tmp_path / "fleurs_audio.wav"
    _write_test_wav(fleurs_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)
    fleurs_tsv_path.parent.mkdir(parents=True, exist_ok=True)
    fleurs_archive_path.parent.mkdir(parents=True, exist_ok=True)
    fleurs_tsv_path.write_text(
        "1641\t14347918279741910315.wav\tHej från Sverige.\thej från sverige\th e j\t24000\tMALE\n",
        encoding="utf-8",
    )
    with tarfile.open(fleurs_archive_path, "w:gz") as archive:
        audio_bytes = fleurs_audio_path.read_bytes()
        member = tarfile.TarInfo(name="dev/14347918279741910315.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    waxholm_root = data_root / "raw/kth_waxholm"
    waxholm_listing_path = waxholm_root / "alloktrainfiles"
    waxholm_speaker_dir = waxholm_root / "scenes_formatted/fp2001"
    waxholm_wav_path = waxholm_speaker_dir / "fp2001.1.01.wav"
    waxholm_mix_path = waxholm_speaker_dir / "fp2001.1.01.smp.mix"
    _write_test_wav(waxholm_wav_path, sample_rate_hz=16_000, duration_seconds=2.0)
    waxholm_listing_path.parent.mkdir(parents=True, exist_ok=True)
    waxholm_listing_path.write_text("fp2001.1.01.smp\n", encoding="utf-8")
    waxholm_mix_path.parent.mkdir(parents=True, exist_ok=True)
    waxholm_mix_path.write_text("TEXT:\nhej från sverige .\n", encoding="utf-8")

    rixvox_root = data_root / "raw/kblab_rixvox/data"
    rixvox_root.mkdir(parents=True, exist_ok=True)
    rixvox_parquet_path = rixvox_root / "test_metadata.parquet"
    rixvox_table = pa.Table.from_pylist(
        [
            {
                "dokid": "GR01KRU1",
                "anforande_nummer": 5,
                "observation_nr": 0,
                "speaker": "Peter Pedersen",
                "party": "V",
                "gender": "male",
                "debatedate": None,
                "electoral_district": "Örebro län",
                "birth_year": 1954,
                "intressent_id": "0556347007015",
                "speaker_from_id": True,
                "speaker_audio_meta": "Peter Pedersen (V)",
                "text": "Hej från Sverige.",
                "start": 0.64,
                "end": 27.0,
                "duration": 26.36,
                "bleu_score": 0.39,
                "filename": "GR01KRU1/2442210220028627521_anf5_1_27.wav",
                "speaker_total_hours": 5.026244444444444,
            }
        ]
    )
    pq.write_table(rixvox_table, rixvox_parquet_path)

    source_records = staged_public_corpus_source_records(
        data_root,
        fleurs_splits=("dev",),
        rixvox_splits=("test",),
    )

    assert [source_record.dataset for source_record in source_records] == [
        "fleurs_sv_se",
        "rixvox",
        "waxholm",
    ]
    assert source_records[0].source_audio_locator is not None
    assert source_records[1].source_audio_locator is None
    assert source_records[2].source_audio_locator is not None


def test_staged_public_corpus_source_records_attach_rixvox_train_archive_locators(
    tmp_path: Path,
) -> None:
    """The staged loader should attach RixVox train audio locators from staged archives."""
    data_root = tmp_path / "data_root"
    rixvox_root = data_root / "raw/kblab_rixvox/data"
    rixvox_root.mkdir(parents=True, exist_ok=True)
    train_parquet_path = rixvox_root / "train_metadata.parquet"
    train_archive_root = rixvox_root / "train"
    train_archive_root.mkdir(parents=True, exist_ok=True)
    train_archive_path = train_archive_root / "train_0.tar.gz"
    source_audio_path = tmp_path / "rixvox_train_audio.wav"
    _write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)
    with tarfile.open(train_archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01BOU3/2442210220028601121_anf191_1_25.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "dokid": "GR01BOU3",
                    "anforande_nummer": 191,
                    "observation_nr": 0,
                    "speaker": "Göran Hägglund",
                    "party": "KD",
                    "gender": "male",
                    "debatedate": None,
                    "electoral_district": None,
                    "birth_year": 1959,
                    "intressent_id": "0584659199514",
                    "speaker_from_id": True,
                    "speaker_audio_meta": "Göran Hägglund (KD)",
                    "text": "Hej från Sverige.",
                    "start": 1.0,
                    "end": 25.0,
                    "duration": 23.56,
                    "bleu_score": 0.72,
                    "filename": "GR01BOU3/2442210220028601121_anf191_1_25.wav",
                    "speaker_total_hours": 30.621333333333332,
                }
            ]
        ),
        train_parquet_path,
    )

    source_records = staged_public_corpus_source_records(
        data_root,
        include_waxholm=False,
        fleurs_splits=(),
        rixvox_splits=("train",),
    )

    assert len(source_records) == 1
    assert source_records[0].dataset == "rixvox"
    assert source_records[0].source_audio_locator is not None
    assert source_records[0].source_audio_locator.path == train_archive_path
    assert source_records[0].source_audio_locator.archive_member == (
        "GR01BOU3/2442210220028601121_anf191_1_25.wav"
    )


def test_staged_public_corpus_source_records_cap_fleurs_rows_per_split(tmp_path: Path) -> None:
    """The staged loader should support one deterministic FLEURS per-split cap."""
    data_root = tmp_path / "data_root"
    fleurs_root = data_root / "raw/google_fleurs"
    fleurs_tsv_path = fleurs_root / "data/sv_se/dev.tsv"
    fleurs_archive_path = fleurs_root / "data/sv_se/audio/dev.tar.gz"
    first_audio_path = tmp_path / "first_audio.wav"
    second_audio_path = tmp_path / "second_audio.wav"
    _write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)
    _write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)

    fleurs_tsv_path.parent.mkdir(parents=True, exist_ok=True)
    fleurs_archive_path.parent.mkdir(parents=True, exist_ok=True)
    fleurs_tsv_path.write_text(
        "\n".join(
            [
                "1641\t111.wav\tFörsta raden.\tforsta raden\tf ö r s t a\t24000\tMALE",
                "1641\t222.wav\tAndra raden.\tandra raden\ta n d r a\t24000\tMALE",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    with tarfile.open(fleurs_archive_path, "w:gz") as archive:
        for archive_name, source_audio_path in (
            ("dev/111.wav", first_audio_path),
            ("dev/222.wav", second_audio_path),
        ):
            audio_bytes = source_audio_path.read_bytes()
            member = tarfile.TarInfo(name=archive_name)
            member.size = len(audio_bytes)
            archive.addfile(member, io.BytesIO(audio_bytes))

    waxholm_root = data_root / "raw/kth_waxholm"
    waxholm_listing_path = waxholm_root / "alloktrainfiles"
    waxholm_speaker_dir = waxholm_root / "scenes_formatted/fp2001"
    waxholm_wav_path = waxholm_speaker_dir / "fp2001.1.01.wav"
    waxholm_mix_path = waxholm_speaker_dir / "fp2001.1.01.smp.mix"
    _write_test_wav(waxholm_wav_path, sample_rate_hz=16_000, duration_seconds=2.0)
    waxholm_listing_path.parent.mkdir(parents=True, exist_ok=True)
    waxholm_listing_path.write_text("fp2001.1.01.smp\n", encoding="utf-8")
    waxholm_mix_path.parent.mkdir(parents=True, exist_ok=True)
    waxholm_mix_path.write_text("TEXT:\nhej från sverige .\n", encoding="utf-8")

    rixvox_root = data_root / "raw/kblab_rixvox/data"
    rixvox_root.mkdir(parents=True, exist_ok=True)
    rixvox_parquet_path = rixvox_root / "test_metadata.parquet"
    pq.write_table(
        pa.Table.from_pylist(
            [
                {
                    "dokid": "GR01KRU1",
                    "anforande_nummer": 5,
                    "observation_nr": 0,
                    "speaker": "Peter Pedersen",
                    "party": "V",
                    "gender": "male",
                    "debatedate": None,
                    "electoral_district": "Örebro län",
                    "birth_year": 1954,
                    "intressent_id": "0556347007015",
                    "speaker_from_id": True,
                    "speaker_audio_meta": "Peter Pedersen (V)",
                    "text": "Hej från Sverige.",
                    "start": 0.64,
                    "end": 27.0,
                    "duration": 26.36,
                    "bleu_score": 0.39,
                    "filename": "GR01KRU1/2442210220028627521_anf5_1_27.wav",
                    "speaker_total_hours": 5.026244444444444,
                }
            ]
        ),
        rixvox_parquet_path,
    )

    source_records = staged_public_corpus_source_records(
        data_root,
        fleurs_splits=("dev",),
        fleurs_max_rows_per_split=1,
        rixvox_splits=("test",),
    )

    assert [source_record.dataset for source_record in source_records] == [
        "fleurs_sv_se",
        "rixvox",
        "waxholm",
    ]


def test_task103_runner_main_staged_public_corpus_passes_source_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The runner should resolve staged public-corpus records before core execution."""
    expected_report = Task103PreprocessingReport(
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
        _build_source_record(
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
    observed_runner_settings: list[Task103RunnerSettings] = []
    observed_source_records: list[list[SourceRecord] | None] = []

    def _fake_resolve_source_records(
        settings: Task103RunnerSettings,
        **kwargs: object,
    ) -> list[SourceRecord]:
        del kwargs
        observed_runner_settings.append(settings)
        return expected_source_records

    def _fake_run_task103_preprocessing(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
        row_heartbeat_callback=None,
        finalization_heartbeat_callback=None,
    ) -> Task103PreprocessingReport:
        assert source_records is not None
        observed_source_records.append(list(source_records))
        return expected_report

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
        _fake_resolve_source_records,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing.run_task103_preprocessing",
        _fake_run_task103_preprocessing,
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


def test_whisper_strict_scorer_transcribes_with_pipeline(
    tmp_path: Path,
) -> None:
    """The ASR scorer should delegate transcription to the cached pipeline."""

    class _FakePipeline:
        def __call__(
            self,
            inputs: object,
            *,
            generate_kwargs: dict[str, object] | None = None,
        ) -> dict[str, object]:
            assert inputs == (tmp_path / "audio.wav").as_posix()
            assert generate_kwargs == {"task": "transcribe"}
            return {"text": "Hej från Sverige."}

    scorer = WhisperStrictScorer(
        model_id="KBLab/kb-whisper-large",
        revision="strict",
        _pipeline=_FakePipeline(),
    )

    transcript = scorer.transcribe(tmp_path / "audio.wav")

    assert transcript == "Hej från Sverige."


def test_whisper_strict_scorer_uses_pipeline_gpu_loading_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CUDA pipeline loading should use the documented GPU pipeline surface."""

    class _FakeTorchCuda:
        @staticmethod
        def is_available() -> bool:
            return True

    class _FakeTorch:
        cuda = _FakeTorchCuda()
        float16 = "float16"
        float32 = "float32"

        @staticmethod
        def device(name: str) -> object:
            return type("_FakeDevice", (), {"type": name})()

    captured_kwargs: dict[str, object] = {}

    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        type(
            "_FakeTransformersModule",
            (),
            {
                "pipeline": staticmethod(
                    lambda **kwargs: captured_kwargs.update(kwargs) or object()
                ),
            },
        )(),
    )

    scorer = WhisperStrictScorer(model_id="KBLab/kb-whisper-large", revision="strict")
    scorer._ensure_loaded()

    assert captured_kwargs["revision"] == "strict"
    assert captured_kwargs["dtype"] == "float16"
    assert captured_kwargs["device"] == 0
    assert captured_kwargs["task"] == "automatic-speech-recognition"


def test_whisper_strict_scorer_serializes_pipeline_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent scorer calls should initialize one cached pipeline per scorer."""

    class _FakeTorchCuda:
        @staticmethod
        def is_available() -> bool:
            return False

    class _FakeTorch:
        cuda = _FakeTorchCuda()
        float16 = "float16"
        float32 = "float32"

    load_call_count = 0
    load_call_lock = threading.Lock()

    class _FakePipeline:
        def __call__(
            self,
            inputs: object,
            *,
            generate_kwargs: dict[str, object] | None = None,
        ) -> dict[str, object]:
            assert generate_kwargs == {"task": "transcribe"}
            return {"text": f"transcribed:{inputs}"}

    def _fake_pipeline(**_: object) -> _FakePipeline:
        nonlocal load_call_count
        with load_call_lock:
            load_call_count += 1
        return _FakePipeline()

    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        type("_FakeTransformersModule", (), {"pipeline": staticmethod(_fake_pipeline)})(),
    )

    scorer = WhisperStrictScorer(model_id="KBLab/kb-whisper-large", revision="strict")
    audio_path = Path("/tmp/example.wav")

    first_thread = threading.Thread(target=scorer.transcribe, args=(audio_path,))
    second_thread = threading.Thread(target=scorer.transcribe, args=(audio_path,))
    first_thread.start()
    second_thread.start()
    first_thread.join()
    second_thread.join()

    assert load_call_count == 1
