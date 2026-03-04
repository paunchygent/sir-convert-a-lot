"""CLI behavior tests for Sir Convert-a-Lot.

Purpose:
    Validate deterministic manifest output and batch outcomes for the unified
    v2-only CLI conversion path.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.cli_app` command behavior.
    - Stubs `scripts.sir_convert_a_lot.interfaces.cli_app.SirConvertALotClientV2`.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces import cli_app
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ArtifactOutcomeV2,
    ClientErrorV2,
)


class FakeV2Client:
    """Test double for SirConvertALotClientV2 used by CLI integration tests."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def __enter__(self) -> "FakeV2Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
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
            job_spec,
            idempotency_key,
            wait_seconds,
            max_poll_seconds,
            stall_timeout_seconds,
            retry_mode,
            correlation_id,
            resources_zip_bytes,
            reference_docx_bytes,
        )

        if source_path.stem.endswith("9") or source_path.stem.endswith("10"):
            raise ClientErrorV2(
                code="conversion_failed",
                message="simulated failure",
                retryable=False,
                status_code=500,
                job_id=f"job_fail_{source_path.stem}",
            )

        return ArtifactOutcomeV2(
            job_id=f"job_ok_{source_path.stem}",
            status=JobStatus.SUCCEEDED,
            artifact_bytes=f"# Converted {source_path.name}\n".encode("utf-8"),
        )


class FakeTimeoutV2Client(FakeV2Client):
    """Test double that simulates long-running background jobs."""

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
            job_spec,
            idempotency_key,
            wait_seconds,
            max_poll_seconds,
            stall_timeout_seconds,
            retry_mode,
            correlation_id,
            resources_zip_bytes,
            reference_docx_bytes,
        )
        if source_path.stem.endswith("slow"):
            raise ClientErrorV2(
                code="job_poll_window_exceeded",
                message="Timed out waiting for terminal state.",
                retryable=True,
                status_code=202,
                job_id=f"job_running_{source_path.stem}",
            )
        return ArtifactOutcomeV2(
            job_id=f"job_ok_{source_path.stem}",
            status=JobStatus.SUCCEEDED,
            artifact_bytes=f"# Converted {source_path.name}\n".encode("utf-8"),
        )


class CapturingV2Client(FakeV2Client):
    """Test double that captures submitted v2 job specifications."""

    captured_specs: list[dict[str, object]] = []
    captured_requests: list[dict[str, object]] = []

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
        self.captured_specs.append(job_spec)
        self.captured_requests.append(
            {
                "source_path": source_path,
                "idempotency_key": idempotency_key,
                "retry_mode": retry_mode,
                "correlation_id": correlation_id,
                "wait_seconds": wait_seconds,
                "max_poll_seconds": max_poll_seconds,
                "stall_timeout_seconds": stall_timeout_seconds,
                "resources_zip_bytes": resources_zip_bytes,
                "reference_docx_bytes": reference_docx_bytes,
            }
        )
        return ArtifactOutcomeV2(
            job_id=f"job_ok_{source_path.stem}",
            status=JobStatus.SUCCEEDED,
            artifact_bytes=f"# Converted {source_path.name}\n".encode("utf-8"),
        )


runner = CliRunner()


def test_convert_command_writes_deterministic_manifest_for_mixed_batch(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "pdfs"
    source_dir.mkdir(parents=True)
    for index in range(1, 11):
        (source_dir / f"paper_{index}.pdf").write_bytes(
            f"%PDF-1.4\n% {index}\n%%EOF\n".encode("utf-8")
        )

    output_dir = tmp_path / "research_markdown"
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--api-key",
            "dev-key",
            "--service-url",
            "http://127.0.0.1:18085",
            "--wait-seconds",
            "0",
        ],
    )

    assert result.exit_code == 1

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    assert manifest_path.exists()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert len(entries) == 10

    source_labels = [entry["source_file_path"] for entry in entries]
    assert source_labels == sorted(source_labels)

    success_count = sum(1 for entry in entries if entry["status"] == "succeeded")
    failure_count = sum(1 for entry in entries if entry["status"] == "failed")
    assert success_count == 8
    assert failure_count == 2
    assert {entry["source_format"] for entry in entries} == {"pdf"}
    assert {entry["target_format"] for entry in entries} == {"md"}
    assert {entry["pipeline_used"] for entry in entries} == {"service: pdf -> md (v2)"}

    assert (output_dir / "paper_1.md").exists()
    assert (output_dir / "paper_8.md").exists()
    assert not (output_dir / "paper_9.md").exists()
    assert not (output_dir / "paper_10.md").exists()


def test_convert_command_single_file_success(tmp_path: Path, monkeypatch) -> None:
    source_file = tmp_path / "single.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% single\n%%EOF\n")
    output_dir = tmp_path / "single_out"

    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "single.md").exists()

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["status"] == "succeeded"
    assert payload["entries"][0]["source_format"] == "pdf"
    assert payload["entries"][0]["target_format"] == "md"
    assert payload["entries"][0]["pipeline_used"] == "service: pdf -> md (v2)"


def test_convert_command_defaults_to_auto_retry_mode(tmp_path: Path, monkeypatch) -> None:
    CapturingV2Client.captured_specs = []
    CapturingV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", CapturingV2Client)

    source_file = tmp_path / "single.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% single\n%%EOF\n")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    assert CapturingV2Client.captured_requests[0]["retry_mode"] == "auto"


def test_convert_command_timeout_marks_job_running_without_cli_failure(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "pdfs"
    source_dir.mkdir(parents=True)
    (source_dir / "paper_fast.pdf").write_bytes(b"%PDF-1.4\n% fast\n%%EOF\n")
    (source_dir / "paper_slow.pdf").write_bytes(b"%PDF-1.4\n% slow\n%%EOF\n")
    output_dir = tmp_path / "out"

    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeTimeoutV2Client)

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--api-key",
            "dev-key",
            "--max-poll-seconds",
            "5",
        ],
    )

    assert result.exit_code == 0

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload["entries"]
    assert len(entries) == 2

    by_source = {entry["source_file_path"]: entry for entry in entries}
    assert by_source["paper_fast.pdf"]["status"] == "succeeded"
    assert by_source["paper_slow.pdf"]["status"] == "running"
    assert by_source["paper_slow.pdf"]["job_id"] == "job_running_paper_slow"
    assert by_source["paper_slow.pdf"]["output_path"] is None
    assert by_source["paper_slow.pdf"]["error_code"] == "job_poll_window_exceeded"
    assert by_source["paper_fast.pdf"]["source_format"] == "pdf"
    assert by_source["paper_fast.pdf"]["target_format"] == "md"
    assert by_source["paper_fast.pdf"]["pipeline_used"] == "service: pdf -> md (v2)"
    assert by_source["paper_slow.pdf"]["source_format"] == "pdf"
    assert by_source["paper_slow.pdf"]["target_format"] == "md"
    assert by_source["paper_slow.pdf"]["pipeline_used"] == "service: pdf -> md (v2)"


def test_convert_command_uses_hardened_defaults_for_job_spec(tmp_path: Path, monkeypatch) -> None:
    source_file = tmp_path / "default_spec.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% default-spec\n%%EOF\n")
    output_dir = tmp_path / "default_spec_out"

    CapturingV2Client.captured_specs = []
    CapturingV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", CapturingV2Client)

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    assert len(CapturingV2Client.captured_specs) == 1
    assert len(CapturingV2Client.captured_requests) == 1
    spec = CapturingV2Client.captured_specs[0]
    request = CapturingV2Client.captured_requests[0]
    conversion = spec["conversion"]
    execution = spec["execution"]
    pdf_options = spec["pdf_options"]
    assert isinstance(conversion, dict)
    assert isinstance(execution, dict)
    assert isinstance(pdf_options, dict)
    assert conversion["output_format"] == "md"
    assert pdf_options["backend_strategy"] == "auto"
    assert pdf_options["ocr_mode"] == "auto"
    assert pdf_options["table_mode"] == "accurate"
    assert pdf_options["normalize"] == "strict"
    assert execution["acceleration_policy"] == "gpu_required"
    idempotency_key = request["idempotency_key"]
    correlation_id = request["correlation_id"]
    assert isinstance(idempotency_key, str)
    assert isinstance(correlation_id, str)
    assert idempotency_key.startswith("idemv2_")
    assert correlation_id.startswith("corr_")
    assert request["resources_zip_bytes"] is None
    assert request["reference_docx_bytes"] is None


def test_convert_command_allows_explicit_job_spec_flags(tmp_path: Path, monkeypatch) -> None:
    source_file = tmp_path / "explicit_spec.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% explicit-spec\n%%EOF\n")
    output_dir = tmp_path / "explicit_spec_out"

    CapturingV2Client.captured_specs = []
    CapturingV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", CapturingV2Client)

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--api-key",
            "dev-key",
            "--backend-strategy",
            "pymupdf",
            "--ocr-mode",
            "off",
            "--table-mode",
            "fast",
            "--normalize",
            "standard",
            "--acceleration-policy",
            "cpu_only",
        ],
    )

    assert result.exit_code == 0
    assert len(CapturingV2Client.captured_specs) == 1
    spec = CapturingV2Client.captured_specs[0]
    execution = spec["execution"]
    pdf_options = spec["pdf_options"]
    assert isinstance(execution, dict)
    assert isinstance(pdf_options, dict)
    assert pdf_options["backend_strategy"] == "pymupdf"
    assert pdf_options["ocr_mode"] == "off"
    assert pdf_options["table_mode"] == "fast"
    assert pdf_options["normalize"] == "standard"
    assert execution["acceleration_policy"] == "cpu_only"
