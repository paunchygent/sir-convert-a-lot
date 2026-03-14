"""Tests for the canonical training-bundle finalization benchmark helper."""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import iter_spool_rows
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    build_training_bundle,
)
from scripts.sir_convert_a_lot.ml.qwen.training.finalization_benchmark import (
    prepare_benchmark_root,
    run_finalization_benchmark,
)
from tests.sir_convert_a_lot.ml.qwen.training.test_bundles import (
    fake_encode_audio_codes,
    repo_root,
    write_frozen_root_fixture,
)


def test_prepare_benchmark_root_copies_only_selected_source_batch_rows(tmp_path: Path) -> None:
    """The benchmark helper should stage only the requested source-batch rows."""
    source_root = tmp_path / "frozen-root"
    source_bundle_root = tmp_path / "source-bundle"
    benchmark_root = tmp_path / "benchmark-root"
    write_frozen_root_fixture(source_root, train_row_count=3, dev_row_count=2)
    build_training_bundle(
        source_root=source_root,
        output_root=source_bundle_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        audio_codes_chunk_size=64,
        encode_audio_codes_fn=fake_encode_audio_codes,
        repo_root=repo_root(),
    )

    plan = prepare_benchmark_root(
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


def test_run_finalization_benchmark_writes_report(tmp_path: Path) -> None:
    """The benchmark runner should emit a report for the selected benchmark root."""
    source_root = tmp_path / "frozen-root"
    source_bundle_root = tmp_path / "source-bundle"
    benchmark_root = tmp_path / "benchmark-root"
    write_frozen_root_fixture(source_root, train_row_count=2, dev_row_count=1)
    build_training_bundle(
        source_root=source_root,
        output_root=source_bundle_root,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=1,
        audio_codes_chunk_size=64,
        encode_audio_codes_fn=fake_encode_audio_codes,
        repo_root=repo_root(),
    )

    report = run_finalization_benchmark(
        source_bundle_root=source_bundle_root,
        benchmark_root=benchmark_root,
        variant_label="optimized",
        manifest_family="swedish_pilot_train",
        source_start_batch_index=0,
        source_batch_count=1,
        benchmark_batch_row_count=1,
        audio_codes_chunk_size=64,
        container_batch_span=1,
    )

    assert report.selected_row_count == 1
    assert report.planned_batch_count == 1
    assert Path(report.training_bundle_report_path).is_file()
