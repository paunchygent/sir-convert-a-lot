"""In-container ROCm probe for Qwen codebook-fusion proof codebook-fusion decisions.

Purpose:
    Measure numeric error and hot-path cost for the current auxiliary-codebook
    reduction contract against the previous vectorized baseline on the governed
    Qwen ROCm runtime.

Relationships:
    - Executed inside the Qwen training image by `codebook_fusion_proof.py`.
    - Imports `sft_12hz_codebook_fusion.py` to exercise the live candidate
      reduction contract under review for `codebook-fusion reduction`.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_codebook_fusion import (
    _reduce_masked_embeddings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso

_DTYPE_ALIASES = {
    "bf16": torch.bfloat16,
    "bfloat16": torch.bfloat16,
    "fp16": torch.float16,
    "float16": torch.float16,
}
_REFERENCE_DTYPE = torch.float32
_EPSILON = 1e-8
_Reducer = Callable[[torch.Tensor], torch.Tensor]


@dataclass(frozen=True)
class ProbeShape:
    """One representative reducer input shape."""

    batch_size: int
    sequence_length: int
    codebook_count: int
    embedding_dim: int


@dataclass(frozen=True)
class ReducerObservation:
    """Timing and oracle-error metrics for one reducer implementation."""

    average_runtime_ms: float
    max_abs_error: float
    mean_abs_error: float
    max_rel_error: float
    mean_rel_error: float


@dataclass(frozen=True)
class SeedProbeResult:
    """Per-seed comparison between the naive and candidate reducers."""

    seed: int
    naive: ReducerObservation
    candidate: ReducerObservation


@dataclass(frozen=True)
class DtypeProbeResult:
    """Aggregated comparison metrics for one low-precision dtype."""

    dtype: str
    seed_results: tuple[SeedProbeResult, ...]
    naive_mean_runtime_ms: float
    candidate_mean_runtime_ms: float
    candidate_runtime_ratio_vs_naive: float | None
    naive_worst_max_abs_error: float
    candidate_worst_max_abs_error: float
    naive_mean_mean_abs_error: float
    candidate_mean_mean_abs_error: float
    candidate_error_better_or_equal_all_seeds: bool


@dataclass(frozen=True)
class CodebookFusionProbeReport:
    """Machine-readable result for one in-container codebook-fusion probe."""

    generated_at: str
    device_name: str
    torch_version: str
    torch_hip_version: str | None
    shape: ProbeShape
    seeds: tuple[int, ...]
    reference_dtype: str
    benchmark_iterations: int
    warmup_iterations: int
    dtype_summaries: tuple[DtypeProbeResult, ...]


def _parse_dtype_names(raw_value: str) -> tuple[str, ...]:
    """Parse one comma-delimited dtype list into canonical dtype names."""
    names = [item.strip().lower() for item in raw_value.split(",") if item.strip() != ""]
    if len(names) == 0:
        raise argparse.ArgumentTypeError("Expected at least one dtype name.")
    canonical_names: list[str] = []
    for name in names:
        if name not in _DTYPE_ALIASES:
            raise argparse.ArgumentTypeError(
                "Supported dtypes are `bfloat16`/`bf16` and `float16`/`fp16`."
            )
        canonical_name = "bfloat16" if _DTYPE_ALIASES[name] is torch.bfloat16 else "float16"
        if canonical_name not in canonical_names:
            canonical_names.append(canonical_name)
    return tuple(canonical_names)


def _parse_seeds(raw_value: str) -> tuple[int, ...]:
    """Parse one comma-delimited seed list."""
    seeds = [item.strip() for item in raw_value.split(",") if item.strip() != ""]
    if len(seeds) == 0:
        raise argparse.ArgumentTypeError("Expected at least one integer seed.")
    return tuple(int(seed) for seed in seeds)


def _build_parser() -> argparse.ArgumentParser:
    """Build the in-container probe parser."""
    parser = argparse.ArgumentParser(
        description="Run the Qwen codebook-fusion proof codebook-fusion ROCm probe."
    )
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--sequence-length", type=int, default=508)
    parser.add_argument("--codebook-count", type=int, default=15)
    parser.add_argument("--embedding-dim", type=int, default=2048)
    parser.add_argument("--benchmark-iterations", type=int, default=25)
    parser.add_argument("--warmup-iterations", type=int, default=10)
    parser.add_argument("--dtypes", type=_parse_dtype_names, default=("bfloat16", "float16"))
    parser.add_argument("--seeds", type=_parse_seeds, default=(0, 1, 2))
    return parser


def _naive_reduce(masked_embeddings: torch.Tensor) -> torch.Tensor:
    """Return the pre-codebook-fusion reduction vectorized reduction contract."""
    return torch.sum(masked_embeddings, dim=2)


def _build_masked_embeddings(
    *,
    shape: ProbeShape,
    dtype: torch.dtype,
    seed: int,
    device: torch.device,
) -> torch.Tensor:
    """Create one deterministic masked-embedding tensor for the reduction probe."""
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    masked_embeddings = torch.randn(
        (
            shape.batch_size,
            shape.sequence_length,
            shape.codebook_count,
            shape.embedding_dim,
        ),
        generator=generator,
        dtype=torch.float32,
    )
    token_mask = torch.randint(
        0,
        2,
        (shape.batch_size, shape.sequence_length, 1, 1),
        generator=generator,
        dtype=torch.int64,
    ).to(dtype=torch.float32)
    masked_embeddings = masked_embeddings * token_mask
    return masked_embeddings.to(device=device, dtype=dtype)


def _build_observation(
    *,
    reducer: _Reducer,
    masked_embeddings: torch.Tensor,
    reference: torch.Tensor,
    warmup_iterations: int,
    benchmark_iterations: int,
) -> ReducerObservation:
    """Measure runtime plus oracle error for one reducer implementation."""
    result = reducer(masked_embeddings)
    delta = (result.to(dtype=_REFERENCE_DTYPE) - reference).abs()
    relative_delta = delta / reference.abs().clamp_min(_EPSILON)
    for _ in range(warmup_iterations):
        reducer(masked_embeddings)
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(benchmark_iterations):
        reducer(masked_embeddings)
    end.record()
    torch.cuda.synchronize()
    return ReducerObservation(
        average_runtime_ms=float(start.elapsed_time(end) / benchmark_iterations),
        max_abs_error=float(delta.max().item()),
        mean_abs_error=float(delta.mean().item()),
        max_rel_error=float(relative_delta.max().item()),
        mean_rel_error=float(relative_delta.mean().item()),
    )


def _probe_dtype(
    *,
    shape: ProbeShape,
    dtype_name: str,
    seeds: tuple[int, ...],
    warmup_iterations: int,
    benchmark_iterations: int,
    device: torch.device,
) -> DtypeProbeResult:
    """Run the reducer comparison for one low-precision dtype."""
    dtype = _DTYPE_ALIASES[dtype_name]
    seed_results: list[SeedProbeResult] = []
    for seed in seeds:
        masked_embeddings = _build_masked_embeddings(
            shape=shape,
            dtype=dtype,
            seed=seed,
            device=device,
        )
        reference = torch.sum(masked_embeddings, dim=2, dtype=_REFERENCE_DTYPE)
        naive = _build_observation(
            reducer=_naive_reduce,
            masked_embeddings=masked_embeddings,
            reference=reference,
            warmup_iterations=warmup_iterations,
            benchmark_iterations=benchmark_iterations,
        )
        candidate = _build_observation(
            reducer=_reduce_masked_embeddings,
            masked_embeddings=masked_embeddings,
            reference=reference,
            warmup_iterations=warmup_iterations,
            benchmark_iterations=benchmark_iterations,
        )
        seed_results.append(SeedProbeResult(seed=seed, naive=naive, candidate=candidate))
    candidate_runtime = sum(result.candidate.average_runtime_ms for result in seed_results) / len(
        seed_results
    )
    naive_runtime = sum(result.naive.average_runtime_ms for result in seed_results) / len(
        seed_results
    )
    runtime_ratio = None if naive_runtime == 0.0 else candidate_runtime / naive_runtime
    return DtypeProbeResult(
        dtype="bfloat16" if dtype is torch.bfloat16 else "float16",
        seed_results=tuple(seed_results),
        naive_mean_runtime_ms=naive_runtime,
        candidate_mean_runtime_ms=candidate_runtime,
        candidate_runtime_ratio_vs_naive=runtime_ratio,
        naive_worst_max_abs_error=max(result.naive.max_abs_error for result in seed_results),
        candidate_worst_max_abs_error=max(
            result.candidate.max_abs_error for result in seed_results
        ),
        naive_mean_mean_abs_error=sum(result.naive.mean_abs_error for result in seed_results)
        / len(seed_results),
        candidate_mean_mean_abs_error=sum(
            result.candidate.mean_abs_error for result in seed_results
        )
        / len(seed_results),
        candidate_error_better_or_equal_all_seeds=all(
            result.candidate.max_abs_error <= result.naive.max_abs_error for result in seed_results
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """Execute the in-container codebook-fusion probe and print JSON."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not torch.cuda.is_available():
        raise SystemExit(
            "Qwen codebook-fusion proof codebook-fusion probe requires a ROCm/CUDA runtime."
        )
    shape = ProbeShape(
        batch_size=args.batch_size,
        sequence_length=args.sequence_length,
        codebook_count=args.codebook_count,
        embedding_dim=args.embedding_dim,
    )
    device = torch.device("cuda")
    dtype_summaries = tuple(
        _probe_dtype(
            shape=shape,
            dtype_name=dtype_name,
            seeds=args.seeds,
            warmup_iterations=args.warmup_iterations,
            benchmark_iterations=args.benchmark_iterations,
            device=device,
        )
        for dtype_name in args.dtypes
    )
    report = CodebookFusionProbeReport(
        generated_at=utc_now_iso(),
        device_name=torch.cuda.get_device_name(device),
        torch_version=str(torch.__version__),
        torch_hip_version=(None if torch.version.hip is None else str(torch.version.hip)),
        shape=shape,
        seeds=args.seeds,
        reference_dtype="float32",
        benchmark_iterations=args.benchmark_iterations,
        warmup_iterations=args.warmup_iterations,
        dtype_summaries=dtype_summaries,
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
