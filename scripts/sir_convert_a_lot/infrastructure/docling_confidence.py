"""Docling confidence helpers for PDF conversion.

Purpose:
    Interpret Docling confidence metadata used by the PDF backend's OCR retry
    decision without coupling that parsing to backend orchestration.

Relationships:
    Used by `infrastructure.docling_backend` when deciding whether an automatic
    OCR retry is warranted after a Docling pass.
"""

from __future__ import annotations

_LOW_CONFIDENCE_GRADES = {"poor", "fair"}


def is_docling_low_confidence(result: object) -> bool:
    """Return whether a Docling result reports a low confidence grade."""
    confidence = getattr(result, "confidence", None)
    if confidence is None:
        return False
    low_grade = getattr(confidence, "low_grade", None)
    if low_grade is None:
        return False
    if hasattr(low_grade, "value"):
        grade_value = str(low_grade.value).lower()
    else:
        grade_value = str(low_grade).lower()
    return grade_value in _LOW_CONFIDENCE_GRADES
