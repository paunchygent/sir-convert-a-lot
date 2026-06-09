"""Public command surface for permanent Hemma Qwen Docker bind roots.

Purpose:
    Provide one committed CLI for installing, inspecting, probing, and repairing
    the persistent system-level bind roots that expose scratch-backed Qwen
    build/cache paths through Docker-visible home paths on Hemma.

Relationships:
    - Wraps `qwen_docker_bind_roots_runtime.py` for all host operations.
    - Emits deterministic evidence under `build/verification/...`
      when used in operator mode.
    - Can be invoked directly by the installed systemd service in service mode.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_contracts import (
    DEFAULT_OUTPUT_ROOT,
    default_settings,
)
from scripts.sir_convert_a_lot.devops.qwen_docker_bind_roots_runtime import (
    install_bind_root_service,
    parse_bind_root,
    probe_bind_roots,
    repair_bind_roots,
    settings_with_bind_roots,
    status_bind_roots,
    teardown_bind_roots,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the persistent Hemma bind-root surface."""
    parser = argparse.ArgumentParser(
        description="Install and inspect the persistent Hemma Qwen Docker bind roots."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_install_parser(subparsers)
    _add_status_parser(subparsers)
    _add_probe_parser(subparsers)
    _add_repair_parser(subparsers)
    _add_teardown_parser(subparsers)
    return parser


def _add_common_overrides(parser: argparse.ArgumentParser) -> None:
    """Register shared settings overrides for every command."""
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--bind-root",
        action="append",
        default=None,
        help="Override one bind root as label:/canonical/path:/home/path.",
    )


def _add_install_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the install command parser."""
    install = subparsers.add_parser(
        "install",
        help="Install or refresh the persistent system-level bind-root service.",
    )
    install.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    install.add_argument(
        "--no-enable-now",
        action="store_true",
        help="Write the unit file without enabling and starting the service.",
    )
    _add_common_overrides(install)


def _add_status_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the status command parser."""
    status = subparsers.add_parser("status", help="Inspect the persistent bind-root service.")
    status.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    _add_common_overrides(status)


def _add_probe_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the Docker probe command parser."""
    probe = subparsers.add_parser(
        "probe",
        help="Verify Docker can bind-mount the installed effective home roots.",
    )
    probe.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    probe.add_argument("--image", default=None, help="Override the Docker image used for probes.")
    _add_common_overrides(probe)


def _add_repair_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the live repair command parser."""
    repair = subparsers.add_parser(
        "repair",
        help="Install the live bind mounts without changing systemd enablement.",
    )
    repair.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    repair.add_argument("--service-mode", action="store_true")
    _add_common_overrides(repair)


def _add_teardown_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the teardown command parser."""
    teardown = subparsers.add_parser(
        "teardown",
        help="Unmount the live bind roots without removing the service unit.",
    )
    teardown.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    teardown.add_argument("--service-mode", action="store_true")
    _add_common_overrides(teardown)


def _prepare_output_root(output_root: Path) -> None:
    """Create one deterministic output tree for operator-facing commands."""
    output_root.mkdir(parents=True, exist_ok=True)


def _write_artifacts(
    output_root: Path, *, stem: str, payload: dict[str, object], markdown: str
) -> None:
    """Write one JSON/Markdown artifact pair for the current command."""
    _prepare_output_root(output_root)
    (output_root / f"{stem}.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_root / f"{stem}.md").write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _render_markdown(title: str, payload: dict[str, object]) -> str:
    """Render one small deterministic markdown report from a JSON-like payload."""
    return "\n".join(
        [
            f"# {title}",
            "",
            "```json",
            json.dumps(payload, indent=2, ensure_ascii=False),
            "```",
        ]
    )


def _effective_settings(args: argparse.Namespace):
    """Build the effective settings from defaults and explicit overrides."""
    settings = default_settings()
    bind_roots = None
    if args.bind_root is not None:
        bind_roots = tuple(parse_bind_root(raw_value) for raw_value in args.bind_root)
    effective_settings = settings_with_bind_roots(
        settings,
        bind_roots=bind_roots,
        repo_root=Path(args.repo_root) if args.repo_root is not None else None,
    )
    if getattr(args, "image", None) is not None:
        from dataclasses import replace

        effective_settings = replace(effective_settings, probe_image=str(args.image))
    return effective_settings


def main(argv: list[str] | None = None) -> int:
    """Run the committed persistent Hemma bind-root command surface."""
    args = build_parser().parse_args(argv)
    settings = _effective_settings(args)

    if args.command == "install":
        install_report = install_bind_root_service(
            settings,
            enable_now=not bool(args.no_enable_now),
        )
        payload = asdict(install_report)
        _write_artifacts(
            Path(args.output_root),
            stem="install",
            payload=payload,
            markdown=_render_markdown("Qwen Docker Bind Roots Install", payload),
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "status":
        status_report = status_bind_roots(settings)
        payload = asdict(status_report)
        _write_artifacts(
            Path(args.output_root),
            stem="status",
            payload=payload,
            markdown=_render_markdown("Qwen Docker Bind Roots Status", payload),
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "probe":
        probe_report = probe_bind_roots(settings)
        payload = asdict(probe_report)
        _write_artifacts(
            Path(args.output_root),
            stem="probe",
            payload=payload,
            markdown=_render_markdown("Qwen Docker Bind Roots Probe", payload),
        )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "repair":
        repair_report = repair_bind_roots(settings)
        payload = asdict(repair_report)
        if not bool(args.service_mode):
            _write_artifacts(
                Path(args.output_root),
                stem="repair",
                payload=payload,
                markdown=_render_markdown("Qwen Docker Bind Roots Repair", payload),
            )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if args.command == "teardown":
        teardown_report = teardown_bind_roots(settings)
        payload = asdict(teardown_report)
        if not bool(args.service_mode):
            _write_artifacts(
                Path(args.output_root),
                stem="teardown",
                payload=payload,
                markdown=_render_markdown("Qwen Docker Bind Roots Teardown", payload),
            )
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
