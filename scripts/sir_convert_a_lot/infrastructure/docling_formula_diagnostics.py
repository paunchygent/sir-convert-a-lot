"""Docling formula/code VLM diagnostic instrumentation.

Purpose:
    Capture sanitized low-level diagnostics from Docling's code/formula VLM path.

Relationships:
    Installed by `infrastructure.docling_backend`; read by Docling page-window replay replay.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from collections.abc import Callable, Iterable
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from os import environ

from docling.datamodel.base_models import ItemAndImageEnrichmentElement
from docling.models.inference_engines.vlm import VlmEngineInput, VlmEngineOutput
from docling.models.inference_engines.vlm.auto_inline_engine import AutoInlineVlmEngine
from docling.models.inference_engines.vlm.transformers_engine import TransformersVlmEngine
from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel
from docling_core.types.doc import DoclingDocument, NodeItem

from scripts.sir_convert_a_lot.infrastructure.docling_formula_crop_metrics import (
    element_label as formula_element_label,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_crop_metrics import (
    formula_crop_metrics,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_crop_metrics import (
    image_dimensions as formula_image_dimensions,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_events import (
    docling_formula_diagnostic_events_enabled,
    docling_formula_single_item_replay_enabled,
    emit_docling_formula_diagnostic_event,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_helpers import (
    converter_key_payload,
    enum_or_string,
    record_int,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_diagnostics_payload import (
    output_token_counts,
    transformers_call_payload,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_duplicate_guard import (
    FormulaBatchPartition,
    partition_formula_batch_by_doc,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_generation_diagnostics import (
    run_with_transformers_generate_events,
)
from scripts.sir_convert_a_lot.infrastructure.docling_formula_runtime_controls import (
    activate_formula_model_runtime_controls,
    apply_formula_runtime_controls_to_inputs,
    disable_formula_torch_compile_for_rocm,
    reset_formula_model_runtime_controls,
)

CodeFormulaCall = Callable[..., Iterable[NodeItem]]
AutoInlinePredictBatch = Callable[..., list[VlmEngineOutput]]
TransformersPredictBatch = Callable[..., list[VlmEngineOutput]]

_MAX_RECORDS = 48
_ACTIVE_COLLECTOR: ContextVar[FormulaDiagnosticsCollector | None] = ContextVar(
    "sir_convert_a_lot_docling_formula_diagnostics",
    default=None,
)
_PATCH_LOCK = threading.Lock()
_PATCH_INSTALLED = False
_ORIGINAL_CODE_FORMULA_CALL: CodeFormulaCall | None = None
_ORIGINAL_AUTO_INLINE_PREDICT_BATCH: AutoInlinePredictBatch | None = None
_ORIGINAL_TRANSFORMERS_PREDICT_BATCH: TransformersPredictBatch | None = None
_FORMULA_TARGET_ITEM_REF_ENV_VAR = "SIR_CONVERT_A_LOT_DOCLING_FORMULA_TARGET_ITEM_REF"


@dataclass
class FormulaDiagnosticsCollector:
    """In-memory sanitized diagnostic accumulator for one conversion."""

    converter_cache_hits: int = 0
    converter_cache_misses: int = 0
    converter_requests: list[dict[str, object]] = field(default_factory=list)
    code_formula_batches: list[dict[str, object]] = field(default_factory=list)
    auto_inline_calls: list[dict[str, object]] = field(default_factory=list)
    transformers_calls: list[dict[str, object]] = field(default_factory=list)

    def record_converter_cache_lookup(self, *, hit: bool, key: object) -> None:
        """Record converter cache behavior without source or document content."""
        if hit:
            self.converter_cache_hits += 1
        else:
            self.converter_cache_misses += 1
        _append_bounded(
            self.converter_requests,
            {
                "cache_hit": hit,
                "key": converter_key_payload(key),
            },
        )

    def record_code_formula_batch(
        self,
        *,
        model: object,
        element_batch: Iterable[object],
        yielded_count: int,
        elapsed_ms: int,
    ) -> None:
        """Record one Docling code/formula enrichment batch."""
        elements = tuple(element_batch)
        label_counts: Counter[str] = Counter()
        crop_areas: list[int] = []
        for element in elements:
            label_counts[formula_element_label(element)] += 1
            width, height = formula_image_dimensions(getattr(element, "image", None))
            if width is not None and height is not None:
                crop_areas.append(width * height)
        _append_bounded(
            self.code_formula_batches,
            {
                "model_class": type(model).__name__,
                "batch_size": len(elements),
                "yielded_count": yielded_count,
                "elapsed_ms": elapsed_ms,
                "label_counts": dict(sorted(label_counts.items())),
                "crop_count": len(crop_areas),
                "crop_pixel_area_total": sum(crop_areas),
                "crop_pixel_area_max": max(crop_areas) if crop_areas else 0,
            },
        )

    def record_auto_inline_call(
        self,
        *,
        engine: object,
        input_batch: Iterable[object],
        elapsed_ms: int,
        status: str,
        error_type: str | None,
        initialized_before: bool,
    ) -> None:
        """Record one AutoInline engine delegation call."""
        actual_engine = getattr(engine, "actual_engine", None)
        _append_bounded(
            self.auto_inline_calls,
            {
                "engine_class": type(engine).__name__,
                "actual_engine_class": type(actual_engine).__name__
                if actual_engine is not None
                else None,
                "selected_engine_type": enum_or_string(
                    getattr(engine, "selected_engine_type", None)
                ),
                "batch_size": len(tuple(input_batch)),
                "elapsed_ms": elapsed_ms,
                "status": status,
                "error_type": error_type,
                "initialized_before": initialized_before,
                "initialized_after": bool(getattr(engine, "_initialized", False)),
            },
        )

    def record_transformers_call(
        self,
        *,
        engine: object,
        input_batch: Iterable[object],
        outputs: Iterable[object],
        elapsed_ms: int,
        status: str,
        error_type: str | None,
        initialized_before: bool,
    ) -> None:
        """Record one Transformers VLM generation call."""
        inputs = tuple(input_batch)
        output_items = tuple(outputs)
        token_counts = output_token_counts(output_items)
        payload = transformers_call_payload(
            engine=engine,
            inputs=inputs,
            token_counts=token_counts,
            elapsed_ms=elapsed_ms,
            status=status,
            error_type=error_type,
            initialized_before=initialized_before,
        )
        _append_bounded(
            self.transformers_calls,
            payload,
        )
        emit_docling_formula_diagnostic_event(
            {
                "event": "transformers_predict_batch_completed",
                **payload,
            }
        )

    def to_payload(self) -> dict[str, object]:
        """Return a stable sanitized diagnostics payload."""
        formula_elapsed_ms = sum(
            record_int(item, "elapsed_ms") for item in self.code_formula_batches
        )
        transformer_elapsed_ms = sum(
            record_int(item, "elapsed_ms") for item in self.transformers_calls
        )
        formula_item_count = sum(
            record_int(item, "batch_size") for item in self.code_formula_batches
        )
        generated_token_total = sum(
            record_int(item, "generated_token_total") for item in self.transformers_calls
        )
        return {
            "schema_version": "docling_formula_diagnostics_v1",
            "converter_cache_hits": self.converter_cache_hits,
            "converter_cache_misses": self.converter_cache_misses,
            "converter_requests": list(self.converter_requests),
            "formula_vlm_batch_count": len(self.code_formula_batches),
            "formula_vlm_item_count": formula_item_count,
            "formula_vlm_total_ms": formula_elapsed_ms,
            "auto_inline_call_count": len(self.auto_inline_calls),
            "transformers_call_count": len(self.transformers_calls),
            "transformers_total_ms": transformer_elapsed_ms,
            "transformers_generated_token_total": generated_token_total,
            "code_formula_batches": list(self.code_formula_batches),
            "auto_inline_calls": list(self.auto_inline_calls),
            "transformers_calls": list(self.transformers_calls),
        }


def install_docling_formula_diagnostics_patch() -> None:
    """Install idempotent wrappers around the Docling formula/code VLM path."""
    global _ORIGINAL_AUTO_INLINE_PREDICT_BATCH
    global _ORIGINAL_CODE_FORMULA_CALL
    global _ORIGINAL_TRANSFORMERS_PREDICT_BATCH
    global _PATCH_INSTALLED
    with _PATCH_LOCK:
        if _PATCH_INSTALLED:
            return
        _ORIGINAL_CODE_FORMULA_CALL = CodeFormulaVlmModel.__call__
        _ORIGINAL_AUTO_INLINE_PREDICT_BATCH = AutoInlineVlmEngine.predict_batch
        _ORIGINAL_TRANSFORMERS_PREDICT_BATCH = TransformersVlmEngine.predict_batch
        setattr(CodeFormulaVlmModel, "__call__", _instrumented_code_formula_call)
        setattr(AutoInlineVlmEngine, "predict_batch", _instrumented_auto_inline_predict_batch)
        setattr(
            TransformersVlmEngine,
            "predict_batch",
            _instrumented_transformers_predict_batch,
        )
        _PATCH_INSTALLED = True


def begin_docling_formula_diagnostics() -> Token[FormulaDiagnosticsCollector | None]:
    """Start a conversion-local diagnostics context."""
    return _ACTIVE_COLLECTOR.set(FormulaDiagnosticsCollector())


def end_docling_formula_diagnostics(
    token: Token[FormulaDiagnosticsCollector | None],
) -> dict[str, object]:
    """Finish the active diagnostics context and return its payload."""
    collector = _ACTIVE_COLLECTOR.get()
    _ACTIVE_COLLECTOR.reset(token)
    if collector is None:
        return {}
    return collector.to_payload()


def record_docling_converter_cache_lookup(*, hit: bool, key: object) -> None:
    """Record a converter-cache lookup for the active conversion if present."""
    collector = _ACTIVE_COLLECTOR.get()
    if collector is not None:
        collector.record_converter_cache_lookup(hit=hit, key=key)


def emit_code_formula_batch_started(*, model: object, element_batch: Iterable[object]) -> None:
    """Persist per-crop metrics before a formula/code VLM batch starts."""
    if not docling_formula_diagnostic_events_enabled():
        return
    elements = tuple(element_batch)
    emit_docling_formula_diagnostic_event(
        {
            "event": "code_formula_batch_started",
            "model_class": type(model).__name__,
            "batch_size": len(elements),
            "crops": formula_crop_metrics(elements),
        }
    )


def emit_code_formula_batch_split_started(
    *,
    model: object,
    element_batch: Iterable[object],
) -> None:
    """Persist the parent batch before diagnostic single-item replay begins."""
    if not docling_formula_diagnostic_events_enabled():
        return
    elements = tuple(element_batch)
    emit_docling_formula_diagnostic_event(
        {
            "event": "code_formula_batch_split_started",
            "model_class": type(model).__name__,
            "batch_size": len(elements),
            "crops": formula_crop_metrics(elements),
        }
    )


def emit_code_formula_duplicate_items_skipped(
    *,
    model: object,
    element_batch: Iterable[object],
) -> None:
    """Persist duplicate formula items skipped before model generation."""
    if not docling_formula_diagnostic_events_enabled():
        return
    elements = tuple(element_batch)
    emit_docling_formula_diagnostic_event(
        {
            "event": "code_formula_duplicate_items_skipped",
            "model_class": type(model).__name__,
            "batch_size": len(elements),
            "crops": formula_crop_metrics(elements),
        }
    )


def emit_transformers_predict_batch_started(
    *,
    engine: object,
    input_batch: Iterable[object],
    initialized_before: bool,
) -> None:
    """Persist a pre-generation breadcrumb for killable replay children."""
    emit_docling_formula_diagnostic_event(
        {
            "event": "transformers_predict_batch_started",
            **transformers_call_payload(
                engine=engine,
                inputs=tuple(input_batch),
                token_counts=[],
                elapsed_ms=None,
                status="started",
                error_type=None,
                initialized_before=initialized_before,
            ),
        }
    )


def formula_enrichment_elapsed_ms(diagnostics: dict[str, object]) -> int | None:
    """Extract the formula enrichment elapsed milliseconds from diagnostics."""
    batch_count = diagnostics.get("formula_vlm_batch_count")
    if isinstance(batch_count, bool) or not isinstance(batch_count, int) or batch_count <= 0:
        return None
    value = diagnostics.get("formula_vlm_total_ms")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(0, value)


def _instrumented_code_formula_call(
    self: CodeFormulaVlmModel,
    doc: DoclingDocument,
    element_batch: Iterable[ItemAndImageEnrichmentElement],
) -> Iterable[NodeItem]:
    original = _ORIGINAL_CODE_FORMULA_CALL
    if original is None:
        raise RuntimeError("Docling formula diagnostics patch is not installed.")
    control_token = activate_formula_model_runtime_controls(self)
    try:
        batch = tuple(element_batch)
        partition = _partition_batch(doc, batch)
        if partition.has_duplicates:
            yield from _instrumented_partitioned_code_formula_call(self, doc, partition, original)
            return
        if docling_formula_single_item_replay_enabled():
            yield from _instrumented_single_item_code_formula_call(self, doc, batch, original)
            return
        yielded_count = 0
        emit_code_formula_batch_started(model=self, element_batch=batch)
        started = time.perf_counter()
        try:
            for item in original(self, doc, batch):
                yielded_count += 1
                yield item
        finally:
            collector = _ACTIVE_COLLECTOR.get()
            if collector is not None:
                collector.record_code_formula_batch(
                    model=self,
                    element_batch=batch,
                    yielded_count=yielded_count,
                    elapsed_ms=_elapsed_ms(started),
                )
    finally:
        reset_formula_model_runtime_controls(control_token)


def _partition_batch(
    doc: DoclingDocument,
    batch: tuple[ItemAndImageEnrichmentElement, ...],
) -> FormulaBatchPartition:
    return partition_formula_batch_by_doc(doc, batch)


def _instrumented_partitioned_code_formula_call(
    model: CodeFormulaVlmModel,
    doc: DoclingDocument,
    partition: FormulaBatchPartition,
    original: CodeFormulaCall,
) -> Iterable[NodeItem]:
    emit_code_formula_duplicate_items_skipped(
        model=model,
        element_batch=partition.duplicate_elements,
    )
    outputs: list[NodeItem | None] = list(partition.outputs)
    if partition.fresh_elements:
        fresh_outputs = tuple(
            _call_fresh_code_formula_elements(model, doc, partition.fresh_elements, original)
        )
        for position, fresh_output in zip(partition.fresh_positions, fresh_outputs, strict=True):
            outputs[position] = fresh_output
    for candidate in outputs:
        if candidate is not None:
            yield candidate


def _call_fresh_code_formula_elements(
    model: CodeFormulaVlmModel,
    doc: DoclingDocument,
    elements: tuple[ItemAndImageEnrichmentElement, ...],
    original: CodeFormulaCall,
) -> Iterable[NodeItem]:
    if docling_formula_single_item_replay_enabled():
        yield from _instrumented_single_item_code_formula_call(model, doc, elements, original)
        return
    yielded_count = 0
    emit_code_formula_batch_started(model=model, element_batch=elements)
    started = time.perf_counter()
    try:
        for item in original(model, doc, elements):
            yielded_count += 1
            yield item
    finally:
        collector = _ACTIVE_COLLECTOR.get()
        if collector is not None:
            collector.record_code_formula_batch(
                model=model,
                element_batch=elements,
                yielded_count=yielded_count,
                elapsed_ms=_elapsed_ms(started),
            )


def _instrumented_single_item_code_formula_call(
    model: CodeFormulaVlmModel,
    doc: DoclingDocument,
    batch: tuple[ItemAndImageEnrichmentElement, ...],
    original: CodeFormulaCall,
) -> Iterable[NodeItem]:
    emit_code_formula_batch_split_started(model=model, element_batch=batch)
    target_item_ref = environ.get(_FORMULA_TARGET_ITEM_REF_ENV_VAR)
    for element in batch:
        if target_item_ref and _element_self_ref(element) != target_item_ref:
            _emit_single_item_target_skip(
                model=model,
                element=element,
                target_item_ref=target_item_ref,
            )
            item = getattr(element, "item", None)
            if item is not None:
                yield item
            continue
        single_batch = (element,)
        yielded_count = 0
        emit_code_formula_batch_started(model=model, element_batch=single_batch)
        started = time.perf_counter()
        try:
            for item in original(model, doc, single_batch):
                yielded_count += 1
                yield item
        finally:
            collector = _ACTIVE_COLLECTOR.get()
            if collector is not None:
                collector.record_code_formula_batch(
                    model=model,
                    element_batch=single_batch,
                    yielded_count=yielded_count,
                    elapsed_ms=_elapsed_ms(started),
                )


def _element_self_ref(element: object) -> str | None:
    item = getattr(element, "item", None)
    self_ref = getattr(item, "self_ref", None)
    return self_ref if isinstance(self_ref, str) else None


def _emit_single_item_target_skip(
    *,
    model: CodeFormulaVlmModel,
    element: ItemAndImageEnrichmentElement,
    target_item_ref: str,
) -> None:
    emit_docling_formula_diagnostic_event(
        {
            "event": "code_formula_single_item_skipped_by_target",
            "model_class": type(model).__name__,
            "target_item_self_ref": target_item_ref,
            "crops": formula_crop_metrics((element,)),
        }
    )


def _instrumented_auto_inline_predict_batch(
    self: AutoInlineVlmEngine,
    input_batch: list[VlmEngineInput],
) -> list[VlmEngineOutput]:
    original = _ORIGINAL_AUTO_INLINE_PREDICT_BATCH
    if original is None:
        raise RuntimeError("Docling formula diagnostics patch is not installed.")
    initialized_before = bool(getattr(self, "_initialized", False))
    started = time.perf_counter()
    try:
        outputs = original(self, input_batch)
    except Exception as exc:
        _record_auto_inline(
            self, input_batch, started, "failed", type(exc).__name__, initialized_before
        )
        raise
    _record_auto_inline(self, input_batch, started, "succeeded", None, initialized_before)
    return outputs


def _instrumented_transformers_predict_batch(
    self: TransformersVlmEngine,
    input_batch: list[VlmEngineInput],
) -> list[VlmEngineOutput]:
    original = _ORIGINAL_TRANSFORMERS_PREDICT_BATCH
    if original is None:
        raise RuntimeError("Docling formula diagnostics patch is not installed.")
    controlled_batch = apply_formula_runtime_controls_to_inputs(input_batch)
    if disable_formula_torch_compile_for_rocm(self):
        emit_docling_formula_diagnostic_event(
            {
                "event": "formula_torch_compile_disabled",
                "engine_class": type(self).__name__,
                "model_class": type(getattr(self, "vlm_model", None)).__name__,
            }
        )
    initialized_before = bool(getattr(self, "_initialized", False))
    emit_transformers_predict_batch_started(
        engine=self,
        input_batch=controlled_batch,
        initialized_before=initialized_before,
    )
    started = time.perf_counter()
    try:
        outputs = run_with_transformers_generate_events(
            engine=self,
            input_batch=controlled_batch,
            predict_batch=lambda: original(self, controlled_batch),
        )
    except Exception as exc:
        _record_transformers(
            self, controlled_batch, (), started, "failed", type(exc).__name__, initialized_before
        )
        raise
    _record_transformers(
        self,
        controlled_batch,
        outputs,
        started,
        "succeeded",
        None,
        initialized_before,
    )
    return outputs


def _record_auto_inline(
    engine: AutoInlineVlmEngine,
    input_batch: list[VlmEngineInput],
    started: float,
    status: str,
    error_type: str | None,
    initialized_before: bool,
) -> None:
    collector = _ACTIVE_COLLECTOR.get()
    if collector is not None:
        collector.record_auto_inline_call(
            engine=engine,
            input_batch=input_batch,
            elapsed_ms=_elapsed_ms(started),
            status=status,
            error_type=error_type,
            initialized_before=initialized_before,
        )


def _record_transformers(
    engine: TransformersVlmEngine,
    input_batch: list[VlmEngineInput],
    outputs: Iterable[VlmEngineOutput],
    started: float,
    status: str,
    error_type: str | None,
    initialized_before: bool,
) -> None:
    collector = _ACTIVE_COLLECTOR.get()
    if collector is not None:
        collector.record_transformers_call(
            engine=engine,
            input_batch=input_batch,
            outputs=outputs,
            elapsed_ms=_elapsed_ms(started),
            status=status,
            error_type=error_type,
            initialized_before=initialized_before,
        )


def _append_bounded(records: list[dict[str, object]], record: dict[str, object]) -> None:
    records.append(record)
    if len(records) > _MAX_RECORDS:
        del records[0 : len(records) - _MAX_RECORDS]


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
