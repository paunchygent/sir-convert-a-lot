"""Tests for the historical Qwen pilot training control surface.

Purpose:
    Verify the committed historical-control CLI writes the historical contract diff and
    routes launch metadata through the dedicated runtime surface instead of the
    invalid historical approximation.

Relationships:
    - Exercises `qwen_historical_pilot_control.py`.
    - Reuses the detached launch contract from `ml.qwen.training.models`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.settings_snapshot import (
    snapshot_settings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control import main


def test_launch_writes_contract_diff_and_launch_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Launching historical control should persist the contract diff and latest pointer."""

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control._validate_launch_environment",
        lambda settings, historical_bundle_root: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control._validate_historical_bundle",
        lambda historical_bundle_root, train_manifest_family, eval_manifest_family: (8445, 8),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control.run_checked",
        lambda command, label: "ok",
    )

    bundle_mount = MountResolution(
        canonical_root=tmp_path / "historical-bundle",
        effective_root=tmp_path / "home-bundle",
        used_home_mount=True,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control.prepare_runtime_dependencies",
        lambda **kwargs: (
            False,
            "sha256:qwen-historical-control-image",
            MountResolution(tmp_path / "hf", tmp_path / "hf-home", True),
            MountResolution(tmp_path / "scratch", tmp_path / "scratch-home", True),
            bundle_mount,
        ),
    )

    def fake_launch(settings, **kwargs) -> DetachedLaunch:
        return DetachedLaunch(
            generated_at="2026-03-17T19:00:00Z",
            launch_kind="historical-control",
            launch_id=kwargs["launch_id"],
            container_name=kwargs["container_name"],
            container_id="container-123",
            repo_root=kwargs["repo_root"].as_posix(),
            run_root=(settings.runs_root / kwargs["launch_id"]).as_posix(),
            pilot_bundle_root=settings.pilot_bundle_root.as_posix(),
            train_jsonl=(
                settings.pilot_bundle_root
                / "manifests"
                / f"{settings.train_manifest_family}.prepared.jsonl"
            ).as_posix(),
            eval_jsonl=(
                settings.pilot_bundle_root
                / "manifests"
                / f"{settings.eval_manifest_family}.prepared.jsonl"
            ).as_posix(),
            train_manifest_family=settings.train_manifest_family,
            eval_manifest_family=settings.eval_manifest_family,
            dockerfile_path=kwargs["dockerfile_path"].as_posix(),
            resumed_from_checkpoint_path=None,
            settings=snapshot_settings(settings),
            command=["sudo", "-n", "docker", "run"],
            tracking={"project_name": "qwen-historical-pilot"},
            diagnostic={"kind": "qwen_historical_pilot_control"},
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control.launch_detached_historical_control",
        fake_launch,
    )

    result = main(
        [
            "launch",
            "--output-root",
            tmp_path.as_posix(),
            "--runs-root",
            (tmp_path / "runs").as_posix(),
            "--historical-bundle-root",
            (tmp_path / "historical-bundle").as_posix(),
            "--historical-bundle-home-mount",
            (tmp_path / "home-bundle").as_posix(),
            "--hf-cache-dir",
            (tmp_path / "hf").as_posix(),
            "--hf-cache-home-mount",
            (tmp_path / "hf-home").as_posix(),
            "--scratch-build-root",
            (tmp_path / "scratch").as_posix(),
            "--scratch-build-home-mount",
            (tmp_path / "scratch-home").as_posix(),
            "--launch-id",
            "qwen-historical-control-proof",
        ]
    )
    capsys.readouterr()

    assert result == 0
    launch_root = tmp_path / "qwen-historical-control-proof"
    contract_payload = json.loads((launch_root / "contract-diff.json").read_text(encoding="utf-8"))
    launch_payload = json.loads((launch_root / "launch.json").read_text(encoding="utf-8"))
    latest_payload = json.loads((tmp_path / "latest-launch.json").read_text(encoding="utf-8"))

    assert contract_payload["historical_contract"]["batch_size"] == 1
    assert contract_payload["invalid_historical_approximation"]["batch_size"] == 8
    assert (
        contract_payload["historical_control_recreation"]["text_embedding_assembly_mode"]
        == "full_channel_masked"
    )
    assert (
        contract_payload["historical_control_recreation"]["text_embedding_mask_policy"]
        == "text_span_only"
    )
    assert launch_payload["launch_kind"] == "historical-control"
    assert launch_payload["settings"]["batch_size"] == 1
    assert launch_payload["settings"]["gradient_accumulation_steps"] == 4
    assert latest_payload["launch_root"] == launch_root.as_posix()
