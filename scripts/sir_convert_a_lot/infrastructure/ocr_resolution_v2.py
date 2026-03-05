"""OCR engine/language resolution helpers for service API v2.

Purpose:
    Resolve effective OCR engine and languages for v2 PDF conversions by
    combining:
      - per-job `pdf_options` fields, and
      - runtime defaults from `ServiceConfig`.

    This resolution is shared by preflight gates and the v2 PDF executor to
    ensure a single source of truth for OCR engine selection.

Relationships:
    - Used by `infrastructure.ocr_preflight_v2` to reject missing OCR engines or
      language packs before long-running conversions begin.
    - Used by `infrastructure.v2_pdf_checkpointed_executor` to pass resolved OCR
      configuration into the Docling backend execution surface.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy, OcrMode
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OcrEngineV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.ocr_language_mapping_v2 import (
    normalize_bcp47_language_tags,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig


@dataclass(frozen=True)
class ResolvedPdfOcrRequestV2:
    """Effective OCR configuration resolved for a v2 PDF job."""

    engine: OcrEngineV2
    languages: tuple[str, ...]
    use_gpu: bool


def resolve_pdf_ocr_request(
    *, spec: JobSpecV2, config: ServiceConfig
) -> ResolvedPdfOcrRequestV2 | None:
    """Resolve OCR engine/languages for a v2 PDF job, or None when OCR is disabled."""
    if spec.source.format != SourceFormatV2.PDF:
        return None
    if spec.pdf_options is None or spec.execution is None:
        return None
    if spec.pdf_options.ocr_mode == OcrMode.OFF:
        return None

    requested_engine = spec.pdf_options.ocr_engine
    engine = (
        config.default_pdf_ocr_engine if requested_engine == OcrEngineV2.AUTO else requested_engine
    )

    raw_languages = (
        spec.pdf_options.ocr_languages
        if spec.pdf_options.ocr_languages
        else list(config.default_pdf_ocr_languages)
    )
    languages = normalize_bcp47_language_tags(raw_languages)
    if not languages:
        raise ValueError("Resolved OCR language list must not be empty.")

    use_gpu = (
        spec.execution.acceleration_policy != AccelerationPolicy.CPU_ONLY and config.gpu_available
    )
    return ResolvedPdfOcrRequestV2(engine=engine, languages=languages, use_gpu=use_gpu)
