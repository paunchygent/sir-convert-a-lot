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
from typing import Callable, Protocol, TypeVar

from docling.datamodel.accelerator_options import AcceleratorDevice

from scripts.sir_convert_a_lot.domain.specs import TableMode
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    BackendExecutionError,
    ConversionRequest,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_quality import (
    FORMULA_FALLBACK_PRESET,
    FORMULA_PRIMARY_PRESET,
    formula_placeholder_count,
    is_formula_runtime_unavailable,
    markdown_quality_penalty,
)


class FormulaAttempt(Protocol):
    """Protocol for conversion attempts evaluated by formula fallback policy."""

    @property
    def markdown_content(self) -> str: ...


AttemptT = TypeVar("AttemptT", bound=FormulaAttempt)


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
) -> tuple[AttemptT, list[str], dict[str, int]]:
    """Execute conversion with deterministic formula-preset fallback policy."""
    formula_enrichment = request.table_mode == TableMode.ACCURATE
    formula_enrichment_ms = 0
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
        )

    warnings: list[str] = []
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
        formula_enrichment_ms += primary_timing_ms
        primary_quality_penalty = markdown_quality_penalty(primary_attempt.markdown_content)
    except BackendExecutionError as exc:
        if not is_formula_runtime_unavailable(str(exc)):
            raise
        primary_error = exc
        primary_attempt = None

    fallback_error: BackendExecutionError | None = None
    fallback_attempt: AttemptT | None = None
    needs_fallback_attempt = (
        primary_attempt is None
        or (formula_placeholder_count(primary_attempt.markdown_content) > 0)
        or primary_quality_penalty > 0
    )
    if needs_fallback_attempt:
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
            formula_enrichment_ms += fallback_timing_ms
        except BackendExecutionError as exc:
            if not is_formula_runtime_unavailable(str(exc)):
                raise
            fallback_error = exc
    timings = {"formula_enrichment_ms": formula_enrichment_ms}

    if primary_attempt is None and fallback_attempt is not None:
        warnings.append(formula_preset_switch_warning)
        warnings.extend(ordering_warnings_resolver(fallback_attempt))
        return fallback_attempt, warnings, timings

    if primary_attempt is not None and fallback_attempt is not None:
        primary_placeholder_count = formula_placeholder_count(primary_attempt.markdown_content)
        fallback_placeholder_count = formula_placeholder_count(fallback_attempt.markdown_content)
        primary_quality_penalty = markdown_quality_penalty(primary_attempt.markdown_content)
        fallback_quality_penalty = markdown_quality_penalty(fallback_attempt.markdown_content)
        if fallback_placeholder_count < primary_placeholder_count:
            warnings.append(formula_preset_switch_warning)
            warnings.extend(ordering_warnings_resolver(fallback_attempt))
            return fallback_attempt, warnings, timings
        if (
            fallback_placeholder_count == primary_placeholder_count
            and fallback_quality_penalty < primary_quality_penalty
        ):
            warnings.append(formula_preset_switch_warning)
            warnings.append(formula_quality_switch_warning)
            warnings.extend(ordering_warnings_resolver(fallback_attempt))
            return fallback_attempt, warnings, timings
        warnings.extend(ordering_warnings_resolver(primary_attempt))
        return primary_attempt, warnings, timings

    if primary_attempt is not None:
        warnings.extend(ordering_warnings_resolver(primary_attempt))
        return primary_attempt, warnings, timings

    if primary_error is not None or fallback_error is not None:
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
            [formula_enrichment_fallback_warning] + ordering_warnings_resolver(attempt),
            timings,
        )

    raise BackendExecutionError("Docling formula enrichment failed without runtime diagnostics.")


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
