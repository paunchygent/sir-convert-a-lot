"""Dirty PDF OCR corpus manifest and report validation for dirty PDF OCR corpus.

Purpose:
    Validate metadata-only dirty PDF OCR corpus manifests and build sanitized
    benchmark report extensions that can be committed without private PDFs,
    PII-bearing paths, or unsafe benchmark profile claims.

Relationships:
    - Extends the PDF throughput benchmark PDF throughput lane throughput benchmark payload with
      dirty-corpus evidence.
    - Feeds `pdf_throughput_report.write_report` with a safe summary for
      markdown rendering.
    - Keeps dirty PDF OCR final proof Hemma benchmark evidence tied to PDF throughput benchmark
    profile safety
      and Hemma deploy verification runtime parity requirements.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from .pdf_throughput_types import (
    DirtyCorpusFailureTaxonomy,
    DirtyCorpusManifestEntry,
    DirtyCorpusManifestSummary,
    DirtyCorpusOcrMetadataSummary,
    DirtyCorpusReportExtension,
    DirtyPdfBenchmarkProofSummary,
    ProfilePayload,
    ProfileSafetySummary,
    RuntimeParitySummary,
    RuntimeSurface,
)

MANIFEST_SCHEMA_VERSION = "dirty_pdf_ocr_corpus_manifest_v1"
REPORT_SCHEMA_VERSION = "dirty_pdf_ocr_benchmark_report_extension_v1"
DIRTY_PDF_TARGET_EXECUTED_PAGES = 150
DIRTY_PDF_TARGET_WALL_CLOCK_SECONDS = 3600
REQUIRED_DIRTY_DATA_CLASSES = (
    "scanned",
    "mixed_scanned_text",
    "low_contrast",
    "rotated_skewed",
    "table_form_heavy",
    "swedish_diacritic",
    "long_document",
)
ALLOWED_PRIVACY_STATES = ("private", "sanitized", "synthetic")
FORBIDDEN_MANIFEST_KEYS = (
    "source_pdf_path",
    "source_path",
    "local_path",
    "absolute_path",
    "pdf_path",
    "file_path",
)
_SOURCE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,127}$")
_SHA256_PATTERN = re.compile(r"^sha256:[a-f0-9]{64}$")


def _object_mapping(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object.")
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{label} contains a non-string key.")
        result[key] = item
    return result


def _object_list(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array.")
    return list(value)


def _required_str(mapping: dict[str, object], *, key: str, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError(f"{label}.{key} must be a non-empty string.")
    return value.strip()


def _required_bool(mapping: dict[str, object], *, key: str, label: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{label}.{key} must be a boolean.")
    return value


def _required_positive_int(mapping: dict[str, object], *, key: str, label: str) -> int:
    value = mapping.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label}.{key} must be a positive integer.")
    return value


def _required_str_list(mapping: dict[str, object], *, key: str, label: str) -> list[str]:
    values = _object_list(mapping.get(key), label=f"{label}.{key}")
    result: list[str] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or value.strip() == "":
            raise ValueError(f"{label}.{key}[{index}] must be a non-empty string.")
        stripped = value.strip()
        if stripped not in result:
            result.append(stripped)
    if not result:
        raise ValueError(f"{label}.{key} must contain at least one value.")
    return result


def _reject_path_fields(mapping: dict[str, object], *, label: str) -> None:
    for key in mapping:
        if key in FORBIDDEN_MANIFEST_KEYS:
            raise ValueError(
                f"{label}.{key} is not allowed in committed dirty-corpus manifests; "
                "use source_id plus source_sha256 and keep private PDF locations in operator docs."
            )


def _parse_manifest_entry(raw_entry: object, *, index: int) -> DirtyCorpusManifestEntry:
    label = f"entries[{index}]"
    entry = _object_mapping(raw_entry, label=label)
    _reject_path_fields(entry, label=label)

    source_id = _required_str(entry, key="source_id", label=label)
    if _SOURCE_ID_PATTERN.fullmatch(source_id) is None:
        raise ValueError(
            f"{label}.source_id must be a stable id with letters, numbers, dots, "
            "underscores, or hyphens; path separators are not allowed."
        )

    source_sha256 = _required_str(entry, key="source_sha256", label=label)
    if _SHA256_PATTERN.fullmatch(source_sha256) is None:
        raise ValueError(f"{label}.source_sha256 must use `sha256:<64 lowercase hex>`.")

    dirty_classes = _required_str_list(entry, key="dirty_data_classes", label=label)
    invalid_classes = [
        dirty_class
        for dirty_class in dirty_classes
        if dirty_class not in REQUIRED_DIRTY_DATA_CLASSES
    ]
    if invalid_classes:
        allowed = ", ".join(REQUIRED_DIRTY_DATA_CLASSES)
        raise ValueError(
            f"{label}.dirty_data_classes contains unsupported values: "
            f"{', '.join(invalid_classes)}. Allowed: {allowed}."
        )

    privacy_state = _required_str(entry, key="privacy_state", label=label)
    if privacy_state not in ALLOWED_PRIVACY_STATES:
        allowed = ", ".join(ALLOWED_PRIVACY_STATES)
        raise ValueError(f"{label}.privacy_state must be one of: {allowed}.")

    return {
        "source_id": source_id,
        "source_sha256": source_sha256,
        "page_count": _required_positive_int(entry, key="page_count", label=label),
        "dirty_data_classes": dirty_classes,
        "expected_ocr_languages": _required_str_list(
            entry,
            key="expected_ocr_languages",
            label=label,
        ),
        "privacy_state": privacy_state,
        "safe_excerpts_may_be_reported": _required_bool(
            entry,
            key="safe_excerpts_may_be_reported",
            label=label,
        ),
    }


def _increment_counter(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _sorted_counter_keys(counter: dict[str, int]) -> list[str]:
    return sorted(counter.keys())


def load_dirty_corpus_manifest(manifest_path: Path) -> DirtyCorpusManifestSummary:
    """Load and validate a metadata-only dirty OCR corpus manifest."""
    payload_obj: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = _object_mapping(payload_obj, label="dirty corpus manifest")
    _reject_path_fields(payload, label="dirty corpus manifest")

    schema_version = _required_str(payload, key="schema_version", label="dirty corpus manifest")
    if schema_version != MANIFEST_SCHEMA_VERSION:
        raise ValueError(
            "dirty corpus manifest schema_version must be "
            f"`{MANIFEST_SCHEMA_VERSION}`, got `{schema_version}`."
        )

    entries_obj = _object_list(payload.get("entries"), label="dirty corpus manifest.entries")
    if not entries_obj:
        raise ValueError("dirty corpus manifest.entries must contain at least one entry.")

    entries = [
        _parse_manifest_entry(raw_entry, index=index) for index, raw_entry in enumerate(entries_obj)
    ]
    seen_source_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for entry in entries:
        source_id = entry["source_id"]
        source_hash = entry["source_sha256"]
        if source_id in seen_source_ids:
            raise ValueError(f"duplicate dirty corpus source_id `{source_id}`.")
        if source_hash in seen_hashes:
            raise ValueError(f"duplicate dirty corpus source_sha256 `{source_hash}`.")
        seen_source_ids.add(source_id)
        seen_hashes.add(source_hash)

    class_counts: dict[str, int] = {}
    language_counts: dict[str, int] = {}
    privacy_counts: dict[str, int] = {}
    total_pages = 0
    safe_excerpt_entries = 0
    synthetic_entries = 0
    for entry in entries:
        total_pages += entry["page_count"]
        for dirty_class in entry["dirty_data_classes"]:
            _increment_counter(class_counts, dirty_class)
        for language in entry["expected_ocr_languages"]:
            _increment_counter(language_counts, language)
        _increment_counter(privacy_counts, entry["privacy_state"])
        if entry["safe_excerpts_may_be_reported"]:
            safe_excerpt_entries += 1
        if entry["privacy_state"] == "synthetic":
            synthetic_entries += 1

    required_present = [
        dirty_class
        for dirty_class in REQUIRED_DIRTY_DATA_CLASSES
        if class_counts.get(dirty_class, 0) > 0
    ]
    missing_required = [
        dirty_class
        for dirty_class in REQUIRED_DIRTY_DATA_CLASSES
        if class_counts.get(dirty_class, 0) == 0
    ]
    contains_real_dirty_inputs = synthetic_entries < len(entries)
    return {
        "schema_version": schema_version,
        "corpus_id": _required_str(payload, key="corpus_id", label="dirty corpus manifest"),
        "entry_count": len(entries),
        "executed_entry_count": 0,
        "total_pages": total_pages,
        "dirty_data_class_counts": class_counts,
        "required_dirty_data_classes_present": required_present,
        "missing_required_dirty_data_classes": missing_required,
        "expected_ocr_languages": _sorted_counter_keys(language_counts),
        "privacy_state_counts": privacy_counts,
        "safe_excerpt_entry_count": safe_excerpt_entries,
        "synthetic_fixture_entry_count": synthetic_entries,
        "contains_real_dirty_inputs": contains_real_dirty_inputs,
        "source_hashes_verified": False,
        "real_data_gate_satisfied": False,
        "entries": entries,
    }


def mark_dirty_corpus_sources_verified(
    manifest: DirtyCorpusManifestSummary,
) -> DirtyCorpusManifestSummary:
    """Return a report-ready manifest summary after executed file hash verification."""
    return {
        "schema_version": manifest["schema_version"],
        "corpus_id": manifest["corpus_id"],
        "entry_count": manifest["entry_count"],
        "executed_entry_count": manifest["entry_count"],
        "total_pages": manifest["total_pages"],
        "dirty_data_class_counts": manifest["dirty_data_class_counts"],
        "required_dirty_data_classes_present": manifest["required_dirty_data_classes_present"],
        "missing_required_dirty_data_classes": manifest["missing_required_dirty_data_classes"],
        "expected_ocr_languages": manifest["expected_ocr_languages"],
        "privacy_state_counts": manifest["privacy_state_counts"],
        "safe_excerpt_entry_count": manifest["safe_excerpt_entry_count"],
        "synthetic_fixture_entry_count": manifest["synthetic_fixture_entry_count"],
        "contains_real_dirty_inputs": manifest["contains_real_dirty_inputs"],
        "source_hashes_verified": True,
        "real_data_gate_satisfied": (
            manifest["contains_real_dirty_inputs"]
            and not manifest["missing_required_dirty_data_classes"]
            and manifest["entry_count"] > 0
        ),
        "entries": manifest["entries"],
    }


def _classify_profile_safety(profile: ProfilePayload) -> ProfileSafetySummary:
    config = profile["config"]
    profile_name = profile["profile_name"]
    max_chunk_workers = config["max_chunk_workers"]
    gpu_stage_max_concurrency = config["gpu_stage_max_concurrency"]
    unsafe_reason = None
    if max_chunk_workers > 2:
        unsafe_reason = "max_chunk_workers exceeds PDF throughput benchmark safe 2-worker boundary."
    elif gpu_stage_max_concurrency > 2:
        unsafe_reason = "gpu_stage_max_concurrency exceeds PDF throughput benchmark safe boundary."
    elif "4w" in profile_name or "4-worker" in profile_name:
        unsafe_reason = "profile name matches the removed 4-worker OOM profile family."
    return {
        "profile_name": profile_name,
        "max_chunk_workers": max_chunk_workers,
        "gpu_stage_max_concurrency": gpu_stage_max_concurrency,
        "safe_profile": unsafe_reason is None,
        "unsafe_reason": unsafe_reason,
    }


def _classify_failure_taxonomy(profiles: list[ProfilePayload]) -> DirtyCorpusFailureTaxonomy:
    failed_jobs = 0
    warning_count = 0
    input_quality_warnings = 0
    engine_runtime_failures = 0
    timeout_failures = 0
    gpu_resource_failures = 0
    conversion_bug_failures = 0
    for profile in profiles:
        for job in profile["jobs"]:
            warnings = job["warnings"]
            warning_count += len(warnings)
            status = job["status"]
            warning_text = " ".join(warnings).lower()
            if status != "succeeded":
                failed_jobs += 1
                if "timeout" in warning_text:
                    timeout_failures += 1
                elif "oom" in warning_text or "gpu" in warning_text or "rocm" in warning_text:
                    gpu_resource_failures += 1
                elif "ocr" in warning_text or "engine" in warning_text:
                    engine_runtime_failures += 1
                else:
                    conversion_bug_failures += 1
            if (
                "low_confidence" in warning_text
                or "sparse" in warning_text
                or "low-contrast" in warning_text
                or "skew" in warning_text
            ):
                input_quality_warnings += 1
    return {
        "failed_job_count": failed_jobs,
        "warning_count": warning_count,
        "input_quality_warning_count": input_quality_warnings,
        "engine_runtime_failure_count": engine_runtime_failures,
        "timeout_failure_count": timeout_failures,
        "gpu_resource_failure_count": gpu_resource_failures,
        "conversion_bug_failure_count": conversion_bug_failures,
    }


def _metadata_summary(profiles: list[ProfilePayload]) -> DirtyCorpusOcrMetadataSummary:
    ocr_enabled_count = 0
    engines: set[str] = set()
    languages: set[str] = set()
    backends: set[str] = set()
    accelerations: set[str] = set()
    warning_count = 0
    for profile in profiles:
        for job in profile["jobs"]:
            if job["ocr_enabled"] is True:
                ocr_enabled_count += 1
            if job["ocr_engine_used"] is not None:
                engines.add(job["ocr_engine_used"])
            if job["ocr_languages_used"] is not None:
                languages.update(job["ocr_languages_used"])
            if job["backend_used"] is not None:
                backends.add(job["backend_used"])
            if job["acceleration_used"] is not None:
                accelerations.add(job["acceleration_used"])
            warning_count += len(job["warnings"])
    return {
        "ocr_enabled_job_count": ocr_enabled_count,
        "ocr_engine_used_values": sorted(engines),
        "ocr_languages_used_values": sorted(languages),
        "backend_used_values": sorted(backends),
        "acceleration_used_values": sorted(accelerations),
        "warning_count": warning_count,
    }


def _select_dirty_pdf_profile(profiles: list[ProfilePayload]) -> ProfilePayload:
    candidates = [profile for profile in profiles[1:] if profile["summary"]["failed_jobs"] == 0]
    if not candidates:
        candidates = [profile for profile in profiles if profile["summary"]["failed_jobs"] == 0]
    if not candidates:
        candidates = profiles[1:] or profiles
    return min(candidates, key=lambda profile: profile["summary"]["latency_seconds"]["p50"])


def _sum_profile_pages(profile: ProfilePayload) -> int:
    return sum(job["page_count"] for job in profile["jobs"])


def _build_dirty_pdf_proof_summary(
    *,
    manifest: DirtyCorpusManifestSummary,
    profiles: list[ProfilePayload],
    runtime_surface: RuntimeSurface,
    runtime_parity: RuntimeParitySummary,
    all_profiles_safe: bool,
) -> DirtyPdfBenchmarkProofSummary:
    tuned_profile = _select_dirty_pdf_profile(profiles)
    tuned_summary = tuned_profile["summary"]
    tuned_total_pages = _sum_profile_pages(tuned_profile)
    tuned_wall_clock_seconds = tuned_summary["total_latency_seconds"]
    production_service_runtime = runtime_surface["mode"] == "production_service"
    meets_150_page_target = (
        production_service_runtime
        and runtime_parity["parity_proven"]
        and all_profiles_safe
        and manifest["source_hashes_verified"]
        and manifest["real_data_gate_satisfied"]
        and tuned_summary["success_rate"] == 1.0
        and tuned_total_pages >= DIRTY_PDF_TARGET_EXECUTED_PAGES
        and tuned_wall_clock_seconds <= DIRTY_PDF_TARGET_WALL_CLOCK_SECONDS
    )
    return {
        "runtime_mode": runtime_surface["mode"],
        "production_service_runtime": production_service_runtime,
        "target_executed_pages": DIRTY_PDF_TARGET_EXECUTED_PAGES,
        "target_wall_clock_seconds": DIRTY_PDF_TARGET_WALL_CLOCK_SECONDS,
        "tuned_profile": tuned_profile["profile_name"],
        "tuned_total_pages": tuned_total_pages,
        "tuned_wall_clock_seconds": tuned_wall_clock_seconds,
        "tuned_success_rate": tuned_summary["success_rate"],
        "source_hashes_verified": manifest["source_hashes_verified"],
        "real_data_gate_satisfied": manifest["real_data_gate_satisfied"],
        "deploy_parity_proven": runtime_parity["parity_proven"],
        "all_profiles_safe": all_profiles_safe,
        "meets_150_page_target": meets_150_page_target,
    }


def build_dirty_corpus_report_extension(
    *,
    manifest: DirtyCorpusManifestSummary,
    profiles: list[ProfilePayload],
    runtime_surface: RuntimeSurface,
    runtime_parity: RuntimeParitySummary,
) -> DirtyCorpusReportExtension:
    """Build the sanitized dirty PDF OCR corpus dirty-corpus benchmark report extension."""
    profile_safety = [_classify_profile_safety(profile) for profile in profiles]
    all_profiles_safe = all(profile["safe_profile"] for profile in profile_safety)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "manifest": manifest,
        "profile_safety": profile_safety,
        "all_profiles_safe": all_profiles_safe,
        "deploy_parity_required": True,
        "deploy_parity_proven": runtime_parity["parity_proven"],
        "failure_taxonomy": _classify_failure_taxonomy(profiles),
        "ocr_metadata_summary": _metadata_summary(profiles),
        "dirty_pdf_ocr_proof": _build_dirty_pdf_proof_summary(
            manifest=manifest,
            profiles=profiles,
            runtime_surface=runtime_surface,
            runtime_parity=runtime_parity,
            all_profiles_safe=all_profiles_safe,
        ),
    }


def main() -> None:
    """Validate a metadata-only dirty PDF OCR corpus manifest."""
    parser = argparse.ArgumentParser(
        description="Validate a dirty PDF OCR corpus dirty PDF OCR manifest."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_dirty_corpus_manifest(args.manifest)
    print(
        "dirty-corpus-manifest-valid",
        json.dumps(manifest, sort_keys=True),
    )


if __name__ == "__main__":
    main()
