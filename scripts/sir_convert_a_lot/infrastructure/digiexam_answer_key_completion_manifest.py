"""Answer-key completion projection for DigiExam migration manifests.

Purpose:
    Expose bounded completion state to migration-manifest consumers without
    coupling target-artifact generation to advisory answer-key execution.

Relationships:
    - Consumes the advisory completion report domain contract.
    - Is used by the DigiExam migration bundle builder.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    DigiExamAnswerKeyCompletionReport,
)
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactKey,
)


def answer_key_completion_manifest(
    *,
    report: DigiExamAnswerKeyCompletionReport | None,
) -> dict[str, str | list[str]]:
    """Project answer-key completion outcome without affecting bundle targets."""

    failure_codes = (
        sorted(
            {
                item.backend_failure_code
                for item in report.items
                if item.backend_failure_code is not None
            }
        )
        if report is not None
        else []
    )
    if report is None:
        status = "not_requested"
    elif "token_lease_ledger_unavailable" in failure_codes:
        status = "token_lease_ledger_unavailable"
    elif "daily_token_lease_exhausted" in failure_codes:
        status = "daily_token_lease_exhausted"
    elif any(item.decision_state.value == "manual_follow_up_required" for item in report.items):
        status = "manual_follow_up_required"
    else:
        status = "completed"
    return {
        "artifact_key": DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT.value,
        "status": status,
        "failure_codes": failure_codes,
    }
