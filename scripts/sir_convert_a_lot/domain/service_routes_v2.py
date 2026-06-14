"""Service API v2 route policy metadata for Sir Convert-a-Lot.

Purpose:
    Define supported v2 source/output route keys and route-owned job-spec
    option policies as the shared authority for model validation and HTTP
    create-job routing.

Relationships:
    - Used by `domain.specs_v2.JobSpecV2` for route-policy validation.
    - Used by `interfaces.http_create_job_routes_v2` for handler registration.
    - Keeps route support separate from conversion execution implementations.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy
from scripts.sir_convert_a_lot.domain.specs_v2 import (
    OutputFormatV2,
    PdfPageCssModeV2,
    SourceFormatV2,
    SourceKindV2,
)


class SourceRoutePolicySubjectV2(Protocol):
    """Source fields required for route-policy validation."""

    @property
    def kind(self) -> SourceKindV2:
        """Return the source kind."""

    @property
    def format(self) -> SourceFormatV2:
        """Return the source format."""


class ConversionRoutePolicySubjectV2(Protocol):
    """Conversion fields required for route-policy validation."""

    @property
    def output_format(self) -> OutputFormatV2:
        """Return the target output format."""

    @property
    def targets(self) -> Sequence[object]:
        """Return route target artifacts."""

    @property
    def artifact_language(self) -> str | None:
        """Return requested artifact language."""

    @property
    def css_filenames(self) -> Sequence[str]:
        """Return requested CSS companion filenames."""

    @property
    def pdf_layout(self) -> object | None:
        """Return requested PDF layout."""

    @property
    def page_css_mode(self) -> PdfPageCssModeV2 | None:
        """Return requested page CSS mode."""

    @property
    def reference_docx_filename(self) -> str | None:
        """Return reference DOCX filename."""

    @property
    def template(self) -> object | None:
        """Return DOCX template selector."""


class ExecutionRoutePolicySubjectV2(Protocol):
    """Execution fields required for route-policy validation."""

    @property
    def acceleration_policy(self) -> AccelerationPolicy:
        """Return requested acceleration policy."""


class RetentionRoutePolicySubjectV2(Protocol):
    """Retention fields required for route-policy validation."""

    @property
    def pin(self) -> bool:
        """Return whether the caller requested pinned retention."""


class JobSpecRoutePolicySubjectV2(Protocol):
    """Structural contract required for route-policy validation."""

    @property
    def source(self) -> SourceRoutePolicySubjectV2:
        """Return the source section."""

    @property
    def conversion(self) -> ConversionRoutePolicySubjectV2:
        """Return the conversion section."""

    @property
    def pdf_options(self) -> object | None:
        """Return PDF route options."""

    @property
    def execution(self) -> ExecutionRoutePolicySubjectV2 | None:
        """Return execution options."""

    @property
    def digiexam_migration_options(self) -> object | None:
        """Return DigiExam migration options."""

    @property
    def audio_transcription_options(self) -> object | None:
        """Return audio transcription options."""

    @property
    def transcript_formatter_options(self) -> object | None:
        """Return transcript formatter replay options."""

    @property
    def retention(self) -> RetentionRoutePolicySubjectV2:
        """Return retention options."""


@dataclass(frozen=True, slots=True)
class RouteKeyV2:
    """Stable v2 route key shared by job specs, HTTP routing, and execution."""

    source_format: SourceFormatV2
    output_format: OutputFormatV2


@dataclass(frozen=True, slots=True)
class RoutePolicyV2:
    """Route-owned job-spec policy for one supported service API v2 route."""

    key: RouteKeyV2
    requires_pdf_options: bool = False
    allows_pdf_options: bool = False
    ignores_pdf_options: bool = False
    requires_execution: bool = False
    allows_execution: bool = False
    ignores_execution: bool = False
    allows_digiexam_migration_options: bool = False
    requires_audio_transcription_options: bool = False
    allows_audio_transcription_options: bool = False
    requires_transcript_formatter_options: bool = False
    allows_transcript_formatter_options: bool = False
    allows_targets: bool = False
    allows_artifact_language: bool = False
    allows_css_filenames: bool = False
    allows_pdf_layout: bool = False
    allows_page_css_mode: bool = False
    allows_reference_docx_filename: bool = False
    allows_template: bool = False
    rejects_retention_pin: bool = False
    uses_route_specific_primary_upload_limit: bool = False
    required_execution_message: str = "execution is required when source.format is 'pdf'"
    create_required_grant: str | None = None
    create_optional_identity_grant: str | None = None
    dispatches_runtime_jobs: bool = True
    unsupported_option_context: str | None = None


def _generic_route_policy(
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
) -> RoutePolicyV2:
    source_is_pdf = source_format == SourceFormatV2.PDF
    output_is_pdf = output_format == OutputFormatV2.PDF
    output_is_docx = output_format == OutputFormatV2.DOCX
    return RoutePolicyV2(
        key=RouteKeyV2(source_format=source_format, output_format=output_format),
        requires_pdf_options=source_is_pdf,
        allows_pdf_options=source_is_pdf,
        ignores_pdf_options=not source_is_pdf,
        requires_execution=source_is_pdf,
        allows_execution=source_is_pdf,
        ignores_execution=not source_is_pdf,
        allows_css_filenames=output_is_pdf,
        allows_pdf_layout=output_is_pdf,
        allows_page_css_mode=output_is_pdf,
        allows_reference_docx_filename=output_is_docx,
        allows_template=output_is_docx,
    )


DIGIEXAM_MIGRATION_ROUTE_KEY_V2 = RouteKeyV2(
    source_format=SourceFormatV2.DIGIEXAM_DXE,
    output_format=OutputFormatV2.EXAMNET_MIGRATION_BUNDLE,
)

AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2 = RouteKeyV2(
    source_format=SourceFormatV2.AUDIO,
    output_format=OutputFormatV2.TRANSCRIPT_BUNDLE,
)

TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2 = RouteKeyV2(
    source_format=SourceFormatV2.TRANSCRIPT_JSON,
    output_format=OutputFormatV2.TRANSCRIPT_BUNDLE,
)


SERVICE_ROUTE_POLICIES_V2: tuple[RoutePolicyV2, ...] = (
    _generic_route_policy(SourceFormatV2.PDF, OutputFormatV2.MD),
    _generic_route_policy(SourceFormatV2.DOCX, OutputFormatV2.MD),
    _generic_route_policy(SourceFormatV2.HTML, OutputFormatV2.MD),
    _generic_route_policy(SourceFormatV2.DOCX, OutputFormatV2.PDF),
    _generic_route_policy(SourceFormatV2.MD, OutputFormatV2.PDF),
    _generic_route_policy(SourceFormatV2.MD, OutputFormatV2.DOCX),
    _generic_route_policy(SourceFormatV2.HTML, OutputFormatV2.PDF),
    _generic_route_policy(SourceFormatV2.HTML, OutputFormatV2.DOCX),
    _generic_route_policy(SourceFormatV2.PDF, OutputFormatV2.DOCX),
    RoutePolicyV2(
        key=DIGIEXAM_MIGRATION_ROUTE_KEY_V2,
        ignores_pdf_options=True,
        ignores_execution=True,
        allows_digiexam_migration_options=True,
        allows_targets=True,
        allows_artifact_language=True,
        create_required_grant="sir-convert:jobs:create",
        unsupported_option_context="DigiExam migration routes",
    ),
    RoutePolicyV2(
        key=AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
        requires_execution=True,
        allows_execution=True,
        requires_audio_transcription_options=True,
        allows_audio_transcription_options=True,
        rejects_retention_pin=True,
        uses_route_specific_primary_upload_limit=True,
        required_execution_message="execution is required for audio transcription routes",
        create_optional_identity_grant="sir-convert:jobs:create",
        dispatches_runtime_jobs=True,
        unsupported_option_context="audio transcription routes",
    ),
    RoutePolicyV2(
        key=TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2,
        requires_transcript_formatter_options=True,
        allows_transcript_formatter_options=True,
        rejects_retention_pin=True,
        dispatches_runtime_jobs=False,
        unsupported_option_context="transcript formatter replay routes",
    ),
)


def route_key_for_values_v2(
    *,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
) -> RouteKeyV2:
    """Return the canonical route key for v2 source/output formats."""

    return RouteKeyV2(source_format=source_format, output_format=output_format)


def route_policy_for_key_v2(key: RouteKeyV2) -> RoutePolicyV2 | None:
    """Return route policy metadata for a v2 route key, if supported."""

    for policy in SERVICE_ROUTE_POLICIES_V2:
        if policy.key == key:
            return policy
    return None


def route_dispatches_runtime_jobs_v2(
    *,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
) -> bool:
    """Return whether queued jobs for a v2 route may enter runtime execution."""

    policy = route_policy_for_key_v2(
        RouteKeyV2(source_format=source_format, output_format=output_format)
    )
    if policy is None:
        return False
    return policy.dispatches_runtime_jobs


def is_transcript_formatter_replay_route_v2(
    *,
    source_format: SourceFormatV2,
    output_format: OutputFormatV2,
) -> bool:
    """Return whether the route is the fast transcript formatter replay lane."""

    return (
        source_format == SourceFormatV2.TRANSCRIPT_JSON
        and output_format == OutputFormatV2.TRANSCRIPT_BUNDLE
    )


def supported_route_keys_v2() -> tuple[RouteKeyV2, ...]:
    """Return all supported v2 route keys in stable policy order."""

    return tuple(policy.key for policy in SERVICE_ROUTE_POLICIES_V2)


def route_key_for_spec_v2(spec: JobSpecRoutePolicySubjectV2) -> RouteKeyV2:
    """Return the canonical route key for a v2 job spec."""

    source = spec.source
    conversion = spec.conversion
    return route_key_for_values_v2(
        source_format=source.format,
        output_format=conversion.output_format,
    )


def route_policy_for_spec_v2(spec: JobSpecRoutePolicySubjectV2) -> RoutePolicyV2 | None:
    """Return route policy metadata for a v2 job spec, if supported."""

    return route_policy_for_key_v2(route_key_for_spec_v2(spec))


def validate_job_spec_route_policy_v2(spec: JobSpecRoutePolicySubjectV2) -> None:
    """Validate route-specific job-spec options through shared route policy."""

    if spec.source.kind != SourceKindV2.UPLOAD:
        raise ValueError("source.kind must be 'upload' in v2")

    policy = route_policy_for_spec_v2(spec)
    if policy is None:
        raise ValueError(
            f"Unsupported v2 route: {spec.source.format.value} -> "
            f"{spec.conversion.output_format.value}"
        )

    from scripts.sir_convert_a_lot.domain.service_route_policy_validation_v2 import (
        validate_supported_job_spec_options_v2,
    )

    validate_supported_job_spec_options_v2(spec=spec, policy=policy)


def ignored_runtime_option_names_for_spec_v2(
    spec: JobSpecRoutePolicySubjectV2,
) -> tuple[str, ...]:
    """Return top-level runtime option names that are accepted but ignored."""

    policy = route_policy_for_spec_v2(spec)
    if policy is None:
        return ()

    ignored: list[str] = []
    if policy.ignores_pdf_options:
        ignored.append("pdf_options")
    if policy.ignores_execution:
        ignored.append("execution")
    return tuple(ignored)


def normalized_fingerprint_payload_for_spec_v2(
    *,
    raw_payload: dict[str, object],
    spec: JobSpecRoutePolicySubjectV2,
) -> dict[str, object]:
    """Return request payload with route-ignored runtime options removed."""

    payload = dict(raw_payload)
    for option_name in ignored_runtime_option_names_for_spec_v2(spec):
        payload.pop(option_name, None)
    return payload
