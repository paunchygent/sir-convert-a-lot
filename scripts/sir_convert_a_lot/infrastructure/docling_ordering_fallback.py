"""Ordering fallback scoring and warning helpers.

Purpose:
    Keep Docling ordering fallback ranking and warning policy deterministic and
    reusable outside backend orchestration methods.

Relationships:
    - Consumed by `infrastructure.docling_backend` when selecting between
      layout-model extraction attempts.
    - Works with ordering quality reports generated in
      `infrastructure.docling_ordering`.
"""

from __future__ import annotations

from typing import Protocol, Sequence, TypeVar

from scripts.sir_convert_a_lot.infrastructure.docling_ordering import OrderingQualityReport

DOCLING_ORDERING_LAYOUT_FALLBACK_WARNING = "docling_ordering_layout_fallback_applied"
DOCLING_ORDERING_QUALITY_UNRESOLVED_WARNING = "docling_ordering_quality_gate_unresolved"


class OrderingAttempt(Protocol):
    """Protocol for candidate attempts evaluated by ordering fallback policy."""

    @property
    def layout_model_key(self) -> str: ...

    @property
    def ordering_quality(self) -> OrderingQualityReport | None: ...

    @property
    def ordering_retry_applied(self) -> bool: ...


AttemptT = TypeVar("AttemptT", bound=OrderingAttempt)


def ordering_warnings_for_attempt(attempt: OrderingAttempt) -> list[str]:
    """Return deterministic warning set for the selected ordering attempt."""
    warnings: list[str] = []
    if attempt.ordering_retry_applied:
        warnings.append(DOCLING_ORDERING_LAYOUT_FALLBACK_WARNING)
    quality = attempt.ordering_quality
    if quality is not None and not quality.passes:
        warnings.append(DOCLING_ORDERING_QUALITY_UNRESOLVED_WARNING)
    return warnings


def select_best_ordering_attempt(attempts: Sequence[AttemptT]) -> AttemptT:
    """Select best attempt by stable ordering quality score."""
    if not attempts:
        raise ValueError("Ordering fallback selection received no candidates.")
    best_attempt = attempts[0]
    best_score = _ordering_score(best_attempt, attempt_index=0)
    for attempt_index, candidate in enumerate(attempts[1:], start=1):
        candidate_score = _ordering_score(candidate, attempt_index=attempt_index)
        if candidate_score < best_score:
            best_attempt = candidate
            best_score = candidate_score
    return best_attempt


def _ordering_score(
    attempt: OrderingAttempt,
    *,
    attempt_index: int,
) -> tuple[int, int, int, int, int, int, int]:
    quality = attempt.ordering_quality
    if quality is None:
        return (
            2,
            10**9,
            10**9,
            10**9,
            10**9,
            10**9,
            attempt_index,
        )
    return (
        0 if quality.passes else 1,
        quality.penalty,
        len(quality.missing_question_numbers),
        quality.trailing_number_signals,
        quality.standalone_number_signals,
        quality.option_before_question_signals,
        attempt_index,
    )
