"""Conversion backend contracts for Sir Convert-a-Lot infrastructure.

Purpose:
    Define typed request/response contracts and backend protocol boundaries for
    conversion execution implementations in the infrastructure layer.

Relationships:
    - Used by `infrastructure.runtime_engine` to call conversion backends.
    - Implemented by backend adapters such as `infrastructure.docling_backend`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from scripts.sir_convert_a_lot.domain.specs import BackendStrategy, OcrMode, TableMode
from scripts.sir_convert_a_lot.infrastructure.gpu_runtime_probe import GpuRuntimeProbeResult


@dataclass(frozen=True)
class ConversionRequest:
    """Backend-independent request payload for one PDF conversion."""

    source_filename: str
    source_bytes: bytes
    backend_strategy: BackendStrategy
    ocr_mode: OcrMode
    table_mode: TableMode
    gpu_available: bool


@dataclass(frozen=True)
class ConversionResultData:
    """Backend-independent conversion result payload."""

    markdown_content: str
    backend_used: str
    acceleration_used: str
    ocr_enabled: bool
    warnings: list[str] = field(default_factory=list)
    phase_timings_ms: dict[str, int] = field(default_factory=dict)


class ConversionBackend(Protocol):
    """Protocol for one conversion backend implementation."""

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        """Convert one PDF request into markdown with metadata."""
        raise NotImplementedError


class BackendInputError(Exception):
    """Raised when conversion input is invalid/unreadable for the backend."""


class BackendExecutionError(Exception):
    """Raised when backend execution fails for internal/runtime reasons."""


class BackendGpuUnavailableError(Exception):
    """Raised when GPU conversion is requested without a usable GPU runtime."""

    def __init__(self, *, backend: str, probe: GpuRuntimeProbeResult) -> None:
        self.backend = backend
        self.probe = probe
        super().__init__(
            f"{backend} backend GPU runtime unavailable "
            f"(runtime_kind={probe.runtime_kind}, is_available={probe.is_available})"
        )

    def as_details(self) -> dict[str, object]:
        """Return deterministic details for API/runtime error mapping."""
        return {
            "backend": self.backend,
            **self.probe.as_details(),
        }
