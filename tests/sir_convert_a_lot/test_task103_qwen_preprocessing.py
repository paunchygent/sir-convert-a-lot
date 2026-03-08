"""Tests for the Task 103 and Task 106 Qwen Swedish preprocessing surfaces."""

from __future__ import annotations

import io
import json
import math
import tarfile
import wave
from pathlib import Path
from typing import Sequence

import numpy as np
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
    DEFAULT_SOURCE_MODE,
    DEFAULT_TOKENIZER_MODEL,
    Task103RunnerSettings,
    _parse_args,
    main,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import (
    manifest_target_for_source,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    CANONICAL_MANIFEST_FAMILIES,
    ProcessorOutputProtocol,
    Task103PreprocessingReport,
    Task103PreprocessingSettings,
    TorchTensorProtocol,
    WhisperStrictScorer,
    run_task103_preprocessing,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_fleurs import fleurs_sv_source_records
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import AudioLocator, SourceRecord
from scripts.sir_convert_a_lot.devops.task103_qwen_source_rixvox import (
    build_rixvox_audio_locator_index,
    rixvox_source_records_from_parquet,
    rixvox_source_records_from_parquet_with_audio_locators,
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


def test_task103_parse_args_defaults() -> None:
    """The Task 103 runner should expose deterministic defaults."""
    runner_settings = _parse_args([])

    assert runner_settings.preprocessing.output_root == DEFAULT_OUTPUT_ROOT
    assert runner_settings.preprocessing.asr_model == DEFAULT_ASR_MODEL
    assert runner_settings.preprocessing.asr_revision == DEFAULT_ASR_REVISION
    assert runner_settings.preprocessing.tokenizer_model == DEFAULT_TOKENIZER_MODEL
    assert runner_settings.source_mode == DEFAULT_SOURCE_MODE
    assert runner_settings.data_root == DEFAULT_DATA_ROOT
    assert runner_settings.fleurs_splits == DEFAULT_FLEURS_SPLITS
    assert runner_settings.fleurs_max_rows_per_split == DEFAULT_FLEURS_MAX_ROWS_PER_SPLIT
    assert runner_settings.rixvox_splits == DEFAULT_RIXVOX_SPLITS


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
        ]
    )

    assert runner_settings.source_mode == "staged-public-corpus"
    assert runner_settings.data_root == tmp_path
    assert runner_settings.fleurs_splits == ("dev",)
    assert runner_settings.fleurs_max_rows_per_split == 8
    assert runner_settings.rixvox_splits == ("test",)


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
        lambda settings, *, source_records=None: expected_report,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing._resolve_source_records",
        lambda settings: None,
    )

    exit_code = main([])

    assert exit_code == 0
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["output_root"] == expected_report.output_root
    assert stdout_payload["prepared_rows"] == 2


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

    def _fake_resolve_source_records(settings: Task103RunnerSettings) -> list[SourceRecord]:
        observed_runner_settings.append(settings)
        return expected_source_records

    def _fake_run_task103_preprocessing(
        settings: Task103PreprocessingSettings,
        *,
        source_records: Sequence[SourceRecord] | None = None,
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
        ]
    )

    assert exit_code == 0
    assert observed_runner_settings[0].source_mode == "staged-public-corpus"
    assert observed_runner_settings[0].fleurs_max_rows_per_split == 8
    assert observed_source_records == [expected_source_records]
    stdout_payload = json.loads(capsys.readouterr().out)
    assert stdout_payload["datasets"] == ["fleurs_sv_se", "rixvox", "waxholm"]


def test_whisper_strict_scorer_resamples_to_processor_rate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The ASR scorer should resample 24 kHz training audio to 16 kHz for Whisper."""

    class _FakeInputFeatures:
        def __init__(self) -> None:
            self.dtype_received: object | None = None

        def to(self, *args: object, **kwargs: object) -> TorchTensorProtocol:
            self.dtype_received = kwargs.get("dtype")
            return self

    class _FakeProcessor:
        def __init__(self) -> None:
            self.feature_extractor = type("_FeatureExtractor", (), {"sampling_rate": 16_000})()
            self.sampling_rate_seen: int | None = None

        class _Processed:
            def __init__(self) -> None:
                self.input_features: TorchTensorProtocol = _FakeInputFeatures()
                self.attention_mask: TorchTensorProtocol | None = _FakeInputFeatures()

        def __call__(
            self,
            waveform: object,
            *,
            sampling_rate: int,
            return_tensors: str,
            return_attention_mask: bool,
        ) -> ProcessorOutputProtocol:
            assert return_tensors == "pt"
            assert return_attention_mask is True
            self.sampling_rate_seen = sampling_rate
            return self._Processed()

        def batch_decode(self, sequences: object, *, skip_special_tokens: bool) -> list[str]:
            assert skip_special_tokens is True
            return ["Hej från Sverige."]

    class _FakeModel:
        def to(self, device: object) -> "_FakeModel":
            return self

        def eval(self) -> None:
            return None

        def generate(
            self,
            input_features: object,
            *,
            attention_mask: object = None,
            max_new_tokens: int,
            task: str,
        ) -> list[list[int]]:
            assert attention_mask is not None
            assert max_new_tokens == 256
            assert task == "transcribe"
            return [[1, 2, 3]]

    fake_processor = _FakeProcessor()
    scorer = WhisperStrictScorer(
        model_id="KBLab/kb-whisper-large",
        revision="strict",
        _model=_FakeModel(),
        _processor=fake_processor,
        _device=type("_FakeDevice", (), {"type": "cpu"})(),
        _dtype=np.float32,
    )

    monkeypatch.setattr(
        "soundfile.read",
        lambda path, dtype: (np.ones(24_000, dtype=np.float32), 24_000),
    )
    monkeypatch.setattr(
        "librosa.resample",
        lambda waveform, *, orig_sr, target_sr: np.ones(target_sr, dtype=np.float32),
    )

    transcript = scorer.transcribe(tmp_path / "audio.wav")

    assert transcript == "Hej från Sverige."
    assert fake_processor.sampling_rate_seen == 16_000
