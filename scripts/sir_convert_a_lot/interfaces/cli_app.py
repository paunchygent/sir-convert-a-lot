"""Sir Convert-a-Lot CLI interface.

Purpose:
    Provide the canonical local "convert-a-lot" UX for submitting PDF-to-Markdown
    jobs to the Sir Convert-a-Lot HTTP service and writing deterministic manifests.

Relationships:
    - Uses `interfaces.http_client` for v1 transport operations.
    - Uses `application.contracts` for manifest schema and `domain.specs` status values.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import typer

from scripts.sir_convert_a_lot.application.contracts import CliManifest, CliManifestEntry
from scripts.sir_convert_a_lot.domain.specs import JobStatus
from scripts.sir_convert_a_lot.interfaces.http_client import ClientError, SirConvertALotClient

app = typer.Typer(help="Please, tell Sir Convert-a-Lot to convert x to y.")


def _discover_pdf_files(source: Path, recursive: bool) -> list[Path]:
    if source.is_file():
        return [source]
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(path for path in source.glob(pattern) if path.is_file())


def _default_job_spec(filename: str, acceleration_policy: str) -> dict[str, object]:
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": "fast",
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def _idempotency_key_for_file(pdf_path: Path, job_spec: dict[str, object]) -> str:
    file_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    spec_sha = hashlib.sha256(
        json.dumps(job_spec, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    combined = hashlib.sha256(f"{pdf_path.name}:{file_sha}:{spec_sha}".encode("utf-8")).hexdigest()
    return f"idem_{combined[:48]}"


def _relative_source_label(source_root: Path, current_file: Path) -> str:
    if source_root.is_file():
        return current_file.name
    return current_file.relative_to(source_root).as_posix()


@app.callback()
def cli_root() -> None:
    """Root command group for Sir Convert-a-Lot workflows."""


@app.command("convert")
def convert_command(
    source: Path = typer.Argument(..., exists=True, resolve_path=True),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", resolve_path=True),
    to: str = typer.Option("md", "--to", help="Target format. v1 supports only 'md'."),
    service_url: str = typer.Option(
        "http://127.0.0.1:18085",
        "--service-url",
        help="Sir Convert-a-Lot base URL (typically a local tunnel endpoint).",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="X-API-Key value. Defaults to SIR_CONVERT_A_LOT_API_KEY env var.",
    ),
    wait_seconds: int = typer.Option(5, "--wait-seconds", min=0, max=20),
    max_poll_seconds: int = typer.Option(120, "--max-poll-seconds", min=5),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive"),
    acceleration_policy: str = typer.Option(
        "gpu_required",
        "--acceleration-policy",
        help="Execution acceleration policy for submitted jobs.",
    ),
    manifest_name: str = typer.Option(
        "sir_convert_a_lot_manifest.json",
        "--manifest-name",
        help="Output manifest filename written in the output directory.",
    ),
) -> None:
    """Convert one PDF or a folder of PDFs into Markdown through Sir Convert-a-Lot."""
    if to != "md":
        raise typer.BadParameter("v1 only supports '--to md'.")

    resolved_api_key = api_key or os.getenv("SIR_CONVERT_A_LOT_API_KEY")
    if resolved_api_key is None or resolved_api_key.strip() == "":
        raise typer.BadParameter(
            "Missing API key. Provide --api-key or set SIR_CONVERT_A_LOT_API_KEY."
        )

    source_files = _discover_pdf_files(source, recursive=recursive)
    if not source_files:
        typer.echo("No PDF files found to convert.")
        raise typer.Exit(code=0)

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[CliManifestEntry] = []
    has_failures = False

    with SirConvertALotClient(base_url=service_url, api_key=resolved_api_key) as client:
        for pdf_path in source_files:
            relative_label = _relative_source_label(source, pdf_path)
            job_spec = _default_job_spec(pdf_path.name, acceleration_policy=acceleration_policy)
            idempotency_key = _idempotency_key_for_file(pdf_path, job_spec)
            correlation_id = (
                f"corr_{hashlib.sha256(relative_label.encode('utf-8')).hexdigest()[:16]}"
            )

            if source.is_file():
                target_markdown = output_dir / pdf_path.with_suffix(".md").name
            else:
                target_markdown = output_dir / Path(relative_label).with_suffix(".md")
            target_markdown.parent.mkdir(parents=True, exist_ok=True)

            try:
                outcome = client.convert_pdf_to_markdown(
                    pdf_path=pdf_path,
                    job_spec=job_spec,
                    idempotency_key=idempotency_key,
                    wait_seconds=wait_seconds,
                    max_poll_seconds=max_poll_seconds,
                    correlation_id=correlation_id,
                )
                target_markdown.write_text(outcome.markdown_content, encoding="utf-8")
                manifest_entries.append(
                    CliManifestEntry(
                        source_file_path=relative_label,
                        job_id=outcome.job_id,
                        status=JobStatus.SUCCEEDED,
                        output_path=target_markdown.as_posix(),
                        error_code=None,
                    )
                )
                typer.echo(f"✓ Converted {relative_label} -> {target_markdown}")
            except ClientError as exc:
                if exc.code == "job_timeout" and exc.job_id is not None:
                    manifest_entries.append(
                        CliManifestEntry(
                            source_file_path=relative_label,
                            job_id=exc.job_id,
                            status=JobStatus.RUNNING,
                            output_path=None,
                            error_code=exc.code,
                        )
                    )
                    typer.echo(
                        "… Submitted and still running "
                        f"{relative_label}: {exc.job_id}. "
                        "Use status/result endpoints to fetch completion later."
                    )
                    continue
                has_failures = True
                manifest_entries.append(
                    CliManifestEntry(
                        source_file_path=relative_label,
                        job_id=exc.job_id,
                        status=JobStatus.FAILED,
                        output_path=None,
                        error_code=exc.code,
                    )
                )
                typer.echo(f"✗ Failed {relative_label}: {exc.code} ({exc.message})")

    manifest_entries.sort(key=lambda entry: entry.source_file_path)
    manifest = CliManifest(
        generated_at=datetime.now(UTC),
        source_root=source.as_posix(),
        output_root=output_dir.as_posix(),
        entries=manifest_entries,
    )

    manifest_path = output_dir / manifest_name
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    typer.echo(f"Manifest written: {manifest_path}")

    if has_failures:
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entrypoint for module execution."""
    app()


if __name__ == "__main__":
    main()
