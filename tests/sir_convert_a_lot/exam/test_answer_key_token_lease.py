"""Focused behavior tests for the filesystem answer-key token lease."""

from __future__ import annotations

import asyncio
import json
import multiprocessing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import JsonValue

import scripts.sir_convert_a_lot.infrastructure.answer_key_token_lease as token_lease_module
from scripts.sir_convert_a_lot.domain.answer_key_token_lease_contracts import (
    AnswerKeyTokenLeaseError,
    AnswerKeyTokenLeaseFailureCode,
)
from scripts.sir_convert_a_lot.domain.structured_llm_contracts import (
    StructuredChatProviderProtocol,
    StructuredLLMBackendFailureCode,
    StructuredLLMEndpointKind,
    StructuredLLMOutputMode,
    StructuredLLMProviderCapabilities,
    StructuredLLMProviderError,
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
    StructuredOutputSpec,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_token_lease import (
    FilesystemAnswerKeyTokenLeaseLedger,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_token_lease_state import (
    AnswerKeyTokenLeaseState,
)
from scripts.sir_convert_a_lot.infrastructure.leased_structured_llm_provider import (
    LeasedStructuredChatProvider,
)

_FIRST_DAY = datetime(2026, 8, 29, 23, 59, tzinfo=UTC)
_SECOND_DAY = datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
_PROCESS_DAY = datetime(2026, 8, 31, 12, 0, tzinfo=UTC)
CHOICE_SCHEMA: dict[str, JsonValue] = {
    "type": "object",
    "properties": {"selected_choice": {"type": "string"}},
    "required": ["selected_choice"],
    "additionalProperties": False,
}


@dataclass
class MutableUTCClock:
    """Deterministic clock whose UTC day can advance during a test."""

    timestamp: datetime

    def __call__(self) -> datetime:
        return self.timestamp


class SuccessfulProvider:
    """Provider double that returns the configured bounded usage metadata."""

    def __init__(self, *, usage: StructuredLLMUsage) -> None:
        self.usage = usage
        self.call_count = 0

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        self.call_count += 1
        return StructuredLLMResponse(
            content={"selected_choice": "choice-a"},
            finish_reason="stop",
            usage=self.usage,
        )


class FailingProvider:
    """Provider double that raises the normal typed provider failure."""

    async def complete_structured_chat(
        self,
        *,
        request: StructuredLLMRequest,
        profile: StructuredLLMProviderProfile,
    ) -> StructuredLLMResponse:
        raise StructuredLLMProviderError(
            failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
            message="Structured provider request timed out.",
            provider_id=profile.provider_id,
        )


def test_reserve_send_reconcile_moves_totals_between_lease_states(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=1_000, clock=MutableUTCClock(_FIRST_DAY))

    lease = ledger.reserve(estimated_input_tokens=100, max_output_tokens=200)
    assert ledger.snapshot().reserved_tokens == 300

    ledger.mark_sent(lease=lease)
    sent_snapshot = ledger.snapshot()
    assert sent_snapshot.reserved_tokens == 0
    assert sent_snapshot.uncertain_tokens == 300

    ledger.reconcile(lease=lease, actual_tokens=240)
    reconciled_snapshot = ledger.snapshot()
    assert reconciled_snapshot.consumed_tokens == 240
    assert reconciled_snapshot.uncertain_tokens == 0
    assert reconciled_snapshot.leases[0].state == AnswerKeyTokenLeaseState.RECONCILED
    assert reconciled_snapshot.leases[0].actual_tokens == 240


def test_utc_day_partition_resets_structurally_at_midnight(tmp_path: Path) -> None:
    clock = MutableUTCClock(_FIRST_DAY)
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=100, clock=clock)
    ledger.reserve(estimated_input_tokens=40, max_output_tokens=50)

    clock.timestamp = _SECOND_DAY
    second_day_snapshot = ledger.snapshot()

    assert second_day_snapshot.utc_day == "2026-08-30"
    assert second_day_snapshot.reserved_tokens == 0
    assert sorted(path.name for path in tmp_path.glob("*.json")) == [
        "answer-key-token-lease-2026-08-29.json"
    ]
    second_day_lease = ledger.reserve(estimated_input_tokens=40, max_output_tokens=50)
    assert second_day_lease.utc_day == "2026-08-30"
    assert sorted(path.name for path in tmp_path.glob("*.json")) == [
        "answer-key-token-lease-2026-08-29.json",
        "answer-key-token-lease-2026-08-30.json",
    ]


def test_exhaustion_refuses_reservation_with_typed_available_balance(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=100, clock=MutableUTCClock(_FIRST_DAY))
    ledger.reserve(estimated_input_tokens=25, max_output_tokens=35)

    with pytest.raises(AnswerKeyTokenLeaseError) as exc_info:
        ledger.reserve(estimated_input_tokens=20, max_output_tokens=30)

    assert exc_info.value.failure_code == AnswerKeyTokenLeaseFailureCode.DAILY_TOKEN_LEASE_EXHAUSTED
    assert exc_info.value.available_tokens == 40
    assert ledger.snapshot().reserved_tokens == 60


def test_provider_failure_remains_uncertain_without_a_refund(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=1_000, clock=MutableUTCClock(_FIRST_DAY))
    provider = LeasedStructuredChatProvider(provider=FailingProvider(), lease_ledger=ledger)

    with pytest.raises(StructuredLLMProviderError):
        asyncio.run(_complete(provider))

    snapshot = ledger.snapshot()
    assert snapshot.uncertain_tokens == 300
    assert snapshot.consumed_tokens == 0
    assert snapshot.leases[0].state == AnswerKeyTokenLeaseState.SENT


def test_provider_success_reconciles_reported_total_usage(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=1_000, clock=MutableUTCClock(_FIRST_DAY))
    delegated_provider = SuccessfulProvider(usage=StructuredLLMUsage(total_tokens=190))
    provider: StructuredChatProviderProtocol = LeasedStructuredChatProvider(
        provider=delegated_provider,
        lease_ledger=ledger,
    )

    response = asyncio.run(_complete(provider))

    assert response.usage.total_tokens == 190
    assert delegated_provider.call_count == 1
    assert ledger.snapshot().consumed_tokens == 190
    assert ledger.snapshot().uncertain_tokens == 0


def test_missing_provider_usage_keeps_sent_lease_uncertain(tmp_path: Path) -> None:
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=1_000, clock=MutableUTCClock(_FIRST_DAY))
    provider = LeasedStructuredChatProvider(
        provider=SuccessfulProvider(usage=StructuredLLMUsage()),
        lease_ledger=ledger,
    )

    asyncio.run(_complete(provider))

    snapshot = ledger.snapshot()
    assert snapshot.uncertain_tokens == 300
    assert snapshot.consumed_tokens == 0
    assert snapshot.leases[0].state == AnswerKeyTokenLeaseState.SENT


def test_corrupt_ledger_fails_closed_with_typed_unavailable_error(tmp_path: Path) -> None:
    (tmp_path / "answer-key-token-lease-2026-08-29.json").write_text("{broken", encoding="utf-8")
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=100, clock=MutableUTCClock(_FIRST_DAY))

    with pytest.raises(AnswerKeyTokenLeaseError) as exc_info:
        ledger.reserve(estimated_input_tokens=10, max_output_tokens=10)

    assert (
        exc_info.value.failure_code == AnswerKeyTokenLeaseFailureCode.TOKEN_LEASE_LEDGER_UNAVAILABLE
    )
    assert str(tmp_path) not in exc_info.value.message


def test_atomic_write_failure_fails_closed_with_typed_unavailable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=100, clock=MutableUTCClock(_FIRST_DAY))
    monkeypatch.setattr(token_lease_module.os, "replace", _raise_atomic_replace_failure)

    with pytest.raises(AnswerKeyTokenLeaseError) as exc_info:
        ledger.reserve(estimated_input_tokens=10, max_output_tokens=10)

    assert (
        exc_info.value.failure_code == AnswerKeyTokenLeaseFailureCode.TOKEN_LEASE_LEDGER_UNAVAILABLE
    )
    assert str(tmp_path) not in exc_info.value.message


def test_cross_process_reservations_never_exceed_daily_limit(tmp_path: Path) -> None:
    process_context = multiprocessing.get_context("spawn")
    barrier = process_context.Barrier(6)
    processes = [
        process_context.Process(
            target=_reserve_in_parallel_process,
            args=(str(tmp_path), barrier),
        )
        for _ in range(6)
    ]

    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=15)
        assert process.exitcode == 0

    ledger = _ledger(tmp_path=tmp_path, daily_token_limit=100, clock=MutableUTCClock(_PROCESS_DAY))
    snapshot = ledger.snapshot()
    assert len(snapshot.leases) == 2
    assert snapshot.reserved_tokens == 100
    assert snapshot.reserved_tokens <= snapshot.daily_token_limit


def _reserve_in_parallel_process(
    ledger_directory: str,
    barrier: multiprocessing.synchronize.Barrier,
) -> None:
    ledger = FilesystemAnswerKeyTokenLeaseLedger(
        ledger_directory=Path(ledger_directory),
        daily_token_limit=100,
        utc_clock=_process_utc_clock,
    )
    barrier.wait(timeout=10)
    try:
        ledger.reserve(estimated_input_tokens=30, max_output_tokens=20)
    except AnswerKeyTokenLeaseError as exc:
        if exc.failure_code != AnswerKeyTokenLeaseFailureCode.DAILY_TOKEN_LEASE_EXHAUSTED:
            raise


def _process_utc_clock() -> datetime:
    return _PROCESS_DAY


def _raise_atomic_replace_failure(source: Path, destination: Path) -> None:
    raise OSError("replace failed")


async def _complete(provider: StructuredChatProviderProtocol) -> StructuredLLMResponse:
    return await provider.complete_structured_chat(request=_request(), profile=_profile())


def _ledger(
    *,
    tmp_path: Path,
    daily_token_limit: int,
    clock: MutableUTCClock,
) -> FilesystemAnswerKeyTokenLeaseLedger:
    return FilesystemAnswerKeyTokenLeaseLedger(
        ledger_directory=tmp_path,
        daily_token_limit=daily_token_limit,
        utc_clock=clock,
    )


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="remote-answer-key",
        model="remote-answer-key-model",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        output_mode=StructuredLLMOutputMode.JSON_SCHEMA,
        is_remote=True,
        context_window_tokens=4_096,
        max_output_tokens=512,
        capabilities=StructuredLLMProviderCapabilities(
            supports_json_schema=True,
            supports_gbnf=False,
            supports_vllm_structured_choice=False,
        ),
    )


def _request() -> StructuredLLMRequest:
    return StructuredLLMRequest(
        job_id="job-001",
        item_id="item-001",
        item_type="single_choice",
        prompt_template_version="answer_key_choice_prompt_v1",
        system_prompt="Return the selected answer key.",
        user_payload=json.dumps({"choices": ["choice-a", "choice-b"]}),
        output_spec=StructuredOutputSpec(
            schema_name="choice_decision",
            schema_version="choice_decision_v1",
            json_schema=CHOICE_SCHEMA,
        ),
        estimated_input_tokens=100,
        max_output_tokens=200,
        allow_remote_fallback=False,
    )
