"""Consumer integration adapter profiles for Story 003c.

Purpose:
    Define thin adapter helper behavior for HuleEdu and Skriptoteket that
    preserves canonical v1 contract semantics and deterministic headers.

Relationships:
    - Delegates conversion execution to `interfaces.http_client.SirConvertALotClient`.
    - Mirrors contract rules documented in `docs/converters/internal_adapter_contract_v1.md`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypedDict

from scripts.sir_convert_a_lot.interfaces.http_client import (
    ConversionOutcome,
    SirConvertALotClient,
)


class ConsumerProfile(StrEnum):
    """Supported consumer integration profiles."""

    HULEDU = "huledu"
    SKRIPTOTEKET = "skriptoteket"


class AdapterProfileConfig(TypedDict):
    """Static profile naming conventions for deterministic identifiers."""

    correlation_prefix: str
    idempotency_prefix: str


ADAPTER_PROFILE_CONFIG: dict[ConsumerProfile, AdapterProfileConfig] = {
    ConsumerProfile.HULEDU: {
        "correlation_prefix": "corr_huledu",
        "idempotency_prefix": "idem_huledu",
    },
    ConsumerProfile.SKRIPTOTEKET: {
        "correlation_prefix": "corr_skriptoteket",
        "idempotency_prefix": "idem_skriptoteket",
    },
}


@dataclass(frozen=True)
class AdapterRequestContext:
    """Typed input context for thin adapter submission behavior."""

    profile: ConsumerProfile
    pdf_path: Path
    source_label: str
    caller_correlation_id: str | None = None
    acceleration_policy: str = "gpu_required"
    wait_seconds: int = 0
    max_poll_seconds: float = 120.0


@dataclass(frozen=True)
class AdapterPreparedSubmission:
    """Prepared adapter payload and deterministic headers for submission."""

    job_spec: dict[str, object]
    idempotency_key: str
    correlation_id: str


def build_job_spec_for_profile(
    profile: ConsumerProfile, *, filename: str, acceleration_policy: str = "gpu_required"
) -> dict[str, object]:
    """Build canonical v1 job spec shared by all integration profiles."""
    del profile  # Profile must not alter canonical job spec shape.
    return {
        "api_version": "v1",
        "source": {"kind": "upload", "filename": filename},
        "conversion": {
            "output_format": "md",
            "backend_strategy": "auto",
            "ocr_mode": "auto",
            "table_mode": "fast",
            "normalize": "standard",
        },
        "execution": {
            "acceleration_policy": acceleration_policy,
            "priority": "normal",
            "document_timeout_seconds": 1800,
        },
        "retention": {"pin": False},
    }


def build_correlation_id(
    profile: ConsumerProfile, *, source_label: str, caller_correlation_id: str | None
) -> str:
    """Build correlation ID with caller pass-through and deterministic fallback."""
    if caller_correlation_id is not None and caller_correlation_id.strip() != "":
        return caller_correlation_id
    config = ADAPTER_PROFILE_CONFIG[profile]
    digest = hashlib.sha256(source_label.encode("utf-8")).hexdigest()[:16]
    return f"{config['correlation_prefix']}_{digest}"


def build_idempotency_key(
    profile: ConsumerProfile, *, job_spec: dict[str, object], file_bytes: bytes
) -> str:
    """Build deterministic idempotency key from canonical spec and file hash."""
    config = ADAPTER_PROFILE_CONFIG[profile]
    normalized_spec = json.dumps(job_spec, sort_keys=True, separators=(",", ":"))
    file_sha = hashlib.sha256(file_bytes).hexdigest()
    digest = hashlib.sha256(f"{normalized_spec}:{file_sha}".encode("utf-8")).hexdigest()[:48]
    return f"{config['idempotency_prefix']}_{digest}"


def prepare_submission(
    context: AdapterRequestContext, *, job_spec: dict[str, object] | None = None
) -> AdapterPreparedSubmission:
    """Prepare canonical job payload and deterministic headers for adapter submit."""
    resolved_job_spec = (
        job_spec
        if job_spec is not None
        else build_job_spec_for_profile(
            context.profile,
            filename=context.pdf_path.name,
            acceleration_policy=context.acceleration_policy,
        )
    )
    file_bytes = context.pdf_path.read_bytes()
    idempotency_key = build_idempotency_key(
        context.profile, job_spec=resolved_job_spec, file_bytes=file_bytes
    )
    correlation_id = build_correlation_id(
        context.profile,
        source_label=context.source_label,
        caller_correlation_id=context.caller_correlation_id,
    )
    return AdapterPreparedSubmission(
        job_spec=resolved_job_spec,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )


def submit_pdf_for_profile(
    *,
    client: SirConvertALotClient,
    context: AdapterRequestContext,
    job_spec: dict[str, object] | None = None,
) -> ConversionOutcome:
    """Submit conversion through the canonical client with adapter-normalized headers."""
    prepared = prepare_submission(context, job_spec=job_spec)
    return client.convert_pdf_to_markdown(
        pdf_path=context.pdf_path,
        job_spec=prepared.job_spec,
        idempotency_key=prepared.idempotency_key,
        wait_seconds=context.wait_seconds,
        max_poll_seconds=context.max_poll_seconds,
        correlation_id=prepared.correlation_id,
    )
