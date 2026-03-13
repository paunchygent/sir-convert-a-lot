"""Metadata and artifact helpers for the detached Task 101 pilot launcher.

Purpose:
    Centralize the path conventions, artifact writers, payload parsing,
    latest-pointer resolution, resume-checkpoint validation, and status
    markdown rendering used by the detached Task 101 Hemma pilot surface.

Relationships:
    - Imported by `run_task101_hemma_qwen_pilot.py`, which remains the CLI and
      launch/resume/stop orchestration entrypoint.
    - Reuses the dataclasses defined in `task101_qwen_pilot_runtime.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_runtime_contract import (
    Task101DetachedLaunch,
    Task101DetachedStatus,
    Task101PilotSettingsSnapshot,
)


def _launch_root(output_root: Path, launch_id: str) -> Path:
    """Return the canonical verification root for one launch."""
    return output_root / launch_id


def _launch_metadata_path(launch_root: Path) -> Path:
    """Return the launch metadata path for one detached pilot."""
    return launch_root / "launch.json"


def _status_metadata_path(launch_root: Path) -> Path:
    """Return the status metadata path for one detached pilot."""
    return launch_root / "status.json"


def _status_markdown_path(launch_root: Path) -> Path:
    """Return the markdown status path for one detached pilot."""
    return launch_root / "status.md"


def _latest_pointer_path(output_root: Path) -> Path:
    """Return the pointer file that records the latest pilot launch root."""
    return output_root / "latest-launch.json"


def _stop_metadata_path(launch_root: Path) -> Path:
    """Return the stop metadata path for one detached pilot."""
    return launch_root / "stop.json"


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_markdown(path: Path, markdown: str) -> None:
    """Write one deterministic markdown artifact."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _status_markdown(status: Task101DetachedStatus) -> str:
    """Render one concise markdown summary for the detached pilot."""
    lines = [
        "# Task 101 Detached Qwen Pilot Status",
        "",
        f"- checked_at: `{status.checked_at}`",
        f"- launch_id: `{status.launch_id}`",
        f"- container_name: `{status.container_name}`",
        f"- container_id: `{status.container_id}`",
        f"- status: `{status.status}`",
        f"- running: `{status.running}`",
        f"- exit_code: `{status.exit_code}`",
        f"- oom_killed: `{status.oom_killed}`",
        f"- started_at: `{status.started_at}`",
        f"- finished_at: `{status.finished_at}`",
        f"- pilot_status_found: `{status.pilot_status_found}`",
        f"- pilot_report_found: `{status.pilot_report_found}`",
        f"- latest_checkpoint_found: `{status.latest_checkpoint_found}`",
        "",
        "## Logs Tail",
        "",
        "```text",
        status.logs_tail,
        "```",
    ]
    if status.pilot_status is not None:
        lines.extend(
            [
                "",
                "## Pilot Status",
                "",
                "```json",
                json.dumps(status.pilot_status, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    if status.pilot_report is not None:
        lines.extend(
            [
                "",
                "## Pilot Report",
                "",
                "```json",
                json.dumps(status.pilot_report, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    if status.latest_checkpoint is not None:
        lines.extend(
            [
                "",
                "## Latest Checkpoint",
                "",
                "```json",
                json.dumps(status.latest_checkpoint, indent=2, ensure_ascii=False, sort_keys=True),
                "```",
            ]
        )
    return "\n".join(lines)


def _write_latest_pointer(output_root: Path, launch_root: Path) -> None:
    """Record the latest detached pilot launch root for status inspection."""
    _write_json(
        _latest_pointer_path(output_root),
        {"launch_root": launch_root.as_posix()},
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return list(value)


def _required_float(payload: dict[str, object], key: str) -> float:
    """Return one required float value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return float(value)


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer value from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return value


def _optional_int(payload: dict[str, object], key: str, *, default: int) -> int:
    """Return one optional integer value from a JSON payload with a fallback."""
    value = payload.get(key)
    if value is None:
        return default
    if not isinstance(value, int):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return value


def _optional_str(payload: dict[str, object], key: str) -> str | None:
    """Return one optional string value from a JSON payload."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SystemExit(f"Detached Task 101 metadata returned malformed `{key}`.")
    return value


def _load_launch(
    launch_root: Path,
    *,
    default_durable_checkpoint_retention: int,
    default_durable_checkpoint_min_free_bytes: int,
) -> Task101DetachedLaunch:
    """Load one previously recorded detached pilot launch payload."""
    payload = json.loads(_launch_metadata_path(launch_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Detached Task 101 launch metadata was malformed.")
    settings_payload = payload.get("settings")
    if not isinstance(settings_payload, dict):
        raise SystemExit("Detached Task 101 launch metadata lacked a valid `settings` object.")
    settings_snapshot = Task101PilotSettingsSnapshot(
        output_root=_required_str(settings_payload, "output_root"),
        image=_required_str(settings_payload, "image"),
        hf_cache_dir=_required_str(settings_payload, "hf_cache_dir"),
        hf_cache_home_mount=_required_str(settings_payload, "hf_cache_home_mount"),
        scratch_build_root=_required_str(settings_payload, "scratch_build_root"),
        scratch_build_home_mount=_required_str(settings_payload, "scratch_build_home_mount"),
        pilot_bundle_root=_required_str(settings_payload, "pilot_bundle_root"),
        runs_root=_required_str(settings_payload, "runs_root"),
        model_id=_required_str(settings_payload, "model_id"),
        train_manifest_family=_required_str(settings_payload, "train_manifest_family"),
        eval_manifest_family=_required_str(settings_payload, "eval_manifest_family"),
        batch_size=_required_int(settings_payload, "batch_size"),
        lr=_required_float(settings_payload, "lr"),
        num_epochs=_required_int(settings_payload, "num_epochs"),
        max_steps=_required_int(settings_payload, "max_steps"),
        checkpoint_interval_steps=_required_int(settings_payload, "checkpoint_interval_steps"),
        durable_checkpoint_retention=_optional_int(
            settings_payload,
            "durable_checkpoint_retention",
            default=default_durable_checkpoint_retention,
        ),
        durable_checkpoint_min_free_bytes=_optional_int(
            settings_payload,
            "durable_checkpoint_min_free_bytes",
            default=default_durable_checkpoint_min_free_bytes,
        ),
    )
    return Task101DetachedLaunch(
        generated_at=_required_str(payload, "generated_at"),
        launch_id=_required_str(payload, "launch_id"),
        container_name=_required_str(payload, "container_name"),
        container_id=_required_str(payload, "container_id"),
        repo_root=_required_str(payload, "repo_root"),
        run_root=_required_str(payload, "run_root"),
        pilot_bundle_root=_required_str(payload, "pilot_bundle_root"),
        train_jsonl=_required_str(payload, "train_jsonl"),
        eval_jsonl=_required_str(payload, "eval_jsonl"),
        train_manifest_family=_required_str(payload, "train_manifest_family"),
        eval_manifest_family=_required_str(payload, "eval_manifest_family"),
        dockerfile_path=_optional_str(payload, "dockerfile_path"),
        resumed_from_checkpoint_path=_optional_str(payload, "resumed_from_checkpoint_path"),
        settings=settings_snapshot,
        command=_required_str_list(payload, "command"),
    )


def _load_latest_checkpoint(run_root: Path) -> Path:
    """Resolve the latest durable checkpoint pointer for one Task 101 run root."""
    pointer_path = run_root / "latest_checkpoint.json"
    if not pointer_path.exists():
        raise SystemExit(
            "Task 101 resume latest requires a run-root `latest_checkpoint.json` pointer."
        )
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Task 101 latest-checkpoint metadata was malformed.")
    return Path(_required_str(payload, "checkpoint_path"))


def _validate_resume_checkpoint_path(run_root: Path, checkpoint_path: Path) -> Path:
    """Reject explicit resume checkpoints that do not belong to the source run root."""
    resolved_run_root = run_root.resolve()
    resolved_checkpoint_path = checkpoint_path.resolve()
    if not resolved_checkpoint_path.exists():
        raise SystemExit(
            f"Task 101 resume checkpoint `{resolved_checkpoint_path.as_posix()}` does not exist."
        )
    try:
        resolved_checkpoint_path.relative_to(resolved_run_root)
    except ValueError as exc:
        raise SystemExit(
            "Task 101 resume --checkpoint-path must belong to the selected source launch run root."
        ) from exc
    return resolved_checkpoint_path


def _resolve_launch_root(output_root: Path, launch_root: Path | None) -> Path:
    """Resolve the launch root for status inspection."""
    if launch_root is not None:
        return launch_root
    pointer_path = _latest_pointer_path(output_root)
    if not pointer_path.exists():
        raise SystemExit(
            "Task 101 status requires `--launch-root` until a launch has recorded "
            "the latest detached pilot pointer."
        )
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Task 101 latest-launch metadata was malformed.")
    return Path(_required_str(payload, "launch_root"))
