"""Tests for the permanent Hemma Qwen Docker bind-root surface.

Purpose:
    Verify the committed Qwen Docker bind-root proof bind-root install/status/probe helpers and
    runner without touching the real Hemma host, systemd, or Docker daemon.

Relationships:
    - Covers `qwen_docker_bind_roots_runtime.py`.
    - Covers `run_qwen_docker_bind_roots.py`.
    - Protects the persistent home-visible bind-root contract for scratch-backed
      Qwen build and cache paths.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_qwen_docker_bind_roots
from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_contracts import (
    QwenDockerBindProbeResult,
    QwenDockerBindRoot,
    QwenDockerBindRootsInstallReport,
    QwenDockerBindRootsProbeReport,
    QwenDockerBindRootsStatusReport,
    QwenDockerBindRootState,
    default_settings,
)
from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime import (
    _ensure_bind_root,
    bind_root_roundtrip_matches,
    build_root_state,
    render_service_unit,
)


def _make_temp_bind_root(base: Path, *, label: str) -> QwenDockerBindRoot:
    """Create one real canonical root pair under a temporary base directory."""
    canonical_root = base / label / "canonical"
    canonical_root.mkdir(parents=True)
    return QwenDockerBindRoot(
        label=label,
        canonical_root=canonical_root,
        home_root=base / label / "home",
    )


def _link_home_to_canonical(bind_root: QwenDockerBindRoot) -> None:
    """Create a synthetic home view whose writes land in the canonical root."""
    bind_root.home_root.symlink_to(bind_root.canonical_root, target_is_directory=True)


def _device_form_source(bind_root: QwenDockerBindRoot, *, device: str = "/dev/sda1") -> str:
    """Render the bracketed findmnt SOURCE form for one synthetic backing."""
    return f"{device}[{bind_root.canonical_root.as_posix()}]"


def _assert_no_sentinel(leftovers: Path) -> None:
    """Assert the roundtrip probe left no sentinel file behind."""
    assert list(leftovers.glob(".qwen_bind_status_probe_*")) == []


@pytest.fixture
def fake_privileged_runner(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Record privileged host commands and skip directory creation on the host."""
    commands: list[list[str]] = []

    def record(command: list[str], *, label: str) -> str:
        commands.append(list(command))
        return ""

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.ensure_directory",
        lambda path, *, require_root: None,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.run_root_checked",
        record,
    )
    return commands


@pytest.mark.parametrize("label", ["build", "cache"])
def test_ensure_bind_root_accepts_device_form_backing_for_existing_mount(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_privileged_runner: list[list[str]],
    label: str,
) -> None:
    """An equivalent device-form mount is accepted without a remount."""
    bind_root = _make_temp_bind_root(tmp_path, label=label)
    _link_home_to_canonical(bind_root)
    device_source = _device_form_source(bind_root)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: device_source,
    )

    _ensure_bind_root(bind_root)

    assert fake_privileged_runner == []
    _assert_no_sentinel(bind_root.canonical_root)
    _assert_no_sentinel(bind_root.home_root)


@pytest.mark.parametrize("label", ["build", "cache"])
@pytest.mark.parametrize("wrong_form", ["wrong-filesystem", "wrong-fsroot"])
def test_ensure_bind_root_rejects_wrong_backing_device_forms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_privileged_runner: list[list[str]],
    label: str,
    wrong_form: str,
) -> None:
    """Device-form SOURCE reports never admit a home root with different backing."""
    bind_root = _make_temp_bind_root(tmp_path, label=label)
    bind_root.home_root.mkdir()
    if wrong_form == "wrong-filesystem":
        mount_source = _device_form_source(bind_root, device="/dev/sdb1")
    else:
        mount_source = "/dev/sda1[/srv/scratch/sir-convert-a-lot/other]"
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: mount_source,
    )

    with pytest.raises(SystemExit) as excinfo:
        _ensure_bind_root(bind_root)

    assert mount_source in str(excinfo.value)
    assert bind_root.canonical_root.as_posix() in str(excinfo.value)
    assert "backing does not match" in str(excinfo.value)
    assert fake_privileged_runner == []
    _assert_no_sentinel(bind_root.canonical_root)
    _assert_no_sentinel(bind_root.home_root)


def test_ensure_bind_root_accepts_literal_source_with_backing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_privileged_runner: list[list[str]],
) -> None:
    """A literal-path SOURCE is accepted when the real backing roundtrip confirms it."""
    bind_root = _make_temp_bind_root(tmp_path, label="build")
    _link_home_to_canonical(bind_root)
    literal_source = bind_root.canonical_root.as_posix()
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: literal_source,
    )

    _ensure_bind_root(bind_root)

    assert fake_privileged_runner == []
    _assert_no_sentinel(bind_root.canonical_root)


def test_ensure_bind_root_rejects_literal_source_without_backing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_privileged_runner: list[list[str]],
) -> None:
    """A literal-path SOURCE alone never proves canonical/home backing."""
    bind_root = _make_temp_bind_root(tmp_path, label="cache")
    bind_root.home_root.mkdir()
    literal_source = bind_root.canonical_root.as_posix()
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: literal_source,
    )

    with pytest.raises(SystemExit) as excinfo:
        _ensure_bind_root(bind_root)

    assert literal_source in str(excinfo.value)
    assert "backing does not match" in str(excinfo.value)
    assert fake_privileged_runner == []
    _assert_no_sentinel(bind_root.canonical_root)
    _assert_no_sentinel(bind_root.home_root)


def test_ensure_bind_root_installs_when_no_mount_is_reported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_privileged_runner: list[list[str]],
) -> None:
    """A missing mount keeps the ordinary bind installation path."""
    bind_root = _make_temp_bind_root(tmp_path, label="build")
    bind_root.home_root.mkdir()
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: None,
    )

    _ensure_bind_root(bind_root)

    assert fake_privileged_runner == [
        ["mount", "--bind", bind_root.canonical_root.as_posix(), bind_root.home_root.as_posix()]
    ]
    _assert_no_sentinel(bind_root.canonical_root)
    _assert_no_sentinel(bind_root.home_root)


def test_build_root_state_uses_real_backing_roundtrip_for_device_form_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Status uses the shared sentinel identity, not the SOURCE display text."""
    bind_root = _make_temp_bind_root(tmp_path, label="build")
    _link_home_to_canonical(bind_root)
    device_source = _device_form_source(bind_root)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: device_source,
    )

    state = build_root_state(bind_root)

    assert state.mount_source == device_source
    assert state.mounted_expected_source is True
    _assert_no_sentinel(bind_root.canonical_root)


def test_bind_root_roundtrip_matches_confirms_backing_and_cleans_sentinels(
    tmp_path: Path,
) -> None:
    """The exported identity helper reports real visibility and leaves no probes."""
    backed = _make_temp_bind_root(tmp_path / "backed", label="build")
    _link_home_to_canonical(backed)
    assert bind_root_roundtrip_matches(backed) is True
    _assert_no_sentinel(backed.canonical_root)
    _assert_no_sentinel(backed.home_root)

    separate = _make_temp_bind_root(tmp_path / "separate", label="cache")
    separate.home_root.mkdir()
    assert bind_root_roundtrip_matches(separate) is False
    _assert_no_sentinel(separate.canonical_root)
    _assert_no_sentinel(separate.home_root)

    absent = QwenDockerBindRoot(
        label="build",
        canonical_root=tmp_path / "absent" / "canonical",
        home_root=tmp_path / "absent" / "home",
    )
    assert bind_root_roundtrip_matches(absent) is False


def test_render_service_unit_uses_repo_owned_repair_surface() -> None:
    """The installed service should call the committed repair surface, not ad hoc shell."""
    settings = default_settings()

    rendered = render_service_unit(settings)

    assert "run_qwen_docker_bind_roots" in rendered
    assert "repair --service-mode" in rendered
    assert settings.repo_root.as_posix() in rendered
    assert settings.service_name not in rendered


def test_build_root_state_marks_expected_mount_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bind-root state should report when the home path is mounted from the canonical root."""
    bind_root = default_settings().bind_roots[0]
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.find_mount_source",
        lambda target: (
            bind_root.canonical_root.as_posix() if target == bind_root.home_root else None
        ),
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime.bind_root_roundtrip_matches",
        lambda observed_bind_root: observed_bind_root == bind_root,
    )

    state = build_root_state(bind_root)

    assert state.mount_source == bind_root.canonical_root.as_posix()
    assert state.mounted_expected_source is True


def test_runner_writes_install_status_and_probe_reports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The Qwen Docker bind-root proof runner should write deterministic artifacts for all public
    commands.
    """
    output_root = tmp_path / "build" / "verification" / "qwen-docker-bind-roots"
    bind_roots = (
        QwenDockerBindRootState(
            label="build",
            canonical_root="/srv/scratch/sir-convert-a-lot/build",
            home_root="/home/paunchygent/.data/sir-convert-a-lot/build",
            canonical_exists=True,
            home_exists=True,
            mount_source="/srv/scratch/sir-convert-a-lot/build",
            mounted_expected_source=True,
        ),
        QwenDockerBindRootState(
            label="cache",
            canonical_root="/srv/scratch/sir-convert-a-lot/cache",
            home_root="/home/paunchygent/.data/sir-convert-a-lot/cache",
            canonical_exists=True,
            home_exists=True,
            mount_source="/srv/scratch/sir-convert-a-lot/cache",
            mounted_expected_source=True,
        ),
    )
    install_report = QwenDockerBindRootsInstallReport(
        installed_at="2026-03-18T18:00:00Z",
        service_name="sir-convert-a-lot-qwen-docker-bind-roots.service",
        service_path="/etc/systemd/system/sir-convert-a-lot-qwen-docker-bind-roots.service",
        service_enabled=True,
        service_active=True,
        bind_roots=bind_roots,
    )
    status_report = QwenDockerBindRootsStatusReport(
        checked_at="2026-03-18T18:01:00Z",
        service_name="sir-convert-a-lot-qwen-docker-bind-roots.service",
        service_path="/etc/systemd/system/sir-convert-a-lot-qwen-docker-bind-roots.service",
        service_unit_exists=True,
        service_enabled=True,
        service_active=True,
        bind_roots=bind_roots,
    )
    probe_report = QwenDockerBindRootsProbeReport(
        checked_at="2026-03-18T18:02:00Z",
        service_name="sir-convert-a-lot-qwen-docker-bind-roots.service",
        probe_image="sir-convert-a-lot-qwen-finetune-hemma:qwen-finetune",
        probe_results=(
            QwenDockerBindProbeResult(
                label="build",
                canonical_root="/srv/scratch/sir-convert-a-lot/build",
                home_root="/home/paunchygent/.data/sir-convert-a-lot/build",
                canonical_probe_ok=False,
                home_probe_ok=True,
                preferred_effective_root="/home/paunchygent/.data/sir-convert-a-lot/build",
            ),
        ),
    )

    monkeypatch.setattr(
        run_qwen_docker_bind_roots,
        "install_bind_root_service",
        lambda settings, enable_now: install_report,
    )
    monkeypatch.setattr(
        run_qwen_docker_bind_roots,
        "status_bind_roots",
        lambda settings: status_report,
    )
    monkeypatch.setattr(
        run_qwen_docker_bind_roots,
        "probe_bind_roots",
        lambda settings: probe_report,
    )

    install_exit_code = run_qwen_docker_bind_roots.main(
        ["install", "--output-root", output_root.as_posix()]
    )
    status_exit_code = run_qwen_docker_bind_roots.main(
        ["status", "--output-root", output_root.as_posix()]
    )
    probe_exit_code = run_qwen_docker_bind_roots.main(
        ["probe", "--output-root", output_root.as_posix()]
    )

    assert install_exit_code == 0
    assert status_exit_code == 0
    assert probe_exit_code == 0
    assert (
        json.loads((output_root / "install.json").read_text(encoding="utf-8"))["service_active"]
        is True
    )
    assert (
        json.loads((output_root / "status.json").read_text(encoding="utf-8"))["service_unit_exists"]
        is True
    )
    assert (
        json.loads((output_root / "probe.json").read_text(encoding="utf-8"))["probe_results"][0][
            "preferred_effective_root"
        ]
        == "/home/paunchygent/.data/sir-convert-a-lot/build"
    )
    rendered_output = capsys.readouterr().out
    assert '"service_active": true' in rendered_output
    assert (
        '"preferred_effective_root": "/home/paunchygent/.data/sir-convert-a-lot/build"'
        in rendered_output
    )
