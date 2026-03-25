"""Sir Convert-a-Lot CLI interface.

Purpose:
    Provide the canonical local "convert-a-lot" UX for submitting conversion
    jobs to the Sir Convert-a-Lot HTTP service (v2) and writing
    deterministic manifests.

Relationships:
    - Uses `interfaces.http_client_v2` for service transport operations.
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
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.interfaces.cli_helpers import (
    build_resources_zip_payload,
    default_job_spec_v2,
    detect_directory_source_format,
    discover_source_files,
    idempotency_key_for_v2_request,
    parse_source_format,
    parse_target_format,
    relative_source_label,
    sha256_bytes,
)
from scripts.sir_convert_a_lot.interfaces.cli_jobs_v2 import jobs_app
from scripts.sir_convert_a_lot.interfaces.cli_routes import (
    SourceFormat,
    TargetFormat,
    infer_source_format_from_path,
    list_routes,
    resolve_route,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import (
    DEFAULT_STALL_TIMEOUT_SECONDS,
    SirConvertALotClientV2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ArtifactOutcomeV2,
    ClientErrorV2,
    RetryModeV2,
)

app = typer.Typer(help="Please, tell Sir Convert-a-Lot to convert x to y.")
app.add_typer(jobs_app, name="jobs")


@app.callback()
def cli_root() -> None:
    """Root command group for Sir Convert-a-Lot workflows."""


@app.command("routes")
def routes_command() -> None:
    """List supported conversion routes and their current implementation status."""
    typer.echo("Supported routes:")
    for route in list_routes():
        status = "implemented" if route.implemented else "planned"
        typer.echo(
            f"- {route.source.value} -> {route.target.value} "
            f"[{route.pipeline_kind.value}] ({status})"
        )


@app.command("convert")
def convert_command(
    source: Path = typer.Argument(..., exists=True, resolve_path=True),
    output_dir: Path = typer.Option(..., "--output-dir", "-o", resolve_path=True),
    to: str = typer.Option(
        "md",
        "--to",
        help=(
            "Target format. Implemented routes include: "
            "'md' (pdf->md, docx->md, and html->md via service v2), "
            "'pdf' (html->pdf and md->pdf via service v2), and 'docx' (pdf->docx, md->docx, "
            "and html->docx via service v2). "
            "Use 'convert-a-lot routes' for details."
        ),
    ),
    from_format: str | None = typer.Option(
        None,
        "--from",
        help="Override source format inference: pdf, md, html, or docx.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print selected route and discovered files without executing conversion.",
    ),
    service_url: str = typer.Option(
        "http://127.0.0.1:28085",
        "--service-url",
        help=(
            "Sir Convert-a-Lot base URL "
            "(canonical lanes: tunnel http://127.0.0.1:28085 or "
            "internet https://convert.hule.education)."
        ),
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="X-API-Key value. Defaults to SIR_CONVERT_A_LOT_V2_API_KEY env var.",
    ),
    wait_seconds: int = typer.Option(5, "--wait-seconds", min=0, max=20),
    max_poll_seconds: int = typer.Option(120, "--max-poll-seconds", min=5),
    stall_timeout_seconds: int = typer.Option(
        int(DEFAULT_STALL_TIMEOUT_SECONDS),
        "--stall-timeout-seconds",
        min=5,
        help=(
            "Seconds without heartbeat/progress considered 'stalled' when the max poll window is "
            "exceeded. Fresh jobs return a non-failure running outcome instead."
        ),
    ),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive"),
    css: list[Path] = typer.Option(
        [],
        "--css",
        help=(
            "CSS stylesheet path(s) applied for HTML->PDF and MD->PDF conversions. "
            "The CLI uploads these to the service as part of the v2 resources bundle. "
            "Can be passed multiple times."
        ),
        exists=True,
        resolve_path=True,
    ),
    resources: Path | None = typer.Option(
        None,
        "--resources",
        help=(
            "Optional resources bundle uploaded to the v2 service. "
            "May be a directory (zipped deterministically) or a .zip file."
        ),
        exists=True,
        resolve_path=True,
    ),
    reference_docx: Path | None = typer.Option(
        None,
        "--reference-docx",
        help="Reference DOCX uploaded to the v2 service for DOCX styling.",
        exists=True,
        resolve_path=True,
    ),
    acceleration_policy: str = typer.Option(
        "gpu_required",
        "--acceleration-policy",
        help="Execution acceleration policy for submitted jobs.",
    ),
    backend_strategy: str = typer.Option(
        "auto",
        "--backend-strategy",
        help="Conversion backend strategy: auto, docling, or pymupdf.",
    ),
    ocr_mode: str = typer.Option(
        "auto",
        "--ocr-mode",
        help="OCR mode: off, force, or auto.",
    ),
    ocr_engine: str = typer.Option(
        "auto",
        "--ocr-engine",
        help="OCR engine: auto, easyocr, or tesseract_cli.",
    ),
    ocr_language: list[str] = typer.Option(
        [],
        "--ocr-language",
        help="OCR language tag (repeatable, e.g. --ocr-language sv --ocr-language en).",
    ),
    table_mode: str = typer.Option(
        "accurate",
        "--table-mode",
        help="Table extraction mode: fast or accurate.",
    ),
    normalize: str = typer.Option(
        "strict",
        "--normalize",
        help="Markdown normalization mode: none, standard, or strict.",
    ),
    manifest_name: str = typer.Option(
        "sir_convert_a_lot_manifest.json",
        "--manifest-name",
        help="Output manifest filename written in the output directory.",
    ),
    replay_only: bool = typer.Option(
        False,
        "--replay-only",
        help="Do not auto-rerun terminal failed/canceled idempotent replays.",
    ),
    new_job: bool = typer.Option(
        False,
        "--new-job",
        help="Always submit with a new Idempotency-Key (disables replay benefits).",
    ),
) -> None:
    """Convert one file or a folder of files through Sir Convert-a-Lot."""
    target_format = parse_target_format(to)

    if from_format is not None:
        source_format = parse_source_format(from_format)
    elif source.is_file():
        inferred = infer_source_format_from_path(source)
        if inferred is None:
            raise typer.BadParameter(
                f"Unsupported input file type: {source.suffix}. Provide --from to override."
            )
        source_format = inferred
    else:
        source_format = detect_directory_source_format(
            source_dir=source,
            target_format=target_format,
            recursive=recursive,
        )

    route = resolve_route(source=source_format, target=target_format)
    if route is None:
        raise typer.BadParameter(
            f"unsupported_route: {source_format.value} -> {target_format.value}. "
            "Use 'convert-a-lot routes' to list supported routes."
        )

    source_files = discover_source_files(source, source_format=source_format, recursive=recursive)
    if not source_files:
        typer.echo("No input files found to convert.")
        raise typer.Exit(code=0)

    if dry_run:
        status = "implemented" if route.implemented else "planned"
        typer.echo(
            f"Dry run: selected route {route.source.value} -> {route.target.value} "
            f"[{route.pipeline_kind.value}] ({status})"
        )
        typer.echo("Pipeline:")
        for step in route.pipeline_steps:
            typer.echo(f"  - {step}")
        typer.echo(f"Discovered {len(source_files)} file(s).")
        raise typer.Exit(code=0)

    if not route.implemented:
        raise typer.BadParameter(
            f"route_not_implemented: {route.source.value} -> {route.target.value}. "
            "Use 'convert-a-lot routes' to see planned routes."
        )

    if route.requires_service:
        resolved_api_key = api_key or os.getenv("SIR_CONVERT_A_LOT_V2_API_KEY")
        if resolved_api_key is None or resolved_api_key.strip() == "":
            raise typer.BadParameter(
                "Missing API key. Provide --api-key or set SIR_CONVERT_A_LOT_V2_API_KEY."
            )
    else:
        resolved_api_key = ""

    if replay_only and new_job:
        raise typer.BadParameter("--replay-only and --new-job are mutually exclusive.")

    retry_mode: RetryModeV2 = "auto"
    if replay_only:
        retry_mode = "replay_only"
    elif new_job:
        retry_mode = "new_job"

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[CliManifestEntry] = []
    has_failures = False

    if route.target is TargetFormat.DOCX and css:
        raise typer.BadParameter("--css is only supported for PDF outputs.")
    if route.target is TargetFormat.PDF and reference_docx is not None:
        raise typer.BadParameter("--reference-docx is only supported for DOCX outputs.")
    if route.target is TargetFormat.MD and css:
        raise typer.BadParameter("V2 markdown-target routes do not accept --css.")
    if route.target is TargetFormat.MD and reference_docx is not None:
        raise typer.BadParameter("V2 markdown-target routes do not accept --reference-docx.")
    if (
        route.target is TargetFormat.MD
        and resources is not None
        and route.source is not SourceFormat.HTML
    ):
        raise typer.BadParameter(
            "V2 markdown-target routes only accept --resources for html -> md."
        )

    resources_zip_bytes: bytes | None
    css_filenames: list[str]
    if route.target is TargetFormat.PDF:
        resources_zip_bytes, css_filenames = build_resources_zip_payload(
            resources=resources, css_paths=tuple(css)
        )
    elif route.target is TargetFormat.DOCX:
        resources_zip_bytes, _ = build_resources_zip_payload(resources=resources, css_paths=())
        css_filenames = []
    elif route.source is SourceFormat.HTML and resources is not None:
        resources_zip_bytes, _ = build_resources_zip_payload(resources=resources, css_paths=())
        css_filenames = []
    else:
        resources_zip_bytes = None
        css_filenames = []

    resources_sha256 = (
        sha256_bytes(resources_zip_bytes) if resources_zip_bytes is not None else None
    )

    reference_docx_bytes: bytes | None = None
    reference_docx_sha256: str | None = None
    if route.target is TargetFormat.DOCX and reference_docx is not None:
        reference_docx_bytes = reference_docx.read_bytes()
        reference_docx_sha256 = sha256_bytes(reference_docx_bytes)

    if route.source is SourceFormat.PDF:
        source_format_v2 = SourceFormatV2.PDF
    elif route.source is SourceFormat.DOCX:
        source_format_v2 = SourceFormatV2.DOCX
    elif route.source is SourceFormat.MD:
        source_format_v2 = SourceFormatV2.MD
    elif route.source is SourceFormat.HTML:
        source_format_v2 = SourceFormatV2.HTML
    else:
        raise typer.BadParameter(
            f"unsupported_route: {route.source.value} -> {route.target.value}."
        )

    if route.target is TargetFormat.MD:
        output_format_v2 = OutputFormatV2.MD
    elif route.target is TargetFormat.PDF:
        output_format_v2 = OutputFormatV2.PDF
    else:
        output_format_v2 = OutputFormatV2.DOCX

    with SirConvertALotClientV2(base_url=service_url, api_key=resolved_api_key) as client:
        for source_path in source_files:
            relative_label = relative_source_label(source, source_path)
            relative_path = Path(relative_label)
            correlation_id = (
                f"corr_{hashlib.sha256(relative_label.encode('utf-8')).hexdigest()[:16]}"
            )
            pipeline_used = (
                route.pipeline_steps[0] if route.pipeline_steps else "service: unknown (v2)"
            )

            if output_format_v2 == OutputFormatV2.MD:
                suffix = ".md"
            elif output_format_v2 == OutputFormatV2.PDF:
                suffix = ".pdf"
            else:
                suffix = ".docx"
            if source.is_file():
                target_path = output_dir / source_path.with_suffix(suffix).name
            else:
                target_path = output_dir / relative_path.with_suffix(suffix)
            target_path.parent.mkdir(parents=True, exist_ok=True)

            reference_docx_filename = (
                reference_docx.name
                if (
                    output_format_v2 == OutputFormatV2.DOCX
                    and reference_docx is not None
                    and reference_docx.name.strip() != ""
                )
                else None
            )

            job_spec = default_job_spec_v2(
                filename=source_path.name,
                source_format=source_format_v2,
                output_format=output_format_v2,
                css_filenames=css_filenames if output_format_v2 == OutputFormatV2.PDF else [],
                reference_docx_filename=reference_docx_filename,
                acceleration_policy=acceleration_policy,
                backend_strategy=backend_strategy,
                ocr_mode=ocr_mode,
                ocr_engine=ocr_engine,
                ocr_languages=ocr_language,
                table_mode=table_mode,
                normalize=normalize,
            )

            file_sha256 = sha256_bytes(source_path.read_bytes())
            idempotency_key = idempotency_key_for_v2_request(
                filename=source_path.name,
                file_sha256=file_sha256,
                spec_payload=job_spec,
                resources_sha256=resources_sha256,
                reference_docx_sha256=reference_docx_sha256,
            )

            try:
                v2_outcome: ArtifactOutcomeV2 = client.convert_upload_to_artifact(
                    source_path=source_path,
                    job_spec=job_spec,
                    idempotency_key=idempotency_key,
                    wait_seconds=wait_seconds,
                    max_poll_seconds=max_poll_seconds,
                    stall_timeout_seconds=float(stall_timeout_seconds),
                    retry_mode=retry_mode,
                    correlation_id=correlation_id,
                    resources_zip_bytes=resources_zip_bytes,
                    reference_docx_bytes=reference_docx_bytes,
                )
                if v2_outcome.rerun_of_job_id is not None:
                    typer.echo(
                        f"[rerun] Replay hit terminal failure for {relative_label}: "
                        f"{v2_outcome.rerun_of_job_id} -> {v2_outcome.job_id}"
                    )
                target_path.write_bytes(v2_outcome.artifact_bytes)
                manifest_entries.append(
                    CliManifestEntry(
                        source_file_path=relative_label,
                        source_format=route.source.value,
                        target_format=route.target.value,
                        pipeline_used=pipeline_used,
                        job_id=v2_outcome.job_id,
                        status=JobStatus.SUCCEEDED,
                        output_path=target_path.as_posix(),
                        error_code=None,
                    )
                )
                typer.echo(f"✓ Converted {relative_label} -> {target_path}")
            except ClientErrorV2 as exc:
                if exc.code == "job_poll_window_exceeded" and exc.job_id is not None:
                    manifest_entries.append(
                        CliManifestEntry(
                            source_file_path=relative_label,
                            source_format=route.source.value,
                            target_format=route.target.value,
                            pipeline_used=pipeline_used,
                            job_id=exc.job_id,
                            status=JobStatus.RUNNING,
                            output_path=None,
                            error_code=exc.code,
                        )
                    )
                    typer.echo(
                        "… Submitted and still running (max poll window exceeded) "
                        f"{relative_label}: {exc.job_id}. "
                        "Use status/result endpoints to fetch completion later."
                    )
                    continue
                if exc.code == "job_timeout" and exc.job_id is not None:
                    has_failures = True
                    manifest_entries.append(
                        CliManifestEntry(
                            source_file_path=relative_label,
                            source_format=route.source.value,
                            target_format=route.target.value,
                            pipeline_used=pipeline_used,
                            job_id=exc.job_id,
                            status=JobStatus.RUNNING,
                            output_path=None,
                            error_code=exc.code,
                        )
                    )
                    typer.echo(
                        "✗ Submitted but appears stalled (heartbeat/progress stale) "
                        f"{relative_label}: {exc.job_id}. "
                        "Check job status and consider cancel/retry if it does not recover."
                    )
                    continue
                has_failures = True
                manifest_entries.append(
                    CliManifestEntry(
                        source_file_path=relative_label,
                        source_format=route.source.value,
                        target_format=route.target.value,
                        pipeline_used=pipeline_used,
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
