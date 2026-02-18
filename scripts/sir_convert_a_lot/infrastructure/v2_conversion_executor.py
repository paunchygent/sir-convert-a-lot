"""Service API v2 conversion execution helpers.

Purpose:
    Encapsulate v2 pipeline execution (html/md/pdf inputs to pdf/docx outputs),
    including resources handling, backend routing (for PDF sources), and
    deterministic error mapping.

Relationships:
    - Called by `infrastructure.runtime_engine_v2` during async job execution.
    - Uses v1 PDF conversion backends (Docling/PyMuPDF) for PDF->Markdown stage.
    - Uses Pandoc/WeasyPrint converters for HTML/Markdown transforms.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    ConversionSpec,
    ExecutionSpec,
    JobSpec,
    RetentionSpec,
    SourceKind,
    SourceSpec,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    validate_acceleration_policy as validate_acceleration_policy_rule,
)
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    validate_backend_strategy as validate_backend_strategy_rule,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    BackendGpuUnavailableError,
    BackendInputError,
    ConversionBackend,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import (
    GpuRuntimeProbeResult,
    probe_torch_gpu_runtime,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_html_to_docx import (
    HtmlToDocxConversionError,
    convert_html_to_docx,
)
from scripts.sir_convert_a_lot.infrastructure.pandoc_markdown_to_html import (
    MarkdownToHtmlConversionError,
    convert_markdown_to_html,
)
from scripts.sir_convert_a_lot.infrastructure.resources_zip import (
    ResourcesZipError,
    extract_resources_zip,
    reset_directory,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_conversion import execute_job_conversion
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.weasyprint_html_to_pdf import (
    HtmlToPdfConversionError,
    convert_html_to_pdf,
)


@dataclass(frozen=True)
class V2ExecutionResult:
    """Successful execution outcome for a v2 conversion job."""

    artifact_bytes: bytes
    pipeline_used: str
    backend_used: str | None
    acceleration_used: str | None
    warnings: list[str]
    phase_timings_ms: dict[str, int]
    options_fingerprint: str


def fingerprint_job_options(spec: JobSpecV2) -> str:
    """Return a deterministic SHA256 fingerprint for a v2 job spec."""
    normalized = json.dumps(spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _resolve_reference_docx(*, job: StoredJobV2, workdir: Path) -> Path | None:
    if job.reference_docx_path is not None:
        return job.reference_docx_path
    filename = job.spec.conversion.reference_docx_filename
    if filename is None:
        return None
    candidate = workdir / filename
    return candidate if candidate.exists() else None


def _validate_backend_strategy_v1(spec: JobSpec) -> None:
    violation = validate_backend_strategy_rule(spec)
    if violation is None:
        return
    raise ServiceError(
        status_code=violation.status_code,
        code=violation.code,
        message=violation.message,
        retryable=violation.retryable,
        details=violation.details,
    )


def _validate_acceleration_policy_v1(
    *, spec: JobSpec, config: ServiceConfig
) -> GpuRuntimeProbeResult | None:
    violation = validate_acceleration_policy_rule(
        spec,
        gpu_available=config.gpu_available,
        allow_cpu_only=config.allow_cpu_only,
        allow_cpu_fallback=config.allow_cpu_fallback,
    )
    if violation is not None:
        raise ServiceError(
            status_code=violation.status_code,
            code=violation.code,
            message=violation.message,
            retryable=violation.retryable,
            details=violation.details,
        )

    probe: GpuRuntimeProbeResult | None = None
    if (
        config.gpu_available
        and spec.execution.acceleration_policy
        in {AccelerationPolicy.GPU_REQUIRED, AccelerationPolicy.GPU_PREFER}
        and spec.conversion.backend_strategy in {BackendStrategy.AUTO, BackendStrategy.DOCLING}
    ):
        probe = probe_torch_gpu_runtime()
        if not (probe.is_available and probe.runtime_kind in {"rocm", "cuda"}):
            raise ServiceError(
                status_code=503,
                code="gpu_not_available",
                message=(
                    "GPU runtime is unavailable for the selected backend under GPU-required policy."
                ),
                retryable=True,
                details={
                    "reason": "backend_gpu_runtime_unavailable",
                    "backend": "docling",
                    "runtime_kind": probe.runtime_kind,
                    "hip_version": probe.hip_version,
                    "cuda_version": probe.cuda_version,
                },
            )
    return probe


def _prepare_workdir(job: StoredJobV2) -> tuple[Path, Path]:
    raw_dir = job.upload_path.parent
    workdir = raw_dir / "workdir"
    reset_directory(workdir)

    if job.resources_zip_path is not None:
        try:
            extract_resources_zip(zip_path=job.resources_zip_path, output_dir=workdir)
        except ResourcesZipError as exc:
            raise ServiceError(
                status_code=422,
                code=exc.code,
                message=exc.message,
                retryable=False,
            ) from exc

    source_name = Path(job.source_filename).name
    input_path = workdir / source_name
    input_path.write_bytes(job.upload_path.read_bytes())
    return workdir, input_path


def _map_converter_error(exc: Exception) -> ServiceError:
    if isinstance(exc, MarkdownToHtmlConversionError):
        retryable = exc.code.endswith("not_installed")
        return ServiceError(
            status_code=503 if retryable else 500,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, HtmlToPdfConversionError):
        retryable = exc.code.endswith("not_installed") or exc.code.endswith("deps_missing")
        return ServiceError(
            status_code=503 if retryable else 500,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    if isinstance(exc, HtmlToDocxConversionError):
        retryable = exc.code.endswith("not_installed")
        return ServiceError(
            status_code=503 if retryable else 500,
            code=exc.code,
            message=exc.message,
            retryable=retryable,
        )
    raise AssertionError(f"Unhandled converter error type: {type(exc).__name__}")


def execute_v2_job_conversion(
    *,
    job: StoredJobV2,
    config: ServiceConfig,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
) -> V2ExecutionResult:
    """Execute one v2 job conversion and return artifact bytes + metadata."""
    workdir, input_path = _prepare_workdir(job)
    warnings: list[str] = []
    phase_timings_ms: dict[str, int] = {}
    options_fingerprint = fingerprint_job_options(job.spec)

    pipeline_used: str
    backend_used: str | None = None
    acceleration_used: str | None = None

    if job.source_format == SourceFormatV2.HTML and job.output_format == OutputFormatV2.PDF:
        pipeline_used = "html_to_pdf_v2"
        backend_used = "weasyprint"
        css_paths = tuple((workdir / name) for name in job.spec.conversion.css_filenames)
        for css_path in css_paths:
            if not css_path.exists():
                raise ServiceError(
                    status_code=422,
                    code="css_not_found",
                    message=f"CSS file not found in resources bundle: {css_path.name}",
                    retryable=False,
                    details={"css_filename": css_path.name},
                )
        try:
            convert_html_to_pdf(
                html_path=input_path,
                output_pdf_path=job.artifact_path,
                css_paths=css_paths,
                base_url=workdir.resolve().as_uri(),
            )
        except (HtmlToPdfConversionError,) as exc:
            raise _map_converter_error(exc) from exc

    elif job.source_format == SourceFormatV2.HTML and job.output_format == OutputFormatV2.DOCX:
        pipeline_used = "html_to_docx_v2"
        backend_used = "pandoc"
        reference_docx = _resolve_reference_docx(job=job, workdir=workdir)
        try:
            convert_html_to_docx(
                html_path=input_path,
                output_docx_path=job.artifact_path,
                resource_root=workdir,
                reference_docx_path=reference_docx,
            )
        except (HtmlToDocxConversionError,) as exc:
            raise _map_converter_error(exc) from exc

    elif job.source_format == SourceFormatV2.MD and job.output_format == OutputFormatV2.PDF:
        pipeline_used = "md_to_pdf_v2"
        backend_used = "pandoc+weasyprint"
        css_paths = tuple((workdir / name) for name in job.spec.conversion.css_filenames)
        for css_path in css_paths:
            if not css_path.exists():
                raise ServiceError(
                    status_code=422,
                    code="css_not_found",
                    message=f"CSS file not found in resources bundle: {css_path.name}",
                    retryable=False,
                    details={"css_filename": css_path.name},
                )

        intermediate_html = workdir / input_path.with_suffix(".html").name
        try:
            convert_markdown_to_html(
                markdown_path=input_path,
                output_html_path=intermediate_html,
            )
            convert_html_to_pdf(
                html_path=intermediate_html,
                output_pdf_path=job.artifact_path,
                css_paths=css_paths,
                base_url=workdir.resolve().as_uri(),
            )
        except (MarkdownToHtmlConversionError, HtmlToPdfConversionError) as exc:
            raise _map_converter_error(exc) from exc

    elif job.source_format == SourceFormatV2.MD and job.output_format == OutputFormatV2.DOCX:
        pipeline_used = "md_to_docx_v2"
        backend_used = "pandoc"
        reference_docx = _resolve_reference_docx(job=job, workdir=workdir)
        intermediate_html = workdir / input_path.with_suffix(".html").name
        try:
            convert_markdown_to_html(
                markdown_path=input_path,
                output_html_path=intermediate_html,
            )
            convert_html_to_docx(
                html_path=intermediate_html,
                output_docx_path=job.artifact_path,
                resource_root=workdir,
                reference_docx_path=reference_docx,
            )
        except (MarkdownToHtmlConversionError, HtmlToDocxConversionError) as exc:
            raise _map_converter_error(exc) from exc

    elif job.source_format == SourceFormatV2.PDF and job.output_format == OutputFormatV2.DOCX:
        pipeline_used = "pdf_to_docx_v2"
        if job.spec.pdf_options is None or job.spec.execution is None:
            raise ServiceError(
                status_code=500,
                code="invalid_job_spec",
                message="v2 job spec is missing required pdf_options/execution for pdf routes.",
                retryable=False,
            )

        v1_spec = JobSpec(
            api_version="v1",
            source=SourceSpec(kind=SourceKind.UPLOAD, filename=job.source_filename),
            conversion=ConversionSpec(
                output_format="md",
                backend_strategy=job.spec.pdf_options.backend_strategy,
                ocr_mode=job.spec.pdf_options.ocr_mode,
                table_mode=job.spec.pdf_options.table_mode,
                normalize=job.spec.pdf_options.normalize,
            ),
            execution=ExecutionSpec(
                acceleration_policy=job.spec.execution.acceleration_policy,
                priority=job.spec.execution.priority,
                document_timeout_seconds=job.spec.execution.document_timeout_seconds,
            ),
            retention=RetentionSpec(pin=job.spec.retention.pin),
        )
        _validate_backend_strategy_v1(v1_spec)
        probe = _validate_acceleration_policy_v1(spec=v1_spec, config=config)

        source_bytes = job.upload_path.read_bytes()
        if not source_bytes.startswith(b"%PDF"):
            raise ServiceError(
                status_code=422,
                code="pdf_unreadable",
                message="Uploaded file is not a readable PDF.",
                retryable=False,
            )

        try:
            markdown_content, pdf_metadata, pdf_warnings, pdf_timings = execute_job_conversion(
                spec=v1_spec,
                source_filename=job.source_filename,
                source_bytes=source_bytes,
                gpu_available=config.gpu_available,
                gpu_runtime_probe=probe,
                docling_backend=docling_backend,
                pymupdf_backend=pymupdf_backend,
            )
        except BackendGpuUnavailableError as exc:
            raise ServiceError(
                status_code=503,
                code="gpu_not_available",
                message=(
                    "GPU runtime is unavailable for the selected backend under GPU-required policy."
                ),
                retryable=True,
                details={
                    "reason": "backend_gpu_runtime_unavailable",
                    "backend": "docling",
                    "runtime_kind": exc.probe.runtime_kind,
                    "hip_version": exc.probe.hip_version,
                    "cuda_version": exc.probe.cuda_version,
                },
            ) from exc
        except BackendInputError as exc:
            raise ServiceError(
                status_code=422,
                code="pdf_unreadable",
                message=f"Uploaded PDF could not be converted: {exc}",
                retryable=False,
            ) from exc
        except BackendExecutionError as exc:
            raise ServiceError(
                status_code=500,
                code="conversion_internal_error",
                message=f"Unexpected backend conversion failure: {exc}",
                retryable=True,
            ) from exc

        backend_used = pdf_metadata.backend_used
        acceleration_used = pdf_metadata.acceleration_used
        warnings.extend(pdf_warnings)
        phase_timings_ms.update(pdf_timings)

        intermediate_md = workdir / input_path.with_suffix(".md").name
        intermediate_md.write_text(markdown_content, encoding="utf-8")
        intermediate_html = workdir / intermediate_md.with_suffix(".html").name
        reference_docx = _resolve_reference_docx(job=job, workdir=workdir)
        try:
            convert_markdown_to_html(
                markdown_path=intermediate_md,
                output_html_path=intermediate_html,
            )
            convert_html_to_docx(
                html_path=intermediate_html,
                output_docx_path=job.artifact_path,
                resource_root=workdir,
                reference_docx_path=reference_docx,
            )
        except (MarkdownToHtmlConversionError, HtmlToDocxConversionError) as exc:
            raise _map_converter_error(exc) from exc

    else:
        raise ServiceError(
            status_code=422,
            code="unsupported_route",
            message=(f"Unsupported route: {job.source_format.value} -> {job.output_format.value}."),
            retryable=False,
        )

    artifact_bytes = job.artifact_path.read_bytes()
    if len(artifact_bytes) == 0:
        raise ServiceError(
            status_code=500,
            code="artifact_empty",
            message="Conversion produced an empty artifact file.",
            retryable=True,
        )

    return V2ExecutionResult(
        artifact_bytes=artifact_bytes,
        pipeline_used=pipeline_used,
        backend_used=backend_used,
        acceleration_used=acceleration_used,
        warnings=warnings,
        phase_timings_ms=phase_timings_ms,
        options_fingerprint=options_fingerprint,
    )
