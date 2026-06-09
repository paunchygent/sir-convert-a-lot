"""Tests for the Chatterbox eSpeak experiment Chatterbox eSpeak experiment surfaces.

Purpose:
    Verify the benchmark-only preprocessing helper, the Hemma experiment
    runner, and the local orchestrator before running the live experiment.

Relationships:
    - Exercises the Chatterbox eSpeak experiment helper container entry module.
    - Exercises the Chatterbox eSpeak experiment local and Hemma runners.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.sir_convert_a_lot.devops import (
    run_chatterbox_espeak_experiment,
    run_chatterbox_espeak_hemma_experiment,
)
from scripts.sir_convert_a_lot.textprep import espeak_phonemizer_cli


def test_espeak_helper_writes_output_with_mocked_phonemizer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    input_file = tmp_path / "input.txt"
    output_file = tmp_path / "output.txt"
    metadata_file = tmp_path / "metadata.json"
    input_file.write_text("Hej världen.", encoding="utf-8")

    fake_module = SimpleNamespace(phonemize=lambda **_: "h ɛ j v æ r l d ɛ n .")
    monkeypatch.setitem(sys.modules, "phonemizer", fake_module)

    result = espeak_phonemizer_cli.main(
        [
            "--input-file",
            input_file.as_posix(),
            "--output-file",
            output_file.as_posix(),
            "--metadata-file",
            metadata_file.as_posix(),
            "--language",
            "sv",
            "--preserve-punctuation",
        ]
    )

    assert result == 0
    assert output_file.read_text(encoding="utf-8").strip() == "h ɛ j v æ r l d ɛ n ."
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    assert metadata["language"] == "sv"
    assert metadata["preserve_punctuation"] is True


def test_hemma_parse_args_defaults() -> None:
    settings = run_chatterbox_espeak_hemma_experiment._parse_args([])

    assert settings.helper_image == "sir-convert-a-lot/textprep-espeak-chatterbox-espeak:local"
    assert settings.espeak_language == "sv"
    assert settings.build_chatterbox_image is False


def test_hemma_parse_args_supports_explicit_benchmark_rebuild() -> None:
    settings = run_chatterbox_espeak_hemma_experiment._parse_args(["--build-benchmark-image"])

    assert settings.build_chatterbox_image is True


def test_local_orchestrator_runs_remote_then_rsync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    class _Completed:
        returncode = 0

    def _fake_run(command: list[str], cwd: Path, check: bool) -> _Completed:
        assert cwd == run_chatterbox_espeak_experiment.REPO_ROOT
        assert check is False
        commands.append(command)
        return _Completed()

    monkeypatch.setattr(run_chatterbox_espeak_experiment.subprocess, "run", _fake_run)

    result = run_chatterbox_espeak_experiment.main([])

    assert result == 0
    assert commands[0][:7] == [
        "pdm",
        "run",
        "run-hemma",
        "--",
        "pdm",
        "run",
        "benchmark:chatterbox-espeak-hemma",
    ]
    assert commands[1][0] == "rsync"
    assert "chatterbox-espeak-hemma" in commands[1][2]
    assert "--probe-text" in commands[0]
    assert "--espeak-language" in commands[0]


def test_hemma_run_chatterbox_benchmark_lane_passes_probe_text_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    def _fake_main(argv: list[str]) -> int:
        calls.append(argv)
        return 0

    monkeypatch.setattr(
        run_chatterbox_espeak_hemma_experiment.run_chatterbox_hemma_benchmark,
        "main",
        _fake_main,
    )
    probe_text_file = tmp_path / "probe.txt"
    probe_text_file.write_text("h ɛ j", encoding="utf-8")

    result = run_chatterbox_espeak_hemma_experiment._run_chatterbox_benchmark_lane(
        lane_output_root=tmp_path / "lane",
        reference_audio_path=tmp_path / "ref.wav",
        probe_text_file=probe_text_file,
        exaggeration=0.5,
        cfg_weight=0.5,
        build_chatterbox_image=False,
    )

    assert result == 0
    assert "--probe-text-file" in calls[0]
    assert probe_text_file.as_posix() in calls[0]
    assert "--skip-build" in calls[0]


def test_hemma_load_lane_summary_handles_missing_report(tmp_path: Path) -> None:
    summary = run_chatterbox_espeak_hemma_experiment._load_lane_summary(
        "baseline",
        tmp_path / "missing-lane",
    )

    assert summary.lane_id == "baseline"
    assert summary.synthesized_ok is None
    assert summary.output_path is None
