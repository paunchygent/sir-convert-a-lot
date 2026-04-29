"""Task 74 throughput benchmark payload assembly.

Purpose:
    Orchestrate Story 20/Task 74 profile execution, merge Task 76 runtime
    parity evidence, add optional Task 270 dirty-corpus summaries, and write
    JSON plus markdown artifacts. Local in-process execution is command-surface
    smoke/regression only; acceptance benchmark evidence remains Hemma-only.

Relationships:
    - Uses `story20_http_profile` for in-process HTTP profile execution.
    - Uses `story20_corpus` for deterministic synthetic smoke corpus creation
      and hash-verified dirty-corpus execution copies.
    - Uses `dirty_pdf_corpus` for metadata-only manifest validation and
      reportable dirty real-data summaries.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .dirty_pdf_corpus import (
    build_dirty_corpus_report_extension,
    load_dirty_corpus_manifest,
    mark_dirty_corpus_sources_verified,
)
from .output_policy import enforce_generated_output_path
from .story20_corpus import build_verified_dirty_corpus, generate_corpus
from .story20_http_profile import run_profile
from .story20_ocr_runtime import assert_in_process_runtime_supports_requested_ocr
from .story20_profiles import (
    DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES,
    DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS,
    ProfileSpec,
    assert_dirty_corpus_profile_specs_safe,
    build_two_worker_sweep_profiles,
    default_profiles,
)
from .story20_runtime_parity import RuntimeParityInputs, build_runtime_parity_summary
from .story20_throughput_report import write_report
from .story20_throughput_types import (
    BenchmarkPayload,
    CorpusFileRecord,
    DirtyCorpusManifestSummary,
    ProfilePayload,
    RuntimeParitySummary,
    RuntimeSurface,
)

DEFAULT_PAGE_COUNTS = (120, 180, 240)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_runtime_parity_inputs() -> RuntimeParityInputs:
    return RuntimeParityInputs(
        report_json_path=None,
        status=None,
        lane=None,
        expected_revision=None,
        remote_revision=None,
        service_revision=None,
        expected_revision_matches_remote=None,
        service_revision_matches_remote=None,
        live_smoke_passed=None,
        metrics_scan_passed=None,
    )


def _select_tuned_profile(profile_payloads: list[ProfilePayload]) -> ProfilePayload:
    tuned_candidates = [
        profile for profile in profile_payloads[1:] if profile["summary"]["failed_jobs"] == 0
    ]
    return min(
        tuned_candidates or profile_payloads[1:],
        key=lambda profile: profile["summary"]["latency_seconds"]["p50"],
    )


def _build_payload(
    *,
    runtime_mode: str,
    corpus_root: Path,
    page_counts: tuple[int, ...],
    corpus_records_count: int,
    corpus_files: list[CorpusFileRecord],
    acceleration_policy: str,
    ocr_mode: str,
    ocr_engine: str,
    resolved_languages: list[str],
    profile_payloads: list[ProfilePayload],
    runtime_surface: RuntimeSurface,
    runtime_parity: RuntimeParitySummary,
    dirty_corpus_summary: DirtyCorpusManifestSummary | None,
) -> BenchmarkPayload:
    baseline = profile_payloads[0]
    tuned = _select_tuned_profile(profile_payloads)
    baseline_p50 = baseline["summary"]["latency_seconds"]["p50"]
    tuned_p50 = tuned["summary"]["latency_seconds"]["p50"]
    improvement_percent = (
        round(((baseline_p50 - tuned_p50) / baseline_p50) * 100.0, 4) if baseline_p50 > 0 else 0.0
    )
    return {
        "benchmark_id": "task-74-throughput-benchmark",
        "generated_at": _utc_now_iso(),
        "mode": runtime_mode,
        "corpus": {
            "corpus_root": str(corpus_root.resolve()),
            "count": corpus_records_count,
            "page_counts": list(page_counts),
            "files": corpus_files,
        },
        "job_defaults": {
            "acceleration_policy": acceleration_policy,
            "ocr_mode": ocr_mode,
            "ocr_engine": ocr_engine,
            "ocr_languages": resolved_languages,
        },
        "runtime_surface": runtime_surface,
        "runtime_parity": runtime_parity,
        "profiles": profile_payloads,
        "comparison": {
            "baseline_profile": baseline["profile_name"],
            "tuned_profile": tuned["profile_name"],
            "p50_improvement_percent": improvement_percent,
            "meets_target": improvement_percent >= 40.0,
            "recommended_profile": tuned["profile_name"],
            "recommended_defaults": tuned["config"],
            "rollback_conditions": [
                "success_rate drops below 1.0 on the benchmark corpus",
                "peak chunk worker saturation remains >= 0.95 while queue depth stays elevated",
                (
                    "observed gpu_busy_percent stays near 0 or "
                    "gpu_memory_used_percent exceeds safe headroom"
                ),
            ],
        },
        "dirty_corpus": (
            build_dirty_corpus_report_extension(
                manifest=dirty_corpus_summary,
                profiles=profile_payloads,
                runtime_parity=runtime_parity,
            )
            if dirty_corpus_summary is not None
            else None
        ),
    }


def run_benchmark(
    *,
    output_json: Path,
    output_report: Path,
    corpus_root: Path,
    data_root: Path,
    page_counts: tuple[int, ...] = DEFAULT_PAGE_COUNTS,
    api_key: str = "benchmark-key",
    acceleration_policy: str = "gpu_required",
    ocr_mode: str = "force",
    ocr_engine: str = "easyocr",
    ocr_languages: list[str] | None = None,
    max_poll_seconds: float = 7200.0,
    gpu_available: bool = True,
    profiles: list[ProfileSpec] | None = None,
    runtime_mode: str = "in_process_app",
    runtime_host: str | None = None,
    runtime_service_url: str | None = None,
    easyocr_model_storage_directory: str | None = "/opt/easyocr-models",
    runtime_parity_inputs: RuntimeParityInputs | None = None,
    two_worker_sweep: bool = False,
    two_worker_chunk_sizes: tuple[int, ...] = DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES,
    two_worker_gpu_stage_caps: tuple[int, ...] = DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS,
    dirty_corpus_manifest: Path | None = None,
    dirty_corpus_source_root: Path | None = None,
) -> BenchmarkPayload:
    """Run the Task 74 throughput benchmark and return the payload."""
    resolved_languages = list(ocr_languages or ["sv", "en"])
    for path_value, label in [
        (output_json, "output_json"),
        (output_report, "output_report"),
        (corpus_root, "corpus_root"),
        (data_root, "data_root"),
    ]:
        enforce_generated_output_path(path_value, label=label)

    if runtime_mode == "in_process_app":
        assert_in_process_runtime_supports_requested_ocr(
            ocr_mode=ocr_mode,
            ocr_engine=ocr_engine,
            easyocr_model_storage_directory=easyocr_model_storage_directory,
        )
    dirty_corpus_summary = (
        load_dirty_corpus_manifest(dirty_corpus_manifest)
        if dirty_corpus_manifest is not None
        else None
    )
    resolved_profiles = profiles or (
        build_two_worker_sweep_profiles(
            chunk_sizes=two_worker_chunk_sizes,
            gpu_stage_caps=two_worker_gpu_stage_caps,
        )
        if two_worker_sweep
        else default_profiles()
    )
    if dirty_corpus_summary is not None:
        assert_dirty_corpus_profile_specs_safe(resolved_profiles)
        if dirty_corpus_source_root is None:
            raise ValueError(
                "dirty-corpus benchmark evidence requires a private source root so "
                "executed PDF bytes can be verified against the manifest hashes."
            )
        verified_dirty_corpus_source_root = dirty_corpus_source_root

    if dirty_corpus_summary is None:
        corpus_records = generate_corpus(corpus_root=corpus_root, page_counts=page_counts)
        effective_page_counts = page_counts
    else:
        corpus_records = build_verified_dirty_corpus(
            source_root=verified_dirty_corpus_source_root,
            execution_corpus_root=corpus_root,
            manifest=dirty_corpus_summary,
        )
        dirty_corpus_summary = mark_dirty_corpus_sources_verified(dirty_corpus_summary)
        effective_page_counts = tuple(
            entry["page_count"] for entry in dirty_corpus_summary["entries"]
        )
    runtime_surface, runtime_parity = build_runtime_parity_summary(
        inputs=runtime_parity_inputs or _default_runtime_parity_inputs()
    )
    runtime_surface["mode"] = runtime_mode
    runtime_surface["host"] = runtime_host
    runtime_surface["service_url"] = runtime_service_url
    profile_payloads = [
        run_profile(
            profile=profile,
            corpus_root=corpus_root,
            corpus_records=corpus_records,
            data_root=data_root,
            api_key=api_key,
            acceleration_policy=acceleration_policy,
            ocr_mode=ocr_mode,
            ocr_engine=ocr_engine,
            ocr_languages=resolved_languages,
            max_poll_seconds=max_poll_seconds,
            gpu_available=gpu_available,
            easyocr_model_storage_directory=easyocr_model_storage_directory,
        )
        for profile in resolved_profiles
    ]
    payload = _build_payload(
        runtime_mode=runtime_mode,
        corpus_root=corpus_root,
        page_counts=effective_page_counts,
        corpus_records_count=len(corpus_records),
        corpus_files=corpus_records,
        acceleration_policy=acceleration_policy,
        ocr_mode=ocr_mode,
        ocr_engine=ocr_engine,
        resolved_languages=resolved_languages,
        profile_payloads=profile_payloads,
        runtime_surface=runtime_surface,
        runtime_parity=runtime_parity,
        dirty_corpus_summary=dirty_corpus_summary,
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(report_path=output_report, benchmark_json_path=output_json, payload=payload)
    return payload
