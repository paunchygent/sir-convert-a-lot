"""Reporting helpers for the Hemma scratch-governance command surface.

Purpose:
    Keep the Task 204/205 CLI as a composition root by owning deterministic
    artifact writing, markdown rendering, and timer-settings normalization.

Relationships:
    - Used by `run_task204_hemma_scratch_policy.py`.
    - Renders reports for both `task204_hemma_scratch_policy_runtime.py` and
      the recurring Task 205 maintenance and timer flows.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task204_hemma_scratch_policy_runtime import (
    DEFAULT_REQUIRED_FREE_BYTES,
    DEFAULT_RUNS_ROOT,
    DEFAULT_SCRATCH_ROOT,
    DEFAULT_STORAGE_ARCHIVE_ROOT,
    DEFAULT_VERIFICATION_ROOT,
    ArchivedScratchPath,
    ScratchAuditReport,
    ScratchConsumer,
    ScratchRemediationReport,
)
from scripts.sir_convert_a_lot.devops.task205_hemma_scratch_maintenance_contracts import (
    DEFAULT_CANDIDATE_MIN_AGE_HOURS,
    DEFAULT_KEEP_MOST_RECENT,
    DEFAULT_MAINTENANCE_BLOCK_FILE,
    DEFAULT_SERVICE_NAME,
    DEFAULT_TARGET_FREE_BYTES,
    DEFAULT_TIMER_NAME,
    DEFAULT_TIMER_ON_BOOT_SEC,
    DEFAULT_TIMER_ON_UNIT_ACTIVE_SEC,
    MaintenanceCandidate,
    ScratchMaintenanceReport,
    ScratchTimerInstallReport,
    ScratchTimerSettings,
)


def prepare_output_root(output_root: Path) -> None:
    """Create one deterministic output root for scratch-policy artifacts."""
    output_root.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    """Write one JSON artifact with deterministic formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    """Write one markdown artifact with deterministic formatting."""
    enforce_generated_output_path(path, label=path.name)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def render_audit_markdown(report: ScratchAuditReport) -> str:
    """Render one concise Task 204 audit report."""
    lines = [
        "# Task 204 Hemma Scratch Audit",
        "",
        f"- checked_at: `{report.checked_at}`",
        f"- scratch_root: `{report.scratch_root}`",
        f"- storage_archive_root: `{report.storage_archive_root}`",
        f"- scratch_free_bytes: `{report.scratch_free_bytes}`",
        f"- required_free_bytes: `{report.required_free_bytes}`",
        f"- meets_required_headroom: `{report.meets_required_headroom}`",
        "",
        "## Docker Summary",
        "",
        "```text",
        report.docker_system_df,
        "```",
        "",
        "## Top-Level Scratch Consumers",
        "",
        *_render_consumers(report.top_level_consumers),
        "",
        "## Run Consumers",
        "",
        *_render_consumers(report.run_consumers),
        "",
        "## Verification Consumers",
        "",
        *_render_consumers(report.verification_consumers),
    ]
    return "\n".join(lines)


def render_remediation_markdown(report: ScratchRemediationReport) -> str:
    """Render one concise Task 204 remediation report."""
    lines = [
        "# Task 204 Hemma Scratch Remediation",
        "",
        f"- checked_at: `{report.checked_at}`",
        f"- scratch_root: `{report.scratch_root}`",
        f"- storage_archive_root: `{report.storage_archive_root}`",
        f"- scratch_free_bytes_before: `{report.scratch_free_bytes_before}`",
        f"- scratch_free_bytes_after: `{report.scratch_free_bytes_after}`",
        f"- required_free_bytes: `{report.required_free_bytes}`",
        f"- meets_required_headroom_after: `{report.meets_required_headroom_after}`",
        f"- pruned_docker_state: `{report.pruned_docker_state}`",
        "",
        "## Archived Paths",
        "",
        *_render_archived_paths(report.archived_paths),
        "",
        "## Docker Before",
        "",
        "```text",
        report.docker_system_df_before,
        "```",
        "",
        "## Docker After",
        "",
        "```text",
        report.docker_system_df_after,
        "```",
    ]
    return "\n".join(lines)


def render_maintenance_markdown(report: ScratchMaintenanceReport) -> str:
    """Render one concise Task 205 maintenance report."""
    payload = asdict(report)
    return "\n".join(
        [
            "# Task 205 Scratch Maintenance",
            "",
            f"- checked_at: `{payload['checked_at']}`",
            f"- status: `{payload['status']}`",
            f"- blocked_reason: `{payload['blocked_reason']}`",
            f"- block_file_present: `{payload['block_file_present']}`",
            f"- scratch_free_bytes_before: `{payload['scratch_free_bytes_before']}`",
            f"- scratch_free_bytes_after: `{payload['scratch_free_bytes_after']}`",
            f"- required_free_bytes: `{payload['required_free_bytes']}`",
            f"- target_free_bytes: `{payload['target_free_bytes']}`",
            f"- meets_target_after: `{payload['meets_target_after']}`",
            f"- pruned_docker_state: `{payload['pruned_docker_state']}`",
            "",
            "## Active Containers",
            "",
            *([f"- `{name}`" for name in payload["active_container_names"]] or ["- none"]),
            "",
            "## Selected Candidates",
            "",
            *_render_maintenance_candidates(report.selected_candidates),
            "",
            "## Archived Paths",
            "",
            *_render_archived_paths(report.archived_paths),
        ]
    )


def render_timer_install_markdown(report: ScratchTimerInstallReport) -> str:
    """Render one concise timer-install summary."""
    return "\n".join(
        [
            "# Task 205 Scratch Maintenance Timer Install",
            "",
            f"- installed_at: `{report.installed_at}`",
            f"- service_name: `{report.service_name}`",
            f"- timer_name: `{report.timer_name}`",
            f"- unit_dir: `{report.unit_dir}`",
            f"- service_path: `{report.service_path}`",
            f"- timer_path: `{report.timer_path}`",
            f"- lingering_enabled_before: `{report.lingering_enabled_before}`",
            f"- lingering_enabled_after: `{report.lingering_enabled_after}`",
            f"- timer_enabled: `{report.timer_enabled}`",
            f"- timer_active: `{report.timer_active}`",
        ]
    )


def build_timer_settings(args: argparse.Namespace) -> ScratchTimerSettings:
    """Build one normalized settings object for recurring timer operations."""
    return ScratchTimerSettings(
        repo_root=Path(getattr(args, "repo_root", Path.cwd())),
        output_root=Path(args.output_root),
        unit_dir=Path(getattr(args, "unit_dir", Path.home() / ".config/systemd/user")),
        service_name=str(getattr(args, "service_name", DEFAULT_SERVICE_NAME)),
        timer_name=str(getattr(args, "timer_name", DEFAULT_TIMER_NAME)),
        scratch_root=Path(getattr(args, "scratch_root", DEFAULT_SCRATCH_ROOT)),
        storage_archive_root=Path(
            getattr(args, "storage_archive_root", DEFAULT_STORAGE_ARCHIVE_ROOT)
        ),
        runs_root=Path(getattr(args, "runs_root", DEFAULT_RUNS_ROOT)),
        verification_root=Path(getattr(args, "verification_root", DEFAULT_VERIFICATION_ROOT)),
        block_file_path=Path(getattr(args, "block_file_path", DEFAULT_MAINTENANCE_BLOCK_FILE)),
        required_free_bytes=int(getattr(args, "required_free_bytes", DEFAULT_REQUIRED_FREE_BYTES)),
        target_free_bytes=int(getattr(args, "target_free_bytes", DEFAULT_TARGET_FREE_BYTES)),
        candidate_min_age_hours=float(
            getattr(args, "candidate_min_age_hours", DEFAULT_CANDIDATE_MIN_AGE_HOURS)
        ),
        keep_most_recent=int(getattr(args, "keep_most_recent", DEFAULT_KEEP_MOST_RECENT)),
        prune_docker_state=bool(getattr(args, "prune_docker_state", False)),
        timer_on_boot_sec=str(getattr(args, "timer_on_boot_sec", DEFAULT_TIMER_ON_BOOT_SEC)),
        timer_on_unit_active_sec=str(
            getattr(args, "timer_on_unit_active_sec", DEFAULT_TIMER_ON_UNIT_ACTIVE_SEC)
        ),
    )


def _render_consumers(consumers: list[ScratchConsumer]) -> list[str]:
    """Render size-ranked consumers as markdown bullet lines."""
    lines: list[str] = []
    for consumer in consumers:
        gib = consumer.size_bytes / 1024**3
        lines.append(f"- `{consumer.path}` ({gib:.1f} GiB)")
    return lines or ["- none"]


def _render_archived_paths(archived_paths: list[ArchivedScratchPath]) -> list[str]:
    """Render archived-path results as markdown bullet lines."""
    lines: list[str] = []
    for archived_path in archived_paths:
        gib = archived_path.size_bytes / 1024**3
        lines.append(
            f"- `{archived_path.source_path}` -> `{archived_path.archive_path}` ({gib:.1f} GiB)"
        )
    return lines or ["- none"]


def _render_maintenance_candidates(candidates: list[MaintenanceCandidate]) -> list[str]:
    """Render maintenance candidates as markdown bullet lines."""
    lines: list[str] = []
    for candidate in candidates:
        gib = candidate.size_bytes / 1024**3
        line = (
            f"- `{candidate.source_path}` -> `{candidate.archive_path}` "
            f"({gib:.1f} GiB, {candidate.age_hours:.1f}h)"
        )
        lines.append(line)
    return lines or ["- none"]
