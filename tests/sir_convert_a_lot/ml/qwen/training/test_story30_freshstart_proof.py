"""Tests for the Story 30 fresh-start proof surface.

Purpose:
    Verify the fresh-start discriminant CLI prepares deterministic proof
    packages and drives the committed remote Hemma surface without ad hoc
    shell glue.

Relationships:
    - Exercises `story30_freshstart_proof.py`.
    - Reuses the mini-bundle helper test contract indirectly through remote
      launch handling.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_input_contract import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_proof import main


def test_prepare_writes_freshstart_package(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Preparing Task 211 should write a deterministic proof package."""
    result = main(["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t211-proof"])
    capsys.readouterr()

    assert result == 0
    proof_root = tmp_path / "t211-proof"
    config_payload = json.loads((proof_root / "proof-config.json").read_text(encoding="utf-8"))
    plan_markdown = (proof_root / "plan.md").read_text(encoding="utf-8")
    checklist_markdown = (proof_root / "checklist.md").read_text(encoding="utf-8")

    assert config_payload["command_name"] == "qwen-story30-freshstart-proof"
    assert config_payload["train_line_start"] == 1
    assert config_payload["train_line_end"] == 16
    assert config_payload["max_steps"] == 2
    assert "qwen-story30-freshstart-proof launch --proof-id t211-proof" in plan_markdown
    assert "swedish_pilot_train lines 1..16" in plan_markdown
    assert "Mini-bundle materialized" in checklist_markdown


def test_launch_uses_remote_story30_surface(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The public launch command should route through the committed remote proof surface."""
    prepare_result = main(
        ["prepare", "--output-root", tmp_path.as_posix(), "--proof-id", "t211-proof"]
    )
    assert prepare_result == 0
    capsys.readouterr()
    calls: list[list[str]] = []

    def fake_run(
        command: list[str], *, check: bool, capture_output: bool, text: bool
    ) -> subprocess.CompletedProcess[str]:
        calls.append(list(command))
        if "qwen-scratch-policy" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "scratch_free_bytes": 32 * 1024**3,
                        "required_free_bytes": 16 * 1024**3,
                        "meets_required_headroom": True,
                    }
                ),
                "",
            )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps({"proof_id": "t211-proof", "remote_launch_root": "/srv/scratch/x"}),
            "",
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_runtime.subprocess.run",
        fake_run,
    )

    result = main(["launch", "--output-root", tmp_path.as_posix(), "--proof-id", "t211-proof"])
    capsys.readouterr()

    assert result == 0
    assert len(calls) == 2
    assert "qwen-scratch-policy" in calls[0]
    assert calls[1][:7] == [
        "pdm",
        "run",
        "run-hemma",
        "--",
        "pdm",
        "run",
        "qwen-story30-freshstart-proof",
    ]
    assert "remote-launch" in calls[1]
    assert "--train-line-start" in calls[1]
    assert "16" in calls[1]
    assert (tmp_path / "t211-proof" / "launch.json").exists() is True


def test_remote_launch_materializes_bundle_and_calls_qwen_train(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Remote launch should build the mini-bundle and then call detached training."""
    source_bundle = tmp_path / "source-bundle"
    _write_manifest(
        source_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl",
        [_row_payload(index) for index in range(1, 5)],
    )
    _write_manifest(
        source_bundle / "manifests" / "swedish_checkpoint_dev.prepared.jsonl",
        [_row_payload(101)],
    )
    calls: list[list[str]] = []

    def fake_launch(command: list[str], *, label: str) -> dict[str, object]:
        del label
        calls.append(list(command))
        return {"launch_id": "t211-proof-freshstart", "container_name": "qwen-train"}

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_proof.run_local_qwen_train_json",
        fake_launch,
    )

    result = main(
        [
            "remote-launch",
            "--proof-id",
            "t211-proof",
            "--remote-proof-output-root",
            (tmp_path / "remote-proof").as_posix(),
            "--remote-training-output-root",
            (tmp_path / "remote-training").as_posix(),
            "--source-bundle-root",
            source_bundle.as_posix(),
            "--train-manifest-family",
            "swedish_pilot_train",
            "--eval-manifest-family",
            "swedish_checkpoint_dev",
            "--text-embedding-mask-policy",
            "text_span_only",
            "--throughput-profile-label",
            "hemma-throughput-balanced-v1",
            "--train-line-start",
            "1",
            "--train-line-end",
            "2",
            "--eval-line-start",
            "1",
            "--eval-line-end",
            "1",
            "--batch-size",
            "8",
            "--max-steps",
            "2",
            "--checkpoint-interval-steps",
            "500",
            "--eval-interval-steps",
            "1000",
            "--gradient-accumulation-steps",
            "1",
            "--launch-id",
            "t211-proof-freshstart",
            "--skip-build",
        ]
    )
    capsys.readouterr()

    assert result == 0
    assert len(calls) == 1
    assert calls[0][0] == "launch"
    assert "--pilot-bundle-root" in calls[0]
    remote_bundle_root = tmp_path / "remote-proof" / "t211-proof" / "mini-bundle"
    assert (
        remote_bundle_root / "manifests" / "swedish_pilot_train.prepared.jsonl"
    ).exists() is True


def _row_payload(index: int) -> dict[str, object]:
    relative_audio = Path("audio") / f"row-{index}.wav"
    relative_ref = Path("refs") / f"row-{index}.wav"
    relative_ref_input = Path("ref_mels") / f"row-{index}.pt"
    return {
        "audio": relative_audio.as_posix(),
        "ref_audio": relative_ref.as_posix(),
        "precomputed_ref_input_path": relative_ref_input.as_posix(),
        "precomputed_ref_input_kind": PRECOMPUTED_REF_INPUT_KIND,
        "precomputed_ref_input_version": PRECOMPUTED_REF_INPUT_VERSION,
        "precomputed_ref_input_source_audio": relative_ref.as_posix(),
        "speaker_id": f"speaker-{index}",
        "text": f"row {index}",
        "audio_codes": [1, 2, 3],
    }


def _write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        audio_path = path.parent.parent / str(row["audio"])
        ref_path = path.parent.parent / str(row["ref_audio"])
        ref_input_path = path.parent.parent / str(row["precomputed_ref_input_path"])
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_input_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"audio")
        ref_path.write_bytes(b"ref")
        ref_input_path.write_bytes(b"ref-mel")
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
