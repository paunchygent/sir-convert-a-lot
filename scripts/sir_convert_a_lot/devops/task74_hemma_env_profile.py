"""Hemma production profile parsing for Task 74 benchmark evidence.

Purpose:
    Convert canonical Hemma environment values into the deployed service profile
    recorded by the Task 74 benchmark report.

Relationships:
    - Used by `run_task74_hemma_benchmark` after syncing the production env
      mirror.
    - Keeps production-service benchmark evidence from inventing per-profile
      tuning that the fixed deployed service cannot apply dynamically.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.benchmarking.story20_profiles import ProfileSpec


def parse_bool_env_value(value: str, *, key: str) -> bool:
    """Parse one boolean production env value."""
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"{key} must be a boolean env value, got `{value}`.")


def parse_positive_env_int(value: str, *, key: str) -> int:
    """Parse one positive integer production env value."""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise SystemExit(f"{key} must be a positive integer, got `{value}`.") from exc
    if parsed <= 0:
        raise SystemExit(f"{key} must be a positive integer, got `{parsed}`.")
    return parsed


def deployed_profile_from_env(env_values: dict[str, str]) -> ProfileSpec:
    """Build the single deployed profile a production-service benchmark can claim."""
    return ProfileSpec(
        profile_name="production_service_current",
        parallel_enabled=parse_bool_env_value(
            env_values["SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS"],
            key="SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS",
        ),
        max_chunk_workers=parse_positive_env_int(
            env_values["SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS"],
            key="SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS",
        ),
        chunk_size_pages=parse_positive_env_int(
            env_values["SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES"],
            key="SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES",
        ),
        gpu_stage_max_concurrency=parse_positive_env_int(
            env_values["SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY"],
            key="SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY",
        ),
    )
