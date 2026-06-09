"""Helpers for Docling formula diagnostic payload normalization.

Purpose:
    Keep low-risk value normalization and elapsed-time helpers separate from
    the formula VLM instrumentation wrappers.

Relationships:
    Used by `infrastructure.docling_formula_diagnostics` when building
    sanitized conversion diagnostics.
"""

from __future__ import annotations


def converter_key_payload(key: object) -> dict[str, object]:
    """Return JSON-safe Docling converter-cache key fields."""
    fields = (
        "table_mode",
        "ocr_enabled",
        "force_full_page_ocr",
        "ocr_engine",
        "ocr_languages",
        "ocr_use_gpu",
        "acceleration_device",
        "layout_model_key",
        "formula_enrichment",
        "formula_preset",
        "document_timeout_seconds",
    )
    return {field_name: safe_value(getattr(key, field_name, None)) for field_name in fields}


def safe_value(value: object) -> object:
    """Return a JSON-safe scalar/list value for diagnostics."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, tuple | list):
        return [safe_value(item) for item in value]
    return enum_or_string(value)


def enum_or_string(value: object) -> str | None:
    """Return enum `.value` when string-like, otherwise `str(value)`."""
    if value is None:
        return None
    enum_value = getattr(value, "value", None)
    if isinstance(enum_value, str):
        return enum_value
    return str(value)


def record_int(record: dict[str, object], key: str) -> int:
    """Return a non-negative integer field from a diagnostic record."""
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)
