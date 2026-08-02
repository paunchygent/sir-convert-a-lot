"""create-job route registry tests for service API v2 create-job route registry.

Purpose:
    Prove that v2 create-job route authority is shared between `JobSpecV2`
    validation and HTTP route-handler lookup.

Relationships:
    - Exercises `domain.service_routes_v2` route-policy metadata.
    - Exercises `interfaces.http_create_job_routes_v2` registry and handlers.
    - Complements public create-job API tests with exact route registration
      expectations.
"""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

import scripts.sir_convert_a_lot.domain.service_routes_v2 as service_routes_v2
from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
    DIGIEXAM_MIGRATION_BUNDLE_TERMINAL_CONTRACT_V2,
    DIGIEXAM_MIGRATION_ROUTE_KEY_V2,
    TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2,
    RouteKeyV2,
    RoutePolicyV2,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import (
    JobSpecV2,
    OutputFormatV2,
    SourceFormatV2,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.interfaces.http_create_job_routes_v2 import (
    DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2,
    AudioTranscriptionAdmissionCreateJobRouteHandlerV2,
    CreateJobCompanionPartsV2,
    DefaultCreateJobRouteHandlerV2,
    DigiExamMigrationCreateJobRouteHandlerV2,
    TranscriptFormatterReplayCreateJobRouteHandlerV2,
    build_create_job_route_registry_v2,
)


def test_create_job_registry_registers_current_route_policy_keys_only() -> None:
    registry = build_create_job_route_registry_v2()

    assert registry.registered_route_keys() == (
        *DEFAULT_DOCUMENT_CREATE_JOB_ROUTE_KEYS_V2,
        DIGIEXAM_MIGRATION_ROUTE_KEY_V2,
        AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2,
        TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2,
    )
    assert all(
        key.source_format.value != "examnet_artifact"
        and key.output_format.value != "teacher_authoring_bundle"
        for key in registry.registered_route_keys()
    )


def test_create_job_registry_resolves_default_and_digiexam_handlers() -> None:
    registry = build_create_job_route_registry_v2()

    default_handler = registry.require_handler(
        RouteKeyV2(source_format=SourceFormatV2.MD, output_format=OutputFormatV2.PDF)
    )
    digiexam_handler = registry.require_handler(DIGIEXAM_MIGRATION_ROUTE_KEY_V2)
    audio_handler = registry.require_handler(AUDIO_TRANSCRIPT_BUNDLE_ROUTE_KEY_V2)
    replay_handler = registry.require_handler(TRANSCRIPT_FORMATTER_REPLAY_ROUTE_KEY_V2)

    assert isinstance(default_handler, DefaultCreateJobRouteHandlerV2)
    assert isinstance(digiexam_handler, DigiExamMigrationCreateJobRouteHandlerV2)
    assert isinstance(audio_handler, AudioTranscriptionAdmissionCreateJobRouteHandlerV2)
    assert isinstance(replay_handler, TranscriptFormatterReplayCreateJobRouteHandlerV2)


def test_route_policy_declares_terminal_artifact_contract_only_for_digiexam() -> None:
    digiexam_policy = service_routes_v2.route_policy_for_key_v2(DIGIEXAM_MIGRATION_ROUTE_KEY_V2)
    generic_policy = service_routes_v2.route_policy_for_key_v2(
        RouteKeyV2(source_format=SourceFormatV2.MD, output_format=OutputFormatV2.PDF)
    )

    assert digiexam_policy is not None
    assert generic_policy is not None
    assert (
        digiexam_policy.terminal_artifact_compatibility_contract
        == DIGIEXAM_MIGRATION_BUNDLE_TERMINAL_CONTRACT_V2
    )
    assert generic_policy.terminal_artifact_compatibility_contract is None


def test_create_job_registry_does_not_auto_register_supported_policy_without_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    future_policy_key = RouteKeyV2(
        source_format=SourceFormatV2.DIGIEXAM_DXE,
        output_format=OutputFormatV2.PDF,
    )
    monkeypatch.setattr(
        service_routes_v2,
        "SERVICE_ROUTE_POLICIES_V2",
        (*service_routes_v2.SERVICE_ROUTE_POLICIES_V2, RoutePolicyV2(key=future_policy_key)),
    )

    registry = build_create_job_route_registry_v2()

    assert future_policy_key not in registry.registered_route_keys()
    with pytest.raises(ServiceError) as error_info:
        registry.require_handler(future_policy_key)
    assert error_info.value.status_code == 422
    assert error_info.value.code == "unsupported_v2_route"


def test_create_job_registry_rejects_unregistered_route_key() -> None:
    registry = build_create_job_route_registry_v2()
    unsupported_key = RouteKeyV2(
        source_format=SourceFormatV2.DIGIEXAM_DXE,
        output_format=OutputFormatV2.PDF,
    )

    with pytest.raises(ServiceError) as error_info:
        registry.require_handler(unsupported_key)

    assert error_info.value.status_code == 422
    assert error_info.value.code == "unsupported_v2_route"
    assert error_info.value.details == {
        "source_format": "digiexam_dxe",
        "output_format": "pdf",
    }


def test_job_spec_validation_delegates_supported_routes_to_policy_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    md_to_pdf_key = RouteKeyV2(
        source_format=SourceFormatV2.MD,
        output_format=OutputFormatV2.PDF,
    )
    route_policies_without_md_to_pdf = tuple(
        policy
        for policy in service_routes_v2.SERVICE_ROUTE_POLICIES_V2
        if policy.key != md_to_pdf_key
    )
    monkeypatch.setattr(
        service_routes_v2,
        "SERVICE_ROUTE_POLICIES_V2",
        route_policies_without_md_to_pdf,
    )

    with pytest.raises(ValidationError) as error_info:
        JobSpecV2.model_validate(_job_spec_payload("note.md", "md", "pdf"))

    assert "Unsupported v2 route: md -> pdf" in str(error_info.value)


def test_digiexam_handler_owns_generic_companion_rejection(tmp_path: Path) -> None:
    policy = service_routes_v2.route_policy_for_key_v2(DIGIEXAM_MIGRATION_ROUTE_KEY_V2)
    assert policy is not None
    handler = DigiExamMigrationCreateJobRouteHandlerV2(policy=policy)
    spec = JobSpecV2.model_validate(
        {
            "api_version": "v2",
            "source": {"kind": "upload", "filename": "exam.dxe", "format": "digiexam_dxe"},
            "conversion": {
                "output_format": "examnet_migration_bundle",
                "targets": ["examnet_pdf"],
                "artifact_language": "sv",
            },
            "retention": {"pin": False},
        }
    )

    with pytest.raises(ServiceError) as error_info:
        asyncio.run(
            handler.prepare(
                spec=spec,
                config=ServiceConfig(api_key="secret-key", data_root=tmp_path),
                primary_payload_size=42,
                parts=CreateJobCompanionPartsV2(
                    resources=UploadFile(file=BytesIO(b"PK\x03\x04zip"), filename="resources.zip"),
                    reference_docx=None,
                    graded_result_pdf=None,
                    parity_pdf=None,
                    digiexam_ingestion_overlay=None,
                    form_part_names=frozenset({"file", "job_spec", "resources"}),
                ),
            )
        )

    assert error_info.value.code == "digiexam_companion_unsupported"
    assert error_info.value.details == {"unsupported_parts": ["resources"]}


def _job_spec_payload(filename: str, source_format: str, output_format: str) -> dict[str, object]:
    return {
        "api_version": "v2",
        "source": {"kind": "upload", "filename": filename, "format": source_format},
        "conversion": {
            "output_format": output_format,
            "css_filenames": [],
            "reference_docx_filename": None,
        },
        "retention": {"pin": False},
    }
