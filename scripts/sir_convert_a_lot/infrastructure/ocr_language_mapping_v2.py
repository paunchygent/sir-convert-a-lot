"""OCR language normalization and engine-specific mapping helpers (v2).

Purpose:
    Centralize OCR language tag normalization and mapping rules used by v2 PDF
    OCR engine selection. This avoids duplicating fragile language-code logic
    across the runtime preflight, backend wiring, and verification flows.

Relationships:
    - Used by v2 PDF execution (`infrastructure.v2_pdf_checkpointed_executor`) to
      resolve requested/default OCR languages.
    - Used by Docling backend wiring (`infrastructure.docling_backend`) to map
      BCP47/ISO639-1 tags to engine-specific codes (e.g., Tesseract CLI codes).
    - Used by v2 job preflight (`infrastructure.ocr_preflight_v2`) to validate
      that requested languages are supported and installed.
"""

from __future__ import annotations

from collections.abc import Sequence

_TESSERACT_LANGUAGE_BY_BCP47_PRIMARY: dict[str, str] = {
    "en": "eng",
    "sv": "swe",
}


def normalize_bcp47_language_tags(tags: Sequence[str]) -> tuple[str, ...]:
    """Normalize OCR language tags to stable BCP47 primary subtags.

    The v2 contract accepts BCP47/ISO639-1 tags such as "sv" or "sv-SE".
    Backend engines are mapped using the primary subtag.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        primary = tag.split("-", maxsplit=1)[0].strip().lower()
        if primary == "":
            raise ValueError("OCR language tag cannot be empty.")
        if len(primary) != 2 or not primary.isalpha():
            raise ValueError(
                "OCR language tags must start with an ISO639-1 code (e.g. 'sv' or 'en')."
            )
        if primary in seen:
            continue
        normalized.append(primary)
        seen.add(primary)
    return tuple(normalized)


def map_bcp47_languages_to_tesseract(tags: Sequence[str]) -> tuple[str, ...]:
    """Map normalized BCP47/ISO639-1 tags to Tesseract language codes."""
    normalized = normalize_bcp47_language_tags(tags)
    mapped: list[str] = []
    missing: list[str] = []
    for primary in normalized:
        code = _TESSERACT_LANGUAGE_BY_BCP47_PRIMARY.get(primary)
        if code is None:
            missing.append(primary)
            continue
        mapped.append(code)
    if missing:
        supported = ", ".join(sorted(_TESSERACT_LANGUAGE_BY_BCP47_PRIMARY))
        missing_joined = ", ".join(sorted(missing))
        raise ValueError(
            "Unsupported OCR language(s) for Tesseract engine: "
            f"{missing_joined}. Supported ISO639-1 tags: {supported}."
        )
    return tuple(mapped)
