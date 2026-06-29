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
    CliRoute,
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
        progress_callback=None,
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
        if progress_callback is not None:
            progress_callback(
                {
                    "job": {
                        "job_id": f"job_ok_{source_path.stem}",
                        "status": "queued",
                        "idempotent_replay": False,
                    }
                }
            )
            progress_callback(
                {
                    "job": {
                        "job_id": f"job_ok_{source_path.stem}",
                        "status": "running",
                        "progress": {
                            "stage": "converting",
                            "processed_pages": 1,
                            "total_pages": 4,
                            "percent_complete": 25.0,
                            "eta_seconds": 45,
                        },
                    }
                }
            )
        self.submitted_specs.append(job_spec)
        return ArtifactOutcomeV2(
            job_id=f"job_ok_{source_path.stem}",
            status=JobStatus.SUCCEEDED,
            artifact_bytes=b"%PDF-1.4\nfake\n",
            formula_authority={
                "action": "accepted",
                "representation": "generated_markdown",
                "source_evidence_state": "absent",
                "reason": "generated_formula_output_allowed",
            },
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
    assert result.entries[0].formula_authority == {
        "action": "accepted",
        "representation": "generated_markdown",
        "source_evidence_state": "absent",
        "reason": "generated_formula_output_allowed",
    }
    assert (output_dir / "note.pdf").read_bytes().startswith(b"%PDF")
    assert messages == [
        "... Submitted note.md: job_ok_note (queued)",
        "... Running note.md, converting, 1/4 pages (25.0%), eta 45s, job_ok_note",
        f"✓ Converted note.md -> {output_dir / 'note.pdf'}",
    ]


def test_cli_route_submission_writes_manifest_when_job_id_is_observed(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "long.md"
    source_file.write_text("# Long\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    route = resolve_route(source=SourceFormat.MD, target=TargetFormat.PDF)
    assert route is not None
    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"

    class _ManifestCheckingClient(_FakeClient):
        def convert_upload_to_artifact(self, **kwargs) -> ArtifactOutcomeV2:
            progress_callback = kwargs["progress_callback"]
            assert progress_callback is not None
            progress_callback(
                {
                    "job": {
                        "job_id": "job_running_long",
                        "status": "running",
                        "progress": {
                            "stage": "converting",
                            "processed_pages": 3,
                            "total_pages": 9,
                            "percent_complete": 33.3,
                        },
                    }
                }
            )
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert payload["entries"] == [
                {
                    "error_code": "job_running",
                    "formula_authority": {},
                    "idempotency": {},
                    "job_id": "job_running_long",
                    "output_path": None,
                    "pipeline_used": "service: md -> pdf (v2)",
                    "source_file_path": "long.md",
                    "source_format": "md",
                    "status": "running",
                    "target_format": "pdf",
                }
            ]
            return ArtifactOutcomeV2(
                job_id="job_running_long",
                status=JobStatus.SUCCEEDED,
                artifact_bytes=b"%PDF-1.4\nfake\n",
            )

    result = submit_service_route_batch_v2(
        options=_submission_options_for_md_pdf(
            source_file=source_file,
            output_dir=output_dir,
            route=route,
        ),
        client_factory=_ManifestCheckingClient,
        message_sink=lambda message: None,
    )

    assert result.has_failures is False
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["entries"][0]["status"] == "succeeded"
    assert payload["entries"][0]["job_id"] == "job_running_long"
    assert payload["entries"][0]["output_path"] == (output_dir / "long.pdf").as_posix()


def test_audio_route_submission_records_service_reattempt_metadata_without_extra_submit(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "lesson.m4a"
    source_file.write_bytes(b"fake-audio")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    route = resolve_route(source=SourceFormat.AUDIO, target=TargetFormat.TRANSCRIPT_BUNDLE)
    assert route is not None
    messages: list[str] = []
    idempotency_keys: list[str] = []
    submitted_specs: list[dict[str, object]] = []

    class _AudioReattemptClient(_FakeClient):
        def convert_upload_to_artifact(self, **kwargs) -> ArtifactOutcomeV2:
            idempotency_key = kwargs["idempotency_key"]
            job_spec = kwargs["job_spec"]
            assert isinstance(idempotency_key, str)
            assert isinstance(job_spec, dict)
            idempotency_keys.append(idempotency_key)
            submitted_specs.append(job_spec)
            return ArtifactOutcomeV2(
                job_id="job_audio_reattempt",
                status=JobStatus.SUCCEEDED,
                artifact_bytes=b'{"schema_version":"transcript_json_v1"}',
                idempotency={
                    "state": "service_reattempt",
                    "idempotent_replay": False,
                    "active_job_id": "job_audio_reattempt",
                    "attempt_count": 2,
                    "previous_attempts": [
                        {
                            "job_id": "job_audio_failed",
                            "status": "failed",
                            "failure_retryable": True,
                        }
                    ],
                    "reattempt_of_job_id": "job_audio_failed",
                },
            )

    result = submit_service_route_batch_v2(
        options=CliRouteSubmissionOptionsV2(
            source=source_file,
            output_dir=output_dir,
            route=route,
            source_files=(source_file,),
            service_url="https://convert.hule.education",
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
        client_factory=_AudioReattemptClient,
        message_sink=messages.append,
    )

    assert result.has_failures is False
    assert len(result.entries) == 1
    assert len(idempotency_keys) == 1
    assert idempotency_keys[0].startswith("idemv2_")
    assert len(submitted_specs) == 1
    spec = submitted_specs[0]
    assert spec["source"] == {"kind": "upload", "filename": "lesson.m4a", "format": "audio"}
    conversion_obj = spec["conversion"]
    audio_options_obj = spec["audio_transcription_options"]
    assert isinstance(conversion_obj, dict)
    assert isinstance(audio_options_obj, dict)
    assert conversion_obj["output_format"] == "transcript_bundle"
    assert audio_options_obj["output_artifacts"] == ["json"]
    entry = result.entries[0]
    assert entry.source_format == "audio"
    assert entry.target_format == "transcript_bundle"
    assert entry.job_id == "job_audio_reattempt"
    assert entry.output_path == (output_dir / "lesson.transcript.json").as_posix()
    assert entry.idempotency["state"] == "service_reattempt"
    assert entry.idempotency["reattempt_of_job_id"] == "job_audio_failed"
    assert (output_dir / "lesson.transcript.json").read_bytes() == (
        b'{"schema_version":"transcript_json_v1"}'
    )
    assert messages == [
        f"✓ Converted lesson.m4a -> {output_dir / 'lesson.transcript.json'}",
    ]


def test_cli_route_submission_preserves_running_manifest_on_interrupt(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "interrupted.md"
    source_file.write_text("# Interrupted\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    route = resolve_route(source=SourceFormat.MD, target=TargetFormat.PDF)
    assert route is not None
    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"

    class _InterruptingClient(_FakeClient):
        def convert_upload_to_artifact(self, **kwargs) -> ArtifactOutcomeV2:
            progress_callback = kwargs["progress_callback"]
            assert progress_callback is not None
            progress_callback(
                {
                    "job": {
                        "job_id": "job_interrupted",
                        "status": "running",
                        "progress": {"stage": "converting"},
                    }
                }
            )
            raise KeyboardInterrupt

    try:
        submit_service_route_batch_v2(
            options=_submission_options_for_md_pdf(
                source_file=source_file,
                output_dir=output_dir,
                route=route,
            ),
            client_factory=_InterruptingClient,
            message_sink=lambda message: None,
        )
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("expected KeyboardInterrupt")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["entries"] == [
        {
            "error_code": "client_interrupted",
            "formula_authority": {},
            "idempotency": {},
            "job_id": "job_interrupted",
            "output_path": None,
            "pipeline_used": "service: md -> pdf (v2)",
            "source_file_path": "interrupted.md",
            "source_format": "md",
            "status": "running",
            "target_format": "pdf",
        }
    ]


def test_cli_route_submission_emits_replayed_running_job_message(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "replay.md"
    source_file.write_text("# Replay\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    route = resolve_route(source=SourceFormat.MD, target=TargetFormat.PDF)
    assert route is not None
    messages: list[str] = []

    class _ReplayClient(_FakeClient):
        def convert_upload_to_artifact(self, **kwargs) -> ArtifactOutcomeV2:
            progress_callback = kwargs["progress_callback"]
            assert progress_callback is not None
            progress_callback(
                {
                    "job": {
                        "job_id": "job_existing_replay",
                        "status": "running",
                        "idempotent_replay": True,
                    }
                }
            )
            return ArtifactOutcomeV2(
                job_id="job_existing_replay",
                status=JobStatus.SUCCEEDED,
                artifact_bytes=b"%PDF-1.4\nfake\n",
            )

    submit_service_route_batch_v2(
        options=_submission_options_for_md_pdf(
            source_file=source_file,
            output_dir=output_dir,
            route=route,
        ),
        client_factory=_ReplayClient,
        message_sink=messages.append,
    )

    assert messages == [
        "... Reusing existing job for replay.md: job_existing_replay (running)",
        f"✓ Converted replay.md -> {output_dir / 'replay.pdf'}",
    ]


def test_cli_route_submission_emits_fresh_running_job_message(
    tmp_path: Path,
) -> None:
    source_file = tmp_path / "fresh-running.md"
    source_file.write_text("# Fresh running\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    route = resolve_route(source=SourceFormat.MD, target=TargetFormat.PDF)
    assert route is not None
    messages: list[str] = []

    class _FreshRunningClient(_FakeClient):
        def convert_upload_to_artifact(self, **kwargs) -> ArtifactOutcomeV2:
            progress_callback = kwargs["progress_callback"]
            assert progress_callback is not None
            progress_callback(
                {
                    "job": {
                        "job_id": "job_fresh_running",
                        "status": "running",
                        "idempotent_replay": False,
                    }
                }
            )
            return ArtifactOutcomeV2(
                job_id="job_fresh_running",
                status=JobStatus.SUCCEEDED,
                artifact_bytes=b"%PDF-1.4\nfake\n",
            )

    submit_service_route_batch_v2(
        options=_submission_options_for_md_pdf(
            source_file=source_file,
            output_dir=output_dir,
            route=route,
        ),
        client_factory=_FreshRunningClient,
        message_sink=messages.append,
    )

    assert messages == [
        "... Submitted fresh-running.md: job_fresh_running (running)",
        f"✓ Converted fresh-running.md -> {output_dir / 'fresh-running.pdf'}",
    ]


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
            formula_authority={
                "action": "skipped",
                "source_evidence_state": "usable",
                "reason": "source_layer_authoritative_formula_vlm_skipped",
            },
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
    assert payload["entries"][1]["formula_authority"] == {
        "action": "skipped",
        "source_evidence_state": "usable",
        "reason": "source_layer_authoritative_formula_vlm_skipped",
    }


def _submission_options_for_md_pdf(
    *,
    source_file: Path,
    output_dir: Path,
    route: CliRoute,
) -> CliRouteSubmissionOptionsV2:
    return CliRouteSubmissionOptionsV2(
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
    )
