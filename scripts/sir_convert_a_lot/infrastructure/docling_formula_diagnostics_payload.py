"""Payload builders for Docling formula VLM diagnostics.

Purpose:
    Build sanitized dictionaries for formula/code VLM runtime events without
    retaining source document content or generated text.

Relationships:
    - Used by `infrastructure.docling_formula_diagnostics`.
    - Complements the JSONL event writer for Docling page-window replay replay evidence.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable


def transformers_call_payload(
    *,
    engine: object,
    inputs: tuple[object, ...],
    token_counts: list[int],
    elapsed_ms: int | None,
    status: str,
    error_type: str | None,
    initialized_before: bool,
) -> dict[str, object]:
    """Return sanitized metadata for one Transformers VLM call."""
    max_new_tokens: list[int] = []
    for item in inputs:
        value = _positive_int(getattr(item, "max_new_tokens", None))
        if value is not None:
            max_new_tokens.append(value)
    payload: dict[str, object] = {
        "engine_class": type(engine).__name__,
        "device": _string_or_none(getattr(engine, "device", None)),
        "model_class": _model_class_name(getattr(engine, "vlm_model", None)),
        "model_dtype": _model_dtype(getattr(engine, "vlm_model", None)),
        "use_kv_cache": bool(getattr(getattr(engine, "options", None), "use_kv_cache", False)),
        "batch_size": len(inputs),
        "prompt_counts": _prompt_counts(inputs),
        "stop_string_count_max": _stop_string_count_max(inputs),
        "max_new_tokens_max": max(max_new_tokens) if max_new_tokens else None,
        "generated_token_counts": list(token_counts),
        "generated_token_total": sum(token_counts),
        "generated_token_max": max(token_counts) if token_counts else None,
        "status": status,
        "error_type": error_type,
        "initialized_before": initialized_before,
        "initialized_after": bool(getattr(engine, "_initialized", False)),
    }
    if elapsed_ms is not None:
        payload["elapsed_ms"] = elapsed_ms
    return payload


def output_token_counts(outputs: Iterable[object]) -> list[int]:
    """Extract sanitized token counts from VLM outputs."""
    values: list[int] = []
    for output in outputs:
        metadata = getattr(output, "metadata", None)
        if isinstance(metadata, dict):
            token_count = _positive_int(metadata.get("num_tokens"))
            if token_count is not None:
                values.append(token_count)
    return values


def _prompt_counts(inputs: Iterable[object]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in inputs:
        prompt = getattr(item, "prompt", None)
        counts[str(prompt) if isinstance(prompt, str) else "unknown"] += 1
    return dict(sorted(counts.items()))


def _stop_string_count_max(inputs: Iterable[object]) -> int | None:
    values: list[int] = []
    for item in inputs:
        stop_strings = getattr(item, "stop_strings", None)
        if isinstance(stop_strings, list | tuple):
            values.append(len(stop_strings))
    return max(values) if values else None


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(0, value)


def _model_class_name(model: object) -> str | None:
    if model is None:
        return None
    return type(model).__name__


def _model_dtype(model: object) -> str | None:
    parameters = getattr(model, "parameters", None)
    if not callable(parameters):
        return None
    try:
        for parameter in parameters():
            dtype = getattr(parameter, "dtype", None)
            if dtype is not None:
                return str(dtype)
    except Exception:
        return None
    return None


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
