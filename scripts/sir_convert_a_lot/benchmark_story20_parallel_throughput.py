"""Benchmark Task 72 parallel PDF throughput evidence for Story 20.

Purpose:
    Execute a deterministic local benchmark that compares serial and bounded
    parallel PDF chunk processing using the real Task 72 executor path.

Relationships:
    - Uses `scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor`
      to exercise the checkpointed PDF executor.
    - Temporarily patches
      `scripts.sir_convert_a_lot.infrastructure.v2_pdf_checkpointed_executor`
      chunk conversion to keep timing deterministic.
    - Writes generated benchmark artifacts under `build/benchmarks/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.domain.specs import JobStatus, TableMode
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure import v2_pdf_checkpointed_executor
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    ConversionRequest,
    ConversionResultData,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.v2_conversion_executor import (
    V2ExecutionResult,
    execute_v2_job_conversion,
)

DEFAULT_OUTPUT_JSON = Path("build/benchmarks/story-20/task-72-parallel-throughput-local.json")
DEFAULT_DATA_ROOT = Path("build/benchmarks/story-20/task-72-parallel-throughput-runtime")


class ProfileSummary(TypedDict):
    """One benchmark profile summary."""

    profile: str
    repeats: int
    durations_seconds: list[float]
    p50_duration_seconds: float
    min_duration_seconds: float
    max_duration_seconds: float
    artifact_sha256: str
    byte_count: int
    result_metadata: dict[str, int | bool | str | None]


class BenchmarkPayload(TypedDict):
    """Top-level benchmark payload."""

    benchmark_id: str
    generated_at: str
    config: dict[str, int | float]
    profiles: list[ProfileSummary]
    comparison: dict[str, float | bool]


class _UnusedBackend:
    """Backend double that must never be called by the stubbed PDF benchmark."""

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        del request
        raise AssertionError("PDF backend conversion should not be invoked in this benchmark.")


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _build_pdf_bytes(*, total_pages: int) -> bytes:
    import pymupdf

    document = pymupdf.open()
    try:
        for page_number in range(1, total_pages + 1):
            page = document.new_page()
            if page is None:
                raise RuntimeError("PyMuPDF returned no page for new_page().")
            page.insert_text((72, 72), f"page {page_number}", fontsize=12)
        return bytes(document.tobytes())
    finally:
        document.close()


def _page_numbers_from_chunk(source_bytes: bytes) -> list[int]:
    import pymupdf

    document = pymupdf.open(stream=source_bytes, filetype="pdf")
    try:
        page_numbers: list[int] = []
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            if page is None:
                raise RuntimeError("PyMuPDF returned no page for load_page().")
            text = page.get_text("text")
            match = re.search(r"page\s+(\d+)", text.lower())
            if match is None:
                raise RuntimeError(f"Could not parse page number from chunk text: {text!r}")
            page_numbers.append(int(match.group(1)))
        return page_numbers
    finally:
        document.close()


def _build_job(tmp_root: Path, *, source_bytes: bytes, job_id: str) -> StoredJobV2:
    raw_dir = tmp_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    upload_path = raw_dir / f"{job_id}.pdf"
    artifact_path = raw_dir / f"{job_id}.md"
    upload_path.write_bytes(source_bytes)
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {
                "kind": "upload",
                "filename": f"{job_id}.pdf",
                "format": SourceFormatV2.PDF.value,
            },
            "conversion": {
                "output_format": OutputFormatV2.MD.value,
                "css_filenames": [],
                "reference_docx_filename": None,
            },
            "pdf_options": {
                "backend_strategy": "auto",
                "ocr_mode": "off",
                "table_mode": "fast",
                "normalize": "standard",
            },
            "execution": {
                "acceleration_policy": "cpu_only",
                "priority": "normal",
                "document_timeout_seconds": 1800,
            },
            "retention": {"pin": False},
        }
    )
    now = datetime.now(UTC)
    return StoredJobV2(
        job_id=job_id,
        spec=spec,
        source_filename=upload_path.name,
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.MD,
        upload_path=upload_path,
        resources_zip_path=None,
        reference_docx_path=None,
        artifact_path=artifact_path,
        status=JobStatus.QUEUED,
        created_at=now,
        updated_at=now,
        expires_at=None,
        progress_stage="queued",
    )


def _stub_chunk_conversion(*, stub_work_seconds: float):
    def _convert(
        *,
        spec,
        source_filename: str,
        source_bytes: bytes,
        gpu_available: bool,
        gpu_runtime_probe,
        docling_backend,
        pymupdf_backend,
        ocr_engine=None,
        ocr_languages=(),
        ocr_use_gpu=None,
    ) -> tuple[str, object, list[str], dict[str, int]]:
        del (
            spec,
            source_filename,
            gpu_available,
            gpu_runtime_probe,
            docling_backend,
            pymupdf_backend,
            ocr_engine,
            ocr_languages,
            ocr_use_gpu,
        )
        if stub_work_seconds > 0:
            time.sleep(stub_work_seconds)
        page_numbers = _page_numbers_from_chunk(source_bytes)
        markdown = "".join(f"# page {page_number}\n" for page_number in page_numbers)
        return (
            markdown,
            ConversionMetadata(
                backend_used="stubbed",
                acceleration_used="cpu",
                ocr_enabled=False,
                table_mode=TableMode.FAST,
                options_fingerprint="sha256:task72-benchmark-stub",
            ),
            [],
            {"ocr_layout_extract_ms": 5, "markdown_normalize_ms": 2},
        )

    return _convert


def _artifact_sha256(artifact_bytes: bytes) -> str:
    return f"sha256:{hashlib.sha256(artifact_bytes).hexdigest()}"


def _resolve_metadata(result: V2ExecutionResult) -> dict[str, int | bool | str | None]:
    return {
        "parallel_enabled": result.parallel_enabled,
        "max_chunk_workers": result.max_chunk_workers,
        "chunk_size_pages": result.chunk_size_pages,
        "effective_gpu_stage_limit": result.effective_gpu_stage_limit,
        "scheduling_mode": result.scheduling_mode,
    }


def _median(sorted_values: list[float]) -> float:
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[midpoint]
    return (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2.0


def _run_profile(
    *,
    profile: str,
    runtime_root: Path,
    pdf_bytes: bytes,
    repeats: int,
    chunk_size_pages: int,
    max_chunk_workers: int,
    stub_work_seconds: float,
) -> ProfileSummary:
    durations: list[float] = []
    last_result: V2ExecutionResult | None = None
    original_execute = v2_pdf_checkpointed_executor.execute_job_conversion
    v2_pdf_checkpointed_executor.execute_job_conversion = _stub_chunk_conversion(
        stub_work_seconds=stub_work_seconds
    )
    try:
        for run_index in range(repeats):
            run_root = runtime_root / profile / f"run-{run_index:02d}"
            job = _build_job(run_root, source_bytes=pdf_bytes, job_id=f"{profile}-{run_index:02d}")
            config = ServiceConfig(
                api_key="benchmark-key",
                data_root=run_root / "service_data",
                gpu_available=False,
                allow_cpu_only=True,
                allow_cpu_fallback=False,
                enable_supervisor=False,
                processing_delay_seconds=0.0,
                enable_parallel_pdf_chunks=(profile == "parallel"),
                max_chunk_workers=max_chunk_workers,
                pdf_chunk_size_pages=chunk_size_pages,
                gpu_stage_max_concurrency=max_chunk_workers,
            )
            started = time.perf_counter()
            last_result = execute_v2_job_conversion(
                job=job,
                config=config,
                docling_backend=_UnusedBackend(),
                pymupdf_backend=_UnusedBackend(),
            )
            durations.append(round(max(0.0, time.perf_counter() - started), 6))
    finally:
        v2_pdf_checkpointed_executor.execute_job_conversion = original_execute

    if last_result is None:
        raise RuntimeError(f"{profile} profile produced no benchmark result.")
    sorted_durations = sorted(durations)
    return {
        "profile": profile,
        "repeats": repeats,
        "durations_seconds": durations,
        "p50_duration_seconds": round(_median(sorted_durations), 6),
        "min_duration_seconds": round(sorted_durations[0], 6),
        "max_duration_seconds": round(sorted_durations[-1], 6),
        "artifact_sha256": _artifact_sha256(last_result.artifact_bytes),
        "byte_count": len(last_result.artifact_bytes),
        "result_metadata": _resolve_metadata(last_result),
    }


def run_benchmark(
    *,
    output_json: Path,
    data_root: Path,
    total_pages: int = 8,
    repeats: int = 5,
    chunk_size_pages: int = 1,
    max_chunk_workers: int = 4,
    stub_work_seconds: float = 0.03,
) -> BenchmarkPayload:
    """Run the deterministic Task 72 throughput benchmark and return the payload."""
    enforce_generated_output_path(output_json, label="output_json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    data_root.mkdir(parents=True, exist_ok=True)

    pdf_bytes = _build_pdf_bytes(total_pages=total_pages)
    serial_summary = _run_profile(
        profile="serial",
        runtime_root=data_root,
        pdf_bytes=pdf_bytes,
        repeats=repeats,
        chunk_size_pages=chunk_size_pages,
        max_chunk_workers=max_chunk_workers,
        stub_work_seconds=stub_work_seconds,
    )
    parallel_summary = _run_profile(
        profile="parallel",
        runtime_root=data_root,
        pdf_bytes=pdf_bytes,
        repeats=repeats,
        chunk_size_pages=chunk_size_pages,
        max_chunk_workers=max_chunk_workers,
        stub_work_seconds=stub_work_seconds,
    )

    serial_p50 = serial_summary["p50_duration_seconds"]
    parallel_p50 = parallel_summary["p50_duration_seconds"]
    improvement_percent = round(((serial_p50 - parallel_p50) / serial_p50) * 100.0, 4)
    payload: BenchmarkPayload = {
        "benchmark_id": "task-72-parallel-throughput",
        "generated_at": _utc_now_iso(),
        "config": {
            "total_pages": total_pages,
            "repeats": repeats,
            "chunk_size_pages": chunk_size_pages,
            "max_chunk_workers": max_chunk_workers,
            "stub_work_seconds": round(stub_work_seconds, 6),
        },
        "profiles": [serial_summary, parallel_summary],
        "comparison": {
            "byte_identical_to_serial": (
                serial_summary["artifact_sha256"] == parallel_summary["artifact_sha256"]
            ),
            "p50_wall_clock_improvement_percent": improvement_percent,
        },
    }
    output_json.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
    return payload


def main() -> None:
    """Parse CLI args and write Task 72 throughput benchmark evidence."""
    parser = argparse.ArgumentParser(description="Run Task 72 parallel throughput benchmark.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--total-pages", type=int, default=8)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--chunk-size-pages", type=int, default=1)
    parser.add_argument("--max-chunk-workers", type=int, default=4)
    parser.add_argument("--stub-work-seconds", type=float, default=0.03)
    args = parser.parse_args()

    payload = run_benchmark(
        output_json=args.output_json,
        data_root=args.data_root,
        total_pages=max(1, args.total_pages),
        repeats=max(1, args.repeats),
        chunk_size_pages=max(1, args.chunk_size_pages),
        max_chunk_workers=max(1, args.max_chunk_workers),
        stub_work_seconds=max(0.0, args.stub_work_seconds),
    )
    print(
        "benchmark-written",
        json.dumps(
            {
                "output_json": args.output_json.as_posix(),
                "p50_wall_clock_improvement_percent": payload["comparison"][
                    "p50_wall_clock_improvement_percent"
                ],
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()
