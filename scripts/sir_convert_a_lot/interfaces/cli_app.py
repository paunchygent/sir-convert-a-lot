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

import os
from pathlib import Path

import typer

from scripts.sir_convert_a_lot.interfaces.cli_helpers import (
    detect_directory_source_format,
    discover_source_files,
    parse_source_format,
    parse_target_format,
)
from scripts.sir_convert_a_lot.interfaces.cli_jobs_v2 import jobs_app
from scripts.sir_convert_a_lot.interfaces.cli_manifest_writer_v2 import write_cli_manifest_v2
from scripts.sir_convert_a_lot.interfaces.cli_route_submission_v2 import (
    CliRouteSubmissionOptionsV2,
    submit_service_route_batch_v2,
)
from scripts.sir_convert_a_lot.interfaces.cli_routes import (
    infer_source_format_from_path,
    list_routes,
    resolve_route,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2 import (
    DEFAULT_STALL_TIMEOUT_SECONDS,
    SirConvertALotClientV2,
)
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import RetryModeV2

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

    submission_result = submit_service_route_batch_v2(
        options=CliRouteSubmissionOptionsV2(
            source=source,
            output_dir=output_dir,
            route=route,
            source_files=tuple(source_files),
            service_url=service_url,
            api_key=resolved_api_key,
            wait_seconds=wait_seconds,
            max_poll_seconds=max_poll_seconds,
            stall_timeout_seconds=stall_timeout_seconds,
            retry_mode=retry_mode,
            css_paths=tuple(css),
            resources=resources,
            reference_docx=reference_docx,
            acceleration_policy=acceleration_policy,
            backend_strategy=backend_strategy,
            ocr_mode=ocr_mode,
            ocr_engine=ocr_engine,
            ocr_languages=tuple(ocr_language),
            table_mode=table_mode,
            normalize=normalize,
            manifest_name=manifest_name,
        ),
        client_factory=SirConvertALotClientV2,
        message_sink=typer.echo,
    )

    manifest_result = write_cli_manifest_v2(
        source=source,
        output_dir=output_dir,
        manifest_name=manifest_name,
        entries=submission_result.entries,
    )
    typer.echo(f"Manifest written: {manifest_result.manifest_path}")

    if submission_result.has_failures:
        raise typer.Exit(code=1)


def main() -> None:
    """CLI entrypoint for module execution."""
    app()


if __name__ == "__main__":
    main()
