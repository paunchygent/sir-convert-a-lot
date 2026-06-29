"""Runtime composition for DigiExam advisory answer-key completion.

Purpose:
    Connect the service-loaded structured LLM provider configuration and Dishka
    composition root to the DigiExam advisory answer-key completion domain
    service.

Relationships:
    - Called by `infrastructure.digiexam_migration_bundle_builder` only when the
      job spec explicitly requests advisory local LLM completion.
    - Uses `infrastructure.structured_llm_di` to construct the HTTP provider
      adapter from structured LLM provider harness.
    - Returns a bounded report artifact payload without raw prompts or provider
      responses.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
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
from scripts.sir_convert_a_lot.domain.structured_llm_admission import (
    StructuredLLMAdmittedRouteSnapshot,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMEndpointKind,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_answer_key_vision_assets import (
    DigiExamDataURLVisionCandidatePlanner,
    DigiExamVisionCandidatePlanner,
    export_digiexam_answer_key_vision_assets,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_migration_bundle_manifest import (
    artifact_path,
    available_entry,
    write_json,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig
from scripts.sir_convert_a_lot.infrastructure.runtime_models_v2 import StoredJobV2
from scripts.sir_convert_a_lot.infrastructure.structured_llm_admission import (
    provider_set_for_admitted_route,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_config import (
    StructuredLLMRuntimeConfig,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_di import (
    create_structured_llm_async_container,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
)


@dataclass(frozen=True)
class DigiExamAnswerKeyCompletionArtifactResult:
    """Persisted advisory completion artifact plus in-memory report."""

    entry: DigiExamMigrationArtifactEntry | None
    report: DigiExamAnswerKeyCompletionReport | None


def write_requested_digiexam_answer_key_completion_report(
    *,
    job: StoredJobV2,
    artifacts_dir: Path,
    exam: DigiExamIntermediateExam,
    config: ServiceConfig,
) -> DigiExamAnswerKeyCompletionArtifactResult:
    """Write the advisory completion report when explicitly requested."""

    options = job.spec.digiexam_migration_options
    completion_mode = (
        options.completion_mode
        if options is not None
        else DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY
    )
    if completion_mode == DigiExamAnswerKeyCompletionModeV2.SOURCE_EVIDENCE_ONLY:
        return DigiExamAnswerKeyCompletionArtifactResult(entry=None, report=None)
    if completion_mode == (
        DigiExamAnswerKeyCompletionModeV2.LOCAL_LLM_APPLY_MISSING_MACHINE_MARKED_WITH_REVIEW
    ):
        return DigiExamAnswerKeyCompletionArtifactResult(entry=None, report=None)

    report_path = artifact_path(
        artifacts_dir,
        DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT,
    )
    report = run_digiexam_answer_key_completion_report(
        job_id=job.job_id,
        completion_mode=completion_mode.value,
        exam=exam,
        config=config,
        admitted_route=job.structured_llm_admission,
    )
    write_json(report_path, report_to_json_payload(report))
    return DigiExamAnswerKeyCompletionArtifactResult(
        entry=available_entry(
            job=job,
            key=DigiExamMigrationArtifactKey.ANSWER_KEY_COMPLETION_REPORT,
            path=report_path,
        ),
        report=report,
    )


def run_digiexam_answer_key_completion_report(
    *,
    job_id: str,
    completion_mode: str,
    exam: DigiExamIntermediateExam,
    config: ServiceConfig,
    admitted_route: StructuredLLMAdmittedRouteSnapshot | None = None,
) -> DigiExamAnswerKeyCompletionReport:
    """Run the advisory completion service from the synchronous bundle builder."""

    return asyncio.run(
        _run_digiexam_answer_key_completion_report(
            job_id=job_id,
            completion_mode=completion_mode,
            exam=exam,
            config=config,
            admitted_route=admitted_route,
        )
    )


async def _run_digiexam_answer_key_completion_report(
    *,
    job_id: str,
    completion_mode: str,
    exam: DigiExamIntermediateExam,
    config: ServiceConfig,
    admitted_route: StructuredLLMAdmittedRouteSnapshot | None,
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
            admitted_route=admitted_route,
        )

    container = create_structured_llm_async_container(config=structured_config)
    try:
        provider = await container.get(HttpStructuredChatProvider)
        provider_set = provider_set_for_admitted_route(
            structured_config=structured_config,
            admitted_route=admitted_route,
        )
        candidate_planner = _vision_candidate_planner(
            job_id=job_id,
            exam=exam,
            structured_config=structured_config,
            provider_set=provider_set,
        )
        return await build_digiexam_answer_key_completion_report(
            job_id=job_id,
            completion_mode=completion_mode,
            exam=exam,
            provider_set=provider_set,
            route_policy=structured_config.route_policy(allow_remote_fallback=False),
            provider=provider,
            candidate_planner=candidate_planner,
            admitted_route=admitted_route,
        )
    finally:
        await container.close()


def _vision_candidate_planner(
    *,
    job_id: str,
    exam: DigiExamIntermediateExam,
    structured_config: StructuredLLMRuntimeConfig,
    provider_set: StructuredChatProviderSet | None,
) -> DigiExamVisionCandidatePlanner | DigiExamDataURLVisionCandidatePlanner | None:
    if provider_set is None:
        return None
    primary = provider_set.primary
    if not primary.capabilities.supports_multimodal_vision:
        return None
    from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
        answer_key_candidate_planner_for_profile,
    )

    base_planner = answer_key_candidate_planner_for_profile(primary)
    if structured_config.vision_media_path is None:
        return DigiExamVisionCandidatePlanner(
            base_planner=base_planner,
            item_assets_by_id={},
        )
    item_assets = export_digiexam_answer_key_vision_assets(
        exam=exam,
        media_path=structured_config.vision_media_path,
        relative_path_prefix=job_id,
    )
    if primary.endpoint_kind == StructuredLLMEndpointKind.RESPONSES or primary.is_remote:
        return DigiExamDataURLVisionCandidatePlanner(
            base_planner=base_planner,
            item_assets_by_id=item_assets,
            media_path=structured_config.vision_media_path,
        )
    return DigiExamVisionCandidatePlanner(
        base_planner=base_planner,
        item_assets_by_id=item_assets,
    )
