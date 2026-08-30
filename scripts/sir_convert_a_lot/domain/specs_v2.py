"""Sir Convert-a-Lot domain specifications for multi-format service API v2.

Purpose:
    Define the core conversion domain language and invariants for v2 jobs,
    independent of transport and infrastructure concerns.

Relationships:
    - Imported by v2 HTTP routes for request validation.
    - Imported by v2 runtime/job-store layers for execution policy enforcement.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scripts.sir_convert_a_lot.domain.audio_transcription_options_v2 import (
    AudioTranscriptionOptionsV2,
    TranscriptFormatterReplayOptionsV2,
)
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

    AUDIO = "audio"
    TRANSCRIPT_JSON = "transcript_json"
    PDF = "pdf"
    MD = "md"
    HTML = "html"
    DOCX = "docx"


class OutputFormatV2(StrEnum):
    """Supported output formats for v2."""

    MD = "md"
    PDF = "pdf"
    DOCX = "docx"
    TRANSCRIPT_BUNDLE = "transcript_bundle"


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
    css_filenames: list[str] = Field(default_factory=list)
    page_css_mode: PdfPageCssModeV2 | None = None
    pdf_layout: PdfLayoutV2 | None = None
    template: TemplateSelectorV2 | None = None
    reference_docx_filename: str | None = None
    artifact_language: str | None = Field(default=None, min_length=2, max_length=8)


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


def _source_format_from_raw_value(value: object) -> SourceFormatV2 | None:
    if isinstance(value, SourceFormatV2):
        return value
    if isinstance(value, str):
        try:
            return SourceFormatV2(value)
        except ValueError:
            return None
    return None


def _output_format_from_raw_value(value: object) -> OutputFormatV2 | None:
    if isinstance(value, OutputFormatV2):
        return value
    if isinstance(value, str):
        try:
            return OutputFormatV2(value)
        except ValueError:
            return None
    return None


def _route_ignored_runtime_option_names_from_raw_payload(value: object) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ()
    source_obj = value.get("source")
    conversion_obj = value.get("conversion")
    if not isinstance(source_obj, Mapping) or not isinstance(conversion_obj, Mapping):
        return ()

    source_format = _source_format_from_raw_value(source_obj.get("format"))
    output_format = _output_format_from_raw_value(conversion_obj.get("output_format"))
    if source_format is None or output_format is None:
        return ()

    from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
        route_key_for_values_v2,
        route_policy_for_key_v2,
    )

    policy = route_policy_for_key_v2(
        route_key_for_values_v2(
            source_format=source_format,
            output_format=output_format,
        )
    )
    if policy is None:
        return ()

    ignored: list[str] = []
    if policy.ignores_pdf_options:
        ignored.append("pdf_options")
    if policy.ignores_execution:
        ignored.append("execution")
    return tuple(ignored)


class JobSpecV2(BaseModel):
    """Complete v2 job specification."""

    model_config = ConfigDict(extra="forbid")

    api_version: Literal["v2"]
    source: SourceSpecV2
    conversion: ConversionSpecV2
    pdf_options: PdfOptionsV2 | None = None
    execution: ExecutionSpecV2 | None = None
    audio_transcription_options: AudioTranscriptionOptionsV2 | None = None
    transcript_formatter_options: TranscriptFormatterReplayOptionsV2 | None = None
    retention: RetentionSpecV2 = Field(default_factory=RetentionSpecV2)

    @model_validator(mode="before")
    @classmethod
    def _strip_route_ignored_runtime_options(cls, value: object) -> object:
        del cls
        ignored_option_names = _route_ignored_runtime_option_names_from_raw_payload(value)
        if not ignored_option_names or not isinstance(value, Mapping):
            return value
        normalized = dict(value)
        for option_name in ignored_option_names:
            normalized.pop(option_name, None)
        return normalized

    @model_validator(mode="after")
    def _validate_route(self) -> "JobSpecV2":
        from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
            ignored_runtime_option_names_for_spec_v2,
            validate_job_spec_route_policy_v2,
        )

        validate_job_spec_route_policy_v2(self)
        for option_name in ignored_runtime_option_names_for_spec_v2(self):
            setattr(self, option_name, None)
        return self
