"""CLI manifest construction and persistence for service API v2 conversions.

Purpose:
    Build deterministic `convert-a-lot` manifest entries and write the batch
    manifest separately from Typer command definitions and route submission.

Relationships:
    - Used by `interfaces.cli_route_submission_v2` for per-file entries.
    - Used by `interfaces.cli_app` to persist the final manifest after a batch.
    - Emits `application.contracts.CliManifest` as the stable public schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.application.contracts import CliManifest, CliManifestEntry
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.cli_routes import CliRoute


@dataclass(frozen=True)
class CliManifestWriteResultV2:
    """Result of writing a deterministic CLI manifest file."""

    manifest_path: Path
    manifest: CliManifest


def build_success_manifest_entry_v2(
    *,
    source_file_path: str,
    route: CliRoute,
    pipeline_used: str,
    job_id: str,
    output_path: Path,
) -> CliManifestEntry:
    """Return one deterministic succeeded conversion manifest entry."""
    return CliManifestEntry(
        source_file_path=source_file_path,
        source_format=route.source.value,
        target_format=route.target.value,
        pipeline_used=pipeline_used,
        job_id=job_id,
        status=JobStatus.SUCCEEDED,
        output_path=output_path.as_posix(),
        error_code=None,
    )


def build_running_manifest_entry_v2(
    *,
    source_file_path: str,
    route: CliRoute,
    pipeline_used: str,
    job_id: str,
    error_code: str,
) -> CliManifestEntry:
    """Return one deterministic running conversion manifest entry."""
    return CliManifestEntry(
        source_file_path=source_file_path,
        source_format=route.source.value,
        target_format=route.target.value,
        pipeline_used=pipeline_used,
        job_id=job_id,
        status=JobStatus.RUNNING,
        output_path=None,
        error_code=error_code,
    )


def build_failed_manifest_entry_v2(
    *,
    source_file_path: str,
    route: CliRoute,
    pipeline_used: str,
    job_id: str | None,
    error_code: str,
) -> CliManifestEntry:
    """Return one deterministic failed conversion manifest entry."""
    return CliManifestEntry(
        source_file_path=source_file_path,
        source_format=route.source.value,
        target_format=route.target.value,
        pipeline_used=pipeline_used,
        job_id=job_id,
        status=JobStatus.FAILED,
        output_path=None,
        error_code=error_code,
    )


def write_cli_manifest_v2(
    *,
    source: Path,
    output_dir: Path,
    manifest_name: str,
    entries: list[CliManifestEntry],
) -> CliManifestWriteResultV2:
    """Write a sorted deterministic CLI manifest and return its path."""
    sorted_entries = sorted(entries, key=lambda entry: entry.source_file_path)
    manifest = CliManifest(
        generated_at=datetime.now(UTC),
        source_root=source.as_posix(),
        output_root=output_dir.as_posix(),
        entries=sorted_entries,
    )
    manifest_path = output_dir / manifest_name
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return CliManifestWriteResultV2(manifest_path=manifest_path, manifest=manifest)
