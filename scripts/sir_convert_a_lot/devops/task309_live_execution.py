"""Task 309 live Granite/vLLM validation execution helpers.

Purpose:
    Run redacted provider microprobes and the in-process DigiExam advisory
    answer-key path against the persistent Granite/vLLM provider.

Relationships:
    - Uses the Task 296 structured-provider adapter for live HTTP execution.
    - Uses the Task 312 provider-protocol answer-key planner through the normal
      advisory orchestration path.
    - Writes retained Task 309 JSON/Markdown reports without raw prompts or
      raw provider responses.
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
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_completion import (
    build_digiexam_answer_key_completion_report,
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
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderProfile,
    StructuredLLMRoutePolicy,
)
from scripts.sir_convert_a_lot.infrastructure.structured_llm_provider import (
    HttpStructuredChatProvider,
    StructuredLLMProviderConnection,
)

TASK309_MICROPROBE_REPORT_SCHEMA_VERSION = "task309_granite_microprobe_report_v1"
TASK309_ADVISORY_CORPUS_RUN_SCHEMA_VERSION = "task309_granite_advisory_corpus_run_v1"
COMPLETION_MODE = "local_llm_suggest_missing_machine_marked"
PROVIDER_ID = "task309-granite-vllm"


@dataclass(frozen=True)
class Task309AdvisoryCorpusRunReport:
    """Redacted full-corpus in-process advisory run report."""

    schema_version: str
    provider_url: str
    model: str
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
    require_provider_ready: bool,
    timeout_seconds: float,
) -> Task309AdvisoryCorpusRunReport:
    ready = build_task309_provider_status(
        provider_url=provider_url,
        timeout_seconds=min(timeout_seconds, 2.0),
    ).ready
    files = tuple(sorted(corpus_root.glob("*.dxe")))
    if require_provider_ready and not ready:
        return _blocked_corpus_report(
            corpus_root=corpus_root,
            provider_url=provider_url,
            model=model,
            file_count=len(files),
        )
    parser = DigiExamDxeParser()
    reports_root.mkdir(parents=True, exist_ok=True)
    report_paths: list[str] = []
    decision_counts: Counter[str] = Counter()
    backend_failures: Counter[str] = Counter()
    item_count = 0
    started = time.perf_counter()
    async with httpx.AsyncClient() as client:
        provider = _provider(
            provider_url=provider_url,
            timeout_seconds=timeout_seconds,
            client=client,
        )
        profile = _base_profile(model=model)
        for source_path in files:
            exam = build_digiexam_intermediate_exam(parser.parse_file(source_path))
            item_count += len(exam.items)
            report = await build_digiexam_answer_key_completion_report(
                job_id=f"task309:{source_path.stem}",
                completion_mode=COMPLETION_MODE,
                exam=exam,
                provider_set=StructuredChatProviderSet(primary=profile),
                route_policy=_route_policy(),
                provider=provider,
            )
            for item in report.items:
                decision_counts[item.decision_state.value] += 1
                if item.backend_failure_code is not None:
                    backend_failures[item.backend_failure_code] += 1
            report_path = reports_root / f"{source_path.stem}.answer-key-completion-report.json"
            report_payload: dict[str, object] = {
                key: value for key, value in report_to_json_payload(report).items()
            }
            write_task309_json(report_payload, report_path)
            report_paths.append(report_path.as_posix())
    return Task309AdvisoryCorpusRunReport(
        schema_version=TASK309_ADVISORY_CORPUS_RUN_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
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
        total_latency_ms=round((time.perf_counter() - started) * 1000, 3),
        report_paths=tuple(report_paths),
    )


def _blocked_corpus_report(
    *,
    corpus_root: Path,
    provider_url: str,
    model: str,
    file_count: int,
) -> Task309AdvisoryCorpusRunReport:
    return Task309AdvisoryCorpusRunReport(
        schema_version=TASK309_ADVISORY_CORPUS_RUN_SCHEMA_VERSION,
        provider_url=provider_url,
        model=model,
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
        total_latency_ms=None,
        report_paths=(),
    )


def _provider(
    *,
    provider_url: str,
    timeout_seconds: float,
    client: httpx.AsyncClient,
) -> HttpStructuredChatProvider:
    connection = StructuredLLMProviderConnection(
        provider_id=PROVIDER_ID,
        base_url=provider_url,
        timeout_seconds=timeout_seconds,
    )
    return HttpStructuredChatProvider(client=client, connections={PROVIDER_ID: connection})


def _base_profile(*, model: str) -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id=PROVIDER_ID,
        model=model,
        endpoint_kind=StructuredLLMEndpointKind.VLLM_CHAT_COMPLETIONS,
        output_mode=StructuredLLMOutputMode.VLLM_JSON_SCHEMA,
        is_remote=False,
        context_window_tokens=4096,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=True,
        ),
    )


def _route_policy() -> StructuredLLMRoutePolicy:
    return StructuredLLMRoutePolicy(
        remote_providers_enabled=False,
        remote_fallback_policy_authorized=False,
        allow_remote_fallback=False,
    )


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
