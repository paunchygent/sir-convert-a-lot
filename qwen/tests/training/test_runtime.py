"""Unit tests for canonical Qwen runtime helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_contracts import (
    QwenDockerBindRoot,
)
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


def _temp_bind_root(tmp_path: Path, *, label: str) -> QwenDockerBindRoot:
    """Create one local bind-root pair whose home symlink shares the canonical backing."""
    canonical_root = tmp_path / "srv" / "sir-convert-a-lot" / label
    canonical_root.mkdir(parents=True)
    home_root = tmp_path / "home" / "sir-convert-a-lot" / label
    home_root.parent.mkdir(parents=True)
    home_root.symlink_to(canonical_root, target_is_directory=True)
    return QwenDockerBindRoot(label=label, canonical_root=canonical_root, home_root=home_root)


def _patch_local_bind_roots(
    monkeypatch: pytest.MonkeyPatch,
    bind_root: QwenDockerBindRoot,
) -> None:
    """Replace the host default bind roots with one local temporary pair."""
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.default_bind_roots",
        lambda: (bind_root,),
    )


def _canonical_subpath(bind_root: QwenDockerBindRoot) -> Path:
    """Return one nested canonical path below the bind root."""
    return bind_root.canonical_root / "verification" / "qwen_stability" / "qwen-stability-lab"


def _assert_no_bind_sentinel(root: Path) -> None:
    """Assert the backing roundtrip left no sentinel under one root."""
    assert list(root.glob(".qwen_bind_status_probe_*")) == []


@pytest.mark.parametrize("label", ["build", "cache"])
def test_resolve_installed_persistent_home_path_maps_installed_subpaths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
) -> None:
    """A literal-path SOURCE with real backing should map nested build/cache subpaths."""
    bind_root = _temp_bind_root(tmp_path, label=label)
    _patch_local_bind_roots(monkeypatch, bind_root)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: bind_root.canonical_root.as_posix() if path == bind_root.home_root else None,
    )

    resolved = _resolve_installed_persistent_home_path(_canonical_subpath(bind_root))

    expected = bind_root.home_root / "verification" / "qwen_stability" / "qwen-stability-lab"
    assert resolved == expected
    assert expected.is_dir()
    _assert_no_bind_sentinel(bind_root.home_root)
    _assert_no_bind_sentinel(bind_root.canonical_root)


@pytest.mark.parametrize("label", ["build", "cache"])
def test_resolve_installed_persistent_home_path_accepts_device_form_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    label: str,
) -> None:
    """A device-form SOURCE with equivalent backing should resolve the mapped home path."""
    bind_root = _temp_bind_root(tmp_path, label=label)
    _patch_local_bind_roots(monkeypatch, bind_root)
    device_source = f"/dev/sda1[{bind_root.canonical_root.as_posix()}]"
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: device_source if path == bind_root.home_root else None,
    )

    resolved = _resolve_installed_persistent_home_path(_canonical_subpath(bind_root))

    expected = bind_root.home_root / "verification" / "qwen_stability" / "qwen-stability-lab"
    assert resolved == expected
    assert expected.is_dir()
    _assert_no_bind_sentinel(bind_root.home_root)
    _assert_no_bind_sentinel(bind_root.canonical_root)


def test_resolve_installed_persistent_home_path_requires_observed_mount(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Equivalent backing without a reported mount must not resolve an installed home path."""
    bind_root = _temp_bind_root(tmp_path, label="build")
    _patch_local_bind_roots(monkeypatch, bind_root)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: None,
    )

    resolved = _resolve_installed_persistent_home_path(_canonical_subpath(bind_root))

    assert resolved is None
    assert not (bind_root.home_root / "verification").exists()


def test_resolve_installed_persistent_home_path_ignores_unmatched_canonical_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A canonical path outside every bind root must resolve nothing without host probes."""
    bind_root = _temp_bind_root(tmp_path, label="build")
    _patch_local_bind_roots(monkeypatch, bind_root)

    def fail_mount_source(path: Path) -> str | None:
        raise AssertionError(f"find_mount_source must not run for {path}")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        fail_mount_source,
    )

    resolved = _resolve_installed_persistent_home_path(tmp_path / "elsewhere" / "result")

    assert resolved is None


@pytest.mark.parametrize("wrong_form", ["wrong-device", "wrong-fsroot"])
def test_resolve_installed_persistent_home_path_refuses_wrong_backing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wrong_form: str,
) -> None:
    """Wrong device or wrong FSROOT backing must be refused without creating a home tree."""
    canonical_root = tmp_path / "srv" / "sir-convert-a-lot" / "build"
    canonical_root.mkdir(parents=True)
    home_root = tmp_path / "home" / "sir-convert-a-lot" / "build"
    home_root.mkdir(parents=True)
    bind_root = QwenDockerBindRoot(
        label="build",
        canonical_root=canonical_root,
        home_root=home_root,
    )
    _patch_local_bind_roots(monkeypatch, bind_root)
    if wrong_form == "wrong-device":
        mount_source = f"/dev/sdb1[{canonical_root.as_posix()}]"
    else:
        mount_source = f"/dev/sda1[{tmp_path.as_posix()}/mnt/other]"
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: mount_source,
    )

    resolved = _resolve_installed_persistent_home_path(_canonical_subpath(bind_root))

    assert resolved is None
    assert not (home_root / "verification").exists()
    _assert_no_bind_sentinel(home_root)
    _assert_no_bind_sentinel(canonical_root)


def test_resolve_effective_bind_root_prefers_installed_persistent_home_mount(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A device-form installed home mount with equivalent backing is preferred."""
    bind_root = _temp_bind_root(tmp_path, label="build")
    _patch_local_bind_roots(monkeypatch, bind_root)
    canonical_root = _canonical_subpath(bind_root)
    device_source = f"/dev/sda1[{bind_root.canonical_root.as_posix()}]"
    probe_calls: list[Path] = []
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: device_source if path == bind_root.home_root else None,
    )

    def fake_probe(path: Path, *, image: str) -> bool:
        del image
        probe_calls.append(path)
        return path == (
            bind_root.home_root / "verification" / "qwen_stability" / "qwen-stability-lab"
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime._probe_docker_bind_mount",
        fake_probe,
    )

    resolved = resolve_effective_bind_root(
        canonical_root,
        tmp_path / "home" / "sir-convert-a-lot" / "qwen-stability-lab-output-roots",
        image="sir-convert-a-lot-qwen-finetune-hemma:historical-control",
        sync_home_into_canonical=False,
    )

    assert resolved.canonical_root == canonical_root
    assert resolved.effective_root == (
        bind_root.home_root / "verification" / "qwen_stability" / "qwen-stability-lab"
    )
    assert resolved.used_home_mount is True
    assert probe_calls == [resolved.effective_root]


def test_resolve_effective_bind_root_falls_back_when_installed_home_backing_differs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wrong installed-home backing must not be preferred over the canonical mount."""
    canonical_root = tmp_path / "srv" / "sir-convert-a-lot" / "build"
    canonical_root.mkdir(parents=True)
    home_root = tmp_path / "home" / "sir-convert-a-lot" / "build"
    home_root.mkdir(parents=True)
    bind_root = QwenDockerBindRoot(
        label="build",
        canonical_root=canonical_root,
        home_root=home_root,
    )
    _patch_local_bind_roots(monkeypatch, bind_root)
    probe_calls: list[Path] = []
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime.find_mount_source",
        lambda path: f"/dev/sdb1[{canonical_root.as_posix()}]",
    )

    def fake_probe(path: Path, *, image: str) -> bool:
        del image
        probe_calls.append(path)
        return path == canonical_root

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.common.runtime._probe_docker_bind_mount",
        fake_probe,
    )

    resolved = resolve_effective_bind_root(
        canonical_root,
        tmp_path / "home" / "sir-convert-a-lot" / "fallback-root",
        image="sir-convert-a-lot-qwen-finetune-hemma:historical-control",
        sync_home_into_canonical=False,
    )

    assert resolved.canonical_root == canonical_root
    assert resolved.effective_root == canonical_root
    assert resolved.used_home_mount is False
    assert probe_calls == [canonical_root]
    assert not (home_root / "verification").exists()
    _assert_no_bind_sentinel(home_root)
