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
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    encode_audio_codes_with_governed_gpu_runtime,
)


def test_parser_build_defaults() -> None:
    """The restored bundle CLI should expose deterministic build defaults."""
    args = build_parser().parse_args(["build"])

    assert args.train_manifest_family == DEFAULT_TRAIN_MANIFEST_FAMILY
    assert args.eval_manifest_family == DEFAULT_EVAL_MANIFEST_FAMILY


def test_main_build_dispatches_to_domain_bundle_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The restored build command should call the migrated domain bundle builder."""

    @dataclass
    class _FakeBundleSummary:
        source_root: str
        output_root: str

    source_root = tmp_path / "source-root"
    output_root = tmp_path / "output-root"
    captured: dict[str, object] = {}

    def _fake_build_training_bundle(**kwargs: object) -> object:
        captured.update(kwargs)
        return _FakeBundleSummary(
            source_root=str(kwargs["source_root"]),
            output_root=str(kwargs["output_root"]),
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_bundle.build_training_bundle",
        _fake_build_training_bundle,
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
    assert captured["source_root"] == source_root
    assert captured["output_root"] == output_root
    assert captured["encode_audio_codes_fn"] is encode_audio_codes_with_governed_gpu_runtime
    rendered = json.loads(capsys.readouterr().out)
    assert rendered["source_root"] == source_root.as_posix()
    assert rendered["output_root"] == output_root.as_posix()
