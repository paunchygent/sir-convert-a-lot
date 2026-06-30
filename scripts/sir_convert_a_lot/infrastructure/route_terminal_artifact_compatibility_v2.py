"""Route terminal-artifact compatibility inspection for idempotent replay.

Purpose:
    Inspect persisted terminal artifacts for routes that declare a current
    Service API v2 compatibility contract before a succeeded job can be
    returned as a strict idempotent replay.

Relationships:
    - Implements the application replay-service compatibility port.
    - Reads route-policy metadata from `domain.service_routes_v2`.
    - Validates DigiExam migration bundle artifacts produced by
      `infrastructure.digiexam_migration_bundle_builder`.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from scripts.sir_convert_a_lot.application.digiexam_answer_key_review_state_models import (
    DigiExamAnswerKeyReviewStateV1,
)
from scripts.sir_convert_a_lot.application.openapi_contracts_v2 import (
    DigiExamMigrationBundleManifestV2,
    DigiExamTargetReadinessReportV1,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    REQUIRED_ARTIFACT_KEYS,
    DigiExamMigrationArtifactAvailability,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.idempotency_replay_policy_v2 import (
    IdempotencyJobSnapshotV2,
    IdempotencyReattemptReasonV2,
    RouteArtifactCompatibilityDecisionV2,
    RouteArtifactCompatibilityStatusV2,
)
from scripts.sir_convert_a_lot.domain.service_routes_v2 import (
    DIGIEXAM_MIGRATION_BUNDLE_TERMINAL_CONTRACT_V2,
    RouteTerminalArtifactCompatibilityContractV2,
    route_key_for_values_v2,
    route_policy_for_key_v2,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2


class RoutePolicyTerminalArtifactCompatibilityAdapterV2:
    """Evaluate terminal artifact compatibility using route-policy contracts."""

    def __init__(self, get_job: Callable[[str], StoredJobV2 | None]) -> None:
        self._get_job = get_job

    def evaluate_terminal_artifact_compatibility(
        self, job: IdempotencyJobSnapshotV2
    ) -> RouteArtifactCompatibilityDecisionV2:
        """Return the route-specific compatibility decision for a terminal job."""

        stored_job = self._get_job(job.job_id)
        if stored_job is None:
            return _incompatible()
        policy = route_policy_for_key_v2(
            route_key_for_values_v2(
                source_format=stored_job.source_format,
                output_format=stored_job.output_format,
            )
        )
        if policy is None or policy.terminal_artifact_compatibility_contract is None:
            return _compatible()
        return _evaluate_contract(
            contract=policy.terminal_artifact_compatibility_contract,
            job=stored_job,
        )


def _evaluate_contract(
    *,
    contract: RouteTerminalArtifactCompatibilityContractV2,
    job: StoredJobV2,
) -> RouteArtifactCompatibilityDecisionV2:
    if contract == DIGIEXAM_MIGRATION_BUNDLE_TERMINAL_CONTRACT_V2:
        return _evaluate_digiexam_migration_bundle(job)
    return _compatible()


def _evaluate_digiexam_migration_bundle(job: StoredJobV2) -> RouteArtifactCompatibilityDecisionV2:
    try:
        manifest = DigiExamMigrationBundleManifestV2.model_validate(
            _json_payload(job.artifact_path)
        )
        if manifest.job_id != job.job_id:
            return _incompatible()
        if not _has_current_required_artifact_keys(manifest):
            return _incompatible()
        if not _available_artifact_bytes_match(job=job, manifest=manifest):
            return _incompatible()
        if not _required_reports_parse(job=job, manifest=manifest):
            return _incompatible()
    except (OSError, json.JSONDecodeError, ValidationError):
        return _incompatible()
    return _compatible()


def _has_current_required_artifact_keys(manifest: DigiExamMigrationBundleManifestV2) -> bool:
    keys = [entry.artifact_key for entry in manifest.artifacts]
    if len(keys) != len(set(keys)):
        return False
    return set(keys) == set(REQUIRED_ARTIFACT_KEYS)


def _available_artifact_bytes_match(
    *,
    job: StoredJobV2,
    manifest: DigiExamMigrationBundleManifestV2,
) -> bool:
    for entry in manifest.artifacts:
        if entry.availability != DigiExamMigrationArtifactAvailability.AVAILABLE:
            continue
        if entry.artifact_key == DigiExamMigrationArtifactKey.BUNDLE_MANIFEST:
            continue
        if entry.size_bytes is None or entry.sha256 is None:
            return False
        path = artifact_path(job.artifact_path.parent, entry.artifact_key)
        if not _artifact_file_matches(path=path, size_bytes=entry.size_bytes, sha256=entry.sha256):
            return False
    return True


def _required_reports_parse(
    *,
    job: StoredJobV2,
    manifest: DigiExamMigrationBundleManifestV2,
) -> bool:
    readiness_key = manifest.readiness.artifact_key
    review_state_key = manifest.answer_key_review_state.artifact_key
    readiness_report = DigiExamTargetReadinessReportV1.model_validate(
        _json_payload(
            artifact_path(
                job.artifact_path.parent,
                DigiExamMigrationArtifactKey(readiness_key),
            )
        )
    )
    if readiness_report.job_id != job.job_id:
        return False
    DigiExamAnswerKeyReviewStateV1.model_validate(
        _json_payload(
            artifact_path(
                job.artifact_path.parent,
                DigiExamMigrationArtifactKey(review_state_key),
            )
        )
    )
    return True


def _artifact_file_matches(*, path: Path, size_bytes: int, sha256: str) -> bool:
    if not path.is_file():
        return False
    payload = path.read_bytes()
    if len(payload) != size_bytes:
        return False
    return f"sha256:{hashlib.sha256(payload).hexdigest()}" == sha256


def _json_payload(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _compatible() -> RouteArtifactCompatibilityDecisionV2:
    return RouteArtifactCompatibilityDecisionV2(
        status=RouteArtifactCompatibilityStatusV2.COMPATIBLE,
        reason=None,
    )


def _incompatible() -> RouteArtifactCompatibilityDecisionV2:
    return RouteArtifactCompatibilityDecisionV2(
        status=RouteArtifactCompatibilityStatusV2.INCOMPATIBLE,
        reason=IdempotencyReattemptReasonV2.TERMINAL_ARTIFACT_CONTRACT_INCOMPATIBLE,
    )
