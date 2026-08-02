"""Tests for backend routing and rollout policy helpers.

Purpose:
    Validate deterministic policy checks and backend selection logic extracted
    from runtime orchestration.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.infrastructure.backend_routing`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.specs import JobSpec
from scripts.sir_convert_a_lot.infrastructure.backend_routing import (
    select_backend,
    validate_acceleration_policy,
    validate_backend_strategy,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import (
    ConversionBackend,
    ConversionRequest,
    ConversionResultData,
)


class _StubBackend(ConversionBackend):
    def __init__(self, label: str) -> None:
        self.label = label

    def convert(self, request: ConversionRequest) -> ConversionResultData:  # pragma: no cover
        raise NotImplementedError(request.source_filename)


def _job_spec(
    *,
    backend_strategy: str = "auto",
    ocr_mode: str = "auto",
    acceleration_policy: str = "gpu_required",
) -> JobSpec:
    return JobSpec.model_validate(
        {
            "api_version": "v1",
            "source": {"kind": "upload", "filename": "paper.pdf"},
            "conversion": {
                "output_format": "md",
                "backend_strategy": backend_strategy,
                "ocr_mode": ocr_mode,
                "table_mode": "fast",
                "normalize": "standard",
            },
            "execution": {
                "acceleration_policy": acceleration_policy,
                "priority": "normal",
                "document_timeout_seconds": 1800,
            },
            "retention": {"pin": False},
        }
    )


def test_validate_backend_strategy_rejects_pymupdf_gpu_policies() -> None:
    issue = validate_backend_strategy(
        _job_spec(
            backend_strategy="pymupdf",
            ocr_mode="off",
            acceleration_policy="gpu_required",
        )
    )
    assert issue is not None
    assert issue.code == "validation_error"
    assert issue.details == {
        "field": "conversion.backend_strategy",
        "reason": "backend_incompatible_with_gpu_policy",
    }


def test_validate_backend_strategy_rejects_pymupdf_ocr_force() -> None:
    issue = validate_backend_strategy(
        _job_spec(
            backend_strategy="pymupdf",
            ocr_mode="force",
            acceleration_policy="cpu_only",
        )
    )
    assert issue is not None
    assert issue.details == {
        "field": "conversion.ocr_mode",
        "reason": "backend_option_incompatible",
        "backend": "pymupdf",
        "supported": ["off"],
    }


def test_validate_backend_strategy_accepts_non_pymupdf() -> None:
    issue = validate_backend_strategy(_job_spec(backend_strategy="auto"))
    assert issue is None


def test_validate_acceleration_policy_rejects_cpu_only_when_locked() -> None:
    issue = validate_acceleration_policy(
        _job_spec(acceleration_policy="cpu_only"),
        gpu_available=False,
        allow_cpu_only=False,
        allow_cpu_fallback=False,
    )
    assert issue is not None
    assert issue.code == "gpu_not_available"


def test_select_backend_routes_explicit_pymupdf() -> None:
    docling_backend = _StubBackend("docling")
    pymupdf_backend = _StubBackend("pymupdf")
    selected = select_backend(
        backend_strategy=_job_spec(backend_strategy="pymupdf").conversion.backend_strategy,
        docling_backend=docling_backend,
        pymupdf_backend=pymupdf_backend,
    )
    assert isinstance(selected, _StubBackend)
    assert selected.label == "pymupdf"
