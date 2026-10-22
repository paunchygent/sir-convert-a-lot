"""Reporting helpers for the Hemma scratch-governance command surface.

Purpose:
    Keep the Hemma scratch audit/205 CLI as a composition root by owning deterministic
    artifact writing, markdown rendering, and timer-settings normalization.

Relationships:
    - Used by `run_hemma_scratch_policy.py`.
    - Renders reports for both `hemma_scratch_policy_runtime.py` and
      the recurring Hemma scratch maintenance maintenance and timer flows.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.hemma_scratch_maintenance_contracts import (
    MaintenanceCandidate,
    ScratchMaintenanceReport,
    ScratchTimerSettings,
    ScratchTimerUninstallReport,
)
from scripts.sir_convert_a_lot.devops.hemma_scratch_policy_runtime import (
    ArchivedScratchPath,
    ScratchAuditReport,
    ScratchConsumer,
    ScratchRemediationReport,
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
    """Render one concise Hemma scratch audit audit report."""
    lines = [
        "# Hemma Scratch Audit",
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
    """Render one concise Hemma scratch audit remediation report."""
    lines = [
        "# Hemma Scratch Remediation",
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
    """Render one concise Hemma scratch maintenance maintenance report."""
    payload = asdict(report)
    return "\n".join(
        [
            "# Hemma scratch maintenance Scratch Maintenance",
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


def render_timer_uninstall_markdown(report: ScratchTimerUninstallReport) -> str:
    """Render one concise retired-timer uninstall summary."""
    return "\n".join(
        [
            "# Hemma scratch maintenance Retired Timer Uninstall",
            "",
            f"- uninstalled_at: `{report.uninstalled_at}`",
            f"- service_name: `{report.service_name}`",
            f"- timer_name: `{report.timer_name}`",
            f"- unit_dir: `{report.unit_dir}`",
            f"- timer_enabled_after: `{report.timer_enabled_after}`",
            f"- timer_active_after: `{report.timer_active_after}`",
            f"- service_active_after: `{report.service_active_after}`",
            "",
            "## Removed unit files",
            "",
            *([f"- `{path}`" for path in report.removed_paths] or ["- none"]),
        ]
    )


def build_timer_settings(args: argparse.Namespace) -> ScratchTimerSettings:
    """Build one normalized settings object for retired-timer operations."""
    return ScratchTimerSettings(
        unit_dir=Path(args.unit_dir),
        service_name=str(args.service_name),
        timer_name=str(args.timer_name),
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
