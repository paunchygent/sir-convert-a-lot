"""Stdout summary helpers for the Task 74 Hemma benchmark command.

Purpose:
    Keep command stdout limited to artifact locations and safety/parity status
    while excluding performance conclusions from the terminal stream.

Relationships:
    - Used by `run_task74_hemma_benchmark`.
    - Complements the governed JSON/Markdown benchmark artifacts where
      performance metrics are allowed to live.
"""

from __future__ import annotations

from pathlib import Path


def build_stdout_summary(
    *,
    output_json: Path,
    output_report: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    """Build the metrics-free machine-readable command stdout summary."""
    runtime_parity_obj = payload.get("runtime_parity")
    if not isinstance(runtime_parity_obj, dict):
        raise SystemExit("Task 74 benchmark payload is missing `runtime_parity`.")
    runtime_surface_obj = payload.get("runtime_surface")
    if not isinstance(runtime_surface_obj, dict):
        raise SystemExit("Task 74 benchmark payload is missing `runtime_surface`.")
    dirty_corpus_obj = payload.get("dirty_corpus")
    dirty_corpus_loaded = dirty_corpus_obj is not None
    all_profiles_safe: object = None
    source_hashes_verified: object = None
    if isinstance(dirty_corpus_obj, dict):
        all_profiles_safe = dirty_corpus_obj.get("all_profiles_safe")
        manifest_obj = dirty_corpus_obj.get("manifest")
        if isinstance(manifest_obj, dict):
            source_hashes_verified = manifest_obj.get("source_hashes_verified")
    return {
        "output_json": output_json.as_posix(),
        "output_report": output_report.as_posix(),
        "runtime_surface_mode": runtime_surface_obj.get("mode"),
        "runtime_parity_proven": runtime_parity_obj.get("parity_proven"),
        "dirty_corpus_manifest_loaded": dirty_corpus_loaded,
        "dirty_corpus_all_profiles_safe": all_profiles_safe,
        "dirty_corpus_source_hashes_verified": source_hashes_verified,
    }
