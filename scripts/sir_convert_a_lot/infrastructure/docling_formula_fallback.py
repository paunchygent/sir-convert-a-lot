"""Docling formula-enrichment fallback orchestration.

Purpose:
    Isolate formula preset fallback control flow from the core Docling backend
    class while preserving deterministic warning and timing behavior.

Relationships:
    - Called by `infrastructure.docling_backend` during each conversion pass.
    - Uses quality heuristics from `infrastructure.docling_formula_quality`.
"""

from __future__ import annotations

import time
from typing import Callable, Protocol, TypeAlias, TypeVar

from docling.datamodel.accelerator_options import AcceleratorDevice

from scripts.sir_convert_a_lot.domain.specs import TableMode
from scripts.sir_convert_a_lot.infrastructure import docling_formula_authority
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_events import (
    emit_docling_formula_diagnostic_event,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_quality import (
    FORMULA_FALLBACK_PRESET,
    FORMULA_PRIMARY_PRESET,
    formula_placeholder_count,
    is_formula_runtime_unavailable,
    markdown_quality_penalty,
    markdown_quality_penalty_breakdown,
)
from scripts.sir_convert_a_lot.infrastructure.phase_timings_v2 import (
    TIMING_KEY_OCR_LAYOUT_EXTRACT_MS,
)


class FormulaAttempt(Protocol):
    """Protocol for conversion attempts evaluated by formula fallback policy."""

    @property
    def markdown_content(self) -> str: ...


AttemptT = TypeVar("AttemptT", bound=FormulaAttempt)
FormulaAuthorityMetadata: TypeAlias = dict[str, object]


def convert_once_guarded_formula(
    *,
    request: ConversionRequest,
    ocr_enabled: bool,
    force_full_page_ocr: bool,
    acceleration_device: AcceleratorDevice,
    convert_once: Callable[..., AttemptT],
    ordering_warnings_resolver: Callable[[AttemptT], list[str]],
    formula_enrichment_fallback_warning: str,
    formula_preset_switch_warning: str,
    formula_quality_switch_warning: str,
) -> tuple[AttemptT, list[str], dict[str, int], FormulaAuthorityMetadata]:
    """Execute conversion with deterministic formula-preset fallback policy."""
    formula_enrichment = request.table_mode == TableMode.ACCURATE
    docling_convert_ms = 0
    if not formula_enrichment:
        attempt = convert_once(
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            formula_enrichment=False,
            formula_preset=FORMULA_PRIMARY_PRESET,
        )
        return (
            attempt,
            ordering_warnings_resolver(attempt),
            {},
            {},
        )

    warnings: list[str] = []
    source_evidence = docling_formula_authority.collect_source_layer_formula_evidence(
        request.source_bytes
    )
    if source_evidence.is_authoritative:
        attempt, docling_convert_ms = _timed_convert_once(
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            formula_enrichment=False,
            formula_preset=FORMULA_PRIMARY_PRESET,
            convert_once=convert_once,
        )
        warning_codes = (docling_formula_authority.FORMULA_SOURCE_BACKED_VLM_SKIPPED_WARNING,)
        warnings.extend(warning_codes)
        warnings.extend(ordering_warnings_resolver(attempt))
        return (
            attempt,
            warnings,
            {TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: docling_convert_ms},
            docling_formula_authority.build_formula_authority_metadata(
                source_evidence=source_evidence,
                action="skipped",
                representation="source_layer_markdown",
                vlm_attempted=False,
                reason="source_layer_authoritative_formula_vlm_skipped",
                warning_codes=warning_codes,
            ),
        )

    primary_error: BackendExecutionError | None = None
    primary_quality_penalty = 0
    try:
        primary_attempt, primary_timing_ms = _timed_convert_once(
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            formula_enrichment=True,
            formula_preset=FORMULA_PRIMARY_PRESET,
            convert_once=convert_once,
        )
        docling_convert_ms += primary_timing_ms
        primary_quality_breakdown = markdown_quality_penalty_breakdown(
            primary_attempt.markdown_content
        )
        primary_quality_penalty = primary_quality_breakdown["penalty"]
    except BackendExecutionError as exc:
        if not is_formula_runtime_unavailable(str(exc)):
            raise
        primary_error = exc
        primary_attempt = None
        primary_quality_breakdown = {"penalty": 0}

    fallback_error: BackendExecutionError | None = None
    fallback_attempt: AttemptT | None = None
    primary_placeholder_count = (
        formula_placeholder_count(primary_attempt.markdown_content)
        if primary_attempt is not None
        else 0
    )
    needs_fallback_attempt = (
        primary_attempt is None or (primary_placeholder_count > 0) or primary_quality_penalty > 0
    )
    if needs_fallback_attempt:
        emit_docling_formula_diagnostic_event(
            {
                "event": "docling_formula_fallback_decision",
                "primary_attempt_succeeded": primary_attempt is not None,
                "primary_placeholder_count": primary_placeholder_count,
                "primary_quality_penalty": primary_quality_penalty,
                "primary_quality_breakdown": primary_quality_breakdown,
                "fallback_formula_preset": FORMULA_FALLBACK_PRESET,
            }
        )
        try:
            fallback_attempt, fallback_timing_ms = _timed_convert_once(
                request=request,
                ocr_enabled=ocr_enabled,
                force_full_page_ocr=force_full_page_ocr,
                acceleration_device=acceleration_device,
                formula_enrichment=True,
                formula_preset=FORMULA_FALLBACK_PRESET,
                convert_once=convert_once,
            )
            docling_convert_ms += fallback_timing_ms
        except BackendExecutionError as exc:
            if not is_formula_runtime_unavailable(str(exc)):
                raise
            fallback_error = exc
    timings = {TIMING_KEY_OCR_LAYOUT_EXTRACT_MS: docling_convert_ms}

    if primary_attempt is None and fallback_attempt is not None:
        source_rejection = _source_backed_rejection_attempt(
            source_evidence=source_evidence,
            generated_output_has_quality_defect=True,
            rejection_path_warnings=[formula_preset_switch_warning],
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            convert_once=convert_once,
            ordering_warnings_resolver=ordering_warnings_resolver,
            timings=timings,
        )
        if source_rejection is not None:
            return source_rejection
        warnings.append(formula_preset_switch_warning)
        warnings.extend(ordering_warnings_resolver(fallback_attempt))
        return fallback_attempt, warnings, timings, {}

    if primary_attempt is not None and fallback_attempt is not None:
        primary_placeholder_count = formula_placeholder_count(primary_attempt.markdown_content)
        fallback_placeholder_count = formula_placeholder_count(fallback_attempt.markdown_content)
        primary_quality_penalty = markdown_quality_penalty(primary_attempt.markdown_content)
        fallback_quality_penalty = markdown_quality_penalty(fallback_attempt.markdown_content)
        if fallback_placeholder_count < primary_placeholder_count:
            source_rejection = _source_backed_rejection_attempt(
                source_evidence=source_evidence,
                generated_output_has_quality_defect=True,
                rejection_path_warnings=[formula_preset_switch_warning],
                request=request,
                ocr_enabled=ocr_enabled,
                force_full_page_ocr=force_full_page_ocr,
                acceleration_device=acceleration_device,
                convert_once=convert_once,
                ordering_warnings_resolver=ordering_warnings_resolver,
                timings=timings,
            )
            if source_rejection is not None:
                return source_rejection
            warnings.append(formula_preset_switch_warning)
            warnings.extend(ordering_warnings_resolver(fallback_attempt))
            return fallback_attempt, warnings, timings, {}
        if (
            fallback_placeholder_count == primary_placeholder_count
            and fallback_quality_penalty < primary_quality_penalty
        ):
            source_rejection = _source_backed_rejection_attempt(
                source_evidence=source_evidence,
                generated_output_has_quality_defect=True,
                rejection_path_warnings=[
                    formula_preset_switch_warning,
                    formula_quality_switch_warning,
                ],
                request=request,
                ocr_enabled=ocr_enabled,
                force_full_page_ocr=force_full_page_ocr,
                acceleration_device=acceleration_device,
                convert_once=convert_once,
                ordering_warnings_resolver=ordering_warnings_resolver,
                timings=timings,
            )
            if source_rejection is not None:
                return source_rejection
            warnings.append(formula_preset_switch_warning)
            warnings.append(formula_quality_switch_warning)
            warnings.extend(ordering_warnings_resolver(fallback_attempt))
            return fallback_attempt, warnings, timings, {}
        warnings.extend(ordering_warnings_resolver(primary_attempt))
        return primary_attempt, warnings, timings, {}

    if primary_attempt is not None:
        source_rejection = _source_backed_rejection_attempt(
            source_evidence=source_evidence,
            generated_output_has_quality_defect=primary_placeholder_count > 0
            or primary_quality_penalty > 0,
            rejection_path_warnings=[],
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            convert_once=convert_once,
            ordering_warnings_resolver=ordering_warnings_resolver,
            timings=timings,
        )
        if source_rejection is not None:
            return source_rejection
        warnings.extend(ordering_warnings_resolver(primary_attempt))
        return primary_attempt, warnings, timings, {}

    if primary_error is not None or fallback_error is not None:
        attempt = convert_once(
            request=request,
            ocr_enabled=ocr_enabled,
            force_full_page_ocr=force_full_page_ocr,
            acceleration_device=acceleration_device,
            formula_enrichment=False,
            formula_preset=FORMULA_PRIMARY_PRESET,
        )
        fallback_warnings = [formula_enrichment_fallback_warning]
        fallback_warnings.extend(ordering_warnings_resolver(attempt))
        return (
            attempt,
            fallback_warnings,
            timings,
            docling_formula_authority.build_formula_authority_metadata(
                source_evidence=source_evidence,
                action="fallback",
                representation="source_layer_markdown",
                vlm_attempted=True,
                reason="formula_vlm_runtime_unavailable",
                warning_codes=fallback_warnings,
            ),
        )

    raise BackendExecutionError("Docling formula enrichment failed without runtime diagnostics.")


def _source_backed_rejection_attempt(
    *,
    source_evidence: docling_formula_authority.SourceLayerFormulaEvidence,
    generated_output_has_quality_defect: bool,
    rejection_path_warnings: list[str],
    request: ConversionRequest,
    ocr_enabled: bool,
    force_full_page_ocr: bool,
    acceleration_device: AcceleratorDevice,
    convert_once: Callable[..., AttemptT],
    ordering_warnings_resolver: Callable[[AttemptT], list[str]],
    timings: dict[str, int],
) -> tuple[AttemptT, list[str], dict[str, int], FormulaAuthorityMetadata] | None:
    authority_decision = docling_formula_authority.decide_formula_authority(
        source_evidence=source_evidence,
        generated_output_has_quality_defect=generated_output_has_quality_defect,
    )
    if authority_decision.use_generated_output:
        return None
    attempt = _convert_once_without_formula(
        request=request,
        ocr_enabled=ocr_enabled,
        force_full_page_ocr=force_full_page_ocr,
        acceleration_device=acceleration_device,
        convert_once=convert_once,
    )
    warnings = list(authority_decision.warning_codes)
    warnings.extend(rejection_path_warnings)
    warnings.extend(ordering_warnings_resolver(attempt))
    return (
        attempt,
        warnings,
        timings,
        docling_formula_authority.build_formula_authority_metadata(
            source_evidence=source_evidence,
            action="rejected",
            representation="source_layer_markdown",
            vlm_attempted=True,
            reason=authority_decision.reason,
            warning_codes=warnings,
        ),
    )


def _convert_once_without_formula(
    *,
    request: ConversionRequest,
    ocr_enabled: bool,
    force_full_page_ocr: bool,
    acceleration_device: AcceleratorDevice,
    convert_once: Callable[..., AttemptT],
) -> AttemptT:
    return convert_once(
        request=request,
        ocr_enabled=ocr_enabled,
        force_full_page_ocr=force_full_page_ocr,
        acceleration_device=acceleration_device,
        formula_enrichment=False,
        formula_preset=FORMULA_PRIMARY_PRESET,
    )


def _timed_convert_once(
    *,
    request: ConversionRequest,
    ocr_enabled: bool,
    force_full_page_ocr: bool,
    acceleration_device: AcceleratorDevice,
    formula_enrichment: bool,
    formula_preset: str,
    convert_once: Callable[..., AttemptT],
) -> tuple[AttemptT, int]:
    start = time.perf_counter()
    attempt = convert_once(
        request=request,
        ocr_enabled=ocr_enabled,
        force_full_page_ocr=force_full_page_ocr,
        acceleration_device=acceleration_device,
        formula_enrichment=formula_enrichment,
        formula_preset=formula_preset,
    )
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return attempt, max(0, elapsed_ms)
