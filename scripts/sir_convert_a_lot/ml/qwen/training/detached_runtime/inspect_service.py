"""Detached inspection service for Qwen training launches.

Purpose:
    Inspect detached Qwen containers, load run artifacts, and build truthful
    `DetachedStatus` payloads.

Relationships:
    - Consumes stale-artifact filtering from `artifact_freshness`.
    - Uses resource-monitor inspection to enrich detached status output.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import docker_checked
from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedLaunch, DetachedStatus
from scripts.sir_convert_a_lot.ml.qwen.training.monitoring import inspect_resource_monitor

from .artifact_freshness import (
    filter_stale_resumed_run_artifacts,
    load_optional_json,
    phase_history_from_status,
    utc_now_iso,
)


def inspect_detached_training(launch: DetachedLaunch) -> DetachedStatus:
    """Inspect one detached training container and its artifacts."""
    raw_inspect = docker_checked(
        ["inspect", launch.container_name],
        label="docker inspect qwen detached training",
    )
    payload = json.loads(raw_inspect)
    if not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict):
        raise SystemExit("Detached training inspect payload was malformed.")
    inspect_payload = payload[0]
    state = inspect_payload.get("State")
    if not isinstance(state, dict):
        raise SystemExit("Detached training inspect payload lacked a valid `State` object.")
    run_root = Path(launch.run_root)
    pilot_status = load_optional_json(run_root / "status.json")
    pilot_report = load_optional_json(run_root / "report.json")
    latest_checkpoint = load_optional_json(run_root / "latest_checkpoint.json")
    pilot_status, pilot_report = filter_stale_resumed_run_artifacts(
        launch,
        state=state,
        pilot_status=pilot_status,
        pilot_report=pilot_report,
    )
    phase_history = phase_history_from_status(pilot_status)
    logs_tail = docker_checked(
        ["logs", "--tail", "200", launch.container_name],
        label="docker logs qwen detached training",
    )
    monitor_summary = inspect_resource_monitor(
        launch.resource_monitor,
        phase_history=phase_history,
    )
    return DetachedStatus(
        checked_at=utc_now_iso(),
        launch_kind=launch.launch_kind,
        launch_id=launch.launch_id,
        container_name=launch.container_name,
        container_id=str(inspect_payload.get("Id", "")),
        status=str(state.get("Status", "")),
        running=bool(state.get("Running")),
        exit_code=int(state.get("ExitCode", 0)),
        oom_killed=bool(state.get("OOMKilled")),
        started_at=str(state.get("StartedAt", "")),
        finished_at=str(state.get("FinishedAt", "")),
        pilot_status_found=pilot_status is not None,
        pilot_status=pilot_status,
        pilot_report_found=pilot_report is not None,
        pilot_report=pilot_report,
        latest_checkpoint_found=latest_checkpoint is not None,
        latest_checkpoint=latest_checkpoint,
        resource_monitor=monitor_summary,
        logs_tail=logs_tail,
    )
