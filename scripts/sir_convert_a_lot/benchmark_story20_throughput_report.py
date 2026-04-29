"""Public entrypoint for the Story 20 Task 74 throughput benchmark.

Purpose:
    Preserve the existing `python -m` and import surface for Task 74 benchmark
    commands while delegating implementation to focused benchmarking modules.

Relationships:
    - `story20_throughput_cli` owns argument parsing.
    - `story20_profile_runner` owns benchmark execution.
    - `story20_profiles` owns the governed profile matrix.
    - `story20_runtime_parity` owns Task 76 parity ingestion.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.benchmarking.story20_profile_runner import (
    DEFAULT_PAGE_COUNTS,
    run_benchmark,
)
from scripts.sir_convert_a_lot.benchmarking.story20_profiles import (
    DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES,
    DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS,
    ProfileSpec,
    build_two_worker_sweep_profiles,
)
from scripts.sir_convert_a_lot.benchmarking.story20_runtime_parity import RuntimeParityInputs
from scripts.sir_convert_a_lot.benchmarking.story20_throughput_cli import (
    DEFAULT_CORPUS_ROOT,
    DEFAULT_DATA_ROOT,
    DEFAULT_OUTPUT_JSON,
    DEFAULT_OUTPUT_REPORT,
    DEFAULT_OUTPUT_ROOT,
    main,
    parse_positive_int_csv,
)

_build_two_worker_sweep_profiles = build_two_worker_sweep_profiles
_parse_positive_int_csv = parse_positive_int_csv

__all__ = [
    "DEFAULT_CORPUS_ROOT",
    "DEFAULT_DATA_ROOT",
    "DEFAULT_OUTPUT_JSON",
    "DEFAULT_OUTPUT_REPORT",
    "DEFAULT_OUTPUT_ROOT",
    "DEFAULT_PAGE_COUNTS",
    "DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES",
    "DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS",
    "ProfileSpec",
    "RuntimeParityInputs",
    "_build_two_worker_sweep_profiles",
    "_parse_positive_int_csv",
    "main",
    "run_benchmark",
]


if __name__ == "__main__":
    main()
