"""Durable daily token leases for answer-key provider attempts.

The ledger owns the local, fail-closed accounting boundary between answer-key
orchestration and remote providers.  A separate lock inode is held for every
UTC day so atomic replacement of a day ledger never weakens mutual exclusion.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TextIO

from scripts.sir_convert_a_lot.domain.answer_key_token_lease_contracts import (
    AnswerKeyTokenLeaseError,
    AnswerKeyTokenLeaseFailureCode,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_token_lease_state import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseSnapshot,
    AnswerKeyTokenLeaseState,
    empty_lease_snapshot,
    lease_snapshot_from_payload,
    lease_snapshot_to_payload,
    snapshot_with_records,
)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class FilesystemAnswerKeyTokenLeaseLedger:
    """Reserve, send, and reconcile answer-key tokens through daily JSON ledgers."""

    def __init__(
        self,
        *,
        ledger_directory: Path,
        daily_token_limit: int,
        utc_clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if daily_token_limit <= 0:
            raise ValueError("daily_token_limit must be positive.")
        self._ledger_directory = ledger_directory
        self._daily_token_limit = daily_token_limit
        self._utc_clock = utc_clock

    def reserve(
        self,
        *,
        estimated_input_tokens: int,
        max_output_tokens: int,
    ) -> AnswerKeyTokenLease:
        """Reserve a request's full input/output allowance before provider I/O."""

        if estimated_input_tokens < 0:
            raise ValueError("estimated_input_tokens cannot be negative.")
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive.")
        requested_tokens = estimated_input_tokens + max_output_tokens
        utc_day = self._current_utc_day()
        lock_file, snapshot = self._open_locked_snapshot(
            utc_day=utc_day,
            requested_tokens=requested_tokens,
            allow_missing=True,
        )
        try:
            if snapshot.available_tokens < requested_tokens:
                raise AnswerKeyTokenLeaseError(
                    failure_code=AnswerKeyTokenLeaseFailureCode.DAILY_TOKEN_LEASE_EXHAUSTED,
                    message="Answer-key daily token lease is exhausted until the next UTC day.",
                    utc_day=utc_day,
                    requested_tokens=requested_tokens,
                    available_tokens=snapshot.available_tokens,
                )
            lease = AnswerKeyTokenLease(
                lease_id=str(uuid.uuid4()),
                utc_day=utc_day,
                reserved_tokens=requested_tokens,
                state=AnswerKeyTokenLeaseState.RESERVED,
            )
            records = {record.lease_id: record for record in snapshot.leases}
            records[lease.lease_id] = lease
            self._write_snapshot(
                snapshot_with_records(snapshot=snapshot, records=records),
                requested_tokens=requested_tokens,
            )
            return lease
        finally:
            self._unlock(lock_file=lock_file, utc_day=utc_day, requested_tokens=requested_tokens)

    def mark_sent(self, *, lease: AnswerKeyTokenLease) -> None:
        """Record that a reserved provider attempt may have consumed tokens."""

        self._transition(lease=lease, target_state=AnswerKeyTokenLeaseState.SENT)

    def reconcile(self, *, lease: AnswerKeyTokenLease, actual_tokens: int) -> None:
        """Replace a sent lease's uncertainty with provider-reported token usage."""

        if actual_tokens < 0:
            raise ValueError("actual_tokens cannot be negative.")
        self._transition(
            lease=lease,
            target_state=AnswerKeyTokenLeaseState.RECONCILED,
            actual_tokens=actual_tokens,
        )

    def _transition(
        self,
        *,
        lease: AnswerKeyTokenLease,
        target_state: AnswerKeyTokenLeaseState,
        actual_tokens: int | None = None,
    ) -> None:
        lock_file, snapshot = self._open_locked_snapshot(
            utc_day=lease.utc_day,
            requested_tokens=lease.reserved_tokens,
            allow_missing=False,
        )
        try:
            records = {record.lease_id: record for record in snapshot.leases}
            record = _require_matching_lease(
                lease=lease,
                records=records,
                expected_state={
                    AnswerKeyTokenLeaseState.SENT: AnswerKeyTokenLeaseState.RESERVED,
                    AnswerKeyTokenLeaseState.RECONCILED: AnswerKeyTokenLeaseState.SENT,
                }.get(target_state),
            )
            records[lease.lease_id] = replace(
                record,
                state=target_state,
                actual_tokens=actual_tokens,
            )
            self._write_snapshot(
                snapshot_with_records(snapshot=snapshot, records=records),
                requested_tokens=lease.reserved_tokens,
            )
        finally:
            self._unlock(
                lock_file=lock_file,
                utc_day=lease.utc_day,
                requested_tokens=lease.reserved_tokens,
            )

    def snapshot(self) -> AnswerKeyTokenLeaseSnapshot:
        """Read the current UTC-day ledger without creating an empty ledger file."""

        utc_day = self._current_utc_day()
        lock_file, snapshot = self._open_locked_snapshot(
            utc_day=utc_day,
            requested_tokens=0,
            allow_missing=True,
        )
        try:
            return snapshot
        finally:
            self._unlock(lock_file=lock_file, utc_day=utc_day, requested_tokens=0)

    def _current_utc_day(self) -> str:
        timestamp = self._utc_clock()
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("utc_clock must return a timezone-aware datetime.")
        return timestamp.astimezone(UTC).date().isoformat()

    def _open_locked_snapshot(
        self,
        *,
        utc_day: str,
        requested_tokens: int,
        allow_missing: bool,
    ) -> tuple[TextIO, AnswerKeyTokenLeaseSnapshot]:
        lock_file: TextIO | None = None
        try:
            self._ledger_directory.mkdir(parents=True, exist_ok=True)
            lock_file = self._day_path(utc_day=utc_day, suffix="lock").open(
                "a+",
                encoding="utf-8",
            )
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            return lock_file, self._read_snapshot(utc_day=utc_day, allow_missing=allow_missing)
        except AnswerKeyTokenLeaseError:
            if lock_file is not None:
                self._unlock(
                    lock_file=lock_file,
                    utc_day=utc_day,
                    requested_tokens=requested_tokens,
                )
            raise
        except OSError as exc:
            if lock_file is not None:
                self._unlock(
                    lock_file=lock_file,
                    utc_day=utc_day,
                    requested_tokens=requested_tokens,
                )
            raise _ledger_unavailable_error(
                utc_day=utc_day,
                requested_tokens=requested_tokens,
            ) from exc

    def _unlock(self, *, lock_file: TextIO, utc_day: str, requested_tokens: int) -> None:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
        except OSError as exc:
            raise _ledger_unavailable_error(
                utc_day=utc_day,
                requested_tokens=requested_tokens,
            ) from exc

    def _read_snapshot(
        self,
        *,
        utc_day: str,
        allow_missing: bool,
    ) -> AnswerKeyTokenLeaseSnapshot:
        ledger_path = self._day_path(utc_day=utc_day, suffix="json")
        if not ledger_path.exists():
            if allow_missing:
                return empty_lease_snapshot(
                    utc_day=utc_day,
                    daily_token_limit=self._daily_token_limit,
                )
            raise ValueError("expected lease ledger is unavailable.")
        try:
            payload = json.loads(ledger_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("lease ledger root must be an object.")
            return lease_snapshot_from_payload(
                payload=payload,
                expected_utc_day=utc_day,
                expected_daily_token_limit=self._daily_token_limit,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise _ledger_unavailable_error(
                utc_day=utc_day,
                requested_tokens=0,
            ) from exc

    def _write_snapshot(
        self,
        snapshot: AnswerKeyTokenLeaseSnapshot,
        requested_tokens: int,
    ) -> None:
        ledger_path = self._day_path(utc_day=snapshot.utc_day, suffix="json")
        temporary_path: Path | None = None
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                dir=self._ledger_directory,
                prefix=f".{ledger_path.name}.",
                suffix=".tmp",
                text=True,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
                json.dump(lease_snapshot_to_payload(snapshot), temporary_file, sort_keys=True)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, ledger_path)
            directory_descriptor = os.open(self._ledger_directory, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        except OSError as exc:
            raise _ledger_unavailable_error(
                utc_day=snapshot.utc_day,
                requested_tokens=requested_tokens,
            ) from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError as exc:
                    raise _ledger_unavailable_error(
                        utc_day=snapshot.utc_day,
                        requested_tokens=requested_tokens,
                    ) from exc

    def _day_path(self, *, utc_day: str, suffix: str) -> Path:
        return self._ledger_directory / f"answer-key-token-lease-{utc_day}.{suffix}"


def _require_matching_lease(
    *,
    lease: AnswerKeyTokenLease,
    records: dict[str, AnswerKeyTokenLease],
    expected_state: AnswerKeyTokenLeaseState | None,
) -> AnswerKeyTokenLease:
    record = records.get(lease.lease_id)
    if record is None or (
        record.lease_id,
        record.utc_day,
        record.reserved_tokens,
    ) != (
        lease.lease_id,
        lease.utc_day,
        lease.reserved_tokens,
    ):
        raise ValueError("lease does not match the persisted daily ledger.")
    if expected_state is None or record.state != expected_state:
        raise ValueError("lease does not match the required accounting state.")
    return record


def _ledger_unavailable_error(
    *,
    utc_day: str,
    requested_tokens: int,
) -> AnswerKeyTokenLeaseError:
    return AnswerKeyTokenLeaseError(
        failure_code=AnswerKeyTokenLeaseFailureCode.TOKEN_LEASE_LEDGER_UNAVAILABLE,
        message="Answer-key token lease ledger is unavailable; retry after storage is restored.",
        utc_day=utc_day,
        requested_tokens=requested_tokens,
        available_tokens=0,
    )
