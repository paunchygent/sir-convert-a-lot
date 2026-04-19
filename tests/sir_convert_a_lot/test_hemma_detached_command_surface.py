"""Tests for the Sir Convert-a-Lot detached Hemma command surface.

Purpose:
    Lock the committed detached launcher/monitor scripts used for long-running
    Hemma deploy commands.

Relationships:
    - Protects Task 254 production deploy recovery operations.
    - Exercises scripts/devops/hemma-command-*.sh contract wiring.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
LOCAL_START = REPO_ROOT / "scripts" / "devops" / "hemma-command-start.sh"
LOCAL_MONITOR = REPO_ROOT / "scripts" / "devops" / "hemma-command-monitor.sh"
REMOTE_START = REPO_ROOT / "scripts" / "devops" / "hemma-command-start-remote.sh"
REMOTE_MONITOR = REPO_ROOT / "scripts" / "devops" / "hemma-command-monitor-remote.sh"


def test_detached_hemma_command_scripts_are_exposed_as_pdm_surfaces() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = pyproject["tool"]["pdm"]["scripts"]

    assert scripts["hemma-command-start"] == "bash scripts/devops/hemma-command-start.sh"
    assert scripts["hemma-command-monitor"] == "bash scripts/devops/hemma-command-monitor.sh"


def test_local_detached_launcher_delegates_through_run_hemma() -> None:
    start_text = LOCAL_START.read_text(encoding="utf-8")
    monitor_text = LOCAL_MONITOR.read_text(encoding="utf-8")

    assert "scripts/devops/hemma-command-start-remote.sh" in start_text
    assert "pdm run run-local-pdm run-hemma" in start_text
    assert "scripts/devops/hemma-command-monitor-remote.sh" in monitor_text
    assert "pdm run run-local-pdm run-hemma" in monitor_text


def test_remote_detached_launcher_writes_log_and_pid_breadcrumbs() -> None:
    start_text = REMOTE_START.read_text(encoding="utf-8")

    assert "nohup" in start_text
    assert ".artifacts/hemma-command-${label}-${run_stamp}.log" in start_text
    assert ".artifacts/hemma-command-${label}-${run_stamp}.pid" in start_text
    assert "Monitor command: pdm run run-local-pdm hemma-command-monitor" in start_text


def test_remote_monitor_selects_detached_command_logs() -> None:
    monitor_text = REMOTE_MONITOR.read_text(encoding="utf-8")

    assert ".artifacts/hemma-command-*.log" in monitor_text
    assert "tail_args=(-n 0 -F" in monitor_text
    assert "grep --line-buffered" in monitor_text
