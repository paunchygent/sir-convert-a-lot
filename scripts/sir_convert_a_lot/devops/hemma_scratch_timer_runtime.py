"""Systemd timer runtime for recurring Hemma scratch maintenance.

Purpose:
    Inspect and uninstall the retired user-level systemd timer that once drove
    recurring scratch maintenance on Hemma (TASK-SIRCON-REP-0036).

Relationships:
    - Used by `run_hemma_scratch_policy.py` for timer commands.
    - Used by `hemma_scratch_maintenance_runtime.py` for shared host
      command execution and active-container detection.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_contracts import (
    ScratchTimerSettings,
    ScratchTimerStatusReport,
    ScratchTimerUninstallReport,
    utc_now_iso,
)


def run_local_checked(command: list[str], *, label: str) -> str:
    """Run one local command and return stdout or fail with diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _run_local_optional(command: list[str]) -> tuple[int, str, str]:
    """Run one local command and return exit code, stdout, and stderr."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def active_qwen_container_names() -> list[str]:
    """Return currently running Qwen-related Docker container names on Hemma."""
    try:
        output = run_local_checked(
            ["sudo", "-n", "docker", "ps", "--format", "{{.Names}}"],
            label="docker ps hemma-scratch-maintenance",
        )
    except SystemExit as exc:
        return [str(exc)]
    return [line.strip() for line in output.splitlines() if line.strip().startswith("qwen-")]


def _user_linger_enabled(username: str) -> bool:
    """Return whether systemd lingering is enabled for the current user."""
    output = run_local_checked(
        ["loginctl", "show-user", username, "--property=Linger"],
        label="loginctl show-user linger hemma-scratch-maintenance",
    )
    return output.strip() == "Linger=yes"


def _systemctl_user_bool(command: list[str]) -> bool:
    """Return whether one `systemctl --user` probe exits successfully."""
    returncode, _, _ = _run_local_optional(["systemctl", "--user", *command])
    return returncode == 0


def uninstall_scratch_timer(settings: ScratchTimerSettings) -> ScratchTimerUninstallReport:
    """Disable, stop and remove the retired user-level timer and its service."""
    unit_names = [settings.timer_name, settings.service_name]
    # An absent unit makes `disable` fail; the post-reload state check below
    # is the authority for whether the units stopped.
    _run_local_optional(["systemctl", "--user", "disable", "--now", *unit_names])
    removed_paths: list[str] = []
    for unit_name in unit_names:
        unit_path = settings.unit_dir / unit_name
        if unit_path.is_file() or unit_path.is_symlink():
            unit_path.unlink()
            removed_paths.append(unit_path.as_posix())
    run_local_checked(
        ["systemctl", "--user", "daemon-reload"],
        label="systemctl daemon-reload hemma-scratch-maintenance",
    )
    _run_local_optional(["systemctl", "--user", "reset-failed", *unit_names])
    report = ScratchTimerUninstallReport(
        uninstalled_at=utc_now_iso(),
        service_name=settings.service_name,
        timer_name=settings.timer_name,
        unit_dir=settings.unit_dir.as_posix(),
        removed_paths=removed_paths,
        timer_enabled_after=_systemctl_user_bool(["is-enabled", settings.timer_name]),
        timer_active_after=_systemctl_user_bool(["is-active", settings.timer_name]),
        service_active_after=_systemctl_user_bool(["is-active", settings.service_name]),
    )
    if report.timer_enabled_after or report.timer_active_after or report.service_active_after:
        raise SystemExit(f"Retired scratch timer is still enabled or active: {report}")
    return report


def status_scratch_timer(settings: ScratchTimerSettings) -> ScratchTimerStatusReport:
    """Return the current recurring timer status for the current user."""
    username = Path.home().name
    timer_list_output = run_local_checked(
        ["systemctl", "--user", "list-timers", "--all", "--no-pager", settings.timer_name],
        label="systemctl list-timers hemma-scratch-maintenance",
    )
    return ScratchTimerStatusReport(
        checked_at=utc_now_iso(),
        service_name=settings.service_name,
        timer_name=settings.timer_name,
        unit_dir=settings.unit_dir.as_posix(),
        timer_enabled=_systemctl_user_bool(["is-enabled", settings.timer_name]),
        timer_active=_systemctl_user_bool(["is-active", settings.timer_name]),
        lingering_enabled=_user_linger_enabled(username),
        timer_list_output=timer_list_output,
    )


def render_timer_status_markdown(report: ScratchTimerStatusReport) -> str:
    """Render one concise markdown summary for the recurring timer status."""
    return "\n".join(
        [
            "# Hemma scratch maintenance Scratch Maintenance Timer Status",
            "",
            f"- checked_at: `{report.checked_at}`",
            f"- service_name: `{report.service_name}`",
            f"- timer_name: `{report.timer_name}`",
            f"- unit_dir: `{report.unit_dir}`",
            f"- timer_enabled: `{report.timer_enabled}`",
            f"- timer_active: `{report.timer_active}`",
            f"- lingering_enabled: `{report.lingering_enabled}`",
            "",
            "## systemctl --user list-timers",
            "",
            "```text",
            report.timer_list_output,
            "```",
        ]
    )
