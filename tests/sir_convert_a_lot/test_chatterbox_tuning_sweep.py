"""Tests for the Chatterbox tuning sweep Chatterbox tuning sweep runner.

Purpose:
    Verify the documented lane order, remote command construction, and local
    summary writing before the live Hemma sweep is executed.

Relationships:
    - Exercises `run_chatterbox_tuning_sweep`.
    - Complements the lower-level Chatterbox benchmark tests.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_chatterbox_tuning_sweep


def test_default_lanes_use_conservative_first_order() -> None:
    lanes = run_chatterbox_tuning_sweep._default_lanes()

    assert [(lane.exaggeration, lane.cfg_weight) for lane in lanes] == [
        (0.5, 0.5),
        (0.5, 0.3),
        (0.7, 0.5),
        (0.7, 0.3),
        (0.5, 0.0),
        (0.7, 0.0),
    ]
    assert lanes[0].output_root == Path("build/verification/chatterbox-tuning-exag-0p5-cfg-0p5")


def test_parse_args_defaults_to_documented_probe_and_remote_root() -> None:
    settings = run_chatterbox_tuning_sweep._parse_args([])

    assert settings.reference_audio == Path(
        "build/verification/openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
    )
    assert "rent svenskt prov" in settings.probe_text
    assert settings.hemma_host == "hemma"
    assert settings.hemma_root == Path("/home/paunchygent/apps/sir-convert-a-lot")
    assert settings.skip_build is True


def test_run_lane_builds_canonical_run_hemma_command(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    class _Completed:
        returncode = 0

    def _fake_run(command: list[str], cwd: Path, check: bool) -> _Completed:
        assert cwd == run_chatterbox_tuning_sweep.REPO_ROOT
        assert check is False
        commands.append(command)
        return _Completed()

    monkeypatch.setattr(
        run_chatterbox_tuning_sweep.subprocess,
        "run",
        _fake_run,
    )
    settings = run_chatterbox_tuning_sweep.SweepSettings(
        output_root=Path("build/verification/chatterbox-tuning-tuning-sweep"),
        reference_audio=Path("build/verification/ref.m4a"),
        probe_text="Hej världen",
        hemma_host="hemma",
        hemma_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        skip_build=True,
    )
    lane = run_chatterbox_tuning_sweep.SweepLane(
        slug="exag-0p5-cfg-0p5",
        exaggeration=0.5,
        cfg_weight=0.5,
        output_root=Path("build/verification/chatterbox-tuning-exag-0p5-cfg-0p5"),
    )

    result = run_chatterbox_tuning_sweep._run_lane(settings, lane)

    assert result == 0
    command = commands[0]
    assert command[:7] == ["pdm", "run", "run-hemma", "--", "pdm", "run", "benchmark:chatterbox"]
    assert "--skip-build" in command
    assert lane.output_root.as_posix() in command
    assert "Hej världen" in command


def test_write_summary_records_lane_results(tmp_path: Path) -> None:
    output_root = tmp_path / "summary"
    settings = run_chatterbox_tuning_sweep.SweepSettings(
        output_root=output_root,
        reference_audio=Path("build/verification/ref.m4a"),
        probe_text="Hej världen",
        hemma_host="hemma",
        hemma_root=Path("/home/paunchygent/apps/sir-convert-a-lot"),
        skip_build=True,
    )
    lanes = [
        run_chatterbox_tuning_sweep.LaneResult(
            slug="exag-0p5-cfg-0p5",
            exaggeration=0.5,
            cfg_weight=0.5,
            output_root="build/verification/chatterbox-tuning-exag-0p5-cfg-0p5",
            returncode=0,
            synthesized_ok=True,
            clone_output_path="build/verification/.../scenario-a-sv-ref-sv-out.wav",
            clone_duration_seconds=12.3,
            clone_sha256="abc",
            peak_vram_used_bytes=123,
        )
    ]

    run_chatterbox_tuning_sweep._write_summary(
        output_root=output_root,
        settings=settings,
        lanes=lanes,
    )

    payload = json.loads((output_root / "report.json").read_text(encoding="utf-8"))
    assert payload["benchmark_id"] == "chatterbox-tuning-tuning-sweep"
    assert payload["lanes"][0]["slug"] == "exag-0p5-cfg-0p5"
    markdown = (output_root / "report.md").read_text(encoding="utf-8")
    assert "Chatterbox tuning sweep Chatterbox Tuning Sweep" in markdown
    assert "synthesized_ok" in markdown
