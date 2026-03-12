"""Task 103 preprocessing, resume, and finalization tests.

Purpose:
    Cover the domain behavior of Task 103 row materialization, manifest routing,
    resume semantics, and finalization without mixing in runner-only or
    source-adapter parsing concerns.

Relationships:
    - Tests `task103_qwen_preprocessing_core`,
      `task103_qwen_preprocessing_row_stage`, and resume-index helpers.
    - Reuses shared builders from `task103_test_support`.
"""

from __future__ import annotations

import io
import json
import tarfile
import wave
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import (
    manifest_targets_for_curated_source,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    CANONICAL_MANIFEST_FAMILIES,
    Task103PreprocessingSettings,
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
)
from scripts.sir_convert_a_lot.devops.task103_qwen_resume_index import (
    main as task103_resume_index_main,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    AudioLocator,
    SourceRecord,
)
from tests.sir_convert_a_lot.task103_test_support import (
    build_source_record,
    stub_whisper_strict_scorer,
    write_test_wav,
)


def test_task103_preprocessing_emits_deterministic_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 103 core should emit inventory, curated, raw, and prepared layers."""
    workspace_root = tmp_path / "workspace"
    source_audio_path = workspace_root / "fixtures/source.wav"
    reference_audio_path = workspace_root / "fixtures/ref.wav"
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.25)
    write_test_wav(reference_audio_path, sample_rate_hz=16_000, duration_seconds=6.0)

    stub_whisper_strict_scorer(monkeypatch)
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
            build_source_record(
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

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
            build_source_record(
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
    write_test_wav(fleurs_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)
    write_test_wav(waxholm_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)

    stub_whisper_strict_scorer(monkeypatch)
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
            build_source_record(
                dataset="fleurs_sv_se",
                source_split="dev",
                dataset_row_id="fleurs-dev-001",
                speaker_id="fleurs_sv_se_123",
                speaker_name="FLEURS speaker 123",
                source_audio_path=fleurs_audio_path,
                reference_audio_path=None,
                text_raw="Hej från Sverige.",
            ),
            build_source_record(
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=3.0)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as archive:
        audio_bytes = source_audio_path.read_bytes()
        member = tarfile.TarInfo(name="GR01BOU3/2442210220028601121_anf191_1_25.wav")
        member.size = len(audio_bytes)
        archive.addfile(member, io.BytesIO(audio_bytes))

    stub_whisper_strict_scorer(monkeypatch)
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.25)
    write_test_wav(reference_audio_path, sample_rate_hz=16_000, duration_seconds=6.0)

    stub_whisper_strict_scorer(monkeypatch)

    report = run_task103_preprocessing(
        Task103PreprocessingSettings(
            output_root=workspace_root / "build/reference/qwen3-tts-swedish-corpus",
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            stage="row-processing",
        ),
        source_records=[
            build_source_record(
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
    write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    stub_whisper_strict_scorer(
        monkeypatch,
        transcribed_paths=transcribed_paths,
    )

    source_records = [
        build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-test-001",
            speaker_id="speaker_test",
            speaker_name="Test Speaker",
            source_audio_path=first_audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        ),
        build_source_record(
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
        for raw_line in completed_row_keys_index_path(output_root)
        .read_text(encoding="utf-8")
        .splitlines()
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
    write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    stub_whisper_strict_scorer(
        monkeypatch,
        transcribed_paths=transcribed_paths,
    )

    source_records = [
        build_source_record(
            dataset="repo_fixture_sv",
            source_split="fixture",
            dataset_row_id="repo-fixture-test-001",
            speaker_id="speaker_test",
            speaker_name="Test Speaker",
            source_audio_path=first_audio_path,
            reference_audio_path=None,
            text_raw="Hej från Sverige.",
        ),
        build_source_record(
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
        for raw_line in completed_row_keys_index_path(output_root)
        .read_text(encoding="utf-8")
        .splitlines()
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    stub_whisper_strict_scorer(
        monkeypatch,
        transcribed_paths=transcribed_paths,
    )

    source_record = build_source_record(
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
        for raw_line in completed_row_keys_index_path(output_root)
        .read_text(encoding="utf-8")
        .splitlines()
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    transcribed_paths: list[str] = []

    stub_whisper_strict_scorer(
        monkeypatch,
        transcribed_paths=transcribed_paths,
    )

    source_record = build_source_record(
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
        output_root / "spool/rows/repo_fixture_sv/fixture/speaker_test/repo-fixture-test-001.json"
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    stub_whisper_strict_scorer(monkeypatch)

    source_record = build_source_record(
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

    rebuild_exit_code = task103_resume_index_main(["rebuild", "--run-root", output_root.as_posix()])
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
    write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)
    write_test_wav(third_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

    stub_whisper_strict_scorer(monkeypatch)

    source_records = [
        build_source_record(
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
