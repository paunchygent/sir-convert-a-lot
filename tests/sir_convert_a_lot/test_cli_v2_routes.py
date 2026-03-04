"""CLI v2 route tests for Sir Convert-a-Lot.

Purpose:
    Validate that multi-format conversion routes are executed via the service
    API v2 client (submit/poll/download) and that manifests remain deterministic
    without requiring local Pandoc/WeasyPrint binaries.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.interfaces.cli_app` through the
      canonical Typer surface `scripts.sir_convert_a_lot.interfaces.cli_app`.
    - Stubs `scripts.sir_convert_a_lot.interfaces.cli_app.SirConvertALotClientV2`.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces import cli_app
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import ArtifactOutcomeV2, ClientErrorV2

runner = CliRunner()


class FakeV2Client:
    """Test double for SirConvertALotClientV2 used by CLI route tests."""

    captured_requests: list[dict[str, object]] = []

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def __enter__(self) -> "FakeV2Client":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
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
        del wait_seconds, max_poll_seconds, stall_timeout_seconds

        if source_path.stem.endswith("slow"):
            raise ClientErrorV2(
                code="job_poll_window_exceeded",
                message="Timed out waiting for terminal state.",
                retryable=True,
                status_code=202,
                job_id=f"job_running_{source_path.stem}",
            )

        self.captured_requests.append(
            {
                "source_path": source_path,
                "job_spec": job_spec,
                "idempotency_key": idempotency_key,
                "retry_mode": retry_mode,
                "correlation_id": correlation_id,
                "resources_zip_bytes": resources_zip_bytes,
                "reference_docx_bytes": reference_docx_bytes,
            }
        )

        conversion_obj = job_spec.get("conversion")
        output_format_obj = (
            conversion_obj.get("output_format") if isinstance(conversion_obj, dict) else None
        )
        output_format = output_format_obj if isinstance(output_format_obj, str) else ""
        if output_format == "pdf":
            artifact_prefix = b"%PDF-1.4\n"
        elif output_format == "md":
            artifact_prefix = b"# "
        else:
            artifact_prefix = b"PK"
        return ArtifactOutcomeV2(
            job_id=f"job_ok_{source_path.stem}",
            status=JobStatus.SUCCEEDED,
            artifact_bytes=artifact_prefix + b"fake-artifact",
        )


def test_html_to_pdf_route_submits_v2_job_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    FakeV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_file = tmp_path / "doc.html"
    source_file.write_text(
        "<!doctype html><html><head><meta charset='utf-8'></head>"
        "<body><h1>Hello</h1><p>World</p></body></html>\n",
        encoding="utf-8",
    )
    css_file = tmp_path / "style.css"
    css_file.write_text("body { font-family: serif; }\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "pdf",
            "--css",
            str(css_file),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    output_pdf = output_dir / "doc.pdf"
    assert output_pdf.exists()
    assert output_pdf.read_bytes().startswith(b"%PDF")

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["entries"][0]["job_id"] == "job_ok_doc"
    assert payload["entries"][0]["status"] == "succeeded"
    assert payload["entries"][0]["output_path"] == str(output_pdf)
    assert payload["entries"][0]["source_format"] == "html"
    assert payload["entries"][0]["target_format"] == "pdf"
    assert payload["entries"][0]["pipeline_used"] == "service: html -> pdf (v2)"

    assert len(FakeV2Client.captured_requests) == 1
    captured = FakeV2Client.captured_requests[0]
    spec = captured["job_spec"]
    assert isinstance(spec, dict)
    assert spec["api_version"] == "v2"
    assert spec["source"]["format"] == "html"
    assert spec["conversion"]["output_format"] == "pdf"
    assert spec["conversion"]["css_filenames"] == ["style.css"]
    assert captured["reference_docx_bytes"] is None
    captured_idempotency = captured["idempotency_key"]
    captured_correlation = captured["correlation_id"]
    assert isinstance(captured_idempotency, str)
    assert isinstance(captured_correlation, str)
    assert captured_idempotency.startswith("idemv2_")
    assert captured_correlation.startswith("corr_")
    assert captured["retry_mode"] == "auto"

    resources_zip_bytes = captured["resources_zip_bytes"]
    assert isinstance(resources_zip_bytes, (bytes, bytearray))
    with zipfile.ZipFile(io.BytesIO(resources_zip_bytes)) as zip_handle:
        assert "style.css" in zip_handle.namelist()


def test_md_to_docx_route_forwards_reference_docx_to_v2(tmp_path: Path, monkeypatch) -> None:
    FakeV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_file = tmp_path / "note.md"
    source_file.write_text("# Title\n\nHello.\n", encoding="utf-8")
    reference_docx = tmp_path / "reference.docx"
    reference_docx_bytes = b"fake-docx"
    reference_docx.write_bytes(reference_docx_bytes)
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "docx",
            "--reference-docx",
            str(reference_docx),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    output_docx = output_dir / "note.docx"
    assert output_docx.exists()
    assert output_docx.stat().st_size > 0

    assert len(FakeV2Client.captured_requests) == 1
    captured = FakeV2Client.captured_requests[0]
    spec = captured["job_spec"]
    assert isinstance(spec, dict)
    assert spec["api_version"] == "v2"
    assert spec["source"]["format"] == "md"
    assert spec["conversion"]["output_format"] == "docx"
    assert spec["conversion"]["reference_docx_filename"] == "reference.docx"
    assert captured["reference_docx_bytes"] == reference_docx_bytes
    assert captured["resources_zip_bytes"] is None
    assert captured["retry_mode"] == "auto"


def test_pdf_to_docx_route_timeout_marks_job_running_without_docx(
    tmp_path: Path, monkeypatch
) -> None:
    FakeV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_dir = tmp_path / "pdfs"
    source_dir.mkdir(parents=True)
    (source_dir / "paper_fast.pdf").write_bytes(b"%PDF-1.4\n% fast\n%%EOF\n")
    (source_dir / "paper_slow.pdf").write_bytes(b"%PDF-1.4\n% slow\n%%EOF\n")

    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_dir),
            "--output-dir",
            str(output_dir),
            "--to",
            "docx",
            "--api-key",
            "dev-key",
            "--max-poll-seconds",
            "5",
        ],
    )

    assert result.exit_code == 0

    assert (output_dir / "paper_fast.docx").exists()
    assert not (output_dir / "paper_slow.docx").exists()
    assert not (output_dir / "_intermediates").exists()

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload["entries"]
    by_source = {entry["source_file_path"]: entry for entry in entries}

    assert by_source["paper_fast.pdf"]["status"] == "succeeded"
    assert by_source["paper_slow.pdf"]["status"] == "running"
    assert by_source["paper_slow.pdf"]["job_id"] == "job_running_paper_slow"
    assert by_source["paper_slow.pdf"]["output_path"] is None
    assert by_source["paper_slow.pdf"]["error_code"] == "job_poll_window_exceeded"
    assert by_source["paper_fast.pdf"]["source_format"] == "pdf"
    assert by_source["paper_fast.pdf"]["target_format"] == "docx"
    assert by_source["paper_fast.pdf"]["pipeline_used"] == "service: pdf -> docx (v2)"
    assert by_source["paper_slow.pdf"]["source_format"] == "pdf"
    assert by_source["paper_slow.pdf"]["target_format"] == "docx"
    assert by_source["paper_slow.pdf"]["pipeline_used"] == "service: pdf -> docx (v2)"


def test_html_to_md_route_submits_v2_job_with_resources(tmp_path: Path, monkeypatch) -> None:
    FakeV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_file = tmp_path / "page.html"
    source_file.write_text(
        "<html><body><img src='assets/logo.png'></body></html>",
        encoding="utf-8",
    )
    resources_dir = tmp_path / "resources"
    assets_dir = resources_dir / "assets"
    assets_dir.mkdir(parents=True)
    (assets_dir / "logo.png").write_bytes(b"\x89PNG\r\n")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
            "--resources",
            str(resources_dir),
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    output_md = output_dir / "page.md"
    assert output_md.exists()
    assert output_md.read_bytes().startswith(b"# ")

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["entries"][0]["source_format"] == "html"
    assert payload["entries"][0]["target_format"] == "md"
    assert payload["entries"][0]["pipeline_used"] == "service: html -> md (v2)"

    assert len(FakeV2Client.captured_requests) == 1
    captured = FakeV2Client.captured_requests[0]
    spec = captured["job_spec"]
    assert isinstance(spec, dict)
    assert spec["source"]["format"] == "html"
    assert spec["conversion"]["output_format"] == "md"
    resources_zip_bytes = captured["resources_zip_bytes"]
    assert isinstance(resources_zip_bytes, (bytes, bytearray))
    with zipfile.ZipFile(io.BytesIO(resources_zip_bytes)) as zip_handle:
        assert "assets/logo.png" in zip_handle.namelist()
    assert captured["retry_mode"] == "auto"


def test_docx_to_md_route_submits_v2_job_and_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    FakeV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_file = tmp_path / "template.docx"
    source_file.write_bytes(b"PK\x03\x04fake-docx")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "md",
            "--api-key",
            "dev-key",
        ],
    )

    assert result.exit_code == 0
    output_md = output_dir / "template.md"
    assert output_md.exists()
    assert output_md.read_bytes().startswith(b"# ")

    manifest_path = output_dir / "sir_convert_a_lot_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["entries"][0]["source_format"] == "docx"
    assert payload["entries"][0]["target_format"] == "md"
    assert payload["entries"][0]["pipeline_used"] == "service: docx -> md (v2)"

    assert len(FakeV2Client.captured_requests) == 1
    captured = FakeV2Client.captured_requests[0]
    spec = captured["job_spec"]
    assert isinstance(spec, dict)
    assert spec["source"]["format"] == "docx"
    assert spec["conversion"]["output_format"] == "md"
    assert captured["retry_mode"] == "auto"


def test_cli_retry_mode_flags_are_mutually_exclusive(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_file = tmp_path / "note.md"
    source_file.write_text("# Title\n\nHello.\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "pdf",
            "--api-key",
            "dev-key",
            "--replay-only",
            "--new-job",
        ],
    )

    assert result.exit_code != 0
    assert "--replay-only and --new-job are mutually exclusive" in result.output


def test_cli_retry_mode_flags_map_to_client_retry_mode(tmp_path: Path, monkeypatch) -> None:
    FakeV2Client.captured_requests = []
    monkeypatch.setattr(cli_app, "SirConvertALotClientV2", FakeV2Client)

    source_file = tmp_path / "note.md"
    source_file.write_text("# Title\n\nHello.\n", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "pdf",
            "--api-key",
            "dev-key",
            "--replay-only",
        ],
    )
    assert result.exit_code == 0
    assert FakeV2Client.captured_requests[0]["retry_mode"] == "replay_only"

    FakeV2Client.captured_requests = []
    result = runner.invoke(
        cli_app.app,
        [
            "convert",
            str(source_file),
            "--output-dir",
            str(output_dir),
            "--to",
            "pdf",
            "--api-key",
            "dev-key",
            "--new-job",
        ],
    )
    assert result.exit_code == 0
    assert FakeV2Client.captured_requests[0]["retry_mode"] == "new_job"
