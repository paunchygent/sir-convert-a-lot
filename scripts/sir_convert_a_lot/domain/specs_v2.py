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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    DOCX = "docx"


class OutputFormatV2(StrEnum):
    """Supported output formats for v2."""

    MD = "md"
    PDF = "pdf"
    DOCX = "docx"


class PdfPaperSizeV2(StrEnum):
    """Supported PDF paper sizes for v2 PDF outputs."""

    A5 = "a5"
    A4 = "a4"
    A3 = "a3"


class PdfOrientationV2(StrEnum):
    """Supported PDF orientations for v2 PDF outputs."""

    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"


class PdfPageCssModeV2(StrEnum):
    """Control whether PDF routes append service page CSS or trust author CSS."""

    PRESET_APPEND = "preset_append"
    AUTHOR_OWNED = "author_owned"


class InputTrustModeV2(StrEnum):
    """Control how HTML input bundles are trusted for PDF rendering."""

    UNTRUSTED_UPLOAD = "untrusted_upload"
    TRUSTED_APP_BUNDLE = "trusted_app_bundle"


class OcrEngineV2(StrEnum):
    """Supported OCR engines for PDF OCR stages."""

    AUTO = "auto"
    EASYOCR = "easyocr"
    TESSERACT_CLI = "tesseract_cli"


class PdfLayoutV2(BaseModel):
    """Typed PDF layout presets for v2 PDF outputs."""

    model_config = ConfigDict(extra="forbid")

    paper_size: PdfPaperSizeV2 = PdfPaperSizeV2.A4
    orientation: PdfOrientationV2 = PdfOrientationV2.PORTRAIT
    margins_mm: int = Field(default=12, ge=0, le=50)


class SourceSpecV2(BaseModel):
    """Source section of the v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    kind: SourceKindV2
    filename: str = Field(min_length=1)
    format: SourceFormatV2


class TemplateSelectorV2(BaseModel):
    """Template selector for DOCX-producing v2 routes."""

    model_config = ConfigDict(extra="forbid")

    template_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str | None = Field(default=None, pattern=r"^\d+\.\d+\.\d+$")


class ConversionSpecV2(BaseModel):
    """Conversion section of the v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    output_format: OutputFormatV2
    input_trust_mode: InputTrustModeV2 = InputTrustModeV2.UNTRUSTED_UPLOAD
    css_filenames: list[str] = Field(default_factory=list)
    page_css_mode: PdfPageCssModeV2 | None = None
    pdf_layout: PdfLayoutV2 | None = None
    template: TemplateSelectorV2 | None = None
    reference_docx_filename: str | None = None


class PdfOptionsV2(BaseModel):
    """PDF-to-intermediate options for v2 routes that start from a PDF."""

    model_config = ConfigDict(extra="forbid")

    backend_strategy: BackendStrategy
    ocr_mode: OcrMode
    ocr_engine: OcrEngineV2 = Field(
        default=OcrEngineV2.AUTO,
        description="OCR engine selection. 'auto' delegates to runtime defaults.",
    )
    ocr_languages: list[str] = Field(
        default_factory=list,
        description=(
            "Requested OCR languages as BCP47/ISO639-1 tags (e.g. ['sv','en']). "
            "Empty list delegates to runtime defaults."
        ),
    )
    table_mode: TableMode
    normalize: NormalizeMode

    @field_validator("ocr_languages", mode="before")
    @classmethod
    def _normalize_ocr_languages(cls, value: object) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("pdf_options.ocr_languages must be a list of strings")
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in value:
            if not isinstance(raw, str):
                raise TypeError("pdf_options.ocr_languages entries must be strings")
            candidate = raw.strip().lower()
            if candidate == "":
                raise ValueError("pdf_options.ocr_languages entries must not be empty")
            parts = candidate.split("-")
            primary = parts[0]
            if len(primary) != 2 or not primary.isalpha():
                raise ValueError(
                    "pdf_options.ocr_languages entries must start with an ISO639-1 tag "
                    "(e.g. 'sv' or 'en')"
                )
            for part in parts[1:]:
                if part == "":
                    raise ValueError(
                        "pdf_options.ocr_languages entries must not include empty tags"
                    )
                if not part.isalnum():
                    raise ValueError(
                        "pdf_options.ocr_languages entries must use only letters/numbers "
                        "and hyphen separators"
                    )
            if candidate in seen:
                continue
            normalized.append(candidate)
            seen.add(candidate)
        return normalized


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
            (SourceFormatV2.PDF, OutputFormatV2.MD),
            (SourceFormatV2.DOCX, OutputFormatV2.MD),
            (SourceFormatV2.HTML, OutputFormatV2.MD),
            (SourceFormatV2.DOCX, OutputFormatV2.PDF),
            (SourceFormatV2.MD, OutputFormatV2.PDF),
            (SourceFormatV2.MD, OutputFormatV2.DOCX),
            (SourceFormatV2.HTML, OutputFormatV2.PDF),
            (SourceFormatV2.HTML, OutputFormatV2.DOCX),
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

        if self.conversion.output_format != OutputFormatV2.PDF and self.conversion.css_filenames:
            raise ValueError("css_filenames is only supported for PDF outputs")

        if (
            self.conversion.output_format != OutputFormatV2.PDF
            and self.conversion.pdf_layout is not None
        ):
            raise ValueError("pdf_layout is only supported for PDF outputs")
        if (
            self.conversion.output_format != OutputFormatV2.PDF
            and self.conversion.page_css_mode is not None
        ):
            raise ValueError("page_css_mode is only supported for PDF outputs")
        if (
            self.conversion.input_trust_mode != InputTrustModeV2.UNTRUSTED_UPLOAD
            and route != (SourceFormatV2.HTML, OutputFormatV2.PDF)
        ):
            raise ValueError("input_trust_mode is only supported for html -> pdf routes")
        if (
            self.conversion.output_format == OutputFormatV2.PDF
            and self.conversion.page_css_mode == PdfPageCssModeV2.AUTHOR_OWNED
            and self.conversion.pdf_layout is not None
        ):
            raise ValueError("page_css_mode='author_owned' cannot be combined with pdf_layout")

        if self.conversion.output_format != OutputFormatV2.DOCX:
            if self.conversion.reference_docx_filename is not None:
                raise ValueError("reference_docx_filename is only supported for DOCX outputs")
            if self.conversion.template is not None:
                raise ValueError("template is only supported for DOCX outputs")
        elif (
            self.conversion.reference_docx_filename is not None
            and self.conversion.template is not None
        ):
            raise ValueError(
                "reference_docx_filename and template cannot both be provided for DOCX outputs"
            )

        return self
