"""Incremental CLI manifest recording for service API v2 conversions.

Purpose:
    Persist known service-backed CLI job state as soon as the v2 client observes
    job identifiers, so long-running or interrupted conversions leave a durable
    recovery trail before terminal artifact download.

Relationships:
    - Used by `interfaces.cli_route_submission_v2` during per-file submission.
    - Reuses `interfaces.cli_manifest_writer_v2` for the stable public manifest
      schema and atomic persistence behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from scripts.sir_convert_a_lot.application.contracts import CliManifestEntry
from scripts.sir_convert_a_lot.domain.specs import TERMINAL_JOB_STATUSES, JobStatus
from scripts.sir_convert_a_lot.interfaces.cli_manifest_writer_v2 import (
    build_nonterminal_manifest_entry_v2,
    write_cli_manifest_v2,
)
from scripts.sir_convert_a_lot.interfaces.cli_routes import CliRoute


@dataclass
class CliIncrementalManifestRecorderV2:
    """Maintain and persist the current v2 CLI batch manifest entries."""

    source: Path
    output_dir: Path
    manifest_name: str
    _entries_by_source: dict[str, CliManifestEntry] = field(default_factory=dict)

    def upsert_entry(self, entry: CliManifestEntry) -> None:
        """Persist one manifest entry, replacing prior state for the same source."""
        self._entries_by_source[entry.source_file_path] = entry
        self._write()

    def record_progress_payload(
        self,
        *,
        relative_label: str,
        route: CliRoute,
        pipeline_used: str,
        payload: dict[str, object],
    ) -> None:
        """Persist non-terminal job state from one client progress payload."""
        entry = _entry_from_progress_payload_v2(
            relative_label=relative_label,
            route=route,
            pipeline_used=pipeline_used,
            payload=payload,
        )
        if entry is not None:
            self.upsert_entry(entry)

    def mark_interrupted(
        self,
        *,
        relative_label: str,
        route: CliRoute,
        pipeline_used: str,
    ) -> None:
        """Persist an interrupt marker for the known job, if one was observed."""
        existing_entry = self._entries_by_source.get(relative_label)
        if existing_entry is None or existing_entry.job_id is None:
            return
        status = existing_entry.status
        if status in TERMINAL_JOB_STATUSES:
            return
        self.upsert_entry(
            build_nonterminal_manifest_entry_v2(
                source_file_path=relative_label,
                route=route,
                pipeline_used=pipeline_used,
                job_id=existing_entry.job_id,
                status=status,
                error_code="client_interrupted",
            )
        )

    def _write(self) -> None:
        entries = list(self._entries_by_source.values())
        write_cli_manifest_v2(
            source=self.source,
            output_dir=self.output_dir,
            manifest_name=self.manifest_name,
            entries=entries,
        )


def _entry_from_progress_payload_v2(
    *,
    relative_label: str,
    route: CliRoute,
    pipeline_used: str,
    payload: dict[str, object],
) -> CliManifestEntry | None:
    job_obj = payload.get("job")
    if not isinstance(job_obj, dict):
        return None

    job_id_obj = job_obj.get("job_id")
    status_obj = job_obj.get("status")
    if not isinstance(job_id_obj, str) or not isinstance(status_obj, str):
        return None

    try:
        status = JobStatus(status_obj)
    except ValueError:
        return None
    if status in TERMINAL_JOB_STATUSES:
        return None

    return build_nonterminal_manifest_entry_v2(
        source_file_path=relative_label,
        route=route,
        pipeline_used=pipeline_used,
        job_id=job_id_obj,
        status=status,
        error_code=f"job_{status.value}",
    )
