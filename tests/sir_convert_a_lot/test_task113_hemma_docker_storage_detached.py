"""Tests for detached Task 113 Hemma Docker storage remediation.

Purpose:
    Verify the committed detached launch/status runner for Task 113 without
    touching the real Hemma host or starting tmux sessions.

Relationships:
    - Covers `task113_hemma_docker_storage_detached_runtime.py`.
    - Covers `run_task113_hemma_docker_storage_detached.py`.
    - Protects the detached execution contract for host-wide Docker migration.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_task113_hemma_docker_storage_detached
from scripts.sir_convert_a_lot.devops.task113_hemma_docker_storage_detached_runtime import (
    Task113DetachedLaunch,
    Task113DetachedStatus,
    build_remote_shell_command,
)


def test_build_remote_shell_command_points_to_committed_task113_runner(tmp_path: Path) -> None:
    """Detached Task 113 should launch the committed remediation runner on Hemma."""
    output_root = tmp_path / "build" / "verification" / "task-113"

    command, log_path, exit_code_path = build_remote_shell_command(output_root=output_root)

    assert "pdm run task-113-docker-storage-remediation" in command
    assert output_root.as_posix() in command
    assert log_path == output_root / "live.log"
    assert exit_code_path == output_root / "exit_code.txt"


def test_task113_detached_runner_writes_launch_and_status_artifacts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Detached Task 113 runner should write deterministic local metadata artifacts."""
    output_root = tmp_path / "build" / "verification" / "task-113-detached"
    launch = Task113DetachedLaunch(
        generated_at="2026-03-09T10:00:00Z",
        session_name="task113-docker-storage-20260309t100000z",
        remote_repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        remote_output_root="/home/paunchygent/apps/sir-convert-a-lot/build/verification/task-113",
        remote_log_path="/home/paunchygent/apps/sir-convert-a-lot/build/verification/task-113/live.log",
        remote_exit_code_path="/home/paunchygent/apps/sir-convert-a-lot/build/verification/task-113/exit_code.txt",
        remote_command="pdm run task-113-docker-storage-remediation",
    )
    status = Task113DetachedStatus(
        checked_at="2026-03-09T10:05:00Z",
        session_name=launch.session_name,
        session_exists=False,
        exit_code=0,
        report_found=True,
        report_payload={"docker_root_after": "/var/snap/docker/common/var-lib-docker"},
        log_tail="migration done",
    )

    monkeypatch.setattr(
        run_task113_hemma_docker_storage_detached,
        "launch_detached_task113_migration",
        lambda *, session_name, output_root: launch,
    )
    monkeypatch.setattr(
        run_task113_hemma_docker_storage_detached,
        "inspect_detached_task113_migration",
        lambda _: status,
    )

    launch_exit = run_task113_hemma_docker_storage_detached.main(
        ["launch", "--output-root", output_root.as_posix()]
    )
    status_exit = run_task113_hemma_docker_storage_detached.main(
        ["status", "--output-root", output_root.as_posix()]
    )

    assert launch_exit == 0
    assert status_exit == 0
    launch_payload = json.loads((output_root / "launch.json").read_text(encoding="utf-8"))
    assert launch_payload["session_name"] == (launch.session_name)
    assert json.loads((output_root / "status.json").read_text(encoding="utf-8"))["exit_code"] == 0
    assert "Task 113 Detached Docker Storage Migration Status" in (
        output_root / "status.md"
    ).read_text(encoding="utf-8")
    assert '"report_found": true' in capsys.readouterr().out
