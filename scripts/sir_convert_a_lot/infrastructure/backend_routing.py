"""Backend routing and policy validation for conversion runtime orchestration.

Purpose:
    Centralize backend-selection and rollout-compatibility checks so runtime
    orchestration remains focused on job lifecycle and persistence concerns.

Relationships:
    - Used by `infrastructure.runtime_engine` for backend-policy enforcement.
    - Consumes canonical domain enums from `domain.specs`.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    JobSpec,
    OcrMode,
)
from scripts.sir_convert_a_lot.infrastructure.conversion_backend import ConversionBackend


@dataclass(frozen=True)
class PolicyViolation:
    """Structured policy-violation payload for runtime error mapping."""

    status_code: int
    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None = None


def validate_backend_strategy(spec: JobSpec) -> PolicyViolation | None:
    """Validate backend-specific compatibility constraints."""
    if spec.conversion.backend_strategy != BackendStrategy.PYMUPDF:
        return None

    if spec.execution.acceleration_policy in {
        AccelerationPolicy.GPU_REQUIRED,
        AccelerationPolicy.GPU_PREFER,
    }:
        return PolicyViolation(
            status_code=422,
            code="validation_error",
            message="Requested backend is incompatible with the selected acceleration policy.",
            retryable=False,
            details={
                "field": "conversion.backend_strategy",
                "reason": "backend_incompatible_with_gpu_policy",
            },
        )

    if spec.conversion.ocr_mode != OcrMode.OFF:
        return PolicyViolation(
            status_code=422,
            code="validation_error",
            message="Requested OCR mode is incompatible with the selected backend.",
            retryable=False,
            details={
                "field": "conversion.ocr_mode",
                "reason": "backend_option_incompatible",
                "backend": "pymupdf",
                "supported": ["off"],
            },
        )

    return None


def validate_acceleration_policy(
    spec: JobSpec,
    *,
    gpu_available: bool,
    allow_cpu_only: bool,
    allow_cpu_fallback: bool,
) -> PolicyViolation | None:
    """Validate rollout acceleration-policy constraints."""
    policy = spec.execution.acceleration_policy

    if policy == AccelerationPolicy.CPU_ONLY and not allow_cpu_only:
        return PolicyViolation(
            status_code=503,
            code="gpu_not_available",
            message=(
                "CPU-only execution is disabled during GPU-first rollout. "
                "Retry when GPU execution is available."
            ),
            retryable=True,
        )

    if gpu_available:
        return None

    if policy in {AccelerationPolicy.GPU_REQUIRED, AccelerationPolicy.GPU_PREFER}:
        if not allow_cpu_fallback:
            return PolicyViolation(
                status_code=503,
                code="gpu_not_available",
                message="GPU execution is required and no fallback is currently allowed.",
                retryable=True,
            )

    return None


def select_backend(
    *,
    backend_strategy: BackendStrategy,
    docling_backend: ConversionBackend,
    pymupdf_backend: ConversionBackend,
) -> ConversionBackend:
    """Return backend adapter for the requested strategy."""
    if backend_strategy == BackendStrategy.PYMUPDF:
        return pymupdf_backend
    return docling_backend
