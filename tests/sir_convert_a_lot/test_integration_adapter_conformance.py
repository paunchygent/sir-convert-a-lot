"""Conformance tests for Story 003c integration adapter behavior.

Purpose:
    Validate that HuleEdu and Skriptoteket adapter profiles remain thin and
    contract-aligned for job spec, headers, and error propagation.

Relationships:
    - Exercises `scripts.sir_convert_a_lot.integrations.adapter_profiles`.
    - Uses the canonical API app from `scripts.sir_convert_a_lot.service`.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.sir_convert_a_lot.integrations.adapter_profiles import (
    AdapterRequestContext,
    ConsumerProfile,
    build_correlation_id,
    build_idempotency_key,
    build_job_spec_for_profile,
    prepare_submission,
    submit_pdf_for_profile,
)
from scripts.sir_convert_a_lot.interfaces.http_client import ClientError, SirConvertALotClient
from scripts.sir_convert_a_lot.models import JobStatus
from scripts.sir_convert_a_lot.service import ServiceConfig, create_app


def _write_pdf(path: Path, label: str) -> None:
    path.write_bytes(f"%PDF-1.4\n% {label}\n%%EOF\n".encode("utf-8"))


@contextmanager
def _service_client(app: FastAPI, *, api_key: str) -> Iterator[SirConvertALotClient]:
    with TestClient(app, base_url="http://testserver") as http_client:
        with SirConvertALotClient(
            base_url="http://testserver",
            api_key=api_key,
            http_client=http_client,
        ) as client:
            yield client


@pytest.mark.parametrize("profile", [ConsumerProfile.HULEDU, ConsumerProfile.SKRIPTOTEKET])
def test_job_spec_shape_is_canonical_and_identical_across_profiles(
    profile: ConsumerProfile,
) -> None:
    expected = build_job_spec_for_profile(ConsumerProfile.HULEDU, filename="paper.pdf")
    candidate = build_job_spec_for_profile(profile, filename="paper.pdf")

    assert candidate == expected
    assert candidate["source"] == {"kind": "upload", "filename": "paper.pdf"}
    assert candidate["execution"] == {
        "acceleration_policy": "gpu_required",
        "priority": "normal",
        "document_timeout_seconds": 1800,
    }


@pytest.mark.parametrize("profile", [ConsumerProfile.HULEDU, ConsumerProfile.SKRIPTOTEKET])
def test_idempotency_key_is_deterministic_and_payload_sensitive(profile: ConsumerProfile) -> None:
    spec = build_job_spec_for_profile(profile, filename="paper.pdf")
    file_bytes = b"%PDF-1.4\n% stable\n%%EOF\n"

    first = build_idempotency_key(profile, job_spec=spec, file_bytes=file_bytes)
    second = build_idempotency_key(profile, job_spec=spec, file_bytes=file_bytes)
    changed = build_idempotency_key(
        profile, job_spec=spec, file_bytes=b"%PDF-1.4\n% changed\n%%EOF\n"
    )

    assert first == second
    assert first != changed
    assert first.startswith(f"idem_{profile.value}_")


@pytest.mark.parametrize("profile", [ConsumerProfile.HULEDU, ConsumerProfile.SKRIPTOTEKET])
def test_correlation_id_pass_through_and_fallback(profile: ConsumerProfile) -> None:
    caller_id = "corr_from_consumer_caller"
    preserved = build_correlation_id(
        profile, source_label="folder/paper.pdf", caller_correlation_id=caller_id
    )
    fallback_first = build_correlation_id(
        profile, source_label="folder/paper.pdf", caller_correlation_id=None
    )
    fallback_second = build_correlation_id(
        profile, source_label="folder/paper.pdf", caller_correlation_id=None
    )

    assert preserved == caller_id
    assert fallback_first == fallback_second
    assert fallback_first.startswith(f"corr_{profile.value}_")


def test_adapter_propagates_auth_error_without_remap(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_auth",
            processing_delay_seconds=0.02,
        )
    )
    pdf_path = tmp_path / "paper.pdf"
    _write_pdf(pdf_path, "auth")

    context = AdapterRequestContext(
        profile=ConsumerProfile.HULEDU,
        pdf_path=pdf_path,
        source_label="paper.pdf",
    )

    with _service_client(app, api_key="wrong-key") as client:
        with pytest.raises(ClientError) as exc_info:
            submit_pdf_for_profile(client=client, context=context)

    assert exc_info.value.code == "auth_invalid_api_key"
    assert exc_info.value.status_code == 401


def test_adapter_propagates_validation_error_without_remap(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_validation",
            processing_delay_seconds=0.02,
        )
    )
    non_pdf_path = tmp_path / "not_a_pdf.txt"
    non_pdf_path.write_bytes(b"%PDF-1.4\n% still invalid due extension\n%%EOF\n")

    context = AdapterRequestContext(
        profile=ConsumerProfile.SKRIPTOTEKET,
        pdf_path=non_pdf_path,
        source_label="not_a_pdf.txt",
    )

    with _service_client(app, api_key="secret-key") as client:
        with pytest.raises(ClientError) as exc_info:
            submit_pdf_for_profile(client=client, context=context)

    assert exc_info.value.code == "unsupported_media_type"
    assert exc_info.value.status_code == 415


def test_adapter_timeout_error_is_not_consumer_remapped(tmp_path: Path) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / "service_data_timeout",
            processing_delay_seconds=0.5,
        )
    )
    pdf_path = tmp_path / "paper.pdf"
    _write_pdf(pdf_path, "timeout")

    context = AdapterRequestContext(
        profile=ConsumerProfile.HULEDU,
        pdf_path=pdf_path,
        source_label="paper.pdf",
        wait_seconds=0,
        max_poll_seconds=0.01,
    )

    with _service_client(app, api_key="secret-key") as client:
        with pytest.raises(ClientError) as exc_info:
            submit_pdf_for_profile(client=client, context=context)

    assert exc_info.value.code == "job_timeout"
    assert exc_info.value.status_code == 408


@pytest.mark.parametrize("profile", [ConsumerProfile.HULEDU, ConsumerProfile.SKRIPTOTEKET])
def test_adapter_integration_smoke_submit_poll_fetch(
    profile: ConsumerProfile, tmp_path: Path
) -> None:
    app = create_app(
        ServiceConfig(
            api_key="secret-key",
            data_root=tmp_path / f"service_data_smoke_{profile.value}",
            processing_delay_seconds=0.02,
        )
    )
    pdf_path = tmp_path / f"{profile.value}_paper.pdf"
    _write_pdf(pdf_path, profile.value)

    context = AdapterRequestContext(
        profile=profile,
        pdf_path=pdf_path,
        source_label=f"inbound/{profile.value}/{pdf_path.name}",
        caller_correlation_id="corr_external_preserved",
        max_poll_seconds=5.0,
    )

    prepared = prepare_submission(context)
    assert prepared.correlation_id == "corr_external_preserved"

    with _service_client(app, api_key="secret-key") as client:
        outcome = submit_pdf_for_profile(client=client, context=context)

    assert outcome.status == JobStatus.SUCCEEDED
    assert outcome.job_id.startswith("job_")
    assert "Converted by Sir Convert-a-Lot" in outcome.markdown_content
