"""Heartbeat helpers for conversion job execution (service API v2).

Purpose:
    Provide a small reusable heartbeat worker that updates running-job liveness
    markers while v2 conversion execution is in progress.

Relationships:
    - Used by `infrastructure.runtime_engine_v2` during async job execution.
    - Calls `infrastructure.job_store_v2.JobStoreV2.touch_heartbeat`.
"""

from __future__ import annotations

import threading

from scripts.sir_convert_a_lot.infrastructure.job_store_models_v2 import (
    JobExpiredV2,
    JobMissingV2,
)
from scripts.sir_convert_a_lot.infrastructure.job_store_v2 import JobStoreV2


def start_conversion_heartbeat_v2(
    *,
    job_store: JobStoreV2,
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
            except (JobMissingV2, JobExpiredV2):
                return
            if not updated:
                return

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    return stop_event, heartbeat_thread
