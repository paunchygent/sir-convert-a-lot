"""OCR metadata contract OCR metadata contract regression tests.

Purpose:
    Lock the selected Outcome B contract for PDF OCR result metadata: active v2
    result metadata reports observed OCR execution fields only, while request
    echo and OCR-stage acceleration remain outside the terminal result model.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.application.contracts_v2`.
    - Complements the PDF-to-Markdown API lifecycle test that proves serialized
      result payloads omit deferred OCR metadata fields.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.contracts_v2 import ConversionMetadataV2


def _legacy_requested_languages_field() -> str:
    return "ocr_languages_" + "requested"


def _legacy_ocr_acceleration_field() -> str:
    return "ocr_" + "acceleration_used"


def _active_metadata_payload() -> dict[str, object]:
    return {
        "pipeline_used": "pdf_to_md_v2",
        "backend_used": "docling",
        "acceleration_used": "cuda",
        "ocr_enabled": True,
        "ocr_engine_used": "easyocr",
        "ocr_languages_used": ["sv", "en"],
        "acceleration_policy_requested": "gpu_required",
        "gpu_runtime_kind": "rocm",
        "gpu_device_count": 1,
        "gpu_busy_percent": 72,
        "gpu_memory_used_percent": 40,
        "options_fingerprint": "ocr-metadata-contract_contract",
        "parallel_enabled": True,
        "max_chunk_workers": 2,
        "chunk_size_pages": 5,
        "effective_gpu_stage_limit": 1,
        "scheduling_mode": "bounded_parallel",
    }


def test_conversion_metadata_v2_accepts_only_active_ocr_result_fields() -> None:
    metadata = ConversionMetadataV2.model_validate(_active_metadata_payload())

    payload = metadata.model_dump()
    assert payload["ocr_enabled"] is True
    assert payload["ocr_engine_used"] == "easyocr"
    assert payload["ocr_languages_used"] == ["sv", "en"]
    assert _legacy_requested_languages_field() not in payload
    assert _legacy_ocr_acceleration_field() not in payload


def test_conversion_metadata_v2_rejects_deferred_ocr_result_fields() -> None:
    payload = _active_metadata_payload()
    payload[_legacy_requested_languages_field()] = ["sv", "en"]
    payload[_legacy_ocr_acceleration_field()] = "cuda"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ConversionMetadataV2.model_validate(payload)
