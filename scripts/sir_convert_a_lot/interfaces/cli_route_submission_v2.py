"""CLI service-route submission for Sir Convert-a-Lot API v2.

Purpose:
    Execute the `convert-a-lot convert` service-backed batch workflow outside
    the Typer command body while preserving route validation, idempotency,
    polling, artifact writing, and deterministic manifest-entry behavior.

Relationships:
    - Called by `interfaces.cli_app` after route/source discovery.
    - Uses `interfaces.http_client_v2` through an injected client factory.
    - Builds manifest entries through `interfaces.cli_manifest_writer_v2`.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Protocol

import typer

from scripts.sir_convert_a_lot.application.contracts import CliManifestEntry
from scripts.sir_convert_a_lot.domain.specs_v2 import OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.interfaces.cli_helpers import (
    build_resources_zip_payload,
    default_job_spec_v2,
    idempotency_key_for_v2_request,
    relative_source_label,
    sha256_bytes,
)
from scripts.sir_convert_a_lot.interfaces.cli_incremental_manifest_v2 import (
    CliIncrementalManifestRecorderV2,
)
from scripts.sir_convert_a_lot.interfaces.cli_manifest_writer_v2 import (
    build_failed_manifest_entry_v2,
    build_running_manifest_entry_v2,
    build_success_manifest_entry_v2,
)
from scripts.sir_convert_a_lot.interfaces.cli_progress_messages_v2 import (
    progress_callback_for_source_v2,
)
from scripts.sir_convert_a_lot.interfaces.cli_routes import CliRoute, SourceFormat, TargetFormat
from scripts.sir_convert_a_lot.interfaces.http_client_v2_models import (
    ArtifactOutcomeV2,
    ClientErrorV2,
    RetryModeV2,
)


class CliArtifactClientV2(Protocol):
    """Client operations needed by CLI route submission."""

    def convert_upload_to_artifact(
        self,
        *,
        source_path: Path,
        job_spec: dict[str, object],
        idempotency_key: str,
        wait_seconds: int,
        max_poll_seconds: float,
        stall_timeout_seconds: float = 120.0,
        retry_mode: RetryModeV2 = "auto",
        correlation_id: str | None = None,
        resources_zip_bytes: bytes | None = None,
        reference_docx_bytes: bytes | None = None,
        progress_callback: Callable[[dict[str, object]], None] | None = None,
    ) -> ArtifactOutcomeV2:
        """Submit one upload and return a terminal artifact or raise a client error."""


class CliArtifactClientContextV2(CliArtifactClientV2, Protocol):
    """Context-managed CLI artifact client."""

    def __enter__(self) -> CliArtifactClientV2:
        """Enter the client context."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        """Exit the client context."""


class CliArtifactClientFactoryV2(Protocol):
    """Factory for context-managed CLI artifact clients."""

    def __call__(self, *, base_url: str, api_key: str) -> CliArtifactClientContextV2:
        """Build one context-managed CLI artifact client."""


@dataclass(frozen=True)
class CliRouteSubmissionOptionsV2:
    """Options required to submit one CLI service-route batch."""

    source: Path
    output_dir: Path
    route: CliRoute
    source_files: tuple[Path, ...]
    service_url: str
    api_key: str
    wait_seconds: int
    max_poll_seconds: int
    stall_timeout_seconds: int
    retry_mode: RetryModeV2
    css_paths: tuple[Path, ...]
    resources: Path | None
    reference_docx: Path | None
    acceleration_policy: str
    backend_strategy: str
    ocr_mode: str
    ocr_engine: str
    ocr_languages: tuple[str, ...]
    table_mode: str
    normalize: str
    manifest_name: str = "sir_convert_a_lot_manifest.json"


@dataclass(frozen=True)
class CliRouteSubmissionResultV2:
    """Manifest entries and failure flag produced by a CLI service-route batch."""

    entries: list[CliManifestEntry]
    has_failures: bool


@dataclass(frozen=True)
class CliRouteCompanionPayloadV2:
    """Prepared companion uploads shared by every file in one CLI route batch."""

    resources_zip_bytes: bytes | None
    resources_sha256: str | None
    css_filenames: list[str]
    reference_docx_bytes: bytes | None
    reference_docx_sha256: str | None


def submit_service_route_batch_v2(
    *,
    options: CliRouteSubmissionOptionsV2,
    client_factory: CliArtifactClientFactoryV2,
    message_sink: Callable[[str], None],
) -> CliRouteSubmissionResultV2:
    """Submit all files for one service route and return manifest entries."""
    _validate_route_companion_options_v2(options)
    companion_payload = _prepare_companion_payload_v2(options)
    source_format_v2 = _source_format_v2_for_route_source(options.route.source)
    output_format_v2 = _output_format_v2_for_route_target(options.route.target)
    pipeline_used = _pipeline_used_for_route(options.route)

    manifest_entries: list[CliManifestEntry] = []
    has_failures = False
    manifest_recorder = CliIncrementalManifestRecorderV2(
        source=options.source,
        output_dir=options.output_dir,
        manifest_name=options.manifest_name,
    )

    with client_factory(base_url=options.service_url, api_key=options.api_key) as client:
        for source_path in options.source_files:
            outcome = _submit_one_source_file_v2(
                options=options,
                client=client,
                source_path=source_path,
                source_format_v2=source_format_v2,
                output_format_v2=output_format_v2,
                pipeline_used=pipeline_used,
                companion_payload=companion_payload,
                message_sink=message_sink,
                manifest_recorder=manifest_recorder,
            )
            manifest_entries.append(outcome.entry)
            manifest_recorder.upsert_entry(outcome.entry)
            if outcome.failed:
                has_failures = True

    return CliRouteSubmissionResultV2(
        entries=manifest_entries,
        has_failures=has_failures,
    )


@dataclass(frozen=True)
class _SingleSubmissionOutcomeV2:
    entry: CliManifestEntry
    failed: bool


def _validate_route_companion_options_v2(options: CliRouteSubmissionOptionsV2) -> None:
    route = options.route
    if route.target is TargetFormat.DOCX and options.css_paths:
        raise typer.BadParameter("--css is only supported for PDF outputs.")
    if route.target is TargetFormat.PDF and options.reference_docx is not None:
        raise typer.BadParameter("--reference-docx is only supported for DOCX outputs.")
    if route.target is TargetFormat.MD and options.css_paths:
        raise typer.BadParameter("V2 markdown-target routes do not accept --css.")
    if route.target is TargetFormat.MD and options.reference_docx is not None:
        raise typer.BadParameter("V2 markdown-target routes do not accept --reference-docx.")
    if (
        route.target is TargetFormat.MD
        and options.resources is not None
        and route.source is not SourceFormat.HTML
    ):
        raise typer.BadParameter(
            "V2 markdown-target routes only accept --resources for html -> md."
        )


def _prepare_companion_payload_v2(
    options: CliRouteSubmissionOptionsV2,
) -> CliRouteCompanionPayloadV2:
    resources_zip_bytes: bytes | None
    css_filenames: list[str]
    if options.route.target is TargetFormat.PDF:
        resources_zip_bytes, css_filenames = build_resources_zip_payload(
            resources=options.resources,
            css_paths=options.css_paths,
        )
    elif options.route.target is TargetFormat.DOCX:
        resources_zip_bytes, _ = build_resources_zip_payload(
            resources=options.resources,
            css_paths=(),
        )
        css_filenames = []
    elif options.route.source is SourceFormat.HTML and options.resources is not None:
        resources_zip_bytes, _ = build_resources_zip_payload(
            resources=options.resources,
            css_paths=(),
        )
        css_filenames = []
    else:
        resources_zip_bytes = None
        css_filenames = []

    resources_sha256 = (
        sha256_bytes(resources_zip_bytes) if resources_zip_bytes is not None else None
    )

    reference_docx_bytes: bytes | None = None
    reference_docx_sha256: str | None = None
    if options.route.target is TargetFormat.DOCX and options.reference_docx is not None:
        reference_docx_bytes = options.reference_docx.read_bytes()
        reference_docx_sha256 = sha256_bytes(reference_docx_bytes)

    return CliRouteCompanionPayloadV2(
        resources_zip_bytes=resources_zip_bytes,
        resources_sha256=resources_sha256,
        css_filenames=css_filenames,
        reference_docx_bytes=reference_docx_bytes,
        reference_docx_sha256=reference_docx_sha256,
    )


def _source_format_v2_for_route_source(source_format: SourceFormat) -> SourceFormatV2:
    if source_format is SourceFormat.PDF:
        return SourceFormatV2.PDF
    if source_format is SourceFormat.DOCX:
        return SourceFormatV2.DOCX
    if source_format is SourceFormat.MD:
        return SourceFormatV2.MD
    if source_format is SourceFormat.HTML:
        return SourceFormatV2.HTML
    raise typer.BadParameter(f"unsupported source format: {source_format.value}.")


def _output_format_v2_for_route_target(target_format: TargetFormat) -> OutputFormatV2:
    if target_format is TargetFormat.MD:
        return OutputFormatV2.MD
    if target_format is TargetFormat.PDF:
        return OutputFormatV2.PDF
    return OutputFormatV2.DOCX


def _pipeline_used_for_route(route: CliRoute) -> str:
    return route.pipeline_steps[0] if route.pipeline_steps else "service: unknown (v2)"


def _target_suffix_for_output_format(output_format: OutputFormatV2) -> str:
    if output_format == OutputFormatV2.MD:
        return ".md"
    if output_format == OutputFormatV2.PDF:
        return ".pdf"
    return ".docx"


def _target_path_for_source_file(
    *,
    source_root: Path,
    source_path: Path,
    output_dir: Path,
    output_format: OutputFormatV2,
) -> Path:
    suffix = _target_suffix_for_output_format(output_format)
    if source_root.is_file():
        return output_dir / source_path.with_suffix(suffix).name
    relative_path = Path(relative_source_label(source_root, source_path))
    return output_dir / relative_path.with_suffix(suffix)


def _reference_docx_filename_v2(
    *,
    output_format: OutputFormatV2,
    reference_docx: Path | None,
) -> str | None:
    if output_format != OutputFormatV2.DOCX or reference_docx is None:
        return None
    if reference_docx.name.strip() == "":
        return None
    return reference_docx.name


def _correlation_id_for_relative_label(relative_label: str) -> str:
    digest = hashlib.sha256(relative_label.encode("utf-8")).hexdigest()
    return f"corr_{digest[:16]}"


def _submit_one_source_file_v2(
    *,
    options: CliRouteSubmissionOptionsV2,
    client: CliArtifactClientV2,
    source_path: Path,
    source_format_v2: SourceFormatV2,
    output_format_v2: OutputFormatV2,
    pipeline_used: str,
    companion_payload: CliRouteCompanionPayloadV2,
    message_sink: Callable[[str], None],
    manifest_recorder: CliIncrementalManifestRecorderV2,
) -> _SingleSubmissionOutcomeV2:
    relative_label = relative_source_label(options.source, source_path)
    target_path = _target_path_for_source_file(
        source_root=options.source,
        source_path=source_path,
        output_dir=options.output_dir,
        output_format=output_format_v2,
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    job_spec = default_job_spec_v2(
        filename=source_path.name,
        source_format=source_format_v2,
        output_format=output_format_v2,
        css_filenames=(
            companion_payload.css_filenames if output_format_v2 == OutputFormatV2.PDF else []
        ),
        reference_docx_filename=_reference_docx_filename_v2(
            output_format=output_format_v2,
            reference_docx=options.reference_docx,
        ),
        acceleration_policy=options.acceleration_policy,
        backend_strategy=options.backend_strategy,
        ocr_mode=options.ocr_mode,
        ocr_engine=options.ocr_engine,
        ocr_languages=list(options.ocr_languages),
        table_mode=options.table_mode,
        normalize=options.normalize,
    )
    file_sha256 = sha256_bytes(source_path.read_bytes())
    idempotency_key = idempotency_key_for_v2_request(
        filename=source_path.name,
        file_sha256=file_sha256,
        spec_payload=job_spec,
        resources_sha256=companion_payload.resources_sha256,
        reference_docx_sha256=companion_payload.reference_docx_sha256,
    )
    correlation_id = _correlation_id_for_relative_label(relative_label)
    progress_message_callback = progress_callback_for_source_v2(
        relative_label=relative_label,
        message_sink=message_sink,
    )

    def _progress_callback(payload: dict[str, object]) -> None:
        manifest_recorder.record_progress_payload(
            relative_label=relative_label,
            route=options.route,
            pipeline_used=pipeline_used,
            payload=payload,
        )
        progress_message_callback(payload)

    try:
        v2_outcome: ArtifactOutcomeV2 = client.convert_upload_to_artifact(
            source_path=source_path,
            job_spec=job_spec,
            idempotency_key=idempotency_key,
            wait_seconds=options.wait_seconds,
            max_poll_seconds=options.max_poll_seconds,
            stall_timeout_seconds=float(options.stall_timeout_seconds),
            retry_mode=options.retry_mode,
            correlation_id=correlation_id,
            resources_zip_bytes=companion_payload.resources_zip_bytes,
            reference_docx_bytes=companion_payload.reference_docx_bytes,
            progress_callback=_progress_callback,
        )
        target_path.write_bytes(v2_outcome.artifact_bytes)
        message_sink(f"✓ Converted {relative_label} -> {target_path}")
        return _SingleSubmissionOutcomeV2(
            entry=build_success_manifest_entry_v2(
                source_file_path=relative_label,
                route=options.route,
                pipeline_used=pipeline_used,
                job_id=v2_outcome.job_id,
                output_path=target_path,
                formula_authority=dict(v2_outcome.formula_authority),
            ),
            failed=False,
        )
    except KeyboardInterrupt:
        manifest_recorder.mark_interrupted(
            relative_label=relative_label,
            route=options.route,
            pipeline_used=pipeline_used,
        )
        raise
    except ClientErrorV2 as exc:
        return _entry_from_client_error_v2(
            options=options,
            exc=exc,
            relative_label=relative_label,
            pipeline_used=pipeline_used,
            message_sink=message_sink,
        )


def _entry_from_client_error_v2(
    *,
    options: CliRouteSubmissionOptionsV2,
    exc: ClientErrorV2,
    relative_label: str,
    pipeline_used: str,
    message_sink: Callable[[str], None],
) -> _SingleSubmissionOutcomeV2:
    if exc.code == "job_poll_window_exceeded" and exc.job_id is not None:
        message_sink(
            "… Submitted and still running (max poll window exceeded) "
            f"{relative_label}: {exc.job_id}. "
            "Use status/result endpoints to fetch completion later."
        )
        return _SingleSubmissionOutcomeV2(
            entry=build_running_manifest_entry_v2(
                source_file_path=relative_label,
                route=options.route,
                pipeline_used=pipeline_used,
                job_id=exc.job_id,
                error_code=exc.code,
            ),
            failed=False,
        )
    if exc.code == "job_timeout" and exc.job_id is not None:
        message_sink(
            "✗ Submitted but appears stalled (heartbeat/progress stale) "
            f"{relative_label}: {exc.job_id}. "
            "Check job status and consider cancel/retry if it does not recover."
        )
        return _SingleSubmissionOutcomeV2(
            entry=build_running_manifest_entry_v2(
                source_file_path=relative_label,
                route=options.route,
                pipeline_used=pipeline_used,
                job_id=exc.job_id,
                error_code=exc.code,
            ),
            failed=True,
        )

    message_sink(f"✗ Failed {relative_label}: {exc.code} ({exc.message})")
    return _SingleSubmissionOutcomeV2(
        entry=build_failed_manifest_entry_v2(
            source_file_path=relative_label,
            route=options.route,
            pipeline_used=pipeline_used,
            job_id=exc.job_id,
            error_code=exc.code,
        ),
        failed=True,
    )
