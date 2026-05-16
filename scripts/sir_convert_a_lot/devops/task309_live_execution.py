"""Task 309 live structured-provider validation execution helpers.

Purpose:
    Run the in-process DigiExam advisory answer-key path against a selected
    Task 309 structured provider runtime.

Relationships:
    - Uses the Task 296 structured-provider adapter for live HTTP execution.
    - Uses the Task 312 provider-protocol answer-key planner through the normal
      advisory orchestration path.
    - Writes retained Task 309 validation JSON/Markdown reports with raw
      provider exchanges so failed live reasoning can be adjudicated.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.task309_granite_provider_contracts import (
    DEFAULT_PROVIDER_MODEL,
    DEFAULT_PROVIDER_URL,
)
from scripts.sir_convert_a_lot.devops.task309_granite_provider_status import (
    build_task309_provider_status,
)
from scripts.sir_convert_a_lot.devops.task309_provider_exchange_capture import (
    Task309CapturingStructuredChatProvider,
    Task309ProviderExchange,
)
from scripts.sir_convert_a_lot.devops.task309_provider_run_metadata import (
    build_task309_provider_run_metadata,
)
from scripts.sir_convert_a_lot.devops.task309_structured_provider_profiles import (
    DEFAULT_TASK309_CONTEXT_WINDOW_TOKENS,
    DEFAULT_TASK309_MAX_OUTPUT_TOKENS,
    DEFAULT_TASK309_PROVIDER_RUNTIME,
    DEFAULT_TASK309_TEMPERATURE,
    Task309ProviderProfileName,
    Task309StructuredProviderRuntime,
    build_task309_provider_profile,
    task309_defaults_for_provider_profile,
)
from scripts.sir_convert_a_lot.devops.task309_vision_assets import (
    Task309VisionCandidatePlanner,
    export_task309_vision_assets,
    vision_item_assets_by_id,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    build_digiexam_answer_key_completion_report,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion_candidates import (
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
    build_digiexam_intermediate_exam,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderSet,
    StructuredLLMRoutePolicy,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    StructuredLLMProviderConnection,
)

TASK309_MICROPROBE_REPORT_SCHEMA_VERSION = "task309_granite_microprobe_report_v1"
TASK309_ADVISORY_CORPUS_RUN_SCHEMA_VERSION = "task309_granite_advisory_corpus_run_v1"
COMPLETION_MODE = "local_llm_suggest_missing_machine_marked"


@dataclass(frozen=True)
class Task309AdvisoryCorpusRunReport:
    """Redacted full-corpus in-process advisory run report."""

    schema_version: str
    provider_url: str
    model: str
    provider_runtime: str
    corpus_root: str
    provider_ready: bool
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


def run_task309_advisory_corpus(
    *,
    corpus_root: Path,
    reports_root: Path,
    provider_url: str = DEFAULT_PROVIDER_URL,
    model: str = DEFAULT_PROVIDER_MODEL,
    provider_profile_name: Task309ProviderProfileName = Task309ProviderProfileName.GRANITE_VLLM,
    provider_runtime: Task309StructuredProviderRuntime = DEFAULT_TASK309_PROVIDER_RUNTIME,
    context_window_tokens: int = DEFAULT_TASK309_CONTEXT_WINDOW_TOKENS,
    max_output_tokens: int = DEFAULT_TASK309_MAX_OUTPUT_TOKENS,
    temperature: float = DEFAULT_TASK309_TEMPERATURE,
    supports_multimodal_vision: bool = False,
    vision_media_path: Path | None = None,
    require_provider_ready: bool = True,
    timeout_seconds: float = 30.0,
) -> Task309AdvisoryCorpusRunReport:
    """Run in-process advisory completion over the Task 309 corpus."""

    return asyncio.run(
        _run_task309_advisory_corpus(
            corpus_root=corpus_root,
            reports_root=reports_root,
            provider_url=provider_url,
            model=model,
            provider_profile_name=provider_profile_name,
            provider_runtime=provider_runtime,
            context_window_tokens=context_window_tokens,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            supports_multimodal_vision=supports_multimodal_vision,
            vision_media_path=vision_media_path,
            require_provider_ready=require_provider_ready,
            timeout_seconds=timeout_seconds,
        )
    )


async def _run_task309_advisory_corpus(
    *,
    corpus_root: Path,
    reports_root: Path,
    provider_url: str,
    model: str,
    provider_profile_name: Task309ProviderProfileName,
    provider_runtime: Task309StructuredProviderRuntime,
    context_window_tokens: int,
    max_output_tokens: int,
    temperature: float,
    supports_multimodal_vision: bool,
    vision_media_path: Path | None,
    require_provider_ready: bool,
    timeout_seconds: float,
) -> Task309AdvisoryCorpusRunReport:
    from urllib.parse import urlparse

    profile = build_task309_provider_profile(
        runtime=provider_runtime,
        model=model,
        context_window_tokens=context_window_tokens,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        supports_multimodal_vision=supports_multimodal_vision,
    )
    resolved_vision_media_path = _resolved_vision_media_path(
        supports_multimodal_vision=profile.capabilities.supports_multimodal_vision,
        vision_media_path=vision_media_path,
    )
    defaults = task309_defaults_for_provider_profile(provider_profile_name.value)
    provider_run_metadata = build_task309_provider_run_metadata(
        profile_name=provider_profile_name,
        defaults=defaults,
        provider_url=provider_url,
        provider_runtime=provider_runtime,
        profile=profile,
        reports_root=reports_root,
        vision_media_path=resolved_vision_media_path,
    ).to_payload()
    parsed = urlparse(provider_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    ready = build_task309_provider_status(
        provider_url=provider_url,
        port=port,
        timeout_seconds=min(timeout_seconds, 2.0),
    ).ready
    files = tuple(sorted(corpus_root.glob("*.dxe")))
    if require_provider_ready and not ready:
        return _blocked_corpus_report(
            corpus_root=corpus_root,
            provider_url=provider_url,
            model=model,
            provider_runtime=provider_runtime,
            provider_run_metadata=provider_run_metadata,
            file_count=len(files),
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
        provider = _capturing_provider(
            provider_url=provider_url,
            timeout_seconds=timeout_seconds,
            client=client,
            provider_id=profile.provider_id,
        )
        for source_path in files:
            exam = build_digiexam_intermediate_exam(parser.parse_file(source_path))
            vision_export = (
                export_task309_vision_assets(
                    exam=exam,
                    source_filename=source_path.name,
                    media_path=resolved_vision_media_path,
                )
                if resolved_vision_media_path is not None
                else None
            )
            item_assets_by_id = vision_item_assets_by_id(vision_export) if vision_export else {}
            candidate_planner = Task309VisionCandidatePlanner(
                base_planner=answer_key_candidate_planner_for_profile(profile),
                item_assets_by_id=item_assets_by_id,
            )
            item_count += len(exam.items)
            report = await build_digiexam_answer_key_completion_report(
                job_id=f"task309:{source_path.stem}",
                completion_mode=COMPLETION_MODE,
                exam=exam,
                provider_set=StructuredChatProviderSet(primary=profile),
                route_policy=_route_policy(),
                provider=provider,
                candidate_planner=candidate_planner,
            )
            asset_eligible_count += len(item_assets_by_id)
            multimodal_request_count += sum(
                1
                for exchange in provider.exchanges_for_job(f"task309:{source_path.stem}").values()
                if exchange.multimodal_request
            )
            for item in report.items:
                decision_counts[item.decision_state.value] += 1
                if item.backend_failure_code is not None:
                    backend_failures[item.backend_failure_code] += 1
            report_path = reports_root / f"{source_path.stem}.answer-key-completion-report.json"
            report_payload: dict[str, object] = {
                key: value for key, value in report_to_json_payload(report).items()
            }
            _attach_provider_exchanges(
                report_payload=report_payload,
                exchanges=provider.exchanges_for_job(f"task309:{source_path.stem}"),
            )
            write_task309_json(report_payload, report_path)
            report_paths.append(report_path.as_posix())
    return Task309AdvisoryCorpusRunReport(
        schema_version=TASK309_ADVISORY_CORPUS_RUN_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
        provider_runtime=provider_runtime.value,
        corpus_root=corpus_root.as_posix(),
        provider_ready=ready,
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
        provider_run_metadata=provider_run_metadata,
        total_latency_ms=round((time.perf_counter() - started) * 1000, 3),
        report_paths=tuple(report_paths),
    )


def _blocked_corpus_report(
    *,
    corpus_root: Path,
    provider_url: str,
    model: str,
    provider_runtime: Task309StructuredProviderRuntime,
    provider_run_metadata: dict[str, object],
    file_count: int,
) -> Task309AdvisoryCorpusRunReport:
    return Task309AdvisoryCorpusRunReport(
        schema_version=TASK309_ADVISORY_CORPUS_RUN_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
        provider_runtime=provider_runtime.value,
        corpus_root=corpus_root.as_posix(),
        provider_ready=False,
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
        provider_run_metadata=provider_run_metadata,
        total_latency_ms=None,
        report_paths=(),
    )


def _capturing_provider(
    *,
    provider_url: str,
    timeout_seconds: float,
    client: httpx.AsyncClient,
    provider_id: str,
) -> Task309CapturingStructuredChatProvider:
    connection = StructuredLLMProviderConnection(
        provider_id=provider_id,
        base_url=provider_url,
        timeout_seconds=timeout_seconds,
    )
    return Task309CapturingStructuredChatProvider(
        client=client,
        connections={provider_id: connection},
    )


def _attach_provider_exchanges(
    *,
    report_payload: dict[str, object],
    exchanges: dict[str, Task309ProviderExchange],
) -> None:
    items = report_payload.get("items")
    if not isinstance(items, list):
        raise ValueError("Task 309 advisory report items must be a list.")
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Task 309 advisory report item must be an object.")
        item_id = item.get("item_id")
        if not isinstance(item_id, str):
            raise ValueError("Task 309 advisory report item_id must be a string.")
        exchange = exchanges.get(item_id)
        if exchange is not None:
            item["task309_provider_exchange"] = exchange.to_payload()


def _route_policy() -> StructuredLLMRoutePolicy:
    return StructuredLLMRoutePolicy(
        remote_providers_enabled=False,
        remote_fallback_policy_authorized=False,
        allow_remote_fallback=False,
    )


def _resolved_vision_media_path(
    *,
    supports_multimodal_vision: bool,
    vision_media_path: Path | None,
) -> Path | None:
    if not supports_multimodal_vision:
        return None
    if vision_media_path is None:
        raise ValueError("Task 309 multimodal advisory runs require a vision_media_path.")
    return vision_media_path


def _counter_payload(counter: Counter[str]) -> tuple[dict[str, object], ...]:
    return tuple({"key": key, "count": counter[key]} for key in sorted(counter))


def _json_object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Task 309 live execution report must serialize to an object.")
    return {str(key): _json_value(child) for key, child in value.items()}


def _json_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_value(child) for key, child in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(child) for child in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    raise TypeError(f"Unsupported Task 309 live execution JSON value: {type(value).__name__}")
