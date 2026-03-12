"""Tests for deterministic Task 101 Qwen pilot-bundle materialization."""

from __future__ import annotations

import errno
import json
import shutil
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle import (
    build_task101_pilot_bundle,
    task101_pilot_bundle_report_path,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import ManifestFamily
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    QualityTier,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    write_json,
    write_spool_row,
)
from tests.sir_convert_a_lot.task103_test_support import write_test_wav


def _write_frozen_root_fixture(source_root: Path) -> None:
    """Persist one minimal frozen-root fixture with pilot/dev rows and freeze reports."""
    _write_spool_row_fixture(
        source_root=source_root,
        dataset_row_id="train-row-1",
        audio_name="train-row-1.wav",
        manifest_targets=("swedish_pilot_train",),
    )
    _write_spool_row_fixture(
        source_root=source_root,
        dataset_row_id="dev-row-1",
        audio_name="dev-row-1.wav",
        manifest_targets=("swedish_checkpoint_dev",),
    )
    _write_spool_row_fixture(
        source_root=source_root,
        dataset_row_id="ignored-row",
        audio_name="ignored-row.wav",
        manifest_targets=("swedish_final_test",),
    )
    write_json(
        source_root / "reports" / "canonical_processed_root_freeze.json",
        {
            "output_root": source_root.as_posix(),
            "retained_row_count": 3,
            "conflict_row_count": 1,
            "owned_row_keys_path": (
                source_root / "reports" / "canonical_processed_root_owned_row_keys.jsonl"
            ).as_posix(),
            "conflict_row_keys_path": (
                source_root / "reports" / "canonical_processed_root_conflict_row_keys.jsonl"
            ).as_posix(),
        },
    )
    (source_root / "reports" / "canonical_processed_root_owned_row_keys.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "dataset": "rixvox",
                        "source_split": "train",
                        "dataset_row_id": "train-row-1",
                    }
                ),
                json.dumps(
                    {
                        "dataset": "rixvox",
                        "source_split": "dev",
                        "dataset_row_id": "dev-row-1",
                    }
                ),
                json.dumps(
                    {
                        "dataset": "rixvox",
                        "source_split": "test",
                        "dataset_row_id": "ignored-row",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (source_root / "reports" / "canonical_processed_root_conflict_row_keys.jsonl").write_text(
        json.dumps(
            {
                "dataset": "rixvox",
                "source_split": "train",
                "dataset_row_id": "conflict-row",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_spool_row_fixture(
    *,
    source_root: Path,
    dataset_row_id: str,
    audio_name: str,
    manifest_targets: tuple[ManifestFamily, ...],
) -> None:
    """Persist one admitted spool row fixture and its audio."""
    split = "train"
    if "checkpoint_dev" in "".join(manifest_targets):
        split = "dev"
    if "final_test" in "".join(manifest_targets):
        split = "test"
    audio_path = source_root / "audio_24k" / "rixvox" / split / "speaker-a" / audio_name
    write_test_wav(audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    write_spool_row(
        source_root,
        SpoolRow(
            dataset="rixvox",
            source_split=split,
            dataset_row_id=dataset_row_id,
            speaker_id="speaker-a",
            speaker_name="speaker-a",
            speaker_from_id=True,
            source_audio_path=f"speaker-a/{audio_name}",
            audio_24k_path=audio_path.relative_to(source_root).as_posix(),
            duration_seconds=1.0,
            text_normalized=f"text for {dataset_row_id}",
            reference_audio_24k_paths={},
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            asr_transcript=f"text for {dataset_row_id}",
            asr_wer=0.0,
            quality_tier=_quality_tier_for_targets(manifest_targets),
            speaker_quality_gate="speaker_from_id",
            dedup_applied=False,
            admission_decision="admit",
            manifest_targets=manifest_targets,
        ),
    )


def _quality_tier_for_targets(manifest_targets: tuple[ManifestFamily, ...]) -> QualityTier:
    """Return one deterministic quality tier for the requested manifest families."""
    del manifest_targets
    return "high_trust"


def _fake_encode_audio_codes(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Return deterministic fake audio codes for pilot-bundle tests."""
    assert tokenizer_model == "Qwen/Qwen3-TTS-Tokenizer-12Hz"
    return [[[index + 1, index + 2]] for index, _ in enumerate(audio_paths)]


def test_build_task101_pilot_bundle_materializes_selected_manifests(tmp_path: Path) -> None:
    """Pilot-bundle build should emit deterministic train/dev manifests and refs."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root)
    output_root = tmp_path / "pilot-bundle"

    summary = build_task101_pilot_bundle(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=Path("/Users/olofs_mba/Documents/Repos/sir-convert-a-lot"),
    )

    assert summary.retained_row_count == 2
    assert summary.conflict_row_count == 1
    assert summary.manifest_row_counts == {
        "swedish_pilot_train": 1,
        "swedish_checkpoint_dev": 1,
    }
    assert summary.speaker_counts == {
        "swedish_pilot_train": 1,
        "swedish_checkpoint_dev": 1,
    }
    assert (output_root / "manifests" / "swedish_pilot_train.prepared.jsonl").is_file()
    assert (output_root / "manifests" / "swedish_checkpoint_dev.prepared.jsonl").is_file()
    assert (output_root / "refs" / "swedish_pilot_train" / "speaker-a" / "ref.wav").is_file()
    assert (output_root / "refs" / "swedish_checkpoint_dev" / "speaker-a" / "ref.wav").is_file()
    report_payload = json.loads(task101_pilot_bundle_report_path(output_root).read_text())
    assert report_payload["conflict_row_count"] == 1
    assert report_payload["train_manifest_family"] == "swedish_pilot_train"


def test_build_task101_pilot_bundle_rejects_duplicate_train_eval_family(tmp_path: Path) -> None:
    """Pilot-bundle build should reject identical train and eval family selection."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root)

    with pytest.raises(ValueError, match="must be distinct"):
        build_task101_pilot_bundle(
            source_root=source_root,
            output_root=tmp_path / "pilot-bundle",
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_pilot_train",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            encode_audio_codes_fn=_fake_encode_audio_codes,
            repo_root=Path("/Users/olofs_mba/Documents/Repos/sir-convert-a-lot"),
        )


def test_build_task101_pilot_bundle_uses_relocated_freeze_ledger_artifacts(
    tmp_path: Path,
) -> None:
    """Pilot-bundle build should prefer the copied frozen-root reports over stale absolute paths."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root)
    relocated_root = tmp_path / "relocated-frozen-root"
    shutil.copytree(source_root, relocated_root)
    shutil.rmtree(source_root)

    summary = build_task101_pilot_bundle(
        source_root=relocated_root,
        output_root=tmp_path / "pilot-bundle",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=Path("/Users/olofs_mba/Documents/Repos/sir-convert-a-lot"),
    )

    assert summary.owned_row_keys_path.startswith(relocated_root.as_posix())
    assert summary.conflict_row_keys_path.startswith(relocated_root.as_posix())


def test_build_task101_pilot_bundle_falls_back_when_freeze_summary_is_unreadable(
    tmp_path: Path,
) -> None:
    """Pilot-bundle build should use readable canonical ledgers when summary access is denied."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root)
    freeze_summary_path = source_root / "reports" / "canonical_processed_root_freeze.json"
    freeze_summary_path.chmod(0)

    summary = build_task101_pilot_bundle(
        source_root=source_root,
        output_root=tmp_path / "pilot-bundle",
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=Path("/Users/olofs_mba/Documents/Repos/sir-convert-a-lot"),
    )

    assert summary.conflict_row_count == 1
    assert summary.owned_row_keys_path.endswith("canonical_processed_root_owned_row_keys.jsonl")
    assert summary.conflict_row_keys_path.endswith(
        "canonical_processed_root_conflict_row_keys.jsonl"
    )


def test_build_task101_pilot_bundle_fails_closed_when_output_filesystem_is_full(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pilot-bundle build should fail before writes when the output filesystem is too full."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root)
    output_root = tmp_path / "pilot-bundle"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle._filesystem_free_bytes",
        lambda path: 1,
    )

    def _unexpected_encode_audio_codes(
        *,
        tokenizer_model: str,
        audio_paths: list[Path],
    ) -> list[list[list[int]]]:
        raise AssertionError(
            "audio-code generation should not start when the output filesystem is full"
        )

    with pytest.raises(OSError, match="requires approximately") as exc_info:
        build_task101_pilot_bundle(
            source_root=source_root,
            output_root=output_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            encode_audio_codes_fn=_unexpected_encode_audio_codes,
            repo_root=Path("/Users/olofs_mba/Documents/Repos/sir-convert-a-lot"),
        )

    assert exc_info.value.errno == errno.ENOSPC
    assert not output_root.exists()
