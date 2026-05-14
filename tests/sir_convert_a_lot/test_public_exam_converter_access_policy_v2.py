"""Policy tests for public Exam Converter access decisions.

Purpose:
    Exercise grant-owned artifact-read authorization as pure policy without
    HTTP adapters, token codecs, or service-route state.

Relationships:
    - Covers Task 292 public Exam Converter grant and lease policy.
    - Complements runtime route tests by asserting exact decision reasons.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.sir_convert_a_lot.application.public_exam_converter_access_policy_v2 import (
    PublicArtifactLeaseRejectionV2,
    PublicExamConverterAccessProfileV2,
    PublicOwnedJobSnapshotV2,
    VerifiedPublicConversionGrantV2,
    evaluate_public_artifact_read_lease_v2,
    public_owner_digest_v2,
    public_owner_scope_v2,
)
from scripts.sir_convert_a_lot.application.public_exam_converter_contract_v2 import (
    PublicArtifactReadLeaseV1,
    PublicConversionGrantV1,
)

_NOW_TS = 1_800_000_000
_ARTIFACT_KEY = "examnet_pdf"


def test_public_artifact_read_lease_policy_accepts_exact_public_job_binding() -> None:
    verified_grant, job, lease = _public_lease_context()

    rejection = evaluate_public_artifact_read_lease_v2(
        lease=lease,
        profile=PublicExamConverterAccessProfileV2(),
        verified_grant=verified_grant,
        job=job,
        artifact_key=_ARTIFACT_KEY,
        now_ts=_NOW_TS,
    )

    assert rejection is None


@pytest.mark.parametrize(
    ("lease_update", "artifact_key", "job_owner_scope", "expected"),
    (
        pytest.param(
            {"parent_grant_jti": "pcg_other"},
            _ARTIFACT_KEY,
            None,
            PublicArtifactLeaseRejectionV2.PARENT_MISMATCH,
            id="parent grant",
        ),
        pytest.param(
            {"job_id": "job-other"},
            _ARTIFACT_KEY,
            None,
            PublicArtifactLeaseRejectionV2.JOB_MISMATCH,
            id="job",
        ),
        pytest.param(
            {},
            "qti_package",
            None,
            PublicArtifactLeaseRejectionV2.ARTIFACT_MISMATCH,
            id="artifact key",
        ),
        pytest.param(
            {"owner_digest": "f" * 64},
            _ARTIFACT_KEY,
            None,
            PublicArtifactLeaseRejectionV2.OWNER_MISMATCH,
            id="owner digest",
        ),
        pytest.param(
            {},
            _ARTIFACT_KEY,
            public_owner_scope_v2("f" * 64),
            PublicArtifactLeaseRejectionV2.PERSISTED_OWNER_MISMATCH,
            id="persisted owner",
        ),
        pytest.param(
            {"allowed_targets_snapshot": ["qti_package"]},
            _ARTIFACT_KEY,
            None,
            PublicArtifactLeaseRejectionV2.TARGET_SNAPSHOT_MISMATCH,
            id="target snapshot",
        ),
        pytest.param(
            {"policy_version": "public-exam-converter-old"},
            _ARTIFACT_KEY,
            None,
            PublicArtifactLeaseRejectionV2.POLICY_MISMATCH,
            id="policy version",
        ),
        pytest.param(
            {"exp": _NOW_TS - 10},
            _ARTIFACT_KEY,
            None,
            PublicArtifactLeaseRejectionV2.EXPIRED,
            id="expired",
        ),
    ),
)
def test_public_artifact_read_lease_policy_reports_exact_denial_reason(
    lease_update: dict[str, object],
    artifact_key: str,
    job_owner_scope: str | None,
    expected: PublicArtifactLeaseRejectionV2,
) -> None:
    verified_grant, job, lease = _public_lease_context()
    if job_owner_scope is not None:
        job = PublicOwnedJobSnapshotV2(
            job_id=job.job_id,
            owner_scope=job_owner_scope,
            expires_at=job.expires_at,
        )

    rejection = evaluate_public_artifact_read_lease_v2(
        lease=lease.model_copy(update=lease_update),
        profile=PublicExamConverterAccessProfileV2(),
        verified_grant=verified_grant,
        job=job,
        artifact_key=artifact_key,
        now_ts=_NOW_TS,
    )

    assert rejection == expected


def _public_lease_context() -> tuple[
    VerifiedPublicConversionGrantV2,
    PublicOwnedJobSnapshotV2,
    PublicArtifactReadLeaseV1,
]:
    grant = _public_grant()
    owner_digest = public_owner_digest_v2(grant)
    verified_grant = VerifiedPublicConversionGrantV2(
        grant=grant,
        owner_digest=owner_digest,
        owner_scope=public_owner_scope_v2(owner_digest),
    )
    job = PublicOwnedJobSnapshotV2(
        job_id="job-public-1",
        owner_scope=verified_grant.owner_scope,
        expires_at=datetime.fromtimestamp(_NOW_TS + 3600, tz=UTC),
    )
    lease = PublicArtifactReadLeaseV1(
        lease_version=1,
        iss="sir-convert-a-lot",
        aud="sir-convert-public-artifact-read",
        parent_grant_jti=grant.jti,
        job_id=job.job_id,
        artifact_key=_ARTIFACT_KEY,
        owner_digest=owner_digest,
        route_key=grant.route_key,
        source_app=grant.source_app,
        allowed_targets_snapshot=list(grant.allowed_targets),
        policy_version=grant.policy_version,
        iat=_NOW_TS - 10,
        exp=_NOW_TS + 300,
        jti="parl_public_exam_converter",
        correlation_id=grant.correlation_id,
    )
    return verified_grant, job, lease


def _public_grant() -> PublicConversionGrantV1:
    return PublicConversionGrantV1(
        grant_version=1,
        iss="api_gateway_service",
        aud="sir-convert-a-lot",
        source_app="skriptoteket",
        capability="documents.conversion_hub.exam_converter",
        route_key="digiexam_dxe_to_examnet_migration_bundle",
        source_format="digiexam_dxe",
        output_format="examnet_migration_bundle",
        allowed_targets=["examnet_pdf"],
        upload_digest="sha256:" + ("a" * 64),
        policy_version="public-exam-converter-2026-05-13",
        policy_profile_id="skriptoteket-public-exam-converter-v1",
        max_upload_bytes=209_715_200,
        allowed_mime_types=["application/octet-stream", "application/pdf"],
        request_time_budget_seconds=300,
        artifact_ttl_seconds=86_400,
        artifact_read_lease_seconds=1800,
        rate_limit_profile_id="public-exam-converter-standard",
        concurrency_profile_id="public-exam-converter-standard",
        correlation_id="corr-public-exam-converter",
        iat=_NOW_TS - 10,
        exp=_NOW_TS + 300,
        jti="pcg_public_exam_converter",
    )
