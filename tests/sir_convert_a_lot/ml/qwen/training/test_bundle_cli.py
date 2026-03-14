"""Tests for the restored Task 101 training-bundle CLI surface.

Purpose:
    Verify that the restored public bundle-build command parses and dispatches
    through the migrated domain modules.

Relationships:
    - Exercises `cli/ml/qwen_bundle.py`.
    - Protects the restored `task-101-pilot-bundle` public operator contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.cli.ml.qwen_bundle import (
    DEFAULT_EVAL_MANIFEST_FAMILY,
    DEFAULT_TRAIN_MANIFEST_FAMILY,
    build_parser,
    main,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_contracts import BundleBatch, BundleBatchPlan
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime import (
    TrainingBundleRuntimeFingerprint,
)


def _required_object(payload: object) -> dict[str, object]:
    """Return one mapping payload from captured monkeypatch state."""
    assert isinstance(payload, dict)
    return payload


def test_parser_build_defaults() -> None:
    """The restored bundle CLI should expose deterministic build defaults."""
    args = build_parser().parse_args(["build"])

    assert args.train_manifest_family == DEFAULT_TRAIN_MANIFEST_FAMILY
    assert args.eval_manifest_family == DEFAULT_EVAL_MANIFEST_FAMILY


def test_main_build_dispatches_to_containerized_bundle_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The restored build command should orchestrate governed batch containers."""

    @dataclass
    class _FakeBundleSummary:
        source_root: str
        output_root: str

    source_root = tmp_path / "source-root"
    output_root = tmp_path / "output-root"
    captured: dict[str, object] = {}
    fingerprint = TrainingBundleRuntimeFingerprint(
        runtime_kind="runtime-kind",
        image="image",
        image_id="image-id",
        dockerfile_path="Dockerfile",
        container_entry_module="entry-module",
        container_hf_home="/cache/hf",
        container_hf_hub_cache="/cache/hf/hub",
        container_torch_home="/cache/hf/torch",
        audio_codes_runtime_kind="audio-runtime",
        audio_codes_device="cuda:0",
        audio_codes_dtype="bfloat16",
        audio_codes_attn_implementation="flash_attention_2",
        audio_codes_require_gpu=True,
        audio_codes_require_flash_attn=True,
    )
    plan = BundleBatchPlan(
        source_root=source_root.as_posix(),
        output_root=output_root.as_posix(),
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        retained_row_count=2,
        conflict_row_count=0,
        owned_row_keys_path="owned.jsonl",
        conflict_row_keys_path="conflicts.jsonl",
        repo_head="deadbeef",
        generated_at="2026-03-14T00:00:00Z",
        family_row_counts={
            "swedish_pilot_train": 1,
            "swedish_checkpoint_dev": 1,
        },
        batches=[
            BundleBatch(
                manifest_family="swedish_pilot_train",
                batch_index=0,
                row_count=1,
                first_row_key=("rixvox", "train", "row-1"),
                last_row_key=("rixvox", "train", "row-1"),
            )
        ],
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.prepare_training_bundle_inputs",
        lambda **kwargs: plan,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.prepare_training_bundle_batch_runtime",
        lambda: ("hf-mount", fingerprint),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.write_training_bundle_runtime_fingerprint",
        lambda output_root_arg, fingerprint_arg: captured.update(
            {
                "runtime_output_root": output_root_arg,
                "runtime_fingerprint": fingerprint_arg,
            }
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.bundle_batch_is_complete",
        lambda *args, **kwargs: False,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.write_progress_state",
        lambda *args, **kwargs: captured.update({"progress_state": kwargs}),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.run_containerized_training_bundle_batch",
        lambda **kwargs: captured.update({"container_batch": kwargs}),
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.assemble_training_bundle",
        lambda output_root_arg: _FakeBundleSummary(
            source_root=source_root.as_posix(),
            output_root=output_root_arg.as_posix(),
        ),
    )

    exit_code = main(
        [
            "build",
            "--source-root",
            source_root.as_posix(),
            "--output-root",
            output_root.as_posix(),
        ]
    )

    assert exit_code == 0
    assert captured["runtime_output_root"] == output_root
    assert captured["runtime_fingerprint"] == fingerprint
    progress_state = _required_object(captured["progress_state"])
    container_batch = _required_object(captured["container_batch"])
    assert progress_state["completed_batch_count"] == 0
    assert container_batch["output_root"] == output_root
    assert container_batch["repo_root"] == Path.cwd()
    assert container_batch["hf_mount"] == "hf-mount"
    assert container_batch["fingerprint"] == fingerprint
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["source_root"] == source_root.as_posix()
    assert rendered["output_root"] == output_root.as_posix()


def test_main_finalize_batch_uses_container_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The direct finalize-batch stage should launch the governed runtime helper."""
    output_root = tmp_path / "bundle-root"
    fingerprint = TrainingBundleRuntimeFingerprint(
        runtime_kind="runtime-kind",
        image="image",
        image_id="image-id",
        dockerfile_path="Dockerfile",
        container_entry_module="entry-module",
        container_hf_home="/cache/hf",
        container_hf_hub_cache="/cache/hf/hub",
        container_torch_home="/cache/hf/torch",
        audio_codes_runtime_kind="audio-runtime",
        audio_codes_device="cuda:0",
        audio_codes_dtype="bfloat16",
        audio_codes_attn_implementation="flash_attention_2",
        audio_codes_require_gpu=True,
        audio_codes_require_flash_attn=True,
    )
    plan = BundleBatchPlan(
        source_root="source-root",
        output_root=output_root.as_posix(),
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        tokenizer_model="Qwen/Qwen3-TTS-Tokenizer-12Hz",
        finalization_batch_row_count=2,
        retained_row_count=2,
        conflict_row_count=0,
        owned_row_keys_path="owned.jsonl",
        conflict_row_keys_path="conflicts.jsonl",
        repo_head="deadbeef",
        generated_at="2026-03-14T00:00:00Z",
        family_row_counts={
            "swedish_pilot_train": 1,
            "swedish_checkpoint_dev": 1,
        },
        batches=[
            BundleBatch(
                manifest_family="swedish_pilot_train",
                batch_index=0,
                row_count=1,
                first_row_key=("rixvox", "train", "row-1"),
                last_row_key=("rixvox", "train", "row-1"),
            )
        ],
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.load_training_bundle_batch_plan",
        lambda output_root_arg: plan,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.prepare_training_bundle_batch_runtime",
        lambda: ("hf-mount", fingerprint),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.write_training_bundle_runtime_fingerprint",
        lambda output_root_arg, fingerprint_arg: captured.update(
            {
                "runtime_output_root": output_root_arg,
                "runtime_fingerprint": fingerprint_arg,
            }
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.run_containerized_training_bundle_batch",
        lambda **kwargs: captured.update({"container_batch": kwargs}),
    )

    exit_code = main(
        [
            "finalize-batch",
            "--output-root",
            output_root.as_posix(),
            "--manifest-family",
            "swedish_pilot_train",
            "--batch-index",
            "0",
        ]
    )

    assert exit_code == 0
    assert captured["runtime_output_root"] == output_root
    assert captured["runtime_fingerprint"] == fingerprint
    container_batch = _required_object(captured["container_batch"])
    assert container_batch["manifest_family"] == "swedish_pilot_train"
    assert container_batch["batch_index"] == 0
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["manifest_family"] == "swedish_pilot_train"
    assert rendered["batch_index"] == 0
