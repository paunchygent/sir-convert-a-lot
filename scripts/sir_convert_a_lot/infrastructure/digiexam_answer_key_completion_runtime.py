"""Runtime composition for DigiExam advisory answer-key completion.

Purpose:
    Connect the service-loaded structured LLM provider configuration and Dishka
    composition root to the DigiExam advisory answer-key completion domain
    service.

Relationships:
    - Called by `infrastructure.digiexam_migration_bundle_builder` only when the
      job spec explicitly requests advisory local LLM completion.
    - Uses `infrastructure.structured_llm_di` to construct the HTTP provider
      adapter from Task 296.
    - Returns a bounded report artifact payload without raw prompts or provider
      responses.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    DigiExamAnswerKeyCompletionReport,
    build_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    report_to_json_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import DigiExamIntermediateExam
from scripts.sir_convert_a_lot.domain.digiexam_migration_bundle_contracts import (
    DigiExamMigrationArtifactEntry,
    DigiExamMigrationArtifactKey,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import DigiExamAnswerKeyCompletionModeV2
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
    available_entry,
    write_json,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig, ServiceError
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.structured_llm_di import (
    create_structured_llm_async_container,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)


def write_requested_digiexam_answer_key_completion_report(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    exam: DigiExamIntermediateExam,
    config: ServiceConfig,
) -> DigiExamMigrationArtifactEntry | None:
    """Write the advisory completion report when explicitly requested."""

    options = job.spec.digiexam_migration_options
    completion_mode = (
        options.completion_mode
        if options is not None
        else DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY
    )
    if completion_mode == DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY:
        return None
    if completion_mode == (
        DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW
    ):
        raise ServiceError(
            status_code=422,
            code="answer_key_completion_apply_not_implemented",
            message="Reviewed LLM answer-key application is reserved for Task 306.",
            retryable=False,
        )

    report_path = artifact_path(
        artifacts_dir,
        DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT,
    )
    report = run_digiexam_answer_key_completion_report(
        job_id=job.job_id,
        completion_mode=completion_mode.value,
        exam=exam,
        config=config,
    )
    write_json(report_path, report_to_json_payload(report))
    return available_entry(
        job=job,
        key=DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT,
        path=report_path,
    )


def run_digiexam_answer_key_completion_report(
    *,
    job_id: str,
    completion_mode: str,
    exam: DigiExamIntermediateExam,
    config: ServiceConfig,
) -> DigiExamAnswerKeyCompletionReport:
    """Run the advisory completion service from the synchronous bundle builder."""

    return asyncio.run(
        _run_digiexam_answer_key_completion_report(
            job_id=job_id,
            completion_mode=completion_mode,
            exam=exam,
            config=config,
        )
    )


async def _run_digiexam_answer_key_completion_report(
    *,
    job_id: str,
    completion_mode: str,
    exam: DigiExamIntermediateExam,
    config: ServiceConfig,
) -> DigiExamAnswerKeyCompletionReport:
    structured_config = config.structured_llm
    if not structured_config.enabled or structured_config.provider_set is None:
        return await build_digiexam_answer_key_completion_report(
            job_id=job_id,
            completion_mode=completion_mode,
            exam=exam,
            provider_set=None,
            route_policy=structured_config.route_policy(allow_remote_fallback=False),
            provider=None,
        )

    container = create_structured_llm_async_container(config=structured_config)
    try:
        provider = await container.get(HttpStructuredChatProvider)
        return await build_digiexam_answer_key_completion_report(
            job_id=job_id,
            completion_mode=completion_mode,
            exam=exam,
            provider_set=structured_config.provider_set,
            route_policy=structured_config.route_policy(allow_remote_fallback=False),
            provider=provider,
        )
    finally:
        await container.close()
