"""Pure state and JSON validation for daily answer-key token lease ledgers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

_SCHEMA_VERSION = 1
LedgerJsonValue: TypeAlias = int | str | None | dict[str, "LedgerJsonValue"]


class AnswerKeyTokenLeaseState(StrEnum):
    """Durable state of one non-refundable provider-attempt lease."""

    RESERVED = "reserved"
    SENT = "sent"
    RECONCILED = "reconciled"


@dataclass(frozen=True)
class AnswerKeyTokenLease:
    """Persisted reservation state for one provider attempt."""

    lease_id: str
    utc_day: str
    reserved_tokens: int
    state: AnswerKeyTokenLeaseState
    actual_tokens: int | None = None


@dataclass(frozen=True)
class AnswerKeyTokenLeaseSnapshot:
    """Complete accounting snapshot for one structurally partitioned UTC day."""

    utc_day: str
    daily_token_limit: int
    consumed_tokens: int
    reserved_tokens: int
    uncertain_tokens: int
    leases: tuple[AnswerKeyTokenLease, ...]

    @property
    def available_tokens(self) -> int:
        """Tokens that remain admissible before the daily limit is reached."""

        return max(
            0,
            self.daily_token_limit
            - self.consumed_tokens
            - self.reserved_tokens
            - self.uncertain_tokens,
        )


def empty_lease_snapshot(
    *,
    utc_day: str,
    daily_token_limit: int,
) -> AnswerKeyTokenLeaseSnapshot:
    """Create the zero-spend state for an as-yet-unwritten UTC-day ledger."""

    return AnswerKeyTokenLeaseSnapshot(
        utc_day=utc_day,
        daily_token_limit=daily_token_limit,
        consumed_tokens=0,
        reserved_tokens=0,
        uncertain_tokens=0,
        leases=(),
    )


def snapshot_with_records(
    *,
    snapshot: AnswerKeyTokenLeaseSnapshot,
    records: dict[str, AnswerKeyTokenLease],
) -> AnswerKeyTokenLeaseSnapshot:
    """Recalculate aggregate totals from the durable per-lease state."""

    ordered_records = tuple(records[lease_id] for lease_id in sorted(records))
    consumed_tokens = sum(
        record.actual_tokens or 0
        for record in ordered_records
        if record.state == AnswerKeyTokenLeaseState.RECONCILED
    )
    reserved_tokens = sum(
        record.reserved_tokens
        for record in ordered_records
        if record.state == AnswerKeyTokenLeaseState.RESERVED
    )
    uncertain_tokens = sum(
        record.reserved_tokens
        for record in ordered_records
        if record.state == AnswerKeyTokenLeaseState.SENT
    )
    return AnswerKeyTokenLeaseSnapshot(
        utc_day=snapshot.utc_day,
        daily_token_limit=snapshot.daily_token_limit,
        consumed_tokens=consumed_tokens,
        reserved_tokens=reserved_tokens,
        uncertain_tokens=uncertain_tokens,
        leases=ordered_records,
    )


def lease_snapshot_to_payload(snapshot: AnswerKeyTokenLeaseSnapshot) -> dict[str, LedgerJsonValue]:
    """Serialize validated lease state without filesystem behavior."""

    return {
        "schema_version": _SCHEMA_VERSION,
        "utc_day": snapshot.utc_day,
        "limit": snapshot.daily_token_limit,
        "consumed_tokens": snapshot.consumed_tokens,
        "reserved_tokens": snapshot.reserved_tokens,
        "uncertain_tokens": snapshot.uncertain_tokens,
        "leases": {
            record.lease_id: {
                "state": record.state.value,
                "reserved_tokens": record.reserved_tokens,
                "actual_tokens": record.actual_tokens,
            }
            for record in snapshot.leases
        },
    }


def lease_snapshot_from_payload(
    *,
    payload: dict[str, LedgerJsonValue],
    expected_utc_day: str,
    expected_daily_token_limit: int,
) -> AnswerKeyTokenLeaseSnapshot:
    """Validate a persisted JSON payload before it becomes ledger state."""

    _require_exact_keys(
        payload,
        {
            "schema_version",
            "utc_day",
            "limit",
            "consumed_tokens",
            "reserved_tokens",
            "uncertain_tokens",
            "leases",
        },
    )
    schema_version = _require_int(payload, "schema_version")
    utc_day = _require_str(payload, "utc_day")
    daily_token_limit = _require_int(payload, "limit")
    leases_payload = payload["leases"]
    if schema_version != _SCHEMA_VERSION:
        raise ValueError("unsupported lease ledger schema version.")
    if utc_day != expected_utc_day or daily_token_limit != expected_daily_token_limit:
        raise ValueError("lease ledger does not match its configured day and limit.")
    if not isinstance(leases_payload, dict):
        raise ValueError("lease ledger leases must be an object.")

    records: dict[str, AnswerKeyTokenLease] = {}
    for lease_id, record_payload in leases_payload.items():
        if not isinstance(lease_id, str) or not isinstance(record_payload, dict):
            raise ValueError("lease ledger contains an invalid lease record.")
        _require_exact_keys(record_payload, {"state", "reserved_tokens", "actual_tokens"})
        state_value = _require_str(record_payload, "state")
        reserved_tokens = _require_int(record_payload, "reserved_tokens")
        actual_tokens = record_payload["actual_tokens"]
        if not lease_id or reserved_tokens <= 0:
            raise ValueError("lease ledger contains invalid lease values.")
        if actual_tokens is not None and (not isinstance(actual_tokens, int) or actual_tokens < 0):
            raise ValueError("lease ledger contains invalid reported usage.")
        try:
            state = AnswerKeyTokenLeaseState(state_value)
        except ValueError as exc:
            raise ValueError("lease ledger contains an unknown lease state.") from exc
        if state == AnswerKeyTokenLeaseState.RECONCILED and actual_tokens is None:
            raise ValueError("reconciled lease lacks reported usage.")
        if state != AnswerKeyTokenLeaseState.RECONCILED and actual_tokens is not None:
            raise ValueError("unreconciled lease includes reported usage.")
        records[lease_id] = AnswerKeyTokenLease(
            lease_id=lease_id,
            utc_day=utc_day,
            reserved_tokens=reserved_tokens,
            state=state,
            actual_tokens=actual_tokens,
        )

    snapshot = snapshot_with_records(
        snapshot=empty_lease_snapshot(
            utc_day=utc_day,
            daily_token_limit=daily_token_limit,
        ),
        records=records,
    )
    for total_name, actual_total in (
        ("consumed_tokens", snapshot.consumed_tokens),
        ("reserved_tokens", snapshot.reserved_tokens),
        ("uncertain_tokens", snapshot.uncertain_tokens),
    ):
        if _require_int(payload, total_name) != actual_total:
            raise ValueError("lease ledger totals do not match its lease records.")
    return snapshot


def _require_exact_keys(payload: dict[str, LedgerJsonValue], keys: set[str]) -> None:
    if set(payload) != keys:
        raise ValueError("lease ledger has an unexpected record shape.")


def _require_int(payload: dict[str, LedgerJsonValue], key: str) -> int:
    value = payload[key]
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("lease ledger has an invalid integer value.")
    return value


def _require_str(payload: dict[str, LedgerJsonValue], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError("lease ledger has an invalid text value.")
    return value
