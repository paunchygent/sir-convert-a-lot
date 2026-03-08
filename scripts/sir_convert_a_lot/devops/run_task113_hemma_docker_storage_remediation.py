"""Run Task 113 Hemma Docker storage-root remediation.

Purpose:
    Provide the committed argv-friendly runner that migrates Docker's persistent
    daemon state off Hemma's root disk and onto SSD scratch through a
    home-visible bind mount compatible with the Docker snap.

Relationships:
    - Wraps `task113_hemma_docker_storage_runtime.py`.
    - Writes deterministic evidence under
      `build/verification/task-113-hemma-docker-storage-remediation/`.
    - Documents the verified host-wide Docker storage contract.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task113_hemma_docker_storage_runtime import (
    DEFAULT_FSTAB_PATH,
    DEFAULT_HOME_DOCKER_ROOT,
    DEFAULT_OLD_DOCKER_ROOT,
    DEFAULT_SCRATCH_DOCKER_ROOT,
    Task113DockerStorageSettings,
    run_task113_docker_storage_migration,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-113-hemma-docker-storage-remediation")


def _parse_args(argv: list[str] | None) -> tuple[Path, Task113DockerStorageSettings]:
    """Parse CLI arguments into one deterministic Task 113 settings object."""
    parser = argparse.ArgumentParser(
        description=(
            "Run Task 113 Hemma Docker storage-root remediation with deterministic evidence."
        )
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--old-docker-root", type=Path, default=DEFAULT_OLD_DOCKER_ROOT)
    parser.add_argument("--scratch-docker-root", type=Path, default=DEFAULT_SCRATCH_DOCKER_ROOT)
    parser.add_argument("--home-docker-root", type=Path, default=DEFAULT_HOME_DOCKER_ROOT)
    parser.add_argument("--fstab-path", type=Path, default=DEFAULT_FSTAB_PATH)
    parser.add_argument(
        "--keep-old-root",
        action="store_true",
        help="Keep the old Docker root after successful migration.",
    )
    args = parser.parse_args(argv)
    settings = Task113DockerStorageSettings(
        old_docker_root=Path(args.old_docker_root),
        scratch_docker_root=Path(args.scratch_docker_root),
        home_docker_root=Path(args.home_docker_root),
        fstab_path=Path(args.fstab_path),
        remove_old_root_after_success=not bool(args.keep_old_root),
    )
    return Path(args.output_root), settings


def _prepare_output_root(output_root: Path) -> tuple[Path, Path]:
    """Create the deterministic Task 113 report paths."""
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root / "report.json", output_root / "report.md"


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with stable formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_markdown(payload: dict[str, object]) -> str:
    """Render one concise Task 113 Markdown report."""
    return (
        "# Task 113 Hemma Docker Storage Remediation Report\n\n"
        f"- Old Docker root: `{payload['old_docker_root']}`\n"
        f"- Scratch Docker root: `{payload['scratch_docker_root']}`\n"
        f"- Home Docker root: `{payload['home_docker_root']}`\n"
        f"- Docker root before: `{payload['docker_root_before']}`\n"
        f"- Docker root after: `{payload['docker_root_after']}`\n"
        f"- Snap data-root before: `{payload['snap_data_root_before']}`\n"
        f"- Snap data-root after: `{payload['snap_data_root_after']}`\n"
        f"- Bind-mount source before: `{payload['bind_mount_source_before']}`\n"
        f"- Bind-mount source after: `{payload['bind_mount_source_after']}`\n"
        f"- Removed old root after success: `{payload['removed_old_root_after_success']}`\n\n"
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
    """Run Task 113 Docker storage remediation and write deterministic evidence."""
    output_root, settings = _parse_args(argv)
    report = run_task113_docker_storage_migration(settings)
    report_json_path, report_md_path = _prepare_output_root(output_root)
    payload = asdict(report)
    _write_json(report_json_path, payload)
    enforce_generated_output_path(report_md_path, label=report_md_path.name)
    report_md_path.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
