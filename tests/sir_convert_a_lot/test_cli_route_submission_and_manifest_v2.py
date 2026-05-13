"""Focused tests for CLI route submission and manifest helpers.

Purpose:
    Prove extracted CLI service-route submission and manifest writing preserve
    deterministic fields outside the Typer command body.

Relationships:
    - Tests `interfaces.cli_route_submission_v2`.
    - Tests `interfaces.cli_manifest_writer_v2`.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import TracebackType

from scripts.sir_convert_a_lot.application.contracts import CliManifestEntry
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.cli_manifest_writer_v2 import write_cli_manifest_v2
from scripts.sir_convert_a_lot.interfaces.cli_route_submission_v2 import (
    CliRouteSubmissionOptionsV2,
    submit_service_route_batch_v2,
)
from scripts.sir_convert_a_lot.interfaces.cli_routes import (
    SourceFormat,
    TargetFormat,
    resolve_route,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import ArtifactOutcomeV2


class _FakeClient:
    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.submitted_specs: list[dict[str, object]] = []

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        del exc_type, exc, traceback
        return None

    def convert_upload_to_artifact(
        self,
        *,
        source_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        max_poll_seconds: float,
        stall_timeout_seconds: float = 120.0,
        retry_mode: str = "auto",
        correlation_id: str | None = None,
        resources_zip_bytes: bytes | None = None,
        reference_docx_bytes: bytes | None = None,
    ) -> ArtifactOutcomeV2:
        del (
            idempotency_key,
            wait_seconds,
            max_poll_seconds,
            stall_timeout_seconds,
            retry_mode,
            correlation_id,
            resources_zip_bytes,
            reference_docx_bytes,
        )
        self.submitted_specs.append(job_spec)
        return ArtifactOutcomeV2(
            job_id=f"job_ok_{source_path.stem}",
            status=JobStatus.SUCCEEDED,
            artifact_bytes=b"%PDF-1.4\nfake\n",
        )


def test_cli_route_submission_builds_success_entry_and_artifact(tmp_path: Path) -> None:
    source_file = tmp_path / "note.md"
    source_file.write_text("# Note\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    route = resolve_route(source=SourceFormat.MD, target=TargetFormat.PDF)
    assert route is not None
    messages: list[str] = []

    result = submit_service_route_batch_v2(
        options=CliRouteSubmissionOptionsV2(
            source=source_file,
            output_dir=output_dir,
            route=route,
            source_files=(source_file,),
            service_url="http://127.0.0.1:28085",
            api_key="dev-key",
            wait_seconds=0,
            max_poll_seconds=5,
            stall_timeout_seconds=30,
            retry_mode="auto",
            css_paths=(),
            resources=None,
            reference_docx=None,
            acceleration_policy="gpu_required",
            backend_strategy="auto",
            ocr_mode="auto",
            ocr_engine="auto",
            ocr_languages=(),
            table_mode="accurate",
            normalize="strict",
        ),
        client_factory=_FakeClient,
        message_sink=messages.append,
    )

    assert result.has_failures is False
    assert len(result.entries) == 1
    assert result.entries[0].source_file_path == "note.md"
    assert result.entries[0].target_format == "pdf"
    assert result.entries[0].pipeline_used == "service: md -> pdf (v2)"
    assert result.entries[0].output_path == (output_dir / "note.pdf").as_posix()
    assert (output_dir / "note.pdf").read_bytes().startswith(b"%PDF")
    assert messages == [f"✓ Converted note.md -> {output_dir / 'note.pdf'}"]


def test_cli_manifest_writer_sorts_entries_by_source_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    entries = [
        CliManifestEntry(
            source_file_path="b.md",
            source_format="md",
            target_format="pdf",
            pipeline_used="service: md -> pdf (v2)",
            job_id="job_b",
            status=JobStatus.SUCCEEDED,
            output_path=(output_dir / "b.pdf").as_posix(),
            error_code=None,
        ),
        CliManifestEntry(
            source_file_path="a.md",
            source_format="md",
            target_format="pdf",
            pipeline_used="service: md -> pdf (v2)",
            job_id="job_a",
            status=JobStatus.FAILED,
            output_path=None,
            error_code="conversion_failed",
        ),
    ]

    result = write_cli_manifest_v2(
        source=tmp_path,
        output_dir=output_dir,
        manifest_name="manifest.json",
        entries=entries,
    )

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert [entry["source_file_path"] for entry in payload["entries"]] == ["a.md", "b.md"]
    assert payload["entries"][0]["error_code"] == "conversion_failed"
