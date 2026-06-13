"""Product-neutral transcript formatter artifact domain logic.

Purpose:
    Validate canonical transcript JSON payloads and render deterministic TXT,
    Markdown, WebVTT, and SubRip/SRT derivatives without reprocessing audio or
    applying downstream product semantics.

Relationships:
    - Consumes the accepted `transcript_json` schema emitted by the audio
      transcript runtime.
    - Provides artifact definitions and pure rendering functions to the
      transcript bundle artifact publication layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CANONICAL_TRANSCRIPT_OUTPUT_ARTIFACT = "json"
TRANSCRIPT_OUTPUT_ARTIFACT_ORDER: tuple[str, ...] = ("json", "txt", "md", "vtt", "srt")
TRANSCRIPT_FORMATTER_OUTPUT_ARTIFACTS: frozenset[str] = frozenset({"txt", "md", "vtt", "srt"})


@dataclass(frozen=True, slots=True)
class TranscriptFormatterArtifactDefinition:
    """Stable public metadata for one formatter artifact."""

    output_artifact: str
    artifact_key: str
    filename: str
    content_type: str


TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS: tuple[
    TranscriptFormatterArtifactDefinition,
    ...,
] = (
    TranscriptFormatterArtifactDefinition(
        output_artifact="txt",
        artifact_key="transcript_txt",
        filename="transcript_txt.txt",
        content_type="text/plain",
    ),
    TranscriptFormatterArtifactDefinition(
        output_artifact="md",
        artifact_key="transcript_md",
        filename="transcript_md.md",
        content_type="text/markdown",
    ),
    TranscriptFormatterArtifactDefinition(
        output_artifact="vtt",
        artifact_key="transcript_vtt",
        filename="transcript_vtt.vtt",
        content_type="text/vtt",
    ),
    TranscriptFormatterArtifactDefinition(
        output_artifact="srt",
        artifact_key="transcript_srt",
        filename="transcript_srt.srt",
        content_type="application/x-subrip",
    ),
)
TRANSCRIPT_FORMATTER_DEFINITIONS_BY_OUTPUT: dict[
    str,
    TranscriptFormatterArtifactDefinition,
] = {
    definition.output_artifact: definition
    for definition in TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS
}
TRANSCRIPT_FORMATTER_DEFINITIONS_BY_KEY: dict[str, TranscriptFormatterArtifactDefinition] = {
    definition.artifact_key: definition for definition in TRANSCRIPT_FORMATTER_ARTIFACT_DEFINITIONS
}


class TranscriptSourcePayload(BaseModel):
    """Canonical source metadata rendered only when a format needs it."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1)
    format: str = Field(min_length=1)


class TranscriptTextPayload(BaseModel):
    """Canonical whole-transcript text payload."""

    model_config = ConfigDict(extra="forbid")

    text: str


class TranscriptLanguagePayload(BaseModel):
    """Canonical language evidence for formatter headers."""

    model_config = ConfigDict(extra="forbid")

    requested: str | None = None
    detected: str = Field(min_length=1)
    confidence: float | None = None


class TranscriptDiarizationPayload(BaseModel):
    """Canonical diarization evidence retained for schema validation."""

    model_config = ConfigDict(extra="forbid")

    requested_mode: str = Field(min_length=1)
    used_mode: str = Field(min_length=1)
    status: str = Field(min_length=1)


class TranscriptChunkPayload(BaseModel):
    """Canonical media chunk metadata retained for schema validation."""

    model_config = ConfigDict(extra="forbid")

    chunk_index: int
    start_seconds: float
    end_seconds: float
    overlap_seconds: float


class TranscriptMediaPayload(BaseModel):
    """Canonical media metadata used for neutral formatter headers."""

    model_config = ConfigDict(extra="forbid")

    duration_seconds: float
    chunk_count: int
    chunks: list[TranscriptChunkPayload]


class TranscriptMetadataSourcePayload(BaseModel):
    """Owner-scoped source metadata retained for schema validation."""

    model_config = ConfigDict(extra="forbid")

    sha256: str = Field(min_length=1)


class TranscriptRuntimeMetadataPayload(BaseModel):
    """Public-safe runtime metadata retained for schema validation."""

    model_config = ConfigDict(extra="forbid")

    sidecar_contract_version: str = Field(min_length=1)
    stt_profile: str | None = None
    diarization_profile: str | None = None
    acceleration_used: str | None = None
    normalization_profile: str | None = None


class TranscriptMetadataPayload(BaseModel):
    """Canonical metadata retained so formatter inputs remain schema-bound."""

    model_config = ConfigDict(extra="forbid")

    source: TranscriptMetadataSourcePayload
    normalized_audio_sha256: str = Field(min_length=1)
    runtime: TranscriptRuntimeMetadataPayload


class TranscriptSegmentPayload(BaseModel):
    """Canonical ordered segment rendered by each formatter."""

    model_config = ConfigDict(extra="forbid")

    segment_id: str = Field(min_length=1)
    start_seconds: float
    end_seconds: float
    speaker_label: str = Field(min_length=1)
    text: str = Field(min_length=1)
    language: str | None = None
    confidence: float | None = None

    @field_validator("end_seconds")
    @classmethod
    def _end_after_start(cls, value: float, info: object) -> float:
        data = getattr(info, "data", {})
        start_obj = data.get("start_seconds") if isinstance(data, dict) else None
        if isinstance(start_obj, int | float) and value <= float(start_obj):
            raise ValueError("segment end_seconds must be greater than start_seconds")
        return value


class CanonicalTranscriptPayload(BaseModel):
    """Validated canonical transcript JSON payload accepted by formatters."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["transcript_json_v1"]
    artifact_key: Literal["transcript_json"]
    source: TranscriptSourcePayload
    transcript: TranscriptTextPayload
    segments: list[TranscriptSegmentPayload] = Field(min_length=1)
    language: TranscriptLanguagePayload
    diarization: TranscriptDiarizationPayload
    media: TranscriptMediaPayload
    metadata: TranscriptMetadataPayload
    warnings: list[str]


def render_transcript_formatter_outputs(
    *,
    canonical_payload: object,
) -> dict[str, bytes]:
    """Render all product-neutral formatter outputs from canonical JSON."""

    transcript = CanonicalTranscriptPayload.model_validate(canonical_payload)
    return {
        "transcript_txt": _render_txt(transcript).encode("utf-8"),
        "transcript_md": _render_md(transcript).encode("utf-8"),
        "transcript_vtt": _render_vtt(transcript).encode("utf-8"),
        "transcript_srt": _render_srt(transcript).encode("utf-8"),
    }


def _render_txt(transcript: CanonicalTranscriptPayload) -> str:
    lines = [
        _language_line(transcript),
        f"Duration: {_seconds(transcript.media.duration_seconds)} seconds",
    ]
    if transcript.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {_plain_line(warning)}" for warning in transcript.warnings)
    lines.append("")
    for segment in transcript.segments:
        detail = _segment_detail(segment)
        lines.append(
            f"[{_timestamp_dot(segment.start_seconds)} - {_timestamp_dot(segment.end_seconds)}] "
            f"{segment.speaker_label}{detail}: {_plain_line(segment.text)}"
        )
    return "\n".join(lines) + "\n"


def _render_md(transcript: CanonicalTranscriptPayload) -> str:
    lines = [
        "# Transcript",
        "",
        f"{_markdown_text(_language_line(transcript))}  ",
        f"Duration: {_seconds(transcript.media.duration_seconds)} seconds",
        "",
    ]
    if transcript.warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {_markdown_text(warning)}" for warning in transcript.warnings)
        lines.append("")
    lines.extend(
        [
            "| Start | End | Speaker | Language | Confidence | Text |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for segment in transcript.segments:
        lines.append(
            "| "
            f"{_timestamp_dot(segment.start_seconds)} | "
            f"{_timestamp_dot(segment.end_seconds)} | "
            f"{_markdown_text(segment.speaker_label)} | "
            f"{_markdown_text(segment.language or '')} | "
            f"{_confidence(segment.confidence)} | "
            f"{_markdown_text(segment.text)} |"
        )
    return "\n".join(lines) + "\n"


def _render_vtt(transcript: CanonicalTranscriptPayload) -> str:
    lines = ["WEBVTT", ""]
    for segment in transcript.segments:
        cue_identifier = _cue_identifier(segment.segment_id)
        if cue_identifier:
            lines.append(cue_identifier)
        lines.append(
            f"{_timestamp_dot(segment.start_seconds)} --> {_timestamp_dot(segment.end_seconds)}"
        )
        lines.append(f"{_vtt_text(segment.speaker_label)}: {_vtt_text(segment.text)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_srt(transcript: CanonicalTranscriptPayload) -> str:
    lines: list[str] = []
    for index, segment in enumerate(transcript.segments, start=1):
        lines.extend(
            [
                str(index),
                f"{_timestamp_comma(segment.start_seconds)} --> "
                f"{_timestamp_comma(segment.end_seconds)}",
                f"{_subtitle_text(segment.speaker_label)}: {_subtitle_text(segment.text)}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _language_line(transcript: CanonicalTranscriptPayload) -> str:
    confidence = transcript.language.confidence
    if confidence is None:
        return f"Language: {transcript.language.detected}"
    return f"Language: {transcript.language.detected} (confidence {_confidence(confidence)})"


def _segment_detail(segment: TranscriptSegmentPayload) -> str:
    details: list[str] = []
    if segment.language is not None:
        details.append(segment.language)
    if segment.confidence is not None:
        details.append(f"confidence {_confidence(segment.confidence)}")
    if not details:
        return ""
    return f" ({', '.join(details)})"


def _seconds(value: float) -> str:
    return f"{value:.3f}"


def _confidence(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.2f}"


def _timestamp_dot(value: float) -> str:
    return _timestamp(value, millisecond_separator=".")


def _timestamp_comma(value: float) -> str:
    return _timestamp(value, millisecond_separator=",")


def _timestamp(value: float, *, millisecond_separator: str) -> str:
    milliseconds = max(0, int(round(value * 1000.0)))
    hours, hour_remainder = divmod(milliseconds, 3_600_000)
    minutes, minute_remainder = divmod(hour_remainder, 60_000)
    seconds, millis = divmod(minute_remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{millisecond_separator}{millis:03d}"


def _plain_line(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def _markdown_text(value: str) -> str:
    return escape(_plain_line(value), quote=False).replace("|", "\\|")


def _cue_identifier(value: str) -> str:
    return _plain_line(value).replace("-->", "->")


def _vtt_text(value: str) -> str:
    return escape(_plain_line(value).replace("-->", "->"), quote=False)


def _subtitle_text(value: str) -> str:
    return escape(_plain_line(value).replace("-->", "->"), quote=False)
