"""Tests for the Task 152 Task 101 finalization benchmark helper."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task152_hemma_task101_finalization_benchmark import (
    _prepare_benchmark_root,
    run_task152_benchmark,
)
from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import MountResolution
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle import (
    copy_task101_pilot_bundle_inputs,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    load_task101_pilot_bundle_batch_plan,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_execution import (
    finalize_task101_pilot_bundle_batch,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    Task101PilotBundleRuntimeFingerprint,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_spool_rows,
)
from tests.sir_convert_a_lot.test_task101_qwen_pilot_bundle import (
    _fake_encode_audio_codes,
    _repo_root,
    _runtime_fingerprint,
    _write_frozen_root_fixture,
)


def test_prepare_benchmark_root_copies_only_selected_source_batch_rows(tmp_path: Path) -> None:
    """The Task 152 helper should stage only the requested source-batch rows."""
    source_root = tmp_path / "frozen-root"
    source_bundle_root = tmp_path / "source-bundle"
    benchmark_root = tmp_path / "benchmark-root"
    _write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=2)
    copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=source_bundle_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=_repo_root(),
    )

    plan = _prepare_benchmark_root(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        manifest_family="swedish_pilot_train",
        source_start_batch_index=1,
        source_batch_count=1,
        benchmark_batch_row_count=1,
    )

    selected_rows = list(iter_spool_rows(benchmark_root))
    train_rows = [row for row in selected_rows if "swedish_pilot_train" in row.manifest_targets]
    eval_rows = [row for row in selected_rows if "swedish_checkpoint_dev" in row.manifest_targets]
    assert len(train_rows) == 1
    assert train_rows[0].dataset_row_id == "train-row-3"
    assert len(eval_rows) == 2
    assert (benchmark_root / train_rows[0].audio_24k_path).is_file()
    assert plan.family_row_counts["swedish_pilot_train"] == 1
    assert plan.family_row_counts["swedish_checkpoint_dev"] == 2


def test_run_task152_benchmark_groups_contiguous_benchmark_batches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 152 benchmark runner should reuse grouped container launches."""
    source_root = tmp_path / "frozen-root"
    source_bundle_root = tmp_path / "source-bundle"
    benchmark_root = tmp_path / "benchmark-root"
    runtime_fingerprint = _runtime_fingerprint()
    observed_calls: list[tuple[ManifestFamily, int, int]] = []
    _write_frozen_root_fixture(source_root, train_row_count=4, dev_row_count=1)
    copy_task101_pilot_bundle_inputs(
        source_root=source_root,
        output_root=source_bundle_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        repo_root=_repo_root(),
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task152_hemma_task101_finalization_benchmark.prepare_task101_pilot_bundle_batch_runtime",
        lambda settings: (
            MountResolution(
                canonical_root=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
                effective_root=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
                used_home_mount=False,
            ),
            runtime_fingerprint,
        ),
    )

    def _fake_run_containerized_batch(
        *,
        repo_root: Path,
        output_root: Path,
        manifest_family: ManifestFamily,
        batch_index: int,
        batch_count: int,
        audio_codes_chunk_size: int,
        settings: object,
        hf_mount: MountResolution,
        fingerprint: Task101PilotBundleRuntimeFingerprint,
        triton_mount: MountResolution | None = None,
        emit: object = print,
    ) -> Task101PilotBundleRuntimeFingerprint:
        del repo_root, settings, hf_mount, triton_mount, emit
        observed_calls.append((manifest_family, batch_index, batch_count))
        plan = load_task101_pilot_bundle_batch_plan(output_root)
        for current_batch_index in range(batch_index, batch_index + batch_count):
            finalize_task101_pilot_bundle_batch(
                output_root=output_root,
                plan=plan,
                manifest_family=manifest_family,
                batch_index=current_batch_index,
                audio_codes_chunk_size=audio_codes_chunk_size,
                encode_audio_codes_fn=_fake_encode_audio_codes,
                runtime_fingerprint=fingerprint,
            )
        return fingerprint

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task152_hemma_task101_finalization_benchmark.run_containerized_task101_pilot_bundle_batch",
        _fake_run_containerized_batch,
    )

    report = run_task152_benchmark(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        variant_label="optimized",
        manifest_family="swedish_pilot_train",
        source_start_batch_index=0,
        source_batch_count=2,
        benchmark_batch_row_count=1,
        audio_codes_chunk_size=64,
        container_batch_span=2,
        build_image=False,
    )

    assert report.selected_row_count == 4
    assert report.planned_batch_count == 4
    assert observed_calls == [
        ("swedish_pilot_train", 0, 2),
        ("swedish_pilot_train", 2, 2),
        ("swedish_checkpoint_dev", 0, 1),
    ]
    assert Path(report.task101_bundle_report_path).is_file()
