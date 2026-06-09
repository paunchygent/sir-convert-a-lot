"""PDF throughput benchmark profile policy and safety checks.

Purpose:
    Define the PDF throughput lane/PDF throughput benchmark profile matrix, bounded two-worker
    sweep variants, and dirty-corpus fail-closed safety checks.

Relationships:
    - Used by the PDF throughput benchmark runner and CLI.
    - Encodes the dirty PDF OCR benchmark/dirty PDF OCR corpus requirement that dirty-corpus
      evidence stays
      within the PDF throughput benchmark safe 2-worker profile boundary.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TWO_WORKER_SWEEP_CHUNK_SIZES = (2, 3, 4, 6, 8)
DEFAULT_TWO_WORKER_SWEEP_GPU_STAGE_CAPS = (1, 2)


@dataclass(frozen=True)
class ProfileSpec:
    """One benchmark runtime profile."""

    profile_name: str
    parallel_enabled: bool
    max_chunk_workers: int
    chunk_size_pages: int
    gpu_stage_max_concurrency: int


def default_profiles() -> list[ProfileSpec]:
    """Return the committed PDF throughput benchmark baseline profile matrix."""
    return [
        ProfileSpec(
            profile_name="serial_baseline",
            parallel_enabled=False,
            max_chunk_workers=1,
            chunk_size_pages=8,
            gpu_stage_max_concurrency=1,
        ),
        ProfileSpec(
            profile_name="parallel_conservative",
            parallel_enabled=True,
            max_chunk_workers=2,
            chunk_size_pages=4,
            gpu_stage_max_concurrency=2,
        ),
    ]


def build_two_worker_sweep_profiles(
    *,
    chunk_sizes: tuple[int, ...],
    gpu_stage_caps: tuple[int, ...],
) -> list[ProfileSpec]:
    """Build bounded two-worker sweep profiles inside the PDF throughput benchmark safe matrix."""
    profiles = default_profiles()
    for gpu_stage_cap in gpu_stage_caps:
        if gpu_stage_cap > 2:
            raise ValueError(
                "Two-worker sweep only allows gpu_stage_max_concurrency <= 2; "
                f"got `{gpu_stage_cap}`."
            )
    for chunk_size in chunk_sizes:
        for gpu_stage_cap in gpu_stage_caps:
            if chunk_size == 4 and gpu_stage_cap == 2:
                continue
            profiles.append(
                ProfileSpec(
                    profile_name=f"parallel_2w_chunk{chunk_size}_cap{gpu_stage_cap}",
                    parallel_enabled=True,
                    max_chunk_workers=2,
                    chunk_size_pages=chunk_size,
                    gpu_stage_max_concurrency=gpu_stage_cap,
                )
            )
    return profiles


def assert_dirty_corpus_profile_specs_safe(profiles: list[ProfileSpec]) -> None:
    """Reject dirty-corpus benchmark profiles outside the governed safe matrix."""
    unsafe_reasons: list[str] = []
    for profile in profiles:
        if profile.max_chunk_workers > 2:
            unsafe_reasons.append(
                f"{profile.profile_name}: max_chunk_workers={profile.max_chunk_workers} "
                "exceeds PDF throughput benchmark safe 2-worker boundary"
            )
        if profile.gpu_stage_max_concurrency > 2:
            unsafe_reasons.append(
                f"{profile.profile_name}: "
                f"gpu_stage_max_concurrency={profile.gpu_stage_max_concurrency} "
                "exceeds PDF throughput benchmark safe boundary"
            )
        if "4w" in profile.profile_name or "4-worker" in profile.profile_name:
            unsafe_reasons.append(
                f"{profile.profile_name}: removed 4-worker OOM profile family is forbidden"
            )
    if unsafe_reasons:
        joined = "; ".join(unsafe_reasons)
        raise ValueError(f"Dirty-corpus benchmark profiles must fail closed: {joined}.")
