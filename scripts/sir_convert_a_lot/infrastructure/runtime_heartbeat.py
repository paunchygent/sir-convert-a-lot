"""Heartbeat helpers for conversion job execution.

Purpose:
    Provide a small reusable heartbeat worker that updates running-job liveness
    markers while conversion execution is in progress.

Relationships:
    - Used by `infrastructure.runtime_engine` during async job execution.
    - Calls `infrastructure.job_store.JobStore.touch_heartbeat`.
"""

from __future__ import annotations

import threading

from scripts.sir_convert_a_lot.infrastructure.job_store import JobExpired, JobMissing, JobStore


def start_conversion_heartbeat(
    *,
    job_store: JobStore,
    job_id: str,
    heartbeat_interval_seconds: float,
) -> tuple[threading.Event, threading.Thread]:
    """Start a background heartbeat thread and return stop event + thread."""
    stop_event = threading.Event()

    def _heartbeat_loop() -> None:
        interval = max(0.01, heartbeat_interval_seconds)
        while not stop_event.wait(interval):
            try:
                updated = job_store.touch_heartbeat(job_id)
            except (JobMissing, JobExpired):
                return
            if not updated:
                return

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    return stop_event, heartbeat_thread
