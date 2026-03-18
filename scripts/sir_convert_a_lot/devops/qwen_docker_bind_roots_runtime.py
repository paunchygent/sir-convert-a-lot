"""Runtime helpers for the permanent Hemma Qwen Docker bind-root contract.

Purpose:
    Install and inspect the persistent system-level bind-root service that
    exposes scratch-backed Qwen build/cache paths through Docker-visible home
    paths on Hemma.

Relationships:
    - Used by `run_qwen_docker_bind_roots.py` for the public command surface.
    - Shares bind-root contracts with `ml.qwen.common.runtime` so active Qwen
      lanes can prefer the installed home mounts over ad hoc fallback mounts.
"""

from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from scripts.sir_convert_a_lot.devops.host_mounts import (
    ensure_directory,
    find_mount_source,
    run_optional,
    run_root_checked,
    write_root_owned_text,
)
from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_contracts import (
    QwenDockerBindProbeResult,
    QwenDockerBindRoot,
    QwenDockerBindRootsInstallReport,
    QwenDockerBindRootsProbeReport,
    QwenDockerBindRootsSettings,
    QwenDockerBindRootsStatusReport,
    QwenDockerBindRootState,
)


def utc_now_iso() -> str:
    """Return the current UTC timestamp in compact ISO-8601 format."""
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _systemctl_bool(command: list[str]) -> bool:
    """Return whether one system-level systemctl probe exits successfully."""
    returncode, _, _ = run_optional(["systemctl", *command])
    return returncode == 0


def _root_label_prefix(path: Path) -> str:
    """Render a short readable label prefix for one filesystem path."""
    return path.name if path.name != "" else path.as_posix()


def build_root_state(bind_root: QwenDockerBindRoot) -> QwenDockerBindRootState:
    """Build the observed mount state for one canonical/home bind-root pair."""
    mount_source = find_mount_source(bind_root.home_root)
    return QwenDockerBindRootState(
        label=bind_root.label,
        canonical_root=bind_root.canonical_root.as_posix(),
        home_root=bind_root.home_root.as_posix(),
        canonical_exists=bind_root.canonical_root.exists(),
        home_exists=bind_root.home_root.exists(),
        mount_source=mount_source,
        mounted_expected_source=_bind_root_roundtrip_matches(bind_root),
    )


def _bind_root_roundtrip_matches(bind_root: QwenDockerBindRoot) -> bool:
    """Return whether writes through the home root appear at the canonical root."""
    if not bind_root.home_root.exists() or not bind_root.canonical_root.exists():
        return False
    sentinel_name = f".qwen_bind_status_probe_{uuid4().hex}"
    home_probe = bind_root.home_root / sentinel_name
    canonical_probe = bind_root.canonical_root / sentinel_name
    try:
        home_probe.write_text("ok", encoding="utf-8")
        return canonical_probe.exists()
    except OSError:
        return False
    finally:
        home_probe.unlink(missing_ok=True)
        canonical_probe.unlink(missing_ok=True)


def render_service_unit(settings: QwenDockerBindRootsSettings) -> str:
    """Render the systemd service that keeps the home bind roots installed."""
    python_executable = shutil.which("python3") or "/usr/bin/python3"
    bind_root_args: list[str] = []
    for bind_root in settings.bind_roots:
        bind_root_args.extend(
            [
                "--bind-root",
                (
                    f"{bind_root.label}:{bind_root.canonical_root.as_posix()}:"
                    f"{bind_root.home_root.as_posix()}"
                ),
            ]
        )
    exec_start = " ".join(
        [
            python_executable,
            "-m",
            "scripts.sir_convert_a_lot.devops.run_qwen_docker_bind_roots",
            "repair",
            "--service-mode",
            "--repo-root",
            settings.repo_root.as_posix(),
            *bind_root_args,
        ]
    )
    exec_stop = " ".join(
        [
            python_executable,
            "-m",
            "scripts.sir_convert_a_lot.devops.run_qwen_docker_bind_roots",
            "teardown",
            "--service-mode",
            "--repo-root",
            settings.repo_root.as_posix(),
            *bind_root_args,
        ]
    )
    return "\n".join(
        [
            "[Unit]",
            "Description=Sir Convert-a-Lot persistent Qwen Docker bind roots",
            "After=local-fs.target",
            "Before=snap.docker.dockerd.service",
            "",
            "[Service]",
            "Type=oneshot",
            "RemainAfterExit=yes",
            f"WorkingDirectory={settings.repo_root.as_posix()}",
            f"ExecStart={exec_start}",
            f"ExecStop={exec_stop}",
            "TimeoutStartSec=120",
            "",
            "[Install]",
            "WantedBy=multi-user.target",
        ]
    )


def _ensure_bind_root(bind_root: QwenDockerBindRoot) -> None:
    """Ensure one canonical/home bind-root pair is installed live."""
    ensure_directory(bind_root.canonical_root, require_root=True)
    ensure_directory(bind_root.home_root, require_root=True)
    mount_source = find_mount_source(bind_root.home_root)
    expected_source = bind_root.canonical_root.as_posix()
    if mount_source == expected_source:
        return
    if mount_source is not None and mount_source != expected_source:
        raise SystemExit(
            f"Home bind root {bind_root.home_root} is already mounted from {mount_source}, "
            f"not {expected_source}."
        )
    run_root_checked(
        ["mount", "--bind", bind_root.canonical_root.as_posix(), bind_root.home_root.as_posix()],
        label=f"mount --bind {_root_label_prefix(bind_root.home_root)}",
    )


def _teardown_bind_root(bind_root: QwenDockerBindRoot) -> None:
    """Unmount one installed home bind-root when it is active."""
    if find_mount_source(bind_root.home_root) is None:
        return
    run_root_checked(
        ["umount", bind_root.home_root.as_posix()],
        label=f"umount {_root_label_prefix(bind_root.home_root)}",
    )


def repair_bind_roots(settings: QwenDockerBindRootsSettings) -> QwenDockerBindRootsStatusReport:
    """Install the live bind mounts without changing the systemd unit state."""
    for bind_root in settings.bind_roots:
        _ensure_bind_root(bind_root)
    return status_bind_roots(settings)


def teardown_bind_roots(settings: QwenDockerBindRootsSettings) -> QwenDockerBindRootsStatusReport:
    """Unmount the persistent bind roots without removing the unit file."""
    for bind_root in reversed(settings.bind_roots):
        _teardown_bind_root(bind_root)
    return status_bind_roots(settings)


def install_bind_root_service(
    settings: QwenDockerBindRootsSettings,
    *,
    enable_now: bool,
) -> QwenDockerBindRootsInstallReport:
    """Install or refresh the system-level bind-root service."""
    service_text = render_service_unit(settings) + "\n"
    write_root_owned_text(settings.service_path, text=service_text)
    run_root_checked(
        ["systemctl", "daemon-reload"], label="systemctl daemon-reload qwen bind roots"
    )
    if enable_now:
        run_root_checked(
            ["systemctl", "enable", "--now", settings.service_name],
            label="systemctl enable qwen bind roots",
        )
    status_report = status_bind_roots(settings)
    return QwenDockerBindRootsInstallReport(
        installed_at=utc_now_iso(),
        service_name=settings.service_name,
        service_path=settings.service_path.as_posix(),
        service_enabled=status_report.service_enabled,
        service_active=status_report.service_active,
        bind_roots=status_report.bind_roots,
    )


def status_bind_roots(settings: QwenDockerBindRootsSettings) -> QwenDockerBindRootsStatusReport:
    """Return the current service and bind-root status."""
    bind_root_states = tuple(build_root_state(bind_root) for bind_root in settings.bind_roots)
    return QwenDockerBindRootsStatusReport(
        checked_at=utc_now_iso(),
        service_name=settings.service_name,
        service_path=settings.service_path.as_posix(),
        service_unit_exists=settings.service_path.exists(),
        service_enabled=_systemctl_bool(["is-enabled", settings.service_name]),
        service_active=_systemctl_bool(["is-active", settings.service_name]),
        bind_roots=bind_root_states,
    )


def _probe_docker_bind_mount(bind_root_path: Path, *, image: str) -> bool:
    """Return whether Docker can bind-mount one host path and round-trip a probe file."""
    probe_command = [
        "sudo",
        "-n",
        "docker",
        "run",
        "--rm",
        "-v",
        f"{bind_root_path.as_posix()}:/cache-probe",
        "--entrypoint",
        "python",
        image,
        "-c",
        (
            "from pathlib import Path; "
            "probe = Path('/cache-probe/.qwen_bind_probe'); "
            "probe.write_text('ok', encoding='utf-8'); "
            "print(probe.read_text(encoding='utf-8')); "
            "probe.unlink()"
        ),
    ]
    returncode, _, _ = run_optional(probe_command)
    return returncode == 0


def probe_bind_roots(settings: QwenDockerBindRootsSettings) -> QwenDockerBindRootsProbeReport:
    """Run one Docker bind-mount probe against both canonical and home roots."""
    probe_results: list[QwenDockerBindProbeResult] = []
    for bind_root in settings.bind_roots:
        home_probe_ok = _probe_docker_bind_mount(bind_root.home_root, image=settings.probe_image)
        canonical_probe_ok = _probe_docker_bind_mount(
            bind_root.canonical_root,
            image=settings.probe_image,
        )
        preferred_effective_root = (
            bind_root.home_root.as_posix() if home_probe_ok else bind_root.canonical_root.as_posix()
        )
        probe_results.append(
            QwenDockerBindProbeResult(
                label=bind_root.label,
                canonical_root=bind_root.canonical_root.as_posix(),
                home_root=bind_root.home_root.as_posix(),
                canonical_probe_ok=canonical_probe_ok,
                home_probe_ok=home_probe_ok,
                preferred_effective_root=preferred_effective_root,
            )
        )
    return QwenDockerBindRootsProbeReport(
        checked_at=utc_now_iso(),
        service_name=settings.service_name,
        probe_image=settings.probe_image,
        probe_results=tuple(probe_results),
    )


def parse_bind_root(raw_value: str) -> QwenDockerBindRoot:
    """Parse one `label:canonical:home` bind-root argument."""
    pieces = raw_value.split(":")
    if len(pieces) != 3:
        raise SystemExit("Bind roots must be provided as `label:/canonical/path:/home/path`.")
    label, canonical_root, home_root = pieces
    if label.strip() == "":
        raise SystemExit("Bind-root labels must not be empty.")
    return QwenDockerBindRoot(
        label=label.strip(),
        canonical_root=Path(canonical_root),
        home_root=Path(home_root),
    )


def settings_with_bind_roots(
    settings: QwenDockerBindRootsSettings,
    *,
    bind_roots: tuple[QwenDockerBindRoot, ...] | None,
    repo_root: Path | None,
) -> QwenDockerBindRootsSettings:
    """Return settings updated by explicit CLI overrides."""
    effective_settings = settings
    if bind_roots is not None:
        effective_settings = replace(effective_settings, bind_roots=bind_roots)
    if repo_root is not None:
        effective_settings = replace(effective_settings, repo_root=repo_root)
    return effective_settings
