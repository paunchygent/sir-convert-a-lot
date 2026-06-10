"""CLI progress-message helpers for service API v2 conversions.

Purpose:
    Format throttled human-facing progress messages from v2 job payloads so
    long-running remote conversions expose live state without flooding output.

Relationships:
    - Used by `interfaces.cli_route_submission_v2` during service-backed
      conversion polling.
    - Consumes job payloads returned by `interfaces.http_client_v2`.
"""

from __future__ import annotations

import time
from collections.abc import Callable


def progress_callback_for_source_v2(
    *,
    relative_label: str,
    message_sink: Callable[[str], None],
) -> Callable[[dict[str, object]], None]:
    """Return a throttled progress callback for one CLI source label."""
    last_message: str | None = None
    last_emit_at = 0.0

    def _callback(payload: dict[str, object]) -> None:
        nonlocal last_message, last_emit_at
        message = format_running_progress_message_v2(
            relative_label=relative_label,
            payload=payload,
        )
        if message is None:
            return
        now = time.monotonic()
        if message != last_message or now - last_emit_at >= 30.0:
            message_sink(message)
            last_message = message
            last_emit_at = now

    return _callback


def format_running_progress_message_v2(
    *,
    relative_label: str,
    payload: dict[str, object],
) -> str | None:
    """Format one running progress payload or return None for non-running state."""
    job_obj = payload.get("job")
    if not isinstance(job_obj, dict):
        return None
    status = job_obj.get("status")
    if status != "running":
        return _format_submitted_progress_message_v2(
            relative_label=relative_label,
            job_obj=job_obj,
        )
    progress_obj = job_obj.get("progress")
    if not isinstance(progress_obj, dict):
        return _format_submitted_progress_message_v2(
            relative_label=relative_label,
            job_obj=job_obj,
        )

    job_id = job_obj.get("job_id")
    stage = progress_obj.get("stage")
    processed = progress_obj.get("processed_pages")
    total = progress_obj.get("total_pages")
    percent = progress_obj.get("percent_complete")
    eta = progress_obj.get("eta_seconds")

    parts = [f"... Running {relative_label}"]
    if isinstance(stage, str) and stage:
        parts.append(stage)
    if isinstance(processed, int) and isinstance(total, int) and total > 0:
        page_text = f"{processed}/{total} pages"
        if isinstance(percent, int | float) and not isinstance(percent, bool):
            page_text = f"{page_text} ({float(percent):.1f}%)"
        parts.append(page_text)
    if isinstance(eta, int) and not isinstance(eta, bool) and eta > 0:
        parts.append(f"eta {_format_duration_seconds_v2(eta)}")
    if isinstance(job_id, str):
        parts.append(job_id)
    return ", ".join(parts)


def _format_submitted_progress_message_v2(
    *,
    relative_label: str,
    job_obj: dict[object, object],
) -> str | None:
    job_id = job_obj.get("job_id")
    status = job_obj.get("status")
    if not isinstance(job_id, str) or not isinstance(status, str):
        return None
    if status not in {"queued", "running", "succeeded", "failed", "canceled"}:
        return None

    idempotent_replay = job_obj.get("idempotent_replay") is True
    verb = "Reusing existing job for" if idempotent_replay else "Submitted"
    return f"... {verb} {relative_label}: {job_id} ({status})"


def _format_duration_seconds_v2(seconds: int) -> str:
    minutes, remaining_seconds = divmod(max(0, seconds), 60)
    hours, remaining_minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h{remaining_minutes:02d}m"
    if remaining_minutes > 0:
        return f"{remaining_minutes}m{remaining_seconds:02d}s"
    return f"{remaining_seconds}s"
