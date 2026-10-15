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
from scripts.sir_convert_a_lot.ml.qwen.training import qwen_historical_pilot_control as control
from scripts.sir_convert_a_lot.ml.qwen.training.detached_runtime.settings_snapshot import (
    snapshot_settings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control import main


def test_default_hot_build_reaches_bundle_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real Hot default must reach the next producer boundary without host writes."""
    hot_build = Path("/home/paunchygent/.local/share/sir-convert-a-lot/jobs/build")
    assert control.build_parser().parse_args(["launch"]).scratch_build_root == hot_build
    original_mkdir = Path.mkdir
    prepared_builds: list[Path] = []

    def intercept_mkdir(path: Path, *args, **kwargs) -> None:
        if path == hot_build:
            prepared_builds.append(path)
            return
        assert path.is_relative_to(tmp_path)
        original_mkdir(path, *args, **kwargs)

    def stop_at_bundle_validation(*args, **kwargs) -> tuple[int, int]:
        raise RuntimeError("bundle validation intercepted")

    monkeypatch.setattr(Path, "mkdir", intercept_mkdir)
    monkeypatch.setattr(control, "_validate_historical_bundle", stop_at_bundle_validation)
    monkeypatch.setattr(control, "run_checked", lambda *a, **kw: pytest.fail("host call"))
    with pytest.raises(RuntimeError, match="bundle validation intercepted"):
        main(["launch", "--output-root", str(tmp_path / "launches")])
    assert prepared_builds == [hot_build]


@pytest.mark.parametrize("tier", ["/srv/scratch", "/srv/storage"])
@pytest.mark.parametrize("alias", [False, True], ids=["direct", "alias"])
@pytest.mark.parametrize("existing_output", [False, True], ids=["new-output", "retained-output"])
def test_prohibited_build_refused_before_launch_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    tier: str,
    alias: bool,
    existing_output: bool,
) -> None:
    """Invalid primary placement must preserve launch outputs and the latest pointer."""
    build_root = Path(tier) / "sir-convert-a-lot/build"
    if alias:
        redirect = tmp_path / "build-alias"
        redirect.symlink_to(build_root, target_is_directory=True)
        build_root = redirect
    output_root = tmp_path / "launches"
    if existing_output:
        output_root.mkdir()
        (output_root / "latest-launch.json").write_text("retained pointer", encoding="utf-8")

    def refuse_mkdir(path: Path, *args, **kwargs) -> None:
        pytest.fail(f"mkdir before destination refusal: {path}")

    monkeypatch.setattr(Path, "mkdir", refuse_mkdir)
    monkeypatch.setattr(control, "run_checked", lambda *a, **kw: pytest.fail("host call"))
    with pytest.raises(SystemExit, match="requires Hot owner storage"):
        main(["launch", "--output-root", str(output_root), "--scratch-build-root", str(build_root)])
    assert output_root.exists() == existing_output
    if existing_output:
        assert [path.name for path in output_root.iterdir()] == ["latest-launch.json"]
        assert (output_root / "latest-launch.json").read_text(
            encoding="utf-8"
        ) == "retained pointer"


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
