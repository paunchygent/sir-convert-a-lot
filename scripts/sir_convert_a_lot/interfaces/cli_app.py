"""Sir Convert-a-Lot CLI interface.

Purpose:
    Provide the canonical local "convert-a-lot" UX for submitting conversion
    jobs to the Sir Convert-a-Lot HTTP service (v1 and v2) and writing
    deterministic manifests.

Relationships:
    - Uses `interfaces.http_client` for v1 PDF->MD transport operations.
    - Uses `interfaces.http_client_v2` for multi-format transport operations (v2).
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
    default_job_spec_v1,
    default_job_spec_v2,
    detect_directory_source_format,
    discover_source_files,
    idempotency_key_for_file,
    idempotency_key_for_v2_request,
    parse_source_format,
    parse_target_format,
    relative_source_label,
    sha256_bytes,
)
from scripts.sir_convert_a_lot.interfaces.cli_routes import (
    SourceFormat,
    TargetFormat,
    infer_source_format_from_path,
    list_routes,
    resolve_route,
)
from scripts.sir_convert_a_lot.interfaces.http_client import ClientError, SirConvertALotClient
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import (
    ArtifactOutcomeV2,
    SirConvertALotClientV2,
)

app = typer.Typer(help="Please, tell Sir Convert-a-Lot to convert x to y.")


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
            "Target format. Implemented routes include: 'md' (pdf->md via service v1), "
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
        resolved_api_key = api_key or os.getenv("SIR_CONVERT_A_LOT_API_KEY")
        if resolved_api_key is None or resolved_api_key.strip() == "":
            raise typer.BadParameter(
                "Missing API key. Provide --api-key or set SIR_CONVERT_A_LOT_API_KEY."
            )
    else:
        resolved_api_key = ""

    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries: list[CliManifestEntry] = []
    has_failures = False

    if route.source is SourceFormat.PDF and route.target is TargetFormat.MD:
        if css or resources is not None or reference_docx is not None:
            raise typer.BadParameter(
                "The locked v1 pdf->md route does not accept --css, --resources, "
                "or --reference-docx."
            )
        with SirConvertALotClient(base_url=service_url, api_key=resolved_api_key) as client:
            for pdf_path in source_files:
                relative_label = relative_source_label(source, pdf_path)
                job_spec = default_job_spec_v1(
                    filename=pdf_path.name,
                    acceleration_policy=acceleration_policy,
                    backend_strategy=backend_strategy,
                    ocr_mode=ocr_mode,
                    table_mode=table_mode,
                    normalize=normalize,
                )
                idempotency_key = idempotency_key_for_file(pdf_path, job_spec)
                correlation_id = (
                    f"corr_{hashlib.sha256(relative_label.encode('utf-8')).hexdigest()[:16]}"
                )

                if source.is_file():
                    target_markdown = output_dir / pdf_path.with_suffix(".md").name
                else:
                    target_markdown = output_dir / Path(relative_label).with_suffix(".md")
                target_markdown.parent.mkdir(parents=True, exist_ok=True)

                try:
                    v1_outcome = client.convert_pdf_to_markdown(
                        pdf_path=pdf_path,
                        job_spec=job_spec,
                        idempotency_key=idempotency_key,
                        wait_seconds=wait_seconds,
                        max_poll_seconds=max_poll_seconds,
                        correlation_id=correlation_id,
                    )
                    target_markdown.write_text(v1_outcome.markdown_content, encoding="utf-8")
                    manifest_entries.append(
                        CliManifestEntry(
                            source_file_path=relative_label,
                            job_id=v1_outcome.job_id,
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
    else:
        if route.target is TargetFormat.DOCX and css:
            raise typer.BadParameter("--css is only supported for PDF outputs.")
        if route.target is TargetFormat.PDF and reference_docx is not None:
            raise typer.BadParameter("--reference-docx is only supported for DOCX outputs.")

        resources_zip_bytes: bytes | None
        css_filenames: list[str]
        if route.target is TargetFormat.PDF:
            resources_zip_bytes, css_filenames = build_resources_zip_payload(
                resources=resources, css_paths=tuple(css)
            )
        else:
            resources_zip_bytes, _ = build_resources_zip_payload(resources=resources, css_paths=())
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
        elif route.source is SourceFormat.MD:
            source_format_v2 = SourceFormatV2.MD
        elif route.source is SourceFormat.HTML:
            source_format_v2 = SourceFormatV2.HTML
        else:
            raise typer.BadParameter(
                f"unsupported_route: {route.source.value} -> {route.target.value}."
            )

        output_format_v2 = (
            OutputFormatV2.PDF if route.target is TargetFormat.PDF else OutputFormatV2.DOCX
        )

        with SirConvertALotClientV2(base_url=service_url, api_key=resolved_api_key) as client:
            for source_path in source_files:
                relative_label = relative_source_label(source, source_path)
                relative_path = Path(relative_label)
                correlation_id = (
                    f"corr_{hashlib.sha256(relative_label.encode('utf-8')).hexdigest()[:16]}"
                )

                suffix = ".pdf" if output_format_v2 == OutputFormatV2.PDF else ".docx"
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
                        correlation_id=correlation_id,
                        resources_zip_bytes=resources_zip_bytes,
                        reference_docx_bytes=reference_docx_bytes,
                    )
                    target_path.write_bytes(v2_outcome.artifact_bytes)
                    manifest_entries.append(
                        CliManifestEntry(
                            source_file_path=relative_label,
                            job_id=v2_outcome.job_id,
                            status=JobStatus.SUCCEEDED,
                            output_path=target_path.as_posix(),
                            error_code=None,
                        )
                    )
                    typer.echo(f"✓ Converted {relative_label} -> {target_path}")
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
