"""Docling page-window replay bounded Docling page-window replay diagnostics.

Purpose:
    Reproduce slow PDF page windows with hard parent-process budgets, Docling
    document timeouts, and Python stack dumps so pathological chunks can be
    localized without waiting for the original full wall-clock duration.

Relationships:
    - Exercises the production PDF conversion backend through
      `infrastructure.runtime_conversion`.
    - Uses `v2_pdf_chunk_conversion.extract_pdf_page_range_bytes_v2` to match
      checkpointed page-window extraction.
    - Writes sanitized evidence for
      `diagnose-and-harden-pdf-page-window-unit-of-work-head-of-line-blocking`.
"""

from __future__ import annotations

import argparse
import faulthandler
import hashlib
import os
import time
import traceback
from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.devops.docling_page_window_replay_runtime import (
    DEFAULT_ATTEMPT_TIMEOUT_SECONDS,
    DEFAULT_INCIDENT_WINDOW,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_TERMINATE_GRACE_SECONDS,
    DEFAULT_TOTAL_TIMEOUT_SECONDS,
    TAIL_CHARS,
    RunSettings,
    build_locator_windows,
    parse_page_window,
    resolve_ocr_engine,
    resolve_ocr_languages,
    run_replay,
    tail_text,
    write_json,
)
from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    ConversionSpec,
    ExecutionSpec,
    JobSpec,
    NormalizeMode,
    OcrMode,
    Priority,
    RetentionSpec,
    SourceKind,
    SourceSpec,
    TableMode,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import OcrEngineV2
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendGpuUnavailableError,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.docling_backend import DoclingConversionBackend
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_events import (
    DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR,
    DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR,
)
from scripts.sir_convert_a_lot.infrastructure.docling_runtime_inventory import (
    build_docling_runtime_inventory,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import (
    GpuRuntimeProbeResult,
    probe_torch_gpu_runtime,
)
from scripts.sir_convert_a_lot.infrastructure.pymupdf_backend import PyMuPdfConversionBackend
from scripts.sir_convert_a_lot.infrastructure.runtime_conversion import execute_job_conversion
from scripts.sir_convert_a_lot.infrastructure.v2_pdf_chunk_conversion import (
    extract_pdf_page_range_bytes_v2,
)


def child_convert(args: argparse.Namespace) -> int:
    """Run one conversion attempt inside a killable child process."""
    output_json = Path(str(args.output_json))
    stack_path = Path(str(args.stack_dump_path))
    stack_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ[DOCLING_FORMULA_DIAGNOSTICS_JSONL_ENV_VAR] = str(args.formula_diagnostics_jsonl)
    if bool(args.single_formula_items):
        os.environ[DOCLING_FORMULA_SINGLE_ITEM_REPLAY_ENV_VAR] = "1"
    stack_file = stack_path.open("w", encoding="utf-8")
    faulthandler.enable(file=stack_file)
    faulthandler.dump_traceback_later(
        timeout=float(args.stack_dump_after_seconds),
        repeat=False,
        file=stack_file,
    )
    started = time.perf_counter()
    try:
        payload = convert_child_payload(args=args, started=started)
        write_json(output_json, payload)
        return 0 if payload.get("status") == "succeeded" else 1
    finally:
        faulthandler.cancel_dump_traceback_later()
        stack_file.close()


def convert_child_payload(*, args: argparse.Namespace, started: float) -> dict[str, object]:
    """Convert one page window and return sanitized diagnostic payload."""
    source_pdf = Path(str(args.source_pdf))
    start_page = int(args.start_page)
    end_page = int(args.end_page)
    docling_backend: DoclingConversionBackend | None = None
    try:
        import pymupdf

        document = pymupdf.open(source_pdf.as_posix())
        try:
            source_bytes = extract_pdf_page_range_bytes_v2(
                document=document,
                start_page=start_page,
                end_page=end_page,
            )
        finally:
            document.close()

        spec = build_job_spec_from_args(args=args, source_pdf=source_pdf)
        probe = probe_torch_gpu_runtime()
        docling_backend = DoclingConversionBackend(
            easyocr_model_storage_directory=args.easyocr_model_storage_directory,
            easyocr_download_enabled=False,
        )
        if args.formula_preset_only is not None:
            return convert_formula_preset_only_payload(
                args=args,
                started=started,
                source_pdf=source_pdf,
                source_bytes=source_bytes,
                probe=probe,
                docling_backend=docling_backend,
            )
        markdown, metadata, warnings, phase_timings = execute_job_conversion(
            spec=spec,
            source_filename=f"{source_pdf.name}#pages={start_page}-{end_page}",
            source_bytes=source_bytes,
            gpu_available=True,
            gpu_runtime_probe=probe,
            docling_backend=docling_backend,
            pymupdf_backend=PyMuPdfConversionBackend(),
            ocr_engine=resolve_ocr_engine(str(args.ocr_engine))
            if args.ocr_engine is not None
            else None,
            ocr_languages=tuple(str(language) for language in args.ocr_language),
            ocr_use_gpu=spec.execution.acceleration_policy != AccelerationPolicy.CPU_ONLY,
        )
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        markdown_path = persist_markdown_evidence(args=args, markdown=markdown)
        return {
            "status": "succeeded",
            "start_page": start_page,
            "end_page": end_page,
            "elapsed_ms": elapsed_ms,
            "markdown_char_count": len(markdown),
            "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
            "markdown_path": markdown_path.as_posix(),
            "backend_used": metadata.backend_used,
            "acceleration_used": metadata.acceleration_used,
            "ocr_enabled": metadata.ocr_enabled,
            "ocr_engine_used": metadata.ocr_engine_used,
            "ocr_languages_used": list(metadata.ocr_languages_used),
            "warnings": warnings,
            "phase_timings_ms": phase_timings,
            "gpu_probe": probe.as_details(),
            "docling_runtime": build_docling_runtime_inventory(),
            "docling_formula_diagnostics": docling_backend.last_formula_diagnostics(),
        }
    except Exception as exc:
        elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
        docling_formula_diagnostics = (
            docling_backend.last_formula_diagnostics() if docling_backend is not None else {}
        )
        return {
            "status": "failed",
            "start_page": start_page,
            "end_page": end_page,
            "elapsed_ms": elapsed_ms,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "traceback_tail": tail_text(traceback.format_exc(), TAIL_CHARS),
            "docling_runtime": build_docling_runtime_inventory(),
            "docling_formula_diagnostics": docling_formula_diagnostics,
        }


def convert_formula_preset_only_payload(
    *,
    args: argparse.Namespace,
    started: float,
    source_pdf: Path,
    source_bytes: bytes,
    probe: GpuRuntimeProbeResult,
    docling_backend: DoclingConversionBackend,
) -> dict[str, object]:
    """Run a diagnostic-only conversion with one formula preset and no fallback."""
    request = ConversionRequest(
        source_filename=f"{source_pdf.name}#pages={int(args.start_page)}-{int(args.end_page)}",
        source_bytes=source_bytes,
        backend_strategy=BackendStrategy(str(args.backend_strategy)),
        ocr_mode=OcrMode(str(args.ocr_mode)),
        table_mode=TableMode(str(args.table_mode)),
        gpu_available=True,
        ocr_engine=resolve_ocr_engine(str(args.ocr_engine))
        if args.ocr_engine is not None
        else None,
        ocr_languages=tuple(str(language) for language in args.ocr_language),
        ocr_use_gpu=AccelerationPolicy(str(args.acceleration_policy))
        != AccelerationPolicy.CPU_ONLY,
        gpu_runtime_probe=probe,
        document_timeout_seconds=int(args.docling_document_timeout_seconds),
    )
    try:
        acceleration_device, acceleration_used = docling_backend._resolve_acceleration(
            True,
            probe,
        )
    except BackendGpuUnavailableError as exc:
        raise RuntimeError(str(exc)) from exc
    attempt = docling_backend._convert_once(
        request,
        ocr_enabled=False,
        force_full_page_ocr=False,
        acceleration_device=acceleration_device,
        formula_enrichment=True,
        formula_preset=str(args.formula_preset_only),
    )
    elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
    markdown = attempt.markdown_content
    markdown_path = persist_markdown_evidence(args=args, markdown=markdown)
    return {
        "status": "succeeded",
        "start_page": int(args.start_page),
        "end_page": int(args.end_page),
        "elapsed_ms": elapsed_ms,
        "markdown_char_count": len(markdown),
        "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "markdown_path": markdown_path.as_posix(),
        "backend_used": "docling",
        "acceleration_used": acceleration_used,
        "ocr_enabled": False,
        "formula_preset_only": str(args.formula_preset_only),
        "warnings": [],
        "phase_timings_ms": {},
        "gpu_probe": probe.as_details(),
        "docling_runtime": build_docling_runtime_inventory(),
        "docling_formula_diagnostics": docling_backend.last_formula_diagnostics(),
    }


def persist_markdown_evidence(*, args: argparse.Namespace, markdown: str) -> Path:
    """Write replay Markdown beside the child JSON for output-quality review."""
    markdown_path = Path(str(args.output_json)).with_suffix(".md")
    markdown_path.write_text(markdown, encoding="utf-8")
    return markdown_path


def build_job_spec_from_args(*, args: argparse.Namespace, source_pdf: Path) -> JobSpec:
    """Build the v1 PDF job spec used by the backend execution surface."""
    return JobSpec(
        api_version="v1",
        source=SourceSpec(kind=SourceKind.UPLOAD, filename=source_pdf.name),
        conversion=ConversionSpec(
            output_format="md",
            backend_strategy=BackendStrategy(str(args.backend_strategy)),
            ocr_mode=OcrMode(str(args.ocr_mode)),
            table_mode=TableMode(str(args.table_mode)),
            normalize=NormalizeMode(str(args.normalize)),
        ),
        execution=ExecutionSpec(
            acceleration_policy=AccelerationPolicy(str(args.acceleration_policy)),
            priority=Priority(str(args.priority)),
            document_timeout_seconds=int(args.docling_document_timeout_seconds),
        ),
        retention=RetentionSpec(pin=False),
    )


def build_run_settings(args: argparse.Namespace) -> RunSettings:
    """Build typed run settings from argparse output."""
    incident_window = parse_page_window(str(args.incident_window))
    explicit_windows = tuple(parse_page_window(value) for value in args.window)
    windows = explicit_windows if explicit_windows else build_locator_windows(incident_window)
    attempt_timeout_seconds = float(args.attempt_timeout_seconds)
    terminate_grace_seconds = float(args.terminate_grace_seconds)
    docling_timeout_obj = args.docling_document_timeout_seconds
    if docling_timeout_obj is None:
        docling_timeout = max(1, int(attempt_timeout_seconds - terminate_grace_seconds))
    else:
        docling_timeout = int(docling_timeout_obj)
    stack_dump_after_obj = args.stack_dump_after_seconds
    if stack_dump_after_obj is None:
        stack_dump_after = max(1.0, float(docling_timeout))
    else:
        stack_dump_after = float(stack_dump_after_obj)
    ocr_engine = resolve_ocr_engine(str(args.ocr_engine)) if args.ocr_engine is not None else None
    return RunSettings(
        source_pdf=Path(str(args.source_pdf)).expanduser().resolve(),
        output_root=Path(str(args.output_dir)),
        windows=windows,
        attempt_timeout_seconds=attempt_timeout_seconds,
        docling_document_timeout_seconds=docling_timeout,
        stack_dump_after_seconds=stack_dump_after,
        terminate_grace_seconds=terminate_grace_seconds,
        max_total_seconds=float(args.max_total_seconds),
        backend_strategy=BackendStrategy(str(args.backend_strategy)),
        ocr_mode=OcrMode(str(args.ocr_mode)),
        table_mode=TableMode(str(args.table_mode)),
        normalize_mode=NormalizeMode(str(args.normalize)),
        acceleration_policy=AccelerationPolicy(str(args.acceleration_policy)),
        priority=Priority(str(args.priority)),
        ocr_engine=ocr_engine,
        ocr_languages=resolve_ocr_languages(args.ocr_language),
        easyocr_model_storage_directory=args.easyocr_model_storage_directory,
        fail_on_timeout=bool(args.fail_on_timeout),
        formula_preset_only=args.formula_preset_only,
        single_formula_items=bool(args.single_formula_items),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run bounded replay diagnostics.")
    run_parser.add_argument("source_pdf")
    run_parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_ROOT.as_posix())
    run_parser.add_argument("--incident-window", default=DEFAULT_INCIDENT_WINDOW)
    run_parser.add_argument("--window", action="append", default=[])
    run_parser.add_argument(
        "--attempt-timeout-seconds", type=float, default=DEFAULT_ATTEMPT_TIMEOUT_SECONDS
    )
    run_parser.add_argument("--docling-document-timeout-seconds", type=int, default=None)
    run_parser.add_argument("--stack-dump-after-seconds", type=float, default=None)
    run_parser.add_argument(
        "--terminate-grace-seconds", type=float, default=DEFAULT_TERMINATE_GRACE_SECONDS
    )
    run_parser.add_argument(
        "--max-total-seconds", type=float, default=DEFAULT_TOTAL_TIMEOUT_SECONDS
    )
    run_parser.add_argument("--backend-strategy", default=BackendStrategy.AUTO.value)
    run_parser.add_argument("--ocr-mode", default=OcrMode.AUTO.value)
    run_parser.add_argument("--table-mode", default=TableMode.ACCURATE.value)
    run_parser.add_argument("--normalize", default=NormalizeMode.STRICT.value)
    run_parser.add_argument("--acceleration-policy", default=AccelerationPolicy.GPU_REQUIRED.value)
    run_parser.add_argument("--priority", default=Priority.NORMAL.value)
    run_parser.add_argument("--ocr-engine", default=OcrEngineV2.AUTO.value)
    run_parser.add_argument("--ocr-language", action="append", default=[])
    run_parser.add_argument(
        "--easyocr-model-storage-directory",
        default=os.environ.get("SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR"),
    )
    run_parser.add_argument("--fail-on-timeout", action="store_true")
    run_parser.add_argument(
        "--formula-preset-only",
        choices=("codeformulav2", "granite_docling"),
        default=None,
        help="Diagnostic-only: run one formula preset directly without fallback.",
    )
    run_parser.add_argument(
        "--single-formula-items",
        action="store_true",
        help="Diagnostic-only: split Docling formula batches into single items.",
    )

    child_parser = subparsers.add_parser("child", help=argparse.SUPPRESS)
    child_parser.add_argument("source_pdf")
    child_parser.add_argument("--start-page", type=int, required=True)
    child_parser.add_argument("--end-page", type=int, required=True)
    child_parser.add_argument("--output-json", required=True)
    child_parser.add_argument("--stack-dump-path", required=True)
    child_parser.add_argument("--formula-diagnostics-jsonl", required=True)
    child_parser.add_argument("--stack-dump-after-seconds", type=float, required=True)
    child_parser.add_argument("--docling-document-timeout-seconds", type=int, required=True)
    child_parser.add_argument("--backend-strategy", required=True)
    child_parser.add_argument("--ocr-mode", required=True)
    child_parser.add_argument("--table-mode", required=True)
    child_parser.add_argument("--normalize", required=True)
    child_parser.add_argument("--acceleration-policy", required=True)
    child_parser.add_argument("--priority", required=True)
    child_parser.add_argument("--ocr-engine", default=None)
    child_parser.add_argument("--ocr-language", action="append", default=[])
    child_parser.add_argument("--easyocr-model-storage-directory", default=None)
    child_parser.add_argument("--formula-preset-only", default=None)
    child_parser.add_argument("--single-formula-items", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Docling page-window replay replay CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_replay(build_run_settings(args))
    if args.command == "child":
        return child_convert(args)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
