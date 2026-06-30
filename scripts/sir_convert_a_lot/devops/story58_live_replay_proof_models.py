"""Story 58 live replay proof data contracts.

Purpose:
    Define typed settings, case identifiers, and JSON aliases for the Story 58
    Service API replay proof runner.

Relationships:
    - Consumed by the Story 58 proof transport, evidence, report, and
      orchestration modules.
    - Mirrors the Story 58 closeout matrix without importing Service API route
      implementation code.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

JsonObject: TypeAlias = dict[str, object]
JsonList: TypeAlias = list[object]

CaseStatus: TypeAlias = Literal["passed", "failed", "skipped", "requires_governed_setup"]

Story58CaseId: TypeAlias = Literal[
    "compatible_strict_digiexam_replay",
    "stale_incompatible_digiexam_replay",
    "missing_source_correction_apply_fail_closed",
    "exact_duplicate_correction_retry_reuses_artifact_set",
    "distinct_correction_applies_distinct_artifact_sets",
    "stale_mismatched_nested_correction_artifact_download_fail_closed",
    "generic_idempotency_preservation_smoke",
]

STORY58_CASE_IDS: tuple[Story58CaseId, ...] = (
    "compatible_strict_digiexam_replay",
    "stale_incompatible_digiexam_replay",
    "missing_source_correction_apply_fail_closed",
    "exact_duplicate_correction_retry_reuses_artifact_set",
    "distinct_correction_applies_distinct_artifact_sets",
    "stale_mismatched_nested_correction_artifact_download_fail_closed",
    "generic_idempotency_preservation_smoke",
)

CASE_LABELS: dict[Story58CaseId, str] = {
    "compatible_strict_digiexam_replay": "Compatible strict DigiExam replay",
    "stale_incompatible_digiexam_replay": "Stale incompatible DigiExam replay",
    "missing_source_correction_apply_fail_closed": "Missing-source correction apply",
    "exact_duplicate_correction_retry_reuses_artifact_set": ("Exact duplicate correction retry"),
    "distinct_correction_applies_distinct_artifact_sets": ("Distinct correction applies"),
    "stale_mismatched_nested_correction_artifact_download_fail_closed": (
        "Stale or mismatched nested correction artifact download"
    ),
    "generic_idempotency_preservation_smoke": "Generic idempotency preservation smoke",
}


@dataclass(frozen=True)
class Story58LiveReplayProofSettings:
    """Settings for one Story 58 live replay proof run."""

    service_url: str
    api_key: str
    case_manifest: Path
    output_root: Path
    timeout_seconds: float
    monitoring_pointers: tuple[str, ...] = ()
    log_capture_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class Story58RequestEvidence:
    """Sanitized result for one HTTP request in a proof case."""

    label: str
    status_code: int
    response_path: Path
    artifact_metadata_path: Path | None
    passed: bool
    reason: str
    redacted_payload: JsonObject


@dataclass(frozen=True)
class Story58CaseEvidence:
    """Sanitized result for one Story 58 proof matrix case."""

    case_id: Story58CaseId
    label: str
    status: CaseStatus
    reason: str
    requests: tuple[Story58RequestEvidence, ...] = ()
    external_command: str | None = None
