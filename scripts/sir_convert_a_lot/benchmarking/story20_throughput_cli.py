"""Command-line interface for the Task 74 throughput benchmark.

Purpose:
    Parse Task 74 benchmark arguments, support metadata-only dirty-corpus
    manifest validation, require hash-verified dirty-corpus source roots for
    benchmark evidence, and invoke the focused benchmark runner.

Relationships:
    - Called by the public `benchmark_story20_throughput_report` module.
    - Uses `story20_profile_runner.run_benchmark` for benchmark execution.
    - Keeps CLI parsing separate from runtime/profile execution logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .dirty_pdf_corpus import load_dirty_corpus_manifest
from .story20_profile_runner import DEFAULT_PAGE_COUNTS, run_benchmark
from .story20_profiles import (
    DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES,
    DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS,
    ProfileSpec,
)
from .story20_runtime_parity import RuntimeParityInputs, coerce_optional_str

DEFAULT_OUTPUT_ROOT = Path("build/benchmarks/story-20/task-74-throughput")
DEFAULT_OUTPUT_JSON = DEFAULT_OUTPUT_ROOT / "task-74-throughput-benchmark-local.json"
DEFAULT_OUTPUT_REPORT = DEFAULT_OUTPUT_ROOT / "task-74-throughput-report.md"
DEFAULT_CORPUS_ROOT = DEFAULT_OUTPUT_ROOT / "corpus"
DEFAULT_DATA_ROOT = DEFAULT_OUTPUT_ROOT / "runtime"


def parse_positive_int_csv(raw_values: str, *, label: str) -> tuple[int, ...]:
    """Parse a comma-separated list of positive integers."""
    parsed_values: list[int] = []
    for raw_value in raw_values.split(","):
        stripped = raw_value.strip()
        if stripped == "":
            continue
        try:
            parsed = int(stripped)
        except ValueError as exc:
            raise ValueError(f"{label} must contain only integers; got `{stripped}`.") from exc
        if parsed <= 0:
            raise ValueError(f"{label} must contain only positive integers; got `{parsed}`.")
        if parsed not in parsed_values:
            parsed_values.append(parsed)
    if not parsed_values:
        raise ValueError(f"{label} must contain at least one positive integer.")
    return tuple(parsed_values)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Story 20 Task 74 throughput benchmark.")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--page-counts",
        default=",".join(str(value) for value in DEFAULT_PAGE_COUNTS),
    )
    parser.add_argument("--api-key", default="benchmark-key")
    parser.add_argument("--acceleration-policy", default="gpu_required")
    parser.add_argument("--ocr-mode", default="force")
    parser.add_argument("--ocr-engine", default="easyocr")
    parser.add_argument("--ocr-languages", default="sv,en")
    parser.add_argument("--max-poll-seconds", type=float, default=7200.0)
    parser.add_argument("--runtime-mode", default="in_process_app")
    parser.add_argument("--runtime-host")
    parser.add_argument("--runtime-service-url")
    parser.add_argument("--easyocr-model-storage-dir")
    parser.add_argument("--service-profile-name")
    parser.add_argument(
        "--service-profile-parallel-enabled",
        dest="service_profile_parallel_enabled",
        action="store_true",
    )
    parser.add_argument(
        "--service-profile-serial",
        dest="service_profile_parallel_enabled",
        action="store_false",
    )
    parser.add_argument("--service-profile-max-chunk-workers", type=int)
    parser.add_argument("--service-profile-chunk-size-pages", type=int)
    parser.add_argument("--service-profile-gpu-stage-max-concurrency", type=int)
    parser.add_argument("--dirty-corpus-manifest", type=Path)
    parser.add_argument("--dirty-corpus-source-root", type=Path)
    parser.add_argument("--validate-dirty-corpus-manifest-only", action="store_true")
    parser.add_argument("--two-worker-sweep", action="store_true")
    parser.add_argument(
        "--two-worker-chunk-sizes",
        default=",".join(str(value) for value in DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES),
    )
    parser.add_argument(
        "--two-worker-gpu-stage-caps",
        default=",".join(str(value) for value in DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS),
    )
    parser.add_argument("--task76-report-json", type=Path)
    parser.add_argument("--parity-status")
    parser.add_argument("--parity-lane")
    parser.add_argument("--parity-expected-revision")
    parser.add_argument("--parity-remote-revision")
    parser.add_argument("--parity-service-revision")
    parser.add_argument(
        "--parity-expected-remote-ok",
        dest="parity_expected_remote_ok",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-expected-remote-ok",
        dest="parity_expected_remote_ok",
        action="store_false",
    )
    parser.add_argument(
        "--parity-service-remote-ok",
        dest="parity_service_remote_ok",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-service-remote-ok",
        dest="parity_service_remote_ok",
        action="store_false",
    )
    parser.add_argument(
        "--parity-live-smoke-passed",
        dest="parity_live_smoke_passed",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-live-smoke-passed",
        dest="parity_live_smoke_passed",
        action="store_false",
    )
    parser.add_argument(
        "--parity-metrics-scan-passed",
        dest="parity_metrics_scan_passed",
        action="store_true",
    )
    parser.add_argument(
        "--no-parity-metrics-scan-passed",
        dest="parity_metrics_scan_passed",
        action="store_false",
    )
    parser.add_argument("--gpu-available", dest="gpu_available", action="store_true")
    parser.add_argument("--no-gpu-available", dest="gpu_available", action="store_false")
    parser.set_defaults(
        gpu_available=True,
        parity_expected_remote_ok=None,
        parity_service_remote_ok=None,
        parity_live_smoke_passed=None,
        parity_metrics_scan_passed=None,
        service_profile_parallel_enabled=None,
    )
    return parser


def _require_positive_int(value: int | None, *, label: str) -> int:
    if value is None or value <= 0:
        raise ValueError(f"{label} must be a positive integer for production_service mode.")
    return value


def _build_service_profile_from_args(args: argparse.Namespace) -> list[ProfileSpec] | None:
    if str(args.runtime_mode) != "production_service":
        return None
    profile_name_obj = args.service_profile_name
    if not isinstance(profile_name_obj, str) or profile_name_obj.strip() == "":
        raise ValueError("--service-profile-name is required for production_service mode.")
    parallel_enabled_obj = args.service_profile_parallel_enabled
    if not isinstance(parallel_enabled_obj, bool):
        raise ValueError(
            "--service-profile-parallel-enabled or --service-profile-serial is required "
            "for production_service mode."
        )
    return [
        ProfileSpec(
            profile_name=profile_name_obj.strip(),
            parallel_enabled=parallel_enabled_obj,
            max_chunk_workers=_require_positive_int(
                args.service_profile_max_chunk_workers,
                label="--service-profile-max-chunk-workers",
            ),
            chunk_size_pages=_require_positive_int(
                args.service_profile_chunk_size_pages,
                label="--service-profile-chunk-size-pages",
            ),
            gpu_stage_max_concurrency=_require_positive_int(
                args.service_profile_gpu_stage_max_concurrency,
                label="--service-profile-gpu-stage-max-concurrency",
            ),
        )
    ]


def main() -> None:
    """Parse CLI args and run the Task 74 benchmark harness."""
    parser = _build_parser()
    args = parser.parse_args()
    page_counts = parse_positive_int_csv(args.page_counts, label="page-counts")
    two_worker_chunk_sizes = parse_positive_int_csv(
        args.two_worker_chunk_sizes,
        label="two-worker-chunk-sizes",
    )
    two_worker_gpu_stage_caps = parse_positive_int_csv(
        args.two_worker_gpu_stage_caps,
        label="two-worker-gpu-stage-caps",
    )
    if args.validate_dirty_corpus_manifest_only:
        if args.dirty_corpus_manifest is None:
            raise SystemExit(
                "--validate-dirty-corpus-manifest-only requires --dirty-corpus-manifest."
            )
        manifest = load_dirty_corpus_manifest(args.dirty_corpus_manifest)
        print("dirty-corpus-manifest-valid", json.dumps(manifest, sort_keys=True))
        return

    payload = run_benchmark(
        output_json=args.output_json,
        output_report=args.output_report,
        corpus_root=args.corpus_root,
        data_root=args.data_root,
        page_counts=page_counts,
        api_key=args.api_key,
        acceleration_policy=args.acceleration_policy,
        ocr_mode=args.ocr_mode,
        ocr_engine=args.ocr_engine,
        ocr_languages=[value.strip() for value in args.ocr_languages.split(",") if value.strip()],
        max_poll_seconds=args.max_poll_seconds,
        gpu_available=args.gpu_available,
        runtime_mode=str(args.runtime_mode),
        runtime_host=coerce_optional_str(args.runtime_host),
        runtime_service_url=coerce_optional_str(args.runtime_service_url),
        easyocr_model_storage_directory=coerce_optional_str(args.easyocr_model_storage_dir)
        or "/opt/easyocr-models",
        runtime_parity_inputs=RuntimeParityInputs(
            report_json_path=args.task76_report_json,
            status=coerce_optional_str(args.parity_status),
            lane=coerce_optional_str(args.parity_lane),
            expected_revision=coerce_optional_str(args.parity_expected_revision),
            remote_revision=coerce_optional_str(args.parity_remote_revision),
            service_revision=coerce_optional_str(args.parity_service_revision),
            expected_revision_matches_remote=args.parity_expected_remote_ok,
            service_revision_matches_remote=args.parity_service_remote_ok,
            live_smoke_passed=args.parity_live_smoke_passed,
            metrics_scan_passed=args.parity_metrics_scan_passed,
        ),
        two_worker_sweep=bool(args.two_worker_sweep),
        two_worker_chunk_sizes=two_worker_chunk_sizes,
        two_worker_gpu_stage_caps=two_worker_gpu_stage_caps,
        dirty_corpus_manifest=args.dirty_corpus_manifest,
        dirty_corpus_source_root=args.dirty_corpus_source_root,
        profiles=_build_service_profile_from_args(args),
    )
    print(
        "task74-benchmark-written",
        json.dumps(
            {
                "output_json": args.output_json.as_posix(),
                "dirty_corpus_manifest_loaded": payload["dirty_corpus"] is not None,
                "runtime_parity_proven": payload["runtime_parity"]["parity_proven"],
            },
            sort_keys=True,
        ),
    )
