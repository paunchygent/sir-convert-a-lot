"""Conversion execution helpers for runtime orchestration.

Purpose:
    Encapsulate backend routing, normalization, metadata generation, and phase
    timing capture so runtime orchestration remains focused on job lifecycle.

Relationships:
    - Used by `infrastructure.runtime_engine` during `_execute_conversion`.
    - Depends on backend contracts and routing modules in infrastructure.
"""

from __future__ import annotations

import hashlib
import json
import time

from scripts.sir_convert_a_lot.application.contracts import ConversionMetadata
from scripts.sir_convert_a_lot.domain.specs import JobSpec, NormalizeMode
from scripts.sir_convert_a_lot.infrastructure.backend_routing import select_backend
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    ConversionBackend,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult
from scripts.sir_convert_a_lot.infrastructure.markdown_normalizer import normalize_markdown
from scripts.sir_convert_a_lot.infrastructure.markdown_quality_report import (
    build_markdown_quality_report,
    format_extreme_line_warning,
    format_reserved_token_warning,
)


def merge_phase_timings(current: dict[str, int], additional: dict[str, int]) -> dict[str, int]:
    """Return merged timing map by summing overlapping keys."""
    merged = dict(current)
    for key, value in additional.items():
        merged[key] = merged.get(key, 0) + int(value)
    return merged


def execute_job_conversion(
    *,
    spec: JobSpec,
    source_filename: str,
    source_bytes: bytes,
    gpu_available: bool,
    gpu_runtime_probe: GpuRuntimeProbeResult | None,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
) -> tuple[str, ConversionMetadata, list[str], dict[str, int]]:
    """Execute one conversion and return markdown, metadata, warnings, and timings."""
    request = ConversionRequest(
        source_filename=source_filename,
        source_bytes=source_bytes,
        backend_strategy=spec.conversion.backend_strategy,
        ocr_mode=spec.conversion.ocr_mode,
        table_mode=spec.conversion.table_mode,
        gpu_available=gpu_available,
        gpu_runtime_probe=gpu_runtime_probe,
    )
    backend = select_backend(
        backend_strategy=spec.conversion.backend_strategy,
        docling_backend=docling_backend,
        pymupdf_backend=pymupdf_backend,
    )
    phase_timings_ms: dict[str, int] = {}

    backend_started = time.perf_counter()
    backend_result = backend.convert(request)
    phase_timings_ms["backend_convert_ms"] = max(
        0, int((time.perf_counter() - backend_started) * 1000)
    )
    phase_timings_ms = merge_phase_timings(phase_timings_ms, backend_result.phase_timings_ms)
    raw_quality = build_markdown_quality_report(backend_result.markdown_content)

    normalize_started = time.perf_counter()
    markdown_content = normalize_markdown(
        backend_result.markdown_content, spec.conversion.normalize
    )
    phase_timings_ms["normalize_ms"] = max(0, int((time.perf_counter() - normalize_started) * 1000))
    normalized_quality = build_markdown_quality_report(markdown_content)

    options_fingerprint = hashlib.sha256(
        json.dumps(spec.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()

    metadata = ConversionMetadata(
        backend_used=backend_result.backend_used,
        acceleration_used=backend_result.acceleration_used,
        ocr_enabled=backend_result.ocr_enabled,
        table_mode=spec.conversion.table_mode,
        options_fingerprint=f"sha256:{options_fingerprint}",
    )
    warnings: list[str] = list(backend_result.warnings)
    if spec.conversion.normalize == NormalizeMode.STRICT:
        if raw_quality.reserved_token_count > 0 and normalized_quality.reserved_token_count == 0:
            warnings.append(format_reserved_token_warning(label="sanitized", report=raw_quality))
        elif normalized_quality.reserved_token_count > 0:
            warnings.append(
                format_reserved_token_warning(label="normalized", report=normalized_quality)
            )
        elif raw_quality.reserved_token_count > 0:
            warnings.append(format_reserved_token_warning(label="raw", report=raw_quality))
    elif raw_quality.reserved_token_count > 0:
        warnings.append(format_reserved_token_warning(label="raw", report=raw_quality))

    if normalized_quality.lines_gt_1000 > 0:
        warnings.append(format_extreme_line_warning(label="normalized", report=normalized_quality))

    return markdown_content, metadata, warnings, phase_timings_ms
