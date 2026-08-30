"""Create-job route registry tests for service API v2."""

import pytest
from pydantic import ValidationError

from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
    TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2,
    RouteKeyV2,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2, OutputFormatV2, SourceFormatV2
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2,
    AudioTranscriptionAdmissionCreateJobRouteHandlerV2,
    DefaultCreateJobRouteHandlerV2,
    TranscriptFormatterReplayCreateJobRouteHandlerV2,
    build_create_job_route_registry_v2,
)


def test_create_job_registry_registers_current_route_policy_keys_only() -> None:
    registry = build_create_job_route_registry_v2()

    assert registry.registered_route_keys() == (
        *DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2,
        AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
        TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2,
    )


def test_create_job_registry_resolves_generic_audio_and_transcript_handlers() -> None:
    registry = build_create_job_route_registry_v2()

    generic = registry.require_handler(
        RouteKeyV2(source_format=SourceFormatV2.MD, output_format=OutputFormatV2.PDF)
    )
    audio = registry.require_handler(AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2)
    replay = registry.require_handler(TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2)

    assert isinstance(generic, DefaultCreateJobRouteHandlerV2)
    assert isinstance(audio, AudioTranscriptionAdmissionCreateJobRouteHandlerV2)
    assert isinstance(replay, TranscriptFormatterReplayCreateJobRouteHandlerV2)


def test_create_job_registry_rejects_unregistered_route_key() -> None:
    registry = build_create_job_route_registry_v2()
    unsupported = RouteKeyV2(
        source_format=SourceFormatV2.PDF,
        output_format=OutputFormatV2.TRANSCRIPT_BUNDLE,
    )

    with pytest.raises(ServiceError) as error_info:
        registry.require_handler(unsupported)

    assert error_info.value.code == "unsupported_v2_route"


def test_job_spec_rejects_unsupported_route() -> None:
    with pytest.raises(ValidationError):
        JobSpecV2.model_validate(
            {
                "api_version": "v2",
                "source": {"kind": "upload", "filename": "input.pdf", "format": "pdf"},
                "conversion": {"output_format": "transcript_bundle"},
                "pdf_options": {
                    "backend_strategy": "quality_first",
                    "ocr_mode": "auto",
                    "table_mode": "markdown",
                    "normalize": "strict",
                },
                "execution": {"acceleration_policy": "gpu_required"},
            }
        )
