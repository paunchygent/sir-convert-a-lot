"""Run Hemma Docker storage-root remediation.

Purpose:
    Provide the committed argv-friendly runner that migrates Docker's bytes off
    Hemma's root disk by bind-mounting SSD scratch onto Docker's canonical snap
    root path.

Relationships:
    - Wraps `hemma_docker_storage_runtime.py`.
    - Writes deterministic evidence under
      `build/verification/hemma-docker-storage-remediation/`.
    - Documents the verified host-wide Docker storage contract.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.hemma_docker_storage_runtime import (
    DEFAULT_DOCKER_ROOT,
    DEFAULT_DOCKER_ROOT_BACKUP,
    DEFAULT_FSTAB_PATH,
    DEFAULT_LEGACY_HOME_DOCKER_ROOT,
    DEFAULT_SCRATCH_DOCKER_ROOT,
    HemmaDockerStorageSettings,
    run_docker_storage_migration,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/hemma-docker-storage-remediation")


def _parse_args(argv: list[str] | None) -> tuple[Path, HemmaDockerStorageSettings]:
    """Parse CLI arguments into one deterministic Hemma Docker storage settings object."""
    parser = argparse.ArgumentParser(
        description=("Run Hemma Docker storage-root remediation with deterministic evidence.")
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--docker-root", type=Path, default=DEFAULT_DOCKER_ROOT)
    parser.add_argument("--scratch-docker-root", type=Path, default=DEFAULT_SCRATCH_DOCKER_ROOT)
    parser.add_argument("--docker-root-backup", type=Path, default=DEFAULT_DOCKER_ROOT_BACKUP)
    parser.add_argument(
        "--legacy-home-docker-root",
        type=Path,
        default=DEFAULT_LEGACY_HOME_DOCKER_ROOT,
    )
    parser.add_argument("--fstab-path", type=Path, default=DEFAULT_FSTAB_PATH)
    parser.add_argument(
        "--keep-backup",
        action="store_true",
        help="Keep the old root backup after successful migration.",
    )
    args = parser.parse_args(argv)
    settings = HemmaDockerStorageSettings(
        docker_root=Path(args.docker_root),
        scratch_docker_root=Path(args.scratch_docker_root),
        docker_root_backup=Path(args.docker_root_backup),
        legacy_home_docker_root=Path(args.legacy_home_docker_root),
        fstab_path=Path(args.fstab_path),
        remove_backup_after_success=not bool(args.keep_backup),
    )
    return Path(args.output_root), settings


def _prepare_output_root(output_root: Path) -> tuple[Path, Path]:
    """Create the deterministic Hemma Docker storage remediation report paths."""
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / "report.json", output_root / "report.md"


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with stable formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_markdown(payload: dict[str, object]) -> str:
    """Render one concise Hemma Docker storage remediation Markdown report."""
    return (
        "# Hemma Docker Storage Remediation Report\n\n"
        f"- Docker root: `{payload['docker_root']}`\n"
        f"- Scratch Docker root: `{payload['scratch_docker_root']}`\n"
        f"- Docker root backup: `{payload['docker_root_backup']}`\n"
        f"- Legacy home Docker root: `{payload['legacy_home_docker_root']}`\n"
        f"- Docker root before: `{payload['docker_root_before']}`\n"
        f"- Docker root after: `{payload['docker_root_after']}`\n"
        f"- Docker root mount source before: `{payload['docker_root_mount_source_before']}`\n"
        f"- Docker root mount source after: `{payload['docker_root_mount_source_after']}`\n"
        f"- Legacy home mount source before: `{payload['legacy_home_mount_source_before']}`\n"
        f"- Legacy home mount source after: `{payload['legacy_home_mount_source_after']}`\n"
        f"- Snap data-root before: `{payload['snap_data_root_before']}`\n"
        f"- Snap data-root after: `{payload['snap_data_root_after']}`\n"
        f"- Removed backup after success: `{payload['removed_backup_after_success']}`\n\n"
        "## Filesystem Usage Before\n\n"
        "```text\n"
        f"{payload['filesystem_df_before']}\n"
        "```\n\n"
        "## Filesystem Usage After\n\n"
        "```text\n"
        f"{payload['filesystem_df_after']}\n"
        "```\n\n"
        "## Docker Containers Before\n\n"
        "```text\n"
        f"{payload['docker_ps_before']}\n"
        "```\n\n"
        "## Docker Containers After\n\n"
        "```text\n"
        f"{payload['docker_ps_after']}\n"
        "```\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Run Hemma Docker storage remediation Docker storage remediation and write deterministic
    evidence.
    """
    output_root, settings = _parse_args(argv)
    report = run_docker_storage_migration(settings)
    report_json_path, report_md_path = _prepare_output_root(output_root)
    payload = asdict(report)
    _write_json(report_json_path, payload)
    enforce_generated_output_path(report_md_path, label=report_md_path.name)
    report_md_path.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
