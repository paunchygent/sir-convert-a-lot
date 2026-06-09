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
    QwenDockerBindRootsInstallReport,
    QwenDockerBindRootsProbeReport,
    QwenDockerBindRootsStatusReport,
    QwenDockerBindRootState,
    default_settings,
)
from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime import (
    build_root_state,
    render_service_unit,
)


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
        "scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime._bind_root_roundtrip_matches",
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
