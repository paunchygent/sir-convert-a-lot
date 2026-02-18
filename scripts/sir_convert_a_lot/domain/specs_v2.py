"""Sir Convert-a-Lot domain specifications for multi-format service API v2.

Purpose:
    Define the core conversion domain language and invariants for v2 jobs,
    independent of transport and infrastructure concerns.

Relationships:
    - Imported by v2 HTTP routes for request validation.
    - Imported by v2 runtime/job-store layers for execution policy enforcement.
    - Coexists with the locked v1 spec models in `scripts.sir_convert_a_lot.domain.specs`.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    NormalizeMode,
    OcrMode,
    Priority,
    TableMode,
)


class SourceKindV2(StrEnum):
    """Supported source kinds for v2 conversion requests."""

    UPLOAD = "upload"


class SourceFormatV2(StrEnum):
    """Supported uploaded source formats for v2."""

    PDF = "pdf"
    MD = "md"
    HTML = "html"


class OutputFormatV2(StrEnum):
    """Supported output formats for v2."""

    PDF = "pdf"
    DOCX = "docx"


class SourceSpecV2(BaseModel):
    """Source section of the v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    kind: SourceKindV2
    filename: str = Field(min_length=1)
    format: SourceFormatV2


class ConversionSpecV2(BaseModel):
    """Conversion section of the v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    output_format: OutputFormatV2
    css_filenames: list[str] = Field(default_factory=list)
    reference_docx_filename: str | None = None


class PdfOptionsV2(BaseModel):
    """PDF-to-intermediate options for v2 routes that start from a PDF."""

    model_config = ConfigDict(extra="forbid")

    backend_strategy: BackendStrategy
    ocr_mode: OcrMode
    table_mode: TableMode
    normalize: NormalizeMode


class ExecutionSpecV2(BaseModel):
    """Execution section of the v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    acceleration_policy: AccelerationPolicy
    priority: Priority = Priority.NORMAL
    document_timeout_seconds: int = Field(default=1800, ge=30, le=7200)


class RetentionSpecV2(BaseModel):
    """Retention section of the v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    pin: bool = False


class JobSpecV2(BaseModel):
    """Complete v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"]
    source: SourceSpecV2
    conversion: ConversionSpecV2
    pdf_options: PdfOptionsV2 | None = None
    execution: ExecutionSpecV2 | None = None
    retention: RetentionSpecV2 = Field(default_factory=RetentionSpecV2)

    @model_validator(mode="after")
    def _validate_route(self) -> "JobSpecV2":
        if self.source.kind != SourceKindV2.UPLOAD:
            raise ValueError("source.kind must be 'upload' in v2")

        route = (self.source.format, self.conversion.output_format)
        allowed_routes: set[tuple[SourceFormatV2, OutputFormatV2]] = {
            (SourceFormatV2.HTML, OutputFormatV2.PDF),
            (SourceFormatV2.HTML, OutputFormatV2.DOCX),
            (SourceFormatV2.MD, OutputFormatV2.PDF),
            (SourceFormatV2.MD, OutputFormatV2.DOCX),
            (SourceFormatV2.PDF, OutputFormatV2.DOCX),
        }
        if route not in allowed_routes:
            raise ValueError(
                f"Unsupported v2 route: {self.source.format.value} -> "
                f"{self.conversion.output_format.value}"
            )

        if self.source.format == SourceFormatV2.PDF:
            if self.pdf_options is None:
                raise ValueError("pdf_options is required when source.format is 'pdf'")
            if self.execution is None:
                raise ValueError("execution is required when source.format is 'pdf'")

        if self.conversion.output_format == OutputFormatV2.DOCX and self.conversion.css_filenames:
            raise ValueError("css_filenames is only supported for PDF outputs")

        if self.conversion.output_format == OutputFormatV2.PDF:
            if self.conversion.reference_docx_filename is not None:
                raise ValueError("reference_docx_filename is only supported for DOCX outputs")

        return self
