"""CLI subcommands for managing v2 conversion jobs.

Purpose:
    Keep `interfaces.cli_app` lean by isolating job-management commands that
    complement the primary `convert` submission flow:
      - cancel-with-save
      - checkpoint/partial retrieval
      - resume-from-checkpoint

Relationships:
    - Registered by `interfaces.cli_app`.
    - Uses `interfaces.http_client_v2` and `interfaces.http_client_v2_models`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import typer

from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import (
    DEFAULT_STALL_TIMEOUT_SECONDS,
    SirConvertALotClientV2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import ClientErrorV2

jobs_app = typer.Typer(help="Manage v2 conversion jobs (cancel/partial/checkpoint/resume).")


def _resolve_api_key(value: str | None) -> str:
    api_key = value or os.getenv("SIR_CONVERT_A_LOT_API_KEY")
    if api_key is None or api_key.strip() == "":
        raise typer.BadParameter("Missing --api-key and SIR_CONVERT_A_LOT_API_KEY env var.")
    return api_key


def _output_suffix_for_format(fmt: OutputFormatV2) -> str:
    if fmt == OutputFormatV2.MD:
        return ".md"
    if fmt == OutputFormatV2.PDF:
        return ".pdf"
    if fmt == OutputFormatV2.DOCX:
        return ".docx"
    raise AssertionError(f"Unsupported output_format: {fmt}")


def _load_output_format_from_job_payload(payload: dict[str, object]) -> OutputFormatV2:
    job_obj = payload.get("job")
    if not isinstance(job_obj, dict):
        raise ClientErrorV2(
            code="invalid_response",
            message="Job payload missing 'job' object.",
            retryable=False,
            status_code=500,
        )
    output_obj = job_obj.get("output_format")
    if not isinstance(output_obj, str):
        raise ClientErrorV2(
            code="invalid_response",
            message="Job payload missing output_format.",
            retryable=False,
            status_code=500,
        )
    return OutputFormatV2(output_obj)


@jobs_app.command("cancel")
def cancel_job(
    job_id: str = typer.Argument(...),
    service_url: str = typer.Option("http://127.0.0.1:28085", "--service-url"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Cancel a v2 job (PDF routes are cancel-with-save)."""
    with SirConvertALotClientV2(base_url=service_url, api_key=_resolve_api_key(api_key)) as client:
        job = client.cancel_job(job_id)
    typer.echo(f"{job.job_id}: {job.status.value}")


@jobs_app.command("partial")
def fetch_partial_artifact(
    job_id: str = typer.Argument(...),
    out: Path = typer.Option(..., "--out", "-o", resolve_path=True),
    service_url: str = typer.Option("http://127.0.0.1:28085", "--service-url"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Download partial markdown artifact for a long-running PDF job."""
    with SirConvertALotClientV2(base_url=service_url, api_key=_resolve_api_key(api_key)) as client:
        payload = client.download_partial_artifact(job_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(payload)
    typer.echo(out.as_posix())


@jobs_app.command("checkpoint")
def fetch_checkpoint(
    job_id: str = typer.Argument(...),
    out: Path = typer.Option(..., "--out", "-o", resolve_path=True),
    service_url: str = typer.Option("http://127.0.0.1:28085", "--service-url"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Download checkpoint JSON for a long-running PDF job."""
    with SirConvertALotClientV2(base_url=service_url, api_key=_resolve_api_key(api_key)) as client:
        checkpoint = client.get_checkpoint_payload(job_id)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    typer.echo(out.as_posix())


@jobs_app.command("resume")
def resume_job(
    job_id: str = typer.Argument(...),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", resolve_path=True),
    idempotency_key: str | None = typer.Option(None, "--idempotency-key"),
    max_poll_seconds: float = typer.Option(120.0, "--max-poll-seconds", min=5.0),
    stall_timeout_seconds: float = typer.Option(
        float(DEFAULT_STALL_TIMEOUT_SECONDS),
        "--stall-timeout-seconds",
        min=5.0,
    ),
    service_url: str = typer.Option("http://127.0.0.1:28085", "--service-url"),
    api_key: str | None = typer.Option(None, "--api-key"),
) -> None:
    """Resume a canceled/failed long-running PDF job from checkpoint."""
    resolved_idem = idempotency_key or f"resume_{job_id}"
    output_dir.mkdir(parents=True, exist_ok=True)
    with SirConvertALotClientV2(base_url=service_url, api_key=_resolve_api_key(api_key)) as client:
        resumed = client.resume_job(source_job_id=job_id, idempotency_key=resolved_idem)
        status = resumed.status
        if status not in {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED}:
            status = client.wait_for_terminal_status(
                resumed.job_id,
                timeout_seconds=max_poll_seconds,
                stall_timeout_seconds=stall_timeout_seconds,
            )
        if status != JobStatus.SUCCEEDED:
            typer.echo(f"Resume job ended with status '{status.value}'.", err=True)
            raise typer.Exit(code=2)

        job_payload = client.get_job_payload(resumed.job_id)
        output_format = _load_output_format_from_job_payload(job_payload)
        suffix = _output_suffix_for_format(output_format)
        artifact_bytes = client.download_artifact(resumed.job_id)
        out_path = output_dir / f"resumed_{resumed.job_id}{suffix}"
        out_path.write_bytes(artifact_bytes)
    typer.echo(out_path.as_posix())
