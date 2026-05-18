"""Task 326 OpenAI answer-key evaluation gate runner.

Purpose:
    Execute the governed DigiExam answer-key corpus against pinned OpenAI
    Responses profiles while retaining raw diagnostic artifacts for Task 326
    adjudication.

Relationships:
    - Reuses the Task 309 DigiExam corpus and golden-evaluation scorer.
    - Consumes Task 325 OpenAI provider profiles without adding model-name
      branches to answer-key orchestration.
    - Writes ignored `build/verification` artifacts; committed docs should
      retain only aggregate outcomes, hashes, and promotion recommendations.
"""

from __future__ import annotations

import asyncio
import base64
import os
import time
from collections import Counter
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.answer_key_provider_exchange_capture import (
    Task309CapturingStructuredChatProvider,
    Task309ProviderExchange,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    build_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
    DigiExamAnswerKeyCandidatePlannerProtocol,
    DigiExamCompletionCandidatePlan,
    answer_key_candidate_planner_for_profile,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_contracts import (
    report_to_json_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    write_task309_json,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMImageURLContentPart,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMRoutePolicy,
    StructuredLLMTextContentPart,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_openai_model_profiles import (
    OPENAI_API_KEY_ENV,
    AnswerKeyOpenAIProviderDefaults,
    answer_key_openai_defaults_for_provider_profile,
    build_answer_key_openai_provider_profile,
)
from scripts.sir_convert_a_lot.infrastructure.digiexam_answer_key_vision_assets import (
    DigiExamAnswerKeyVisionItemAssets,
    export_digiexam_answer_key_vision_assets,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)

TASK326_OPENAI_ADVISORY_CORPUS_RUN_SCHEMA_VERSION = "task326_openai_advisory_corpus_run_v1"
COMPLETION_MODE = "local_llm_suggest_missing_machine_marked"


@dataclass(frozen=True)
class Task326OpenAIAdvisoryCorpusRunReport:
    """Raw diagnostic full-corpus OpenAI advisory run report."""

    schema_version: str
    provider_url: str
    model: str
    provider_profile_id: str
    corpus_root: str
    credential_env: str
    credential_present: bool
    blocked: bool
    file_count: int
    item_count: int
    eligible_item_count: int
    suggested_count: int
    manual_follow_up_count: int
    skipped_count: int
    backend_failure_counts: tuple[dict[str, object], ...]
    asset_eligible_count: int
    multimodal_request_count: int
    provider_run_metadata: dict[str, object]
    total_latency_ms: float | None
    report_paths: tuple[str, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the corpus run report."""

        return _json_object(asdict(self))


def default_task326_openai_output_root(provider_profile: str) -> Path:
    """Return the ignored Task 326 output root for one OpenAI profile."""

    safe_profile = provider_profile.replace("/", "_")
    return Path("build/verification") / f"task-326-{safe_profile}"


def run_task326_openai_advisory_corpus(
    *,
    corpus_root: Path,
    reports_root: Path,
    provider_profile: str,
    api_key_env: str = OPENAI_API_KEY_ENV,
    timeout_seconds: float | None = None,
    vision_media_path: Path | None = None,
) -> Task326OpenAIAdvisoryCorpusRunReport:
    """Run the Task 326 OpenAI eval corpus, retaining raw diagnostic reports."""

    return asyncio.run(
        _run_task326_openai_advisory_corpus(
            corpus_root=corpus_root,
            reports_root=reports_root,
            provider_profile=provider_profile,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
            vision_media_path=vision_media_path,
        )
    )


def write_task326_openai_advisory_corpus_run(
    *,
    output_root: Path,
    report: Task326OpenAIAdvisoryCorpusRunReport,
) -> Path:
    """Write the Task 326 OpenAI run report."""

    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / "in-process-advisory-corpus-run.json"
    write_task309_json(report.to_payload(), path)
    return path


async def _run_task326_openai_advisory_corpus(
    *,
    corpus_root: Path,
    reports_root: Path,
    provider_profile: str,
    api_key_env: str,
    timeout_seconds: float | None,
    vision_media_path: Path | None,
) -> Task326OpenAIAdvisoryCorpusRunReport:
    defaults = answer_key_openai_defaults_for_provider_profile(provider_profile)
    profile = build_answer_key_openai_provider_profile(defaults)
    resolved_timeout = timeout_seconds if timeout_seconds is not None else defaults.timeout_seconds
    resolved_vision_media_path = vision_media_path or reports_root.parent / "vision-assets"
    metadata = _provider_run_metadata(
        defaults=defaults,
        profile=profile,
        reports_root=reports_root,
        vision_media_path=resolved_vision_media_path,
        timeout_seconds=resolved_timeout,
    )
    files = tuple(sorted(corpus_root.glob("*.dxe")))
    api_key = os.environ.get(api_key_env, "")
    if not api_key.strip():
        return _blocked_report(
            corpus_root=corpus_root,
            provider_url=defaults.base_url,
            model=defaults.model,
            provider_profile_id=defaults.provider_id,
            api_key_env=api_key_env,
            file_count=len(files),
            metadata=metadata,
        )

    parser = DigiExamDxeParser()
    reports_root.mkdir(parents=True, exist_ok=True)
    report_paths: list[str] = []
    decision_counts: Counter[str] = Counter()
    backend_failures: Counter[str] = Counter()
    asset_eligible_count = 0
    multimodal_request_count = 0
    item_count = 0
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        provider = Task309CapturingStructuredChatProvider(
            client=client,
            connections={
                profile.provider_id: StructuredLLMProviderConnection(
                    provider_id=profile.provider_id,
                    base_url=defaults.base_url,
                    api_key=api_key,
                    timeout_seconds=resolved_timeout,
                )
            },
        )
        for source_path in files:
            exam = build_digiexam_intermediate_exam(parser.parse_file(source_path))
            item_assets_by_id = export_digiexam_answer_key_vision_assets(
                exam=exam,
                media_path=resolved_vision_media_path,
                relative_path_prefix=source_path.stem,
            )
            candidate_planner = OpenAIDataURLVisionCandidatePlanner(
                base_planner=answer_key_candidate_planner_for_profile(profile),
                item_assets_by_id=item_assets_by_id,
                media_path=resolved_vision_media_path,
            )
            job_id = f"task326:{source_path.stem}:{profile.provider_id}"
            item_count += len(exam.items)
            report = await build_digiexam_answer_key_completion_report(
                job_id=job_id,
                completion_mode=COMPLETION_MODE,
                exam=exam,
                provider_set=StructuredChatProviderSet(primary=profile),
                route_policy=_route_policy(),
                provider=provider,
                candidate_planner=candidate_planner,
            )
            exchanges = provider.exchanges_for_job(job_id)
            asset_eligible_count += len(item_assets_by_id)
            multimodal_request_count += sum(
                1 for exchange in exchanges.values() if exchange.multimodal_request
            )
            for item in report.items:
                decision_counts[item.decision_state.value] += 1
                if item.backend_failure_code is not None:
                    backend_failures[item.backend_failure_code] += 1
            report_path = reports_root / f"{source_path.stem}.answer-key-completion-report.json"
            report_payload: dict[str, object] = {
                key: value for key, value in report_to_json_payload(report).items()
            }
            _attach_provider_exchanges(report_payload=report_payload, exchanges=exchanges)
            write_task309_json(report_payload, report_path)
            report_paths.append(report_path.as_posix())
    return Task326OpenAIAdvisoryCorpusRunReport(
        schema_version=TASK326_OPENAI_ADVISORY_CORPUS_RUN_SCHEMA_VERSION,
        provider_url=defaults.base_url,
        model=defaults.model,
        provider_profile_id=defaults.provider_id,
        corpus_root=corpus_root.as_posix(),
        credential_env=api_key_env,
        credential_present=True,
        blocked=False,
        file_count=len(files),
        item_count=item_count,
        eligible_item_count=sum(decision_counts.values()) - decision_counts["skipped"],
        suggested_count=decision_counts["suggested"],
        manual_follow_up_count=decision_counts["manual_follow_up_required"],
        skipped_count=decision_counts["skipped"],
        backend_failure_counts=_counter_payload(backend_failures),
        asset_eligible_count=asset_eligible_count,
        multimodal_request_count=multimodal_request_count,
        provider_run_metadata=metadata,
        total_latency_ms=round((time.perf_counter() - started) * 1000, 3),
        report_paths=tuple(report_paths),
    )


@dataclass(frozen=True)
class OpenAIDataURLVisionCandidatePlanner:
    """Attach OpenAI-readable image data URLs to vision-capable requests."""

    base_planner: DigiExamAnswerKeyCandidatePlannerProtocol
    item_assets_by_id: dict[str, DigiExamAnswerKeyVisionItemAssets]
    media_path: Path

    def plan_candidate(
        self,
        *,
        job_id: str,
        item: DigiExamIrItem,
        profile: StructuredLLMProviderProfile | None,
    ) -> DigiExamCompletionCandidatePlan | None:
        """Build a candidate plan with OpenAI Responses image inputs."""

        plan = self.base_planner.plan_candidate(job_id=job_id, item=item, profile=profile)
        if plan is None:
            return None
        if not (item.embedded_assets or item.embedded_asset_references):
            return plan
        if profile is None or not profile.capabilities.supports_multimodal_vision:
            return None
        item_assets = self.item_assets_by_id.get(item.item_id)
        if item_assets is None:
            return None
        image_parts = _data_url_image_parts(media_path=self.media_path, item_assets=item_assets)
        if not image_parts:
            return None
        request = replace(
            plan.request,
            user_content_parts=(
                StructuredLLMTextContentPart(plan.request.user_payload),
                *image_parts,
            ),
        )
        return replace(plan, request=request)


def _blocked_report(
    *,
    corpus_root: Path,
    provider_url: str,
    model: str,
    provider_profile_id: str,
    api_key_env: str,
    file_count: int,
    metadata: dict[str, object],
) -> Task326OpenAIAdvisoryCorpusRunReport:
    return Task326OpenAIAdvisoryCorpusRunReport(
        schema_version=TASK326_OPENAI_ADVISORY_CORPUS_RUN_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
        provider_profile_id=provider_profile_id,
        corpus_root=corpus_root.as_posix(),
        credential_env=api_key_env,
        credential_present=False,
        blocked=True,
        file_count=file_count,
        item_count=0,
        eligible_item_count=0,
        suggested_count=0,
        manual_follow_up_count=0,
        skipped_count=0,
        backend_failure_counts=(),
        asset_eligible_count=0,
        multimodal_request_count=0,
        provider_run_metadata=metadata,
        total_latency_ms=None,
        report_paths=(),
    )


def _provider_run_metadata(
    *,
    defaults: AnswerKeyOpenAIProviderDefaults,
    profile: StructuredLLMProviderProfile,
    reports_root: Path,
    vision_media_path: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    return {
        "schema_version": "task326_openai_provider_run_metadata_v1",
        "available": True,
        "metadata_source": "task326_openai_run_report",
        "profile_name": defaults.profile_name.value,
        "provider_url": defaults.base_url,
        "expected_model_id": defaults.model,
        "provider_id": profile.provider_id,
        "model": profile.model,
        "endpoint_kind": profile.endpoint_kind.value,
        "provider_runtime": profile.endpoint_kind.value,
        "default_output_mode": profile.output_mode.value,
        "is_remote": profile.is_remote,
        "context_window_tokens": profile.context_window_tokens,
        "max_output_tokens": profile.max_output_tokens,
        "temperature": profile.temperature,
        "capabilities": _capabilities_payload(profile.capabilities),
        "output_mode_policy": _output_mode_policy_payload(profile),
        "request_settings": {
            "temperature": profile.temperature,
            "max_output_tokens": profile.max_output_tokens,
            "context_window_tokens": profile.context_window_tokens,
            "reasoning_effort": defaults.reasoning_effort.value,
            "text_verbosity": defaults.text_verbosity.value,
            "timeout_seconds": timeout_seconds,
        },
        "launch_settings": {},
        "artifact_paths": {
            "reports_root": reports_root.as_posix(),
            "vision_media_path": vision_media_path.as_posix(),
        },
    }


def _capabilities_payload(capabilities: StructuredLLMProviderCapabilities) -> dict[str, object]:
    return {
        "supports_json_schema": capabilities.supports_json_schema,
        "supports_gbnf": capabilities.supports_gbnf,
        "supports_vllm_structured_choice": capabilities.supports_vllm_structured_choice,
        "supports_multimodal_vision": capabilities.supports_multimodal_vision,
    }


def _output_mode_policy_payload(profile: StructuredLLMProviderProfile) -> dict[str, object]:
    return {
        "single_choice": profile.output_mode.value,
        "multiple_choice": profile.output_mode.value,
        "multiple_response": profile.output_mode.value,
        "gap_fill": profile.output_mode.value,
    }


def _data_url_image_parts(
    *,
    media_path: Path,
    item_assets: DigiExamAnswerKeyVisionItemAssets,
) -> tuple[StructuredLLMImageURLContentPart, ...]:
    parts: list[StructuredLLMImageURLContentPart] = []
    for asset in item_assets.assets:
        payload = (media_path / asset.relative_path).read_bytes()
        encoded = base64.b64encode(payload).decode("ascii")
        parts.append(
            StructuredLLMImageURLContentPart(
                url=f"data:{asset.media_type};base64,{encoded}",
            )
        )
    return tuple(parts)


def _attach_provider_exchanges(
    *,
    report_payload: dict[str, object],
    exchanges: dict[str, Task309ProviderExchange],
) -> None:
    items = report_payload.get("items")
    if not isinstance(items, list):
        raise ValueError("Task 326 advisory report items must be a list.")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Task 326 advisory report item must be an object.")
        item_id = item.get("item_id")
        if not isinstance(item_id, str):
            raise ValueError("Task 326 advisory report item_id must be a string.")
        exchange = exchanges.get(item_id)
        if exchange is not None:
            item["task309_provider_exchange"] = exchange.to_payload()


def _route_policy() -> StructuredLLMRoutePolicy:
    return StructuredLLMRoutePolicy(
        remote_providers_enabled=True,
        remote_fallback_policy_authorized=True,
        allow_remote_fallback=True,
    )


def _counter_payload(counter: Counter[str]) -> tuple[dict[str, object], ...]:
    return tuple({"key": key, "count": counter[key]} for key in sorted(counter))


def _json_object(value: dict[str, object]) -> dict[str, object]:
    return {str(key): item for key, item in value.items()}
