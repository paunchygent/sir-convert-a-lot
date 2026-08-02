"""Tests for the Sir Convert-a-Lot detached Hemma command surface.

Purpose:
    Lock the committed detached launcher/monitor scripts used for long-running
    Hemma deploy commands.

Relationships:
    - Protects public-edge verification production deploy recovery operations.
    - Exercises scripts/devops/hemma-command-*.sh contract wiring.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT = REPO_ROOT / "pyproject.toml"
LOCAL_START = REPO_ROOT / "scripts" / "devops" / "hemma-command-start.sh"
LOCAL_MONITOR = REPO_ROOT / "scripts" / "devops" / "hemma-command-monitor.sh"
LOCAL_PROD_RECREATE = REPO_ROOT / "scripts" / "devops" / "hemma-prod-recreate.sh"
REMOTE_START = REPO_ROOT / "scripts" / "devops" / "hemma-command-start-remote.sh"
REMOTE_MONITOR = REPO_ROOT / "scripts" / "devops" / "hemma-command-monitor-remote.sh"
DEFAULT_HOST_REMEDIATE = (
    REPO_ROOT / "scripts" / "devops" / "hemma-public-edge-default-host-remediate.sh"
)


def test_detached_hemma_command_scripts_are_exposed_as_pdm_surfaces() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = pyproject["tool"]["pdm"]["scripts"]

    assert scripts["hemma-command-start"] == "bash scripts/devops/hemma-command-start.sh"
    assert scripts["hemma-command-monitor"] == "bash scripts/devops/hemma-command-monitor.sh"
    assert (
        scripts["hemma-public-edge-default-host-remediate"]
        == "bash scripts/devops/hemma-public-edge-default-host-remediate.sh"
    )


def test_local_detached_launcher_delegates_through_run_hemma() -> None:
    start_text = LOCAL_START.read_text(encoding="utf-8")
    monitor_text = LOCAL_MONITOR.read_text(encoding="utf-8")

    assert "scripts/devops/hemma-command-start-remote.sh" in start_text
    assert "pdm run run-local-pdm run-hemma" in start_text
    assert "scripts/devops/hemma-command-monitor-remote.sh" in monitor_text
    assert "pdm run run-local-pdm run-hemma" in monitor_text


def test_prod_recreate_preserves_skill_repository_across_sudo() -> None:
    script_text = LOCAL_PROD_RECREATE.read_text(encoding="utf-8")

    assert "REMOTE_SKILL_REPOSITORY=" in script_text
    assert '"SIR_CONVERT_A_LOT_HEMMA_SKILL_REPOSITORY=${REMOTE_SKILL_REPOSITORY}"' in script_text
    assert '"SIR_CONVERT_A_LOT_CURRENT_SKILL_REPOSITORY=${REMOTE_SKILL_REPOSITORY}"' in script_text


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


def test_default_host_remediation_targets_shared_infrastructure_surface() -> None:
    script_text = DEFAULT_HOST_REMEDIATE.read_text(encoding="utf-8")

    assert "/home/paunchygent/infrastructure" in script_text
    assert "docker-compose.yml" in script_text
    assert "DEFAULT_HOST=hemma-reserved-default-host" in script_text
    assert "VIRTUAL_HOST=hemma-reserved-default-host" in script_text
    assert "CERT_NAME=convert.hule.education" in script_text
    assert "PROXY_DEFAULT_SERVER=true" in script_text
    assert "return 404" in script_text
    assert 'printf "%s\\n", block' in script_text
    assert "sudo docker compose -f" in script_text
    assert "nginx-proxy" in script_text
    assert "acme-companion" in script_text
