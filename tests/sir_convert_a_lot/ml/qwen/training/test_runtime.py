"""Unit tests for canonical Qwen runtime helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.ml.qwen.common.models import QwenImageBuildPlan
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    SmokeSettings,
    _resolve_installed_persistent_home_path,
    _sync_home_cache_into_data_disk,
    inspect_image_build_plan,
    prepare_qwen_image,
    resolve_effective_bind_root,
)


def _settings(*, build_image: bool) -> SmokeSettings:
    """Build one deterministic smoke settings object for helper tests."""
    return SmokeSettings(
        output_root=Path("build/verification/qwen-training-smoke"),
        dockerfile_path=Path("containers/qwen-finetune-hemma/Dockerfile"),
        image="sir-convert-a-lot-qwen-finetune-hemma:latest",
        model_id="Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        hf_cache_dir=Path("/srv/scratch/sir-convert-a-lot/cache/huggingface"),
        hf_cache_home_mount=Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface"),
        build_image=build_image,
    )


def test_sync_home_cache_into_data_disk_uses_rsync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The fallback cache sync should use one resumable rsync command."""
    canonical_dir = tmp_path / "canonical"
    home_mount = tmp_path / "home"
    canonical_dir.mkdir(parents=True, exist_ok=True)
    home_mount.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    def fake_run_checked(command: list[str], *, label: str) -> str:
        captured["command"] = command
        captured["label"] = label
        return ""

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.run_checked",
        fake_run_checked,
    )

    _sync_home_cache_into_data_disk(canonical_dir, home_mount)

    assert captured["label"] == "rsync qwen home cache"
    assert captured["command"] == [
        "rsync",
        "-a",
        "--partial",
        f"{home_mount.as_posix()}/",
        canonical_dir.as_posix(),
    ]


def test_inspect_image_build_plan_requires_build_when_image_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing images should force a build even when skip-build was requested."""
    settings = _settings(build_image=False)

    def fake_docker_checked(args: list[str], *, label: str) -> str:
        del args, label
        raise SystemExit("missing image")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.docker_checked",
        fake_docker_checked,
    )

    build_plan = inspect_image_build_plan(settings)

    assert build_plan == QwenImageBuildPlan(
        image_present=False,
        existing_image_id=None,
        build_required=True,
    )


def test_prepare_qwen_image_emits_warning_before_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """A required cold build should emit an operator-facing warning."""
    settings = _settings(build_image=True)
    emitted: list[str] = []

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.inspect_image_build_plan",
        lambda effective_settings: QwenImageBuildPlan(
            image_present=True,
            existing_image_id="sha256:existing",
            build_required=True,
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.ensure_image_present",
        lambda effective_settings, *, build_plan=None: (True, "sha256:rebuilt"),
    )

    build_performed, image_id = prepare_qwen_image(settings, emit=emitted.append)

    assert build_performed is True
    assert image_id == "sha256:rebuilt"
    assert len(emitted) == 1
    assert "BuildKit image build" in emitted[0]
    assert settings.image in emitted[0]
    assert settings.dockerfile_path.resolve().as_posix() in emitted[0]


def test_resolve_installed_persistent_home_path_maps_build_subpaths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Installed persistent build mounts should resolve arbitrary build subpaths."""
    canonical_root = Path("/srv/scratch/sir-convert-a-lot/build/verification/story31/task240")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: (
            "/srv/scratch/sir-convert-a-lot/build"
            if path == Path("/home/paunchygent/.data/sir-convert-a-lot/build")
            else None
        ),
    )
    monkeypatch.setattr(Path, "mkdir", lambda self, parents=False, exist_ok=False: None)

    resolved = _resolve_installed_persistent_home_path(canonical_root)

    assert resolved == Path(
        "/home/paunchygent/.data/sir-convert-a-lot/build/verification/story31/task240"
    )


def test_resolve_effective_bind_root_prefers_installed_persistent_home_mount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Installed persistent home mounts should be preferred over the failing scratch root."""
    canonical_root = Path("/srv/scratch/sir-convert-a-lot/build/verification/story31/task240")
    home_mount = Path(
        "/home/paunchygent/.data/sir-convert-a-lot/qwen-story31-stability-lab-output-roots/"
        "srv/scratch/sir-convert-a-lot/build/verification/story31/task240"
    )
    probe_calls: list[Path] = []

    monkeypatch.setattr(Path, "mkdir", lambda self, parents=False, exist_ok=False: None)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: (
            "/srv/scratch/sir-convert-a-lot/build"
            if path == Path("/home/paunchygent/.data/sir-convert-a-lot/build")
            else None
        ),
    )

    def fake_probe(path: Path, *, image: str) -> bool:
        del image
        probe_calls.append(path)
        return path == Path(
            "/home/paunchygent/.data/sir-convert-a-lot/build/verification/story31/task240"
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime._probe_docker_bind_mount",
        fake_probe,
    )

    resolved = resolve_effective_bind_root(
        canonical_root,
        home_mount,
        image="sir-convert-a-lot-qwen-finetune-hemma:task100",
        sync_home_into_canonical=False,
    )

    assert resolved.canonical_root == canonical_root
    assert resolved.effective_root == Path(
        "/home/paunchygent/.data/sir-convert-a-lot/build/verification/story31/task240"
    )
    assert resolved.used_home_mount is True
    assert probe_calls == [resolved.effective_root]
