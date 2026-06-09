"""Run the committed Hemma storage remediation surface.

Purpose:
    Provide one deterministic CLI entrypoint for moving hot Qwen build output
    onto SSD scratch, moving raw Qwen corpus data onto HDD bulk storage, and
    reclaiming root-disk space from non-active Docker state.

Relationships:
    - Wraps `hemma_storage_runtime.py`.
    - Writes deterministic evidence under
      `build/verification/hemma-storage-remediation/`.
    - Documents the verified storage contract that later DevOps runbooks and
      skills should follow across repos.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.hemma_storage_runtime import (
    DEFAULT_NEW_QWEN_DATA_ROOT,
    DEFAULT_OLD_QWEN_DATA_ROOT,
    DEFAULT_REPO_BUILD_ROOT,
    DEFAULT_REPO_ROOT,
    DEFAULT_SCRATCH_BUILD_ROOT,
    HemmaStorageSettings,
    run_storage_remediation,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/hemma-storage-remediation")


def _parse_args(argv: list[str] | None) -> tuple[Path, HemmaStorageSettings]:
    """Parse CLI arguments into one deterministic Hemma storage remediation settings object."""
    parser = argparse.ArgumentParser(
        description="Run Hemma storage remediation with deterministic evidence."
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument("--repo-build-root", type=Path, default=DEFAULT_REPO_BUILD_ROOT)
    parser.add_argument("--scratch-build-root", type=Path, default=DEFAULT_SCRATCH_BUILD_ROOT)
    parser.add_argument("--old-qwen-data-root", type=Path, default=DEFAULT_OLD_QWEN_DATA_ROOT)
    parser.add_argument("--new-qwen-data-root", type=Path, default=DEFAULT_NEW_QWEN_DATA_ROOT)
    parser.add_argument(
        "--skip-build-migration",
        action="store_true",
        help="Skip moving repo build output onto scratch.",
    )
    parser.add_argument(
        "--skip-data-migration",
        action="store_true",
        help="Skip moving raw Qwen corpus data onto storage.",
    )
    parser.add_argument(
        "--skip-docker-cleanup",
        action="store_true",
        help="Skip pruning non-active Docker state.",
    )
    args = parser.parse_args(argv)
    settings = HemmaStorageSettings(
        repo_root=Path(args.repo_root),
        repo_build_root=Path(args.repo_build_root),
        scratch_build_root=Path(args.scratch_build_root),
        old_qwen_data_root=Path(args.old_qwen_data_root),
        new_qwen_data_root=Path(args.new_qwen_data_root),
        migrate_repo_build=not bool(args.skip_build_migration),
        migrate_qwen_data=not bool(args.skip_data_migration),
        cleanup_docker_state=not bool(args.skip_docker_cleanup),
    )
    return Path(args.output_root), settings


def _prepare_output_root(output_root: Path) -> tuple[Path, Path]:
    """Create the deterministic Hemma storage remediation report paths."""
    output_root.mkdir(parents=True, exist_ok=True)
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    return report_json_path, report_md_path


def _write_json(path: Path, payload: object) -> None:
    """Write one JSON payload with stable formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _render_markdown(payload: dict[str, object]) -> str:
    """Render one concise Hemma storage remediation Markdown report."""
    return (
        "# Hemma Storage Remediation Report\n\n"
        f"- Repo build root: `{payload['repo_build_root']}`\n"
        f"- Repo build is symlink: `{payload['repo_build_is_symlink']}`\n"
        f"- Repo build target: `{payload['repo_build_target']}`\n"
        f"- Scratch build root: `{payload['scratch_build_root']}`\n"
        f"- Old Qwen data root: `{payload['old_qwen_data_root']}`\n"
        f"- Old Qwen data is symlink: `{payload['old_qwen_data_is_symlink']}`\n"
        f"- Old Qwen data target: `{payload['old_qwen_data_target']}`\n"
        f"- New Qwen data root: `{payload['new_qwen_data_root']}`\n"
        f"- Migrated repo build: `{payload['migrated_repo_build']}`\n"
        f"- Migrated Qwen data: `{payload['migrated_qwen_data']}`\n"
        f"- Cleaned Docker state: `{payload['cleaned_docker_state']}`\n\n"
        "## Docker Usage Before\n\n"
        "```text\n"
        f"{payload['docker_system_df_before']}\n"
        "```\n\n"
        "## Docker Usage After\n\n"
        "```text\n"
        f"{payload['docker_system_df_after']}\n"
        "```\n\n"
        "## Filesystem Usage Before\n\n"
        "```text\n"
        f"{payload['filesystem_df_before']}\n"
        "```\n\n"
        "## Filesystem Usage After\n\n"
        "```text\n"
        f"{payload['filesystem_df_after']}\n"
        "```\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Run Hemma storage remediation storage remediation and write deterministic evidence."""
    output_root, settings = _parse_args(argv)
    report = run_storage_remediation(settings)
    report_json_path, report_md_path = _prepare_output_root(output_root)
    payload = asdict(report)
    _write_json(report_json_path, payload)
    enforce_generated_output_path(report_md_path, label=report_md_path.name)
    report_md_path.write_text(_render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
