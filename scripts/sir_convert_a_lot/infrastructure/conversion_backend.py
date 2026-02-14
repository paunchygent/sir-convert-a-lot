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


class ConversionBackend(Protocol):
    """Protocol for one conversion backend implementation."""

    def convert(self, request: ConversionRequest) -> ConversionResultData:
        """Convert one PDF request into markdown with metadata."""
        raise NotImplementedError
