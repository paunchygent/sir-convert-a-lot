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

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS,
    AudioDiarizationMode,
    AudioTranscriptionErrorCode,
    AudioTranscriptionPublicOptions,
)
from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioDiarizationOptions as DomainAudioDiarizationOptions,
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
    PDF = "pdf"
    MD = "md"
    HTML = "html"
    DOCX = "docx"
    DIGIEXAM_DXE = "digiexam_dxe"


class OutputFormatV2(StrEnum):
    """Supported output formats for v2."""

    MD = "md"
    PDF = "pdf"
    DOCX = "docx"
    TRANSCRIPT_BUNDLE = "transcript_bundle"
    EXAMNET_MIGRATION_BUNDLE = "examnet_migration_bundle"


class ExamMigrationTargetV2(StrEnum):
    """Supported target artifacts for exam-migration bundle routes."""

    EXAMNET_PDF = "examnet_pdf"
    QTI_PACKAGE = "qti_package"


DEFAULT_EXAM_MIGRATION_TARGETS_V2: tuple[ExamMigrationTargetV2, ...] = (
    ExamMigrationTargetV2.EXAMNET_PDF,
    ExamMigrationTargetV2.QTI_PACKAGE,
)


class DigiExamResultPdfUsageV2(StrEnum):
    """Allowed use of optional DigiExam graded-result PDF evidence."""

    CORRECT_MACHINE_MARKED_ANSWERS_ONLY = "correct_machine_marked_answers_only"


class DigiExamManualFollowUpPolicyV2(StrEnum):
    """Allowed manual-follow-up reporting policy for DigiExam migration."""

    EMIT_ITEM_ADDRESSABLE_REPORT = "emit_item_addressable_report"


class DigiExamIngestionOverlayPolicyV2(StrEnum):
    """Allowed teacher overlay application policies for DigiExam migration."""

    NONE = "none"
    APPLY_TEACHER_OVERLAY = "apply_teacher_overlay"


class DigiExamAnswerKeyCompletionModeV2(StrEnum):
    """Allowed answer-key completion modes for DigiExam migration."""

    SOURCE_EVIDENCE_ONLY = "source_evidence_only"
    LOCAL_LLM_SUGGEST_MISSING_MACHINE_MARKED = "local_llm_suggest_missing_machine_marked"
    LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW = (
        "local_llm_apply_missing_machine_marked_with_review"
    )


class DigiExamRemoteProviderPolicyV2(StrEnum):
    """Allowed remote-provider policies for DigiExam answer-key completion."""

    FORBIDDEN = "forbidden"


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
    targets: list[ExamMigrationTargetV2] = Field(default_factory=list)
    artifact_language: str | None = Field(default=None, min_length=2, max_length=8)


class DigiExamMigrationOptionsV2(BaseModel):
    """Route-specific options for DigiExam migration bundle jobs."""

    model_config = ConfigDict(extra="forbid")

    graded_result_pdf_filename: str | None = None
    parity_pdf_filename: str | None = None
    result_pdf_usage: DigiExamResultPdfUsageV2 = (
        DigiExamResultPdfUsageV2.CORRECT_MACHINE_MARKED_ANSWERS_ONLY
    )
    manual_follow_up_policy: DigiExamManualFollowUpPolicyV2 = (
        DigiExamManualFollowUpPolicyV2.EMIT_ITEM_ADDRESSABLE_REPORT
    )
    ingestion_overlay_filename: str | None = None
    ingestion_overlay_policy: DigiExamIngestionOverlayPolicyV2 = (
        DigiExamIngestionOverlayPolicyV2.NONE
    )
    completion_mode: DigiExamAnswerKeyCompletionModeV2 = (
        DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY
    )
    remote_provider_policy: DigiExamRemoteProviderPolicyV2 = (
        DigiExamRemoteProviderPolicyV2.FORBIDDEN
    )

    @model_validator(mode="after")
    def _validate_ingestion_overlay_policy(self) -> "DigiExamMigrationOptionsV2":
        has_filename = self.ingestion_overlay_filename is not None
        if (
            self.completion_mode
            == DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW
            and not has_filename
        ):
            raise ValueError(
                "digiexam_migration_options.ingestion_overlay_filename is required "
                "when completion_mode is "
                f"'{DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW.value}'"
            )
        if has_filename and self.ingestion_overlay_policy != (
            DigiExamIngestionOverlayPolicyV2.APPLY_TEACHER_OVERLAY
        ):
            raise ValueError(
                "digiexam_migration_options.ingestion_overlay_policy must be "
                "'apply_teacher_overlay' when ingestion_overlay_filename is present"
            )
        if (
            not has_filename
            and self.ingestion_overlay_policy != DigiExamIngestionOverlayPolicyV2.NONE
        ):
            raise ValueError(
                "digiexam_migration_options.ingestion_overlay_policy must be "
                "'none' when ingestion_overlay_filename is omitted"
            )
        return self


_AUDIO_TRANSCRIPTION_OPTION_KEYS_V2 = frozenset(
    {"diarization", "language", "max_duration_seconds", "output_artifacts"}
)


def _audio_public_options_error(detail: str) -> ValueError:
    return ValueError(f"{AudioTranscriptionErrorCode.PUBLIC_OPTIONS_UNSUPPORTED.value}: {detail}")


class AudioDiarizationOptionsV2(BaseModel):
    """Public speaker-hint options for audio transcription route admission."""

    model_config = ConfigDict(extra="forbid")

    mode: AudioDiarizationMode
    num_speakers: int | None = None
    min_speakers: int | None = None
    max_speakers: int | None = None


class AudioTranscriptionOptionsV2(BaseModel):
    """Public audio transcription options admitted through Service API v2."""

    model_config = ConfigDict(extra="forbid")

    language: str = "auto"
    diarization: AudioDiarizationOptionsV2
    max_duration_seconds: int = 7200
    output_artifacts: tuple[str, ...] = ("json",)

    @model_validator(mode="before")
    @classmethod
    def _reject_unsupported_option_keys(cls, value: object) -> object:
        del cls
        if not isinstance(value, Mapping):
            return value
        keys = frozenset(key for key in value.keys() if isinstance(key, str))
        forbidden = sorted(keys.intersection(FORBIDDEN_PUBLIC_BACKEND_OPTION_KEYS))
        if forbidden:
            raise _audio_public_options_error(f"unsupported option '{forbidden[0]}'")
        unsupported = sorted(keys.difference(_AUDIO_TRANSCRIPTION_OPTION_KEYS_V2))
        if unsupported:
            raise _audio_public_options_error(f"unsupported option '{unsupported[0]}'")
        return value

    @model_validator(mode="after")
    def _validate_public_options(self) -> "AudioTranscriptionOptionsV2":
        if self.output_artifacts != ("json",):
            raise _audio_public_options_error("unsupported option 'output_artifacts'")
        diarization = DomainAudioDiarizationOptions(
            mode=self.diarization.mode,
            num_speakers=self.diarization.num_speakers,
            min_speakers=self.diarization.min_speakers,
            max_speakers=self.diarization.max_speakers,
        )
        options = AudioTranscriptionPublicOptions(
            language=self.language,
            diarization=diarization,
            max_duration_seconds=self.max_duration_seconds,
            output_artifacts=self.output_artifacts,
            raw_option_keys=_AUDIO_TRANSCRIPTION_OPTION_KEYS_V2,
        )
        failure = options.validation_failure()
        if failure is not None:
            code, details = failure
            detail_text = ", ".join(f"{key}={value}" for key, value in sorted(details.items()))
            raise ValueError(f"{code.value}: {detail_text}")
        return self


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
    digiexam_migration_options: DigiExamMigrationOptionsV2 | None = None
    audio_transcription_options: AudioTranscriptionOptionsV2 | None = None
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


def normalized_exam_migration_targets_v2(spec: JobSpecV2) -> tuple[ExamMigrationTargetV2, ...]:
    """Return exam-migration targets, defaulting to all governed route targets."""

    if not spec.conversion.targets:
        return DEFAULT_EXAM_MIGRATION_TARGETS_V2
    seen: set[ExamMigrationTargetV2] = set()
    ordered: list[ExamMigrationTargetV2] = []
    for target in spec.conversion.targets:
        if target in seen:
            continue
        ordered.append(target)
        seen.add(target)
    return tuple(ordered)
