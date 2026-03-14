"""Tests for canonical training-bundle materialization."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import SpoolRow
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import (
    iter_jsonl_objects,
    iter_spool_rows,
    write_json,
    write_spool_row,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    build_training_bundle,
    bundle_batch_is_complete,
    bundle_batch_plan_path,
    bundle_manifest_path,
    bundle_prepared_batch_path,
    bundle_progress_events_path,
    bundle_progress_state_path,
    bundle_report_path,
    finalize_training_bundle_batch,
    load_training_bundle_batch_plan,
    prepare_training_bundle_inputs,
)
from tests.sir_convert_a_lot.ml.qwen.preprocessing.test_support import write_test_wav


def repo_root() -> Path:
    """Return the repository root for bundle tests."""
    return Path(__file__).resolve().parents[5]


def write_frozen_root_fixture(
    source_root: Path,
    *,
    train_row_count: int = 2,
    dev_row_count: int = 1,
) -> None:
    """Persist one frozen-root fixture with configurable train/dev rows."""
    owned_rows: list[dict[str, str]] = []
    for row_index in range(train_row_count):
        dataset_row_id = f"train-row-{row_index + 1}"
        write_spool_row_fixture(
            source_root=source_root,
            dataset_row_id=dataset_row_id,
            audio_name=f"{dataset_row_id}.wav",
            manifest_targets=("swedish_pilot_train",),
        )
        owned_rows.append(
            {
                "dataset": "rixvox",
                "source_split": "train",
                "dataset_row_id": dataset_row_id,
            }
        )
    for row_index in range(dev_row_count):
        dataset_row_id = f"dev-row-{row_index + 1}"
        write_spool_row_fixture(
            source_root=source_root,
            dataset_row_id=dataset_row_id,
            audio_name=f"{dataset_row_id}.wav",
            manifest_targets=("swedish_checkpoint_dev",),
        )
        owned_rows.append(
            {
                "dataset": "rixvox",
                "source_split": "dev",
                "dataset_row_id": dataset_row_id,
            }
        )
    reports_root = source_root / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    write_json(
        reports_root / "canonical_processed_root_freeze.json",
        {
            "output_root": source_root.as_posix(),
            "retained_row_count": len(owned_rows),
            "conflict_row_count": 0,
            "owned_row_keys_path": (
                reports_root / "canonical_processed_root_owned_row_keys.jsonl"
            ).as_posix(),
            "conflict_row_keys_path": (
                reports_root / "canonical_processed_root_conflict_row_keys.jsonl"
            ).as_posix(),
        },
    )
    (reports_root / "canonical_processed_root_owned_row_keys.jsonl").write_text(
        "\n".join(json.dumps(row) for row in owned_rows) + "\n",
        encoding="utf-8",
    )
    (reports_root / "canonical_processed_root_conflict_row_keys.jsonl").write_text(
        "",
        encoding="utf-8",
    )


def write_spool_row_fixture(
    *,
    source_root: Path,
    dataset_row_id: str,
    audio_name: str,
    manifest_targets: tuple[ManifestFamily, ...],
) -> None:
    """Persist one admitted spool row fixture and its audio."""
    split = "train" if "swedish_pilot_train" in manifest_targets else "dev"
    audio_path = source_root / "audio_24k" / "rixvox" / split / "speaker-a" / audio_name
    ref_audio_path = source_root / "refs" / manifest_targets[0] / "speaker-a" / "ref.wav"
    write_test_wav(audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
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
            reference_audio_24k_paths={
                manifest_targets[0]: ref_audio_path.relative_to(source_root).as_posix()
            },
            asr_model="KBLab/kb-whisper-large",
            asr_revision="strict",
            asr_transcript=f"text for {dataset_row_id}",
            asr_wer=0.0,
            quality_tier="high_trust",
            speaker_quality_gate="speaker_from_id",
            dedup_applied=False,
            admission_decision="admit",
            manifest_targets=manifest_targets,
        ),
    )


def fake_encode_audio_codes(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Return deterministic fake audio codes for bundle tests."""
    assert tokenizer_model == "Qwen/Qwen3-TTS-Tokenizer-12Hz"
    return [[[index + 1, index + 2]] for index, _ in enumerate(audio_paths)]


def test_prepare_training_bundle_inputs_emits_deterministic_batch_plan(tmp_path: Path) -> None:
    """Preparing bundle inputs should copy rows and emit a stable batch plan."""
    source_root = tmp_path / "frozen-root"
    output_root = tmp_path / "bundle-root"
    write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=2)

    plan = prepare_training_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=repo_root(),
    )

    copied_rows = list(iter_spool_rows(output_root))
    assert len(copied_rows) == 5
    assert plan.family_row_counts["swedish_pilot_train"] == 3
    assert plan.family_row_counts["swedish_checkpoint_dev"] == 2
    assert bundle_batch_plan_path(output_root).is_file()


def test_finalize_training_bundle_batch_materializes_prepared_batch(tmp_path: Path) -> None:
    """Finalizing one batch should write the prepared shard and mark it complete."""
    source_root = tmp_path / "frozen-root"
    output_root = tmp_path / "bundle-root"
    write_frozen_root_fixture(source_root, train_row_count=2, dev_row_count=1)
    prepare_training_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=1,
        repo_root=repo_root(),
    )
    plan = load_training_bundle_batch_plan(output_root)
    batch = next(batch for batch in plan.batches if batch.manifest_family == "swedish_pilot_train")

    finalize_training_bundle_batch(
        output_root=output_root,
        plan=plan,
        manifest_family=batch.manifest_family,
        batch_index=batch.batch_index,
        audio_codes_chunk_size=64,
        encode_audio_codes_fn=fake_encode_audio_codes,
    )

    assert bundle_prepared_batch_path(
        output_root, batch.manifest_family, batch.batch_index
    ).is_file()
    assert bundle_batch_is_complete(output_root, batch) is True


def test_build_training_bundle_materializes_manifests_and_progress(tmp_path: Path) -> None:
    """Building a bundle should produce manifests, report, and progress artifacts."""
    source_root = tmp_path / "frozen-root"
    output_root = tmp_path / "bundle-root"
    write_frozen_root_fixture(source_root, train_row_count=2, dev_row_count=1)

    summary = build_training_bundle(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=1,
        audio_codes_chunk_size=64,
        encode_audio_codes_fn=fake_encode_audio_codes,
        repo_root=repo_root(),
    )

    train_manifest = list(
        iter_jsonl_objects(bundle_manifest_path(output_root, "swedish_pilot_train"))
    )
    eval_manifest = list(
        iter_jsonl_objects(bundle_manifest_path(output_root, "swedish_checkpoint_dev"))
    )
    progress_state = json.loads(bundle_progress_state_path(output_root).read_text(encoding="utf-8"))
    progress_events = (
        bundle_progress_events_path(output_root).read_text(encoding="utf-8").strip().splitlines()
    )

    assert len(train_manifest) == 2
    assert len(eval_manifest) == 1
    assert summary.total_batch_count == 3
    assert bundle_report_path(output_root).is_file()
    assert progress_state["status"] == "completed"
    assert len(progress_events) == 3
