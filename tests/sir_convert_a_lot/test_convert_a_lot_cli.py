"""CLI behavior tests for Sir Convert-a-Lot.

Purpose:
    Validate deterministic manifest output and mixed batch outcomes for the
    local `convert-a-lot` developer workflow.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.cli` command behavior.
    - Uses client-facing result contracts from `scripts.sir_convert_a_lot.client`.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from scripts.sir_convert_a_lot import cli
from scripts.sir_convert_a_lot.client import ClientError, ConversionOutcome
from scripts.sir_convert_a_lot.interfaces import cli_app
from scripts.sir_convert_a_lot.models import JobStatus


class FakeClient:
    """Test double for SirConvertALotClient used by CLI integration tests."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url
        self.api_key = api_key

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def convert_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        max_poll_seconds: float,
        correlation_id: str | None = None,
    ) -> ConversionOutcome:
        del job_spec, idempotency_key, wait_seconds, max_poll_seconds, correlation_id

        if pdf_path.stem.endswith("9") or pdf_path.stem.endswith("10"):
            raise ClientError(
                code="conversion_failed",
                message="simulated failure",
                retryable=False,
                status_code=500,
                job_id=f"job_fail_{pdf_path.stem}",
            )

        return ConversionOutcome(
            job_id=f"job_ok_{pdf_path.stem}",
            status=JobStatus.SUCCEEDED,
            markdown_content=f"# Converted {pdf_path.name}\n",
        )


class FakeTimeoutClient(FakeClient):
    """Test double that simulates long-running background jobs."""

    def convert_pdf_to_markdown(
        self,
        *,
        pdf_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        max_poll_seconds: float,
        correlation_id: str | None = None,
    ) -> ConversionOutcome:
        del job_spec, idempotency_key, wait_seconds, max_poll_seconds, correlation_id
        if pdf_path.stem.endswith("slow"):
            raise ClientError(
                code="job_timeout",
                message="Timed out waiting for terminal state.",
                retryable=True,
                status_code=408,
                job_id=f"job_running_{pdf_path.stem}",
            )
        return ConversionOutcome(
            job_id=f"job_ok_{pdf_path.stem}",
            status=JobStatus.SUCCEEDED,
            markdown_content=f"# Converted {pdf_path.name}\n",
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

    monkeypatch.setattr(cli, "SirConvertALotClient", FakeClient)
    monkeypatch.setattr(cli_app, "SirConvertALotClient", FakeClient)

    result = runner.invoke(
        cli.app,
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

    for entry in entries:
        assert set(entry.keys()) == {
            "source_file_path",
            "job_id",
            "status",
            "output_path",
            "error_code",
        }

    success_count = sum(1 for entry in entries if entry["status"] == "succeeded")
    failure_count = sum(1 for entry in entries if entry["status"] == "failed")
    assert success_count == 8
    assert failure_count == 2

    assert (output_dir / "paper_1.md").exists()
    assert (output_dir / "paper_8.md").exists()
    assert not (output_dir / "paper_9.md").exists()
    assert not (output_dir / "paper_10.md").exists()


def test_convert_command_single_file_success(tmp_path: Path, monkeypatch) -> None:
    source_file = tmp_path / "single.pdf"
    source_file.write_bytes(b"%PDF-1.4\n% single\n%%EOF\n")

    output_dir = tmp_path / "single_out"

    monkeypatch.setattr(cli, "SirConvertALotClient", FakeClient)
    monkeypatch.setattr(cli_app, "SirConvertALotClient", FakeClient)

    result = runner.invoke(
        cli.app,
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


def test_convert_command_timeout_marks_job_running_without_cli_failure(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "pdfs"
    source_dir.mkdir(parents=True)
    (source_dir / "paper_fast.pdf").write_bytes(b"%PDF-1.4\n% fast\n%%EOF\n")
    (source_dir / "paper_slow.pdf").write_bytes(b"%PDF-1.4\n% slow\n%%EOF\n")

    output_dir = tmp_path / "out"

    monkeypatch.setattr(cli, "SirConvertALotClient", FakeTimeoutClient)
    monkeypatch.setattr(cli_app, "SirConvertALotClient", FakeTimeoutClient)

    result = runner.invoke(
        cli.app,
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
    assert by_source["paper_slow.pdf"]["error_code"] == "job_timeout"
