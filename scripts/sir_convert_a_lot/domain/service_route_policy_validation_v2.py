"""Service API v2 route option validation.

Purpose:
    Validate route-owned v2 job-spec option combinations while keeping route
    policy metadata separate from validation mechanics.

Relationships:
    - Called by `domain.service_routes_v2`.
    - Uses the route policy dataclasses and route keys as the shared contract
      authority for HTTP create-job admission and domain spec validation.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
    TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2,
    JobSpecRoutePolicySubjectV2,
    RoutePolicyV2,
)
from scripts.sir_convert_a_lot.domain.specs import AccelerationPolicy
from scripts.sir_convert_a_lot.domain.specs_v2 import PdfPageCssModeV2


def validate_supported_job_spec_options_v2(
    *,
    spec: JobSpecRoutePolicySubjectV2,
    policy: RoutePolicyV2,
) -> None:
    """Validate route-specific job-spec options through shared route policy."""

    _validate_pdf_runtime_options(spec=spec, policy=policy)
    _validate_audio_transcription_options(spec=spec, policy=policy)
    _validate_transcript_formatter_options(spec=spec, policy=policy)
    _validate_pdf_output_options(spec=spec, policy=policy)
    _validate_docx_output_options(spec=spec, policy=policy)


def _validate_pdf_runtime_options(
    *,
    spec: JobSpecRoutePolicySubjectV2,
    policy: RoutePolicyV2,
) -> None:
    if policy.requires_pdf_options and spec.pdf_options is None:
        raise ValueError("pdf_options is required when source.format is 'pdf'")
    if (
        not policy.allows_pdf_options
        and not policy.ignores_pdf_options
        and spec.pdf_options is not None
    ):
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="pdf_options",
                default_message="pdf_options is only supported for PDF source routes",
            )
        )
    if policy.requires_execution and spec.execution is None:
        raise ValueError(policy.required_execution_message)
    if not policy.allows_execution and not policy.ignores_execution and spec.execution is not None:
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="execution",
                default_message="execution is only supported for PDF source routes",
            )
        )


def _validate_audio_transcription_options(
    *,
    spec: JobSpecRoutePolicySubjectV2,
    policy: RoutePolicyV2,
) -> None:
    if policy.requires_audio_transcription_options and spec.audio_transcription_options is None:
        raise ValueError("audio_transcription_options is required for audio transcription routes")
    if (
        not policy.allows_audio_transcription_options
        and spec.audio_transcription_options is not None
    ):
        raise ValueError(
            "audio_transcription_options is only supported for audio transcription routes"
        )
    if policy.key == AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2 and spec.retention.pin:
        raise ValueError(
            "audio_retention_pin_unsupported: retention.pin=true is not supported "
            "for audio transcription routes"
        )
    if policy.key != AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2 or spec.execution is None:
        return
    if spec.execution.acceleration_policy != AccelerationPolicy.GPU_REQUIRED:
        raise ValueError(
            "audio_gpu_required_unavailable: execution.acceleration_policy must be "
            "'gpu_required' for audio transcription routes"
        )


def _validate_transcript_formatter_options(
    *,
    spec: JobSpecRoutePolicySubjectV2,
    policy: RoutePolicyV2,
) -> None:
    if policy.requires_transcript_formatter_options and spec.transcript_formatter_options is None:
        raise ValueError(
            "transcript_formatter_options is required for transcript formatter replay routes"
        )
    if (
        not policy.allows_transcript_formatter_options
        and spec.transcript_formatter_options is not None
    ):
        raise ValueError(
            "transcript_formatter_options is only supported for transcript formatter replay routes"
        )
    if policy.key == TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2 and spec.retention.pin:
        raise ValueError(
            "transcript_formatter_retention_pin_unsupported: retention.pin=true is not "
            "supported for transcript formatter replay routes"
        )


def _validate_pdf_output_options(
    *,
    spec: JobSpecRoutePolicySubjectV2,
    policy: RoutePolicyV2,
) -> None:
    if not policy.allows_css_filenames and spec.conversion.css_filenames:
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="css_filenames",
                default_message="css_filenames is only supported for PDF outputs",
            )
        )
    if not policy.allows_pdf_layout and spec.conversion.pdf_layout is not None:
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="pdf_layout",
                default_message="pdf_layout is only supported for PDF outputs",
            )
        )
    if not policy.allows_page_css_mode and spec.conversion.page_css_mode is not None:
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="page_css_mode",
                default_message="page_css_mode is only supported for PDF outputs",
            )
        )
    if (
        spec.conversion.page_css_mode == PdfPageCssModeV2.AUTHOR_OWNED
        and spec.conversion.pdf_layout is not None
    ):
        raise ValueError("page_css_mode='author_owned' cannot be combined with pdf_layout")


def _validate_docx_output_options(
    *,
    spec: JobSpecRoutePolicySubjectV2,
    policy: RoutePolicyV2,
) -> None:
    if not policy.allows_reference_docx_filename and spec.conversion.reference_docx_filename:
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="reference_docx_filename",
                default_message="reference_docx_filename is only supported for DOCX outputs",
            )
        )
    if not policy.allows_template and spec.conversion.template is not None:
        raise ValueError(
            _unsupported_option_message(
                policy=policy,
                option_name="template",
                default_message="template is only supported for DOCX outputs",
            )
        )
    if (
        policy.allows_reference_docx_filename
        and spec.conversion.reference_docx_filename is not None
        and spec.conversion.template is not None
    ):
        raise ValueError(
            "reference_docx_filename and template cannot both be provided for DOCX outputs"
        )


def _unsupported_option_message(
    *,
    policy: RoutePolicyV2,
    option_name: str,
    default_message: str,
) -> str:
    if policy.unsupported_option_context is None:
        return default_message
    return f"{option_name} is not supported for {policy.unsupported_option_context}"
