"""Task 103 source-adapter and staged-corpus tests.

Purpose:
    Cover the bounded parsing and aggregation behavior for FLEURS, Waxholm,
    RixVox, and staged-public-corpus loaders so data-ingest refactors can land
    without being hidden inside runner or row-processing tests.

Relationships:
    - Tests the Task 103 source-adapter modules and staged public-corpus loader.
    - Reuses deterministic fixture helpers from `task103_test_support`.
"""

from __future__ import annotations

import io
import tarfile
from pathlib import Path
from typing import Mapping

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import (
    manifest_target_for_source,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_fleurs import fleurs_sv_source_records
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
from tests.sir_convert_a_lot.task103_test_support import write_test_wav


def test_fleurs_source_records_parse_tsv_and_audio_archive(tmp_path: Path) -> None:
    """The FLEURS adapter should parse TSV rows and build tar-member audio locators."""
    snapshot_root = tmp_path / "fleurs_snapshot"
    tsv_path = snapshot_root / "data/sv_se/dev.tsv"
    archive_path = snapshot_root / "data/sv_se/audio/dev.tar.gz"
    source_audio_path = tmp_path / "tmp_audio.wav"
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)

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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)

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
    write_test_wav(wav_path, sample_rate_hz=16_000, duration_seconds=2.0)
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)
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

        def iter_batches(self):
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=1.0)

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


def test_staged_public_corpus_source_records_load_all_supported_inputs(tmp_path: Path) -> None:
    """The staged public-corpus loader should aggregate FLEURS, Waxholm, and RixVox."""
    data_root = tmp_path / "data_root"

    fleurs_root = data_root / "raw/google_fleurs"
    fleurs_tsv_path = fleurs_root / "data/sv_se/dev.tsv"
    fleurs_archive_path = fleurs_root / "data/sv_se/audio/dev.tar.gz"
    fleurs_audio_path = tmp_path / "fleurs_audio.wav"
    write_test_wav(fleurs_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)
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
    write_test_wav(waxholm_wav_path, sample_rate_hz=16_000, duration_seconds=2.0)
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
    write_test_wav(source_audio_path, sample_rate_hz=16_000, duration_seconds=2.0)
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
    write_test_wav(first_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)
    write_test_wav(second_audio_path, sample_rate_hz=16_000, duration_seconds=1.5)

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
    write_test_wav(waxholm_wav_path, sample_rate_hz=16_000, duration_seconds=2.0)
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
