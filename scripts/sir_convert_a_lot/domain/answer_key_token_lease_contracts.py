"""Typed failures for the answer-key daily token lease boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AnswerKeyTokenLeaseFailureCode(StrEnum):
    """Operator-visible fail-closed lease failure codes."""

    DAILY_TOKEN_LEASE_EXHAUSTED = "daily_token_lease_exhausted"
    TOKEN_LEASE_LEDGER_UNAVAILABLE = "token_lease_ledger_unavailable"


@dataclass(frozen=True)
class AnswerKeyTokenLeaseError(Exception):
    """Bounded lease refusal without prompt, response, or credential data."""

    failure_code: AnswerKeyTokenLeaseFailureCode
    message: str
    utc_day: str
    requested_tokens: int
    available_tokens: int

    def __str__(self) -> str:
        return self.message
