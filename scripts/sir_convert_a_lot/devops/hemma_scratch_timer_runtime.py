"""Systemd timer runtime for recurring Hemma scratch maintenance.

Purpose:
    Install, render, and inspect the lightweight user-level systemd timer that
    drives recurring idle-safe scratch maintenance on Hemma.

Relationships:
    - Used by `run_hemma_scratch_policy.py` for timer commands.
    - Used by `hemma_scratch_maintenance_runtime.py` for shared host
      command execution and active-container detection.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_contracts import (
    ScratchTimerInstallReport,
    ScratchTimerSettings,
    ScratchTimerStatusReport,
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


def render_service_unit(settings: ScratchTimerSettings) -> str:
    """Render the user-level systemd service unit for recurring maintenance."""
    pdm_path = shutil.which("pdm") or str(Path.home() / ".local/bin/pdm")
    exec_parts = [
        pdm_path,
        "run",
        "qwen-scratch-policy",
        "maintain",
        "--output-root",
        settings.output_root.as_posix(),
        "--scratch-root",
        settings.scratch_root.as_posix(),
        "--storage-archive-root",
        settings.storage_archive_root.as_posix(),
        "--runs-root",
        settings.runs_root.as_posix(),
        "--verification-root",
        settings.verification_root.as_posix(),
        "--block-file-path",
        settings.block_file_path.as_posix(),
        "--required-free-bytes",
        str(settings.required_free_bytes),
        "--target-free-bytes",
        str(settings.target_free_bytes),
        "--candidate-min-age-hours",
        str(settings.candidate_min_age_hours),
        "--keep-most-recent",
        str(settings.keep_most_recent),
    ]
    if settings.prune_docker_state:
        exec_parts.append("--prune-docker-state")
    return "\n".join(
        [
            "[Unit]",
            "Description=Sir Convert-a-Lot Qwen scratch maintenance",
            "After=default.target",
            "",
            "[Service]",
            "Type=oneshot",
            f"WorkingDirectory={settings.repo_root.as_posix()}",
            f"ExecStart={' '.join(exec_parts)}",
            "",
            "[Install]",
            "WantedBy=default.target",
        ]
    )


def render_timer_unit(settings: ScratchTimerSettings) -> str:
    """Render the user-level systemd timer unit for recurring maintenance."""
    return "\n".join(
        [
            "[Unit]",
            "Description=Run Sir Convert-a-Lot Qwen scratch maintenance on a light schedule",
            "",
            "[Timer]",
            f"OnBootSec={settings.timer_on_boot_sec}",
            f"OnUnitActiveSec={settings.timer_on_unit_active_sec}",
            "Persistent=true",
            f"Unit={settings.service_name}",
            "",
            "[Install]",
            "WantedBy=timers.target",
        ]
    )


def install_scratch_timer(
    settings: ScratchTimerSettings,
    *,
    enable_linger: bool,
) -> ScratchTimerInstallReport:
    """Install or refresh the recurring user-level systemd timer."""
    username = Path.home().name
    lingering_before = _user_linger_enabled(username)
    settings.unit_dir.mkdir(parents=True, exist_ok=True)
    service_path = settings.unit_dir / settings.service_name
    timer_path = settings.unit_dir / settings.timer_name
    service_path.write_text(render_service_unit(settings) + "\n", encoding="utf-8")
    timer_path.write_text(render_timer_unit(settings) + "\n", encoding="utf-8")
    if enable_linger and not lingering_before:
        run_local_checked(
            ["sudo", "-n", "loginctl", "enable-linger", username],
            label="enable linger hemma-scratch-maintenance",
        )
    run_local_checked(
        ["systemctl", "--user", "daemon-reload"],
        label="systemctl daemon-reload hemma-scratch-maintenance",
    )
    run_local_checked(
        ["systemctl", "--user", "enable", "--now", settings.timer_name],
        label="systemctl enable timer hemma-scratch-maintenance",
    )
    lingering_after = _user_linger_enabled(username)
    return ScratchTimerInstallReport(
        installed_at=utc_now_iso(),
        service_name=settings.service_name,
        timer_name=settings.timer_name,
        unit_dir=settings.unit_dir.as_posix(),
        service_path=service_path.as_posix(),
        timer_path=timer_path.as_posix(),
        lingering_enabled_before=lingering_before,
        lingering_enabled_after=lingering_after,
        timer_enabled=_systemctl_user_bool(["is-enabled", settings.timer_name]),
        timer_active=_systemctl_user_bool(["is-active", settings.timer_name]),
    )


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
