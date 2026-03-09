"""Tests for Task 113 Hemma Docker storage-root remediation.

Purpose:
    Verify the fstab/bind-mount contract and committed runner surface for the
    Docker storage migration without touching the real Hemma daemon.

Relationships:
    - Covers `task113_hemma_docker_storage_runtime.py`.
    - Covers `run_task113_hemma_docker_storage_remediation.py`.
    - Protects the host-wide Docker storage contract introduced by Task 113.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_task113_hemma_docker_storage_remediation
from scripts.sir_convert_a_lot.devops.task113_hemma_docker_storage_runtime import (
    Task113DockerStorageReport,
    Task113DockerStorageSettings,
    ensure_fstab_bind_entry_text,
    find_mount_source,
)


def test_ensure_fstab_bind_entry_text_appends_once(tmp_path: Path) -> None:
    """Task 113 should add the bind-mount fstab entry exactly once."""
    source = tmp_path / "scratch" / "docker"
    target = tmp_path / "var" / "snap" / "docker" / "common" / "var-lib-docker"

    first = ensure_fstab_bind_entry_text(current_text="", source=source, target=target)
    second = ensure_fstab_bind_entry_text(current_text=first, source=source, target=target)

    entry = f"{source.as_posix()} {target.as_posix()} none bind 0 0"
    assert first.count(entry) == 1
    assert second.count(entry) == 1


def test_find_mount_source_returns_none_for_plain_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 113 should ignore plain directories that are not mountpoints."""

    def _fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        if command[0] == "mountpoint":
            return subprocess.CompletedProcess(command, 1, "", "")
        raise AssertionError(f"Unexpected command: {command}")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task113_hemma_docker_storage_runtime.subprocess.run",
        _fake_run,
    )

    assert find_mount_source(tmp_path / "plain") is None


def test_task113_runner_writes_report_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Task 113 runner should write deterministic report files."""
    output_root = tmp_path / "build" / "verification" / "task-113"
    expected_report = Task113DockerStorageReport(
        docker_root="/var/snap/docker/common/var-lib-docker",
        scratch_docker_root="/srv/scratch/docker/data-root",
        docker_root_backup="/var/snap/docker/common/var-lib-docker.task113-backup",
        legacy_home_docker_root="/home/paunchygent/docker-data-root",
        docker_root_before="/var/snap/docker/common/var-lib-docker",
        docker_root_after="/var/snap/docker/common/var-lib-docker",
        docker_root_mount_source_before=None,
        docker_root_mount_source_after="/srv/scratch/docker/data-root",
        legacy_home_mount_source_before="/dev/sdb1[/docker/data-root]",
        legacy_home_mount_source_after=None,
        snap_data_root_before="/home/paunchygent/docker-data-root",
        snap_data_root_after="/var/snap/docker/common/var-lib-docker",
        removed_backup_after_success=True,
        filesystem_df_before="before fs",
        filesystem_df_after="after fs",
        docker_ps_before="before ps",
        docker_ps_after="after ps",
    )

    def _fake_run(settings: Task113DockerStorageSettings) -> Task113DockerStorageReport:
        return expected_report

    monkeypatch.setattr(
        run_task113_hemma_docker_storage_remediation,
        "run_task113_docker_storage_migration",
        _fake_run,
    )

    exit_code = run_task113_hemma_docker_storage_remediation.main(
        ["--output-root", output_root.as_posix()]
    )

    assert exit_code == 0
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    assert (
        json.loads(report_json_path.read_text(encoding="utf-8"))["removed_backup_after_success"]
        is True
    )
    assert "Task 113 Hemma Docker Storage Remediation Report" in report_md_path.read_text(
        encoding="utf-8"
    )
    assert (
        '"docker_root_after": "/var/snap/docker/common/var-lib-docker"'
        in capsys.readouterr().out
    )
