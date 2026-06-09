"""Run the committed Hemma scratch-governance command surface.

Purpose:
    Provide one deterministic CLI for Hemma scratch audit scratch auditing/remediation and
    Hemma scratch maintenance recurring maintenance/timer operations.

Relationships:
    - Wraps `hemma_scratch_policy_runtime.py` for audit/remediation.
    - Wraps `hemma_scratch_maintenance_runtime.py` for idle-safe
      recurring maintenance.
    - Wraps `hemma_scratch_timer_runtime.py` for timer installation and
      status inspection.
    - Writes deterministic evidence under `build/verification/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_contracts import (
    DEFAULT_CANDIDATE_MIN_AGE_HOURS,
    DEFAULT_KEEP_MOST_RECENT,
    DEFAULT_MAINTENANCE_BLOCK_FILE,
    DEFAULT_SERVICE_NAME,
    DEFAULT_TARGET_FREE_BYTES,
    DEFAULT_TIMER_NAME,
    DEFAULT_TIMER_ON_BOOT_SEC,
    DEFAULT_TIMER_ON_UNIT_ACTIVE_SEC,
    DEFAULT_TIMER_OUTPUT_ROOT,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_runtime import (
    run_scratch_maintenance,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_policy_reporting import (
    build_timer_settings,
    prepare_output_root,
    render_audit_markdown,
    render_maintenance_markdown,
    render_remediation_markdown,
    render_timer_install_markdown,
    write_json,
    write_markdown,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_policy_runtime import (
    DEFAULT_AUDIT_MIN_BYTES,
    DEFAULT_REQUIRED_FREE_BYTES,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SCRATCH_ROOT,
    DEFAULT_STORAGE_ARCHIVE_ROOT,
    DEFAULT_TOP_COUNT,
    DEFAULT_VERIFICATION_ROOT,
    build_scratch_audit_report,
    run_scratch_remediation,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_timer_runtime import (
    install_scratch_timer,
    render_service_unit,
    render_timer_status_markdown,
    render_timer_unit,
    status_scratch_timer,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/hemma-scratch-policy-hemma-scratch-policy")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for scratch-governance operations."""
    parser = argparse.ArgumentParser(
        description="Audit and remediate recurring Hemma scratch pressure for Qwen workloads."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_audit_parser(subparsers)
    _add_remediation_parser(subparsers)
    _add_maintenance_parser(subparsers)
    _add_install_timer_parser(subparsers)
    _add_status_timer_parser(subparsers)
    return parser


def _add_audit_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the scratch-audit command parser."""
    audit = subparsers.add_parser("audit", help="Write one deterministic scratch audit report.")
    audit.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    audit.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH_ROOT)
    audit.add_argument("--storage-archive-root", type=Path, default=DEFAULT_STORAGE_ARCHIVE_ROOT)
    audit.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    audit.add_argument("--verification-root", type=Path, default=DEFAULT_VERIFICATION_ROOT)
    audit.add_argument("--min-bytes", type=int, default=DEFAULT_AUDIT_MIN_BYTES)
    audit.add_argument("--required-free-bytes", type=int, default=DEFAULT_REQUIRED_FREE_BYTES)
    audit.add_argument("--top-count", type=int, default=DEFAULT_TOP_COUNT)


def _add_remediation_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the explicit remediation command parser."""
    remediate = subparsers.add_parser(
        "remediate",
        help="Archive explicit scratch paths and optionally prune non-active Docker state.",
    )
    remediate.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    remediate.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH_ROOT)
    remediate.add_argument(
        "--storage-archive-root",
        type=Path,
        default=DEFAULT_STORAGE_ARCHIVE_ROOT,
    )
    remediate.add_argument(
        "--required-free-bytes",
        type=int,
        default=DEFAULT_REQUIRED_FREE_BYTES,
    )
    remediate.add_argument(
        "--source-path",
        type=Path,
        action="append",
        default=[],
        help="Absolute scratch path to archive onto storage while keeping a symlink back.",
    )
    remediate.add_argument(
        "--prune-docker-state",
        action="store_true",
        help="Prune non-active Docker containers/images/volumes/builder cache after archiving.",
    )


def _add_maintenance_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the recurring maintenance command parser."""
    maintain = subparsers.add_parser(
        "maintain",
        help="Run one idle-safe recurring maintenance pass for cold artifact archival.",
    )
    maintain.add_argument("--output-root", type=Path, default=DEFAULT_TIMER_OUTPUT_ROOT)
    maintain.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH_ROOT)
    maintain.add_argument("--storage-archive-root", type=Path, default=DEFAULT_STORAGE_ARCHIVE_ROOT)
    maintain.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    maintain.add_argument("--verification-root", type=Path, default=DEFAULT_VERIFICATION_ROOT)
    maintain.add_argument("--block-file-path", type=Path, default=DEFAULT_MAINTENANCE_BLOCK_FILE)
    maintain.add_argument("--required-free-bytes", type=int, default=DEFAULT_REQUIRED_FREE_BYTES)
    maintain.add_argument("--target-free-bytes", type=int, default=DEFAULT_TARGET_FREE_BYTES)
    maintain.add_argument(
        "--candidate-min-age-hours",
        type=float,
        default=DEFAULT_CANDIDATE_MIN_AGE_HOURS,
    )
    maintain.add_argument("--keep-most-recent", type=int, default=DEFAULT_KEEP_MOST_RECENT)
    maintain.add_argument(
        "--prune-docker-state",
        action="store_true",
        help="Prune non-active Docker state if the target headroom is still not met.",
    )


def _add_install_timer_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the timer-install command parser."""
    install_timer = subparsers.add_parser(
        "install-timer",
        help="Install or refresh the lightweight user-level systemd timer.",
    )
    install_timer.add_argument("--output-root", type=Path, default=DEFAULT_TIMER_OUTPUT_ROOT)
    install_timer.add_argument("--repo-root", type=Path, default=Path.cwd())
    install_timer.add_argument(
        "--unit-dir", type=Path, default=Path.home() / ".config/systemd/user"
    )
    install_timer.add_argument("--service-name", default=DEFAULT_SERVICE_NAME)
    install_timer.add_argument("--timer-name", default=DEFAULT_TIMER_NAME)
    install_timer.add_argument("--scratch-root", type=Path, default=DEFAULT_SCRATCH_ROOT)
    install_timer.add_argument(
        "--storage-archive-root", type=Path, default=DEFAULT_STORAGE_ARCHIVE_ROOT
    )
    install_timer.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    install_timer.add_argument("--verification-root", type=Path, default=DEFAULT_VERIFICATION_ROOT)
    install_timer.add_argument(
        "--block-file-path", type=Path, default=DEFAULT_MAINTENANCE_BLOCK_FILE
    )
    install_timer.add_argument(
        "--required-free-bytes", type=int, default=DEFAULT_REQUIRED_FREE_BYTES
    )
    install_timer.add_argument("--target-free-bytes", type=int, default=DEFAULT_TARGET_FREE_BYTES)
    install_timer.add_argument(
        "--candidate-min-age-hours",
        type=float,
        default=DEFAULT_CANDIDATE_MIN_AGE_HOURS,
    )
    install_timer.add_argument("--keep-most-recent", type=int, default=DEFAULT_KEEP_MOST_RECENT)
    install_timer.add_argument(
        "--prune-docker-state",
        action="store_true",
        help="Allow the timer maintenance pass to prune non-active Docker state when needed.",
    )
    install_timer.add_argument("--timer-on-boot-sec", default=DEFAULT_TIMER_ON_BOOT_SEC)
    install_timer.add_argument(
        "--timer-on-unit-active-sec",
        default=DEFAULT_TIMER_ON_UNIT_ACTIVE_SEC,
    )
    install_timer.add_argument(
        "--enable-linger",
        action="store_true",
        help="Enable user lingering so the timer survives without an active login session.",
    )


def _add_status_timer_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the timer-status command parser."""
    status_timer = subparsers.add_parser(
        "status-timer",
        help="Inspect the installed user-level scratch-maintenance timer.",
    )
    status_timer.add_argument("--output-root", type=Path, default=DEFAULT_TIMER_OUTPUT_ROOT)
    status_timer.add_argument("--unit-dir", type=Path, default=Path.home() / ".config/systemd/user")
    status_timer.add_argument("--service-name", default=DEFAULT_SERVICE_NAME)
    status_timer.add_argument("--timer-name", default=DEFAULT_TIMER_NAME)


def main(argv: list[str] | None = None) -> int:
    """Run the committed Hemma scratch-governance command surface."""
    args = build_parser().parse_args(argv)
    output_root = Path(args.output_root)
    prepare_output_root(output_root)

    if args.command == "audit":
        return _run_audit(args=args, output_root=output_root)
    if args.command == "remediate":
        return _run_remediation(args=args, output_root=output_root)
    if args.command == "maintain":
        return _run_maintenance(args=args, output_root=output_root)
    if args.command == "install-timer":
        return _run_install_timer(args=args, output_root=output_root)
    if args.command == "status-timer":
        return _run_status_timer(args=args, output_root=output_root)
    raise SystemExit(f"Unsupported command: {args.command}")


def _run_audit(*, args: argparse.Namespace, output_root: Path) -> int:
    """Execute the scratch-audit flow and persist deterministic artifacts."""
    report = build_scratch_audit_report(
        scratch_root=Path(args.scratch_root),
        storage_archive_root=Path(args.storage_archive_root),
        runs_root=Path(args.runs_root),
        verification_root=Path(args.verification_root),
        min_bytes=int(args.min_bytes),
        required_free_bytes=int(args.required_free_bytes),
        top_count=int(args.top_count),
    )
    payload = asdict(report)
    write_json(output_root / "audit.json", payload)
    write_markdown(output_root / "audit.md", render_audit_markdown(report))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_remediation(*, args: argparse.Namespace, output_root: Path) -> int:
    """Execute the explicit scratch-remediation flow."""
    report = run_scratch_remediation(
        source_paths=[Path(path) for path in args.source_path],
        scratch_root=Path(args.scratch_root),
        storage_archive_root=Path(args.storage_archive_root),
        required_free_bytes=int(args.required_free_bytes),
        prune_docker_state=bool(args.prune_docker_state),
    )
    payload = asdict(report)
    write_json(output_root / "remediate.json", payload)
    write_markdown(output_root / "remediate.md", render_remediation_markdown(report))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_maintenance(*, args: argparse.Namespace, output_root: Path) -> int:
    """Execute one recurring idle-safe maintenance pass."""
    report = run_scratch_maintenance(
        scratch_root=Path(args.scratch_root),
        storage_archive_root=Path(args.storage_archive_root),
        runs_root=Path(args.runs_root),
        verification_root=Path(args.verification_root),
        block_file_path=Path(args.block_file_path),
        required_free_bytes=int(args.required_free_bytes),
        target_free_bytes=int(args.target_free_bytes),
        candidate_min_age_hours=float(args.candidate_min_age_hours),
        keep_most_recent=int(args.keep_most_recent),
        prune_docker_state=bool(args.prune_docker_state),
    )
    payload = asdict(report)
    write_json(output_root / "maintain.json", payload)
    write_markdown(output_root / "maintain.md", render_maintenance_markdown(report))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_install_timer(*, args: argparse.Namespace, output_root: Path) -> int:
    """Install or refresh the recurring user-level timer."""
    settings = build_timer_settings(args)
    report = install_scratch_timer(settings, enable_linger=bool(args.enable_linger))
    payload = asdict(report)
    write_json(output_root / "install-timer.json", payload)
    write_markdown(output_root / "install-timer.md", render_timer_install_markdown(report))
    write_markdown(output_root / "service.unit", render_service_unit(settings))
    write_markdown(output_root / "timer.unit", render_timer_unit(settings))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _run_status_timer(*, args: argparse.Namespace, output_root: Path) -> int:
    """Inspect the recurring user-level timer."""
    settings = build_timer_settings(args)
    report = status_scratch_timer(settings)
    payload = asdict(report)
    write_json(output_root / "timer-status.json", payload)
    write_markdown(output_root / "timer-status.md", render_timer_status_markdown(report))
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
