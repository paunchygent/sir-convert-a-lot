"""Tests for deterministic batched Task 101 Qwen pilot-bundle materialization."""

from __future__ import annotations

import errno
import json
import shutil
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle import (
    build_task101_pilot_bundle,
    copy_task101_pilot_bundle_inputs,
    task101_pilot_bundle_report_path,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    Task101PilotBundleBatchPlan,
    load_task101_pilot_bundle_batch_plan,
    task101_pilot_bundle_batch_plan_path,
    task101_pilot_bundle_prepared_batch_path,
    task101_pilot_bundle_progress_events_path,
    task101_pilot_bundle_progress_state_path,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_execution import (
    finalize_task101_pilot_bundle_batch,
    task101_pilot_bundle_batch_is_complete,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    Task101PilotBundleRuntimeFingerprint,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import ManifestFamily
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    AudioCodesEncoderProtocol,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    QualityTier,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_jsonl_objects,
    write_json,
    write_spool_row,
)
from tests.sir_convert_a_lot.task103_test_support import write_test_wav


def _repo_root() -> Path:
    """Return the repository root for Task 101 bundle tests."""
    return Path(__file__).resolve().parents[2]


def _write_frozen_root_fixture(
    source_root: Path,
    *,
    train_row_count: int = 1,
    dev_row_count: int = 1,
    include_ignored_row: bool = True,
) -> None:
    """Persist one frozen-root fixture with configurable pilot/dev row counts."""
    owned_rows: list[dict[str, str]] = []
    for row_index in range(train_row_count):
        dataset_row_id = f"train-row-{row_index + 1}"
        _write_spool_row_fixture(
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
        _write_spool_row_fixture(
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
    if include_ignored_row:
        _write_spool_row_fixture(
            source_root=source_root,
            dataset_row_id="ignored-row",
            audio_name="ignored-row.wav",
            manifest_targets=("swedish_final_test",),
        )
        owned_rows.append(
            {
                "dataset": "rixvox",
                "source_split": "test",
                "dataset_row_id": "ignored-row",
            }
        )
    write_json(
        source_root / "reports" / "canonical_processed_root_freeze.json",
        {
            "output_root": source_root.as_posix(),
            "retained_row_count": len(owned_rows),
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
        "\n".join(json.dumps(row) for row in owned_rows) + "\n",
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


def _failing_encode_audio_codes(
    *,
    tokenizer_model: str,
    audio_paths: list[Path],
) -> list[list[list[int]]]:
    """Raise one deterministic failure to emulate an interrupted batch."""
    del tokenizer_model, audio_paths
    raise RuntimeError("simulated audio-code failure")


def _run_batch_in_process(
    output_root: Path,
    plan: Task101PilotBundleBatchPlan,
    manifest_family: ManifestFamily,
    batch_index: int,
    audio_codes_chunk_size: int,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    repo_root: Path,
) -> None:
    """Replace the fresh-process batch runner with a direct call in tests."""
    del repo_root
    finalize_task101_pilot_bundle_batch(
        output_root=output_root,
        plan=plan,
        manifest_family=manifest_family,
        batch_index=batch_index,
        audio_codes_chunk_size=audio_codes_chunk_size,
        encode_audio_codes_fn=encode_audio_codes_fn,
    )


def _runtime_fingerprint(*, image_id: str = "sha256:test") -> Task101PilotBundleRuntimeFingerprint:
    """Return one deterministic governed runtime fingerprint for Task 101 tests."""
    return Task101PilotBundleRuntimeFingerprint(
        runtime_kind="task101_qwen_pilot_bundle_containerized_batch_v2",
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        image_id=image_id,
        dockerfile_path="containers/qwen-finetune-hemma/Dockerfile",
        container_entry_module=(
            "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_in_container"
        ),
        container_hf_home="/cache/huggingface",
        container_hf_hub_cache="/cache/huggingface/hub",
        container_torch_home="/cache/huggingface/torch",
        audio_codes_runtime_kind="task101_task103_qwen_audio_codes_gpu_v1",
        audio_codes_device="cuda:0",
        audio_codes_dtype="bfloat16",
        audio_codes_attn_implementation="flash_attention_2",
        audio_codes_require_gpu=True,
        audio_codes_require_flash_attn=True,
    )


def _read_event_payloads(output_root: Path) -> list[dict[str, object]]:
    """Load the Task 101 batch events ledger for assertions."""
    return list(iter_jsonl_objects(task101_pilot_bundle_progress_events_path(output_root)))


def test_copy_task101_pilot_bundle_inputs_emits_deterministic_batch_plan(
    tmp_path: Path,
) -> None:
    """Copy stage should emit a stable family-specific batch plan before tokenizer work."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=5, dev_row_count=3)
    output_root = tmp_path / "pilot-bundle"

    plan = copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=_repo_root(),
    )

    assert task101_pilot_bundle_batch_plan_path(output_root).is_file()
    assert plan.retained_row_count == 8
    assert plan.family_row_counts == {
        "swedish_pilot_train": 5,
        "swedish_checkpoint_dev": 3,
    }
    assert [
        (batch.manifest_family, batch.batch_index, batch.row_count) for batch in plan.batches
    ] == [
        ("swedish_pilot_train", 0, 2),
        ("swedish_pilot_train", 1, 2),
        ("swedish_pilot_train", 2, 1),
        ("swedish_checkpoint_dev", 0, 2),
        ("swedish_checkpoint_dev", 1, 1),
    ]
    assert plan.batches[0].first_row_key == "rixvox/train/train-row-1"
    assert plan.batches[0].last_row_key == "rixvox/train/train-row-2"
    assert plan.batches[-1].first_row_key == "rixvox/dev/dev-row-3"
    assert (output_root / "refs" / "swedish_pilot_train" / "speaker-a" / "ref.wav").is_file()
    assert (output_root / "refs" / "swedish_checkpoint_dev" / "speaker-a" / "ref.wav").is_file()


def test_build_task101_pilot_bundle_materializes_selected_manifests_and_logs_progress(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Batched build should emit final manifests plus plan/events/status artifacts."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=2)
    output_root = tmp_path / "pilot-bundle"

    summary = build_task101_pilot_bundle(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=_repo_root(),
        run_batch_fn=_run_batch_in_process,
    )

    assert summary.retained_row_count == 5
    assert summary.conflict_row_count == 1
    assert summary.finalization_batch_row_count == 2
    assert summary.total_batch_count == 3
    assert summary.manifest_row_counts == {
        "swedish_pilot_train": 3,
        "swedish_checkpoint_dev": 2,
    }
    assert summary.speaker_counts == {
        "swedish_pilot_train": 1,
        "swedish_checkpoint_dev": 1,
    }
    assert (output_root / "manifests" / "swedish_pilot_train.prepared.jsonl").is_file()
    assert (output_root / "manifests" / "swedish_checkpoint_dev.prepared.jsonl").is_file()
    assert task101_pilot_bundle_report_path(output_root).is_file()
    assert task101_pilot_bundle_batch_plan_path(output_root).is_file()
    assert task101_pilot_bundle_progress_events_path(output_root).is_file()
    assert task101_pilot_bundle_progress_state_path(output_root).is_file()
    event_names = [payload["event"] for payload in _read_event_payloads(output_root)]
    assert event_names == [
        "copy_completed",
        "batch_started",
        "batch_completed",
        "batch_started",
        "batch_completed",
        "batch_started",
        "batch_completed",
        "assemble_started",
        "assemble_completed",
        "report_completed",
    ]
    status_payload = json.loads(task101_pilot_bundle_progress_state_path(output_root).read_text())
    assert status_payload["completed_batch_count"] == 3
    assert status_payload["last_completed_family"] == "swedish_checkpoint_dev"
    report_payload = json.loads(task101_pilot_bundle_report_path(output_root).read_text())
    assert report_payload["batch_plan_path"].endswith("task101_pilot_bundle_plan.json")
    assert report_payload["events_path"].endswith("task101_pilot_bundle_events.jsonl")
    assert report_payload["status_path"].endswith("task101_pilot_bundle_status.json")
    captured_stdout = capsys.readouterr().out
    assert '"event": "copy_completed"' in captured_stdout
    assert '"event": "batch_completed"' in captured_stdout
    assert '"event": "report_completed"' in captured_stdout


def test_build_task101_pilot_bundle_resumes_from_validated_batch_shards(
    tmp_path: Path,
) -> None:
    """Build should skip validated completed batches and finish the remaining ones."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=2)
    output_root = tmp_path / "pilot-bundle"

    copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=_repo_root(),
    )
    plan = load_task101_pilot_bundle_batch_plan(output_root)
    finalize_task101_pilot_bundle_batch(
        output_root=output_root,
        plan=plan,
        manifest_family="swedish_pilot_train",
        batch_index=0,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
    )

    summary = build_task101_pilot_bundle(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=_repo_root(),
        run_batch_fn=_run_batch_in_process,
    )

    assert summary.total_batch_count == 3
    events = _read_event_payloads(output_root)
    assert any(
        payload["event"] == "batch_skipped_existing"
        and payload["manifest_family"] == "swedish_pilot_train"
        and payload["batch_index"] == 0
        for payload in events
    )
    assert any(
        payload["event"] == "batch_completed"
        and payload["manifest_family"] == "swedish_checkpoint_dev"
        and payload["batch_index"] == 0
        for payload in events
    )
    status_payload = json.loads(task101_pilot_bundle_progress_state_path(output_root).read_text())
    assert status_payload["completed_batch_count"] == 3
    assert status_payload["skipped_batch_event_count"] >= 1


def test_task101_batch_validation_rejects_middle_row_drift(tmp_path: Path) -> None:
    """Validated shard reuse should fail when a middle prepared row drifts."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=1)
    output_root = tmp_path / "pilot-bundle"

    copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=3,
        repo_root=_repo_root(),
    )
    plan = load_task101_pilot_bundle_batch_plan(output_root)
    batch = plan.batches[0]
    finalize_task101_pilot_bundle_batch(
        output_root=output_root,
        plan=plan,
        manifest_family=batch.manifest_family,
        batch_index=batch.batch_index,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
    )

    prepared_path = task101_pilot_bundle_prepared_batch_path(
        output_root,
        batch.manifest_family,
        batch.batch_index,
    )
    prepared_rows = list(iter_jsonl_objects(prepared_path))
    prepared_rows[1]["text"] = "corrupted-middle-row"
    prepared_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in prepared_rows) + "\n",
        encoding="utf-8",
    )

    assert not task101_pilot_bundle_batch_is_complete(output_root, batch)


def test_finalize_task101_batch_records_interrupted_progress_and_supports_resume(
    tmp_path: Path,
) -> None:
    """A failed batch should preserve last-started progress evidence and allow a safe rerun."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=2)
    output_root = tmp_path / "pilot-bundle"

    copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=_repo_root(),
    )
    plan = load_task101_pilot_bundle_batch_plan(output_root)

    with pytest.raises(RuntimeError, match="simulated audio-code failure"):
        finalize_task101_pilot_bundle_batch(
            output_root=output_root,
            plan=plan,
            manifest_family="swedish_pilot_train",
            batch_index=0,
            audio_codes_chunk_size=1,
            encode_audio_codes_fn=_failing_encode_audio_codes,
        )

    event_names = [payload["event"] for payload in _read_event_payloads(output_root)]
    assert event_names == ["copy_completed", "batch_started"]
    status_payload = json.loads(task101_pilot_bundle_progress_state_path(output_root).read_text())
    assert status_payload["started_batch_count"] == 1
    assert status_payload["completed_batch_count"] == 0
    assert status_payload["last_event"] == "batch_started"
    assert status_payload["last_started_family"] == "swedish_pilot_train"
    assert status_payload["last_started_batch_index"] == 0
    assert status_payload["last_completed_family"] is None
    assert not task101_pilot_bundle_prepared_batch_path(
        output_root,
        "swedish_pilot_train",
        0,
    ).exists()

    summary = build_task101_pilot_bundle(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=_repo_root(),
        run_batch_fn=_run_batch_in_process,
    )

    assert summary.total_batch_count == 3
    assert any(
        payload["event"] == "batch_completed"
        and payload["manifest_family"] == "swedish_pilot_train"
        and payload["batch_index"] == 0
        for payload in _read_event_payloads(output_root)
    )
    resumed_status_payload = json.loads(
        task101_pilot_bundle_progress_state_path(output_root).read_text()
    )
    assert resumed_status_payload["completed_batch_count"] == 3
    assert resumed_status_payload["last_completed_family"] == "swedish_checkpoint_dev"


def test_task101_batch_validation_requires_matching_runtime_fingerprint(tmp_path: Path) -> None:
    """Validated shard reuse should require the expected governed runtime fingerprint."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=2, dev_row_count=1)
    output_root = tmp_path / "pilot-bundle"

    copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=_repo_root(),
    )
    plan = load_task101_pilot_bundle_batch_plan(output_root)
    batch = plan.batches[0]
    finalize_task101_pilot_bundle_batch(
        output_root=output_root,
        plan=plan,
        manifest_family=batch.manifest_family,
        batch_index=batch.batch_index,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        runtime_fingerprint=_runtime_fingerprint(),
    )

    assert task101_pilot_bundle_batch_is_complete(
        output_root,
        batch,
        expected_runtime_fingerprint=_runtime_fingerprint(),
    )
    assert not task101_pilot_bundle_batch_is_complete(
        output_root,
        batch,
        expected_runtime_fingerprint=_runtime_fingerprint(image_id="sha256:other"),
    )


def test_build_task101_pilot_bundle_rejects_completed_bundle_without_runtime_fingerprint(
    tmp_path: Path,
) -> None:
    """Completed legacy bundles should not pass as governed container output."""
    source_root = tmp_path / "frozen-root"
    _write_frozen_root_fixture(source_root, train_row_count=2, dev_row_count=1)
    output_root = tmp_path / "pilot-bundle"

    build_task101_pilot_bundle(
        source_root=source_root,
        output_root=output_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=_repo_root(),
        run_batch_fn=_run_batch_in_process,
    )

    with pytest.raises(ValueError, match="governed container runtime fingerprint"):
        build_task101_pilot_bundle(
            source_root=source_root,
            output_root=output_root,
            train_manifest_family="swedish_pilot_train",
            eval_manifest_family="swedish_checkpoint_dev",
            tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
            finalization_batch_row_count=2,
            audio_codes_chunk_size=1,
            encode_audio_codes_fn=_fake_encode_audio_codes,
            repo_root=_repo_root(),
            run_batch_fn=_run_batch_in_process,
            expected_runtime_fingerprint=_runtime_fingerprint(),
        )


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
            finalization_batch_row_count=2,
            audio_codes_chunk_size=1,
            encode_audio_codes_fn=_fake_encode_audio_codes,
            repo_root=_repo_root(),
            run_batch_fn=_run_batch_in_process,
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
        finalization_batch_row_count=2,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=_repo_root(),
        run_batch_fn=_run_batch_in_process,
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
        finalization_batch_row_count=2,
        audio_codes_chunk_size=1,
        encode_audio_codes_fn=_fake_encode_audio_codes,
        repo_root=_repo_root(),
        run_batch_fn=_run_batch_in_process,
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
        "scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_source.filesystem_free_bytes",
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
            finalization_batch_row_count=2,
            audio_codes_chunk_size=1,
            encode_audio_codes_fn=_unexpected_encode_audio_codes,
            repo_root=_repo_root(),
            run_batch_fn=_run_batch_in_process,
        )

    assert exc_info.value.errno == errno.ENOSPC
    assert not output_root.exists()
