"""Tests for Task 114 isolated Qwen preprocessing stage orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.run_task114_hemma_qwen_isolated_stages import (
    _build_parser,
    _resolve_stage_selector,
    main,
)
from scripts.sir_convert_a_lot.devops.task114_qwen_isolated_stages_runtime import (
    Task114DetachedStageLaunch,
    Task114DetachedStageStop,
    _load_optional_json,
    inspect_detached_stage,
    resolve_next_stage,
)


def test_task114_parser_launch_defaults() -> None:
    """The Task 114 runner should default to stage auto and detached launch."""
    parser = _build_parser()
    args = parser.parse_args(["launch"])

    assert args.task103_stage == "auto"
    assert args.task103_promote_on_success is False


def test_task114_parser_accepts_stop_command() -> None:
    """The Task 114 runner should expose a committed stop command."""
    parser = _build_parser()
    args = parser.parse_args(["stop"])

    assert args.command == "stop"


def test_resolve_next_stage_prefers_row_processing_when_spool_is_missing(tmp_path: Path) -> None:
    """A fresh run root should start with row-processing."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)

    assert resolve_next_stage(run_root=run_root) == "row-processing"


def test_resolve_next_stage_prefers_finalization_when_spool_exists_without_manifests(
    tmp_path: Path,
) -> None:
    """A run root with spool rows but no prepared manifests should resume at finalization."""
    spool_row = tmp_path / "run/spool/rows/rixvox/train/speaker/row.json"
    spool_row.parent.mkdir(parents=True, exist_ok=True)
    spool_row.write_text("{}", encoding="utf-8")

    assert resolve_next_stage(run_root=tmp_path / "run") == "finalization"


def test_resolve_next_stage_returns_none_when_report_exists(tmp_path: Path) -> None:
    """A run root with a final report should be considered complete."""
    run_root = tmp_path / "run"
    prepared_path = run_root / "manifests/swedish_smoke_train.prepared.jsonl"
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    prepared_path.write_text("{}", encoding="utf-8")
    (run_root / "report.json").write_text("{}", encoding="utf-8")

    assert resolve_next_stage(run_root=run_root) is None


def test_resolve_next_stage_prefers_reports_after_completed_finalization(tmp_path: Path) -> None:
    """A run root with completed finalization but no report should advance to reports."""
    run_root = tmp_path / "run"
    spool_row = run_root / "spool/rows/rixvox/train/speaker/row.json"
    prepared_path = run_root / "manifests/swedish_smoke_train.prepared.jsonl"
    spool_row.parent.mkdir(parents=True, exist_ok=True)
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    spool_row.write_text("{}", encoding="utf-8")
    prepared_path.write_text("{}", encoding="utf-8")
    (run_root / "status.json").write_text(
        json.dumps({"stage": "finalization", "status": "completed"}) + "\n",
        encoding="utf-8",
    )

    assert resolve_next_stage(run_root=run_root) == "reports"


def test_task114_stage_selector_auto_uses_existing_run_state(tmp_path: Path) -> None:
    """The runner should resolve auto stage selection from the preserved run root."""
    run_root = tmp_path / "run"
    spool_row = run_root / "spool/rows/rixvox/train/speaker/row.json"
    spool_row.parent.mkdir(parents=True, exist_ok=True)
    spool_row.write_text("{}", encoding="utf-8")

    assert _resolve_stage_selector("auto", run_root=run_root) == "finalization"


def test_inspect_detached_stage_reads_container_status_and_task103_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The detached Task 114 status view should combine Docker and Task 103 state."""
    run_root = tmp_path / "run"
    run_root.mkdir(parents=True, exist_ok=True)
    (run_root / "status.json").write_text(
        json.dumps({"stage": "finalization", "status": "running"}) + "\n",
        encoding="utf-8",
    )
    (run_root / "report.json").write_text(
        json.dumps({"prepared_rows": 52, "manifest_counts": {"swedish_smoke_train": 52}}) + "\n",
        encoding="utf-8",
    )
    launch = Task114DetachedStageLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="task114-finalization-20260309t120000z",
        stage="finalization",
        container_name="task114-finalization-20260309t120000z-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        task103_run_root=run_root.as_posix(),
        task103_promoted_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus",
        command=["sudo", "-n", "docker", "run", "-d"],
    )

    def _fake_docker_checked(args: list[str], *, label: str) -> str:
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Id": "container-id",
                        "State": {
                            "Status": "exited",
                            "Running": False,
                            "ExitCode": 0,
                            "OOMKilled": False,
                            "StartedAt": "2026-03-09T12:00:01Z",
                            "FinishedAt": "2026-03-09T12:04:01Z",
                        },
                    }
                ]
            )
        if args[0] == "logs":
            return "finalization log tail"
        raise AssertionError(f"Unexpected docker args: {args} ({label})")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task114_qwen_isolated_stages_runtime.docker_checked",
        _fake_docker_checked,
    )

    status = inspect_detached_stage(launch)

    assert status.running is False
    assert status.exit_code == 0
    assert status.task103_status_found is True
    assert status.task103_report_found is True
    assert status.task103_report is not None
    assert status.task103_report["prepared_rows"] == 52
    assert status.logs_tail == "finalization log tail"


def test_load_optional_json_uses_sudo_fallback_on_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unreadable Task 103 artifacts should still load through sudo fallback."""
    payload_path = tmp_path / "status.json"
    payload_path.write_text(json.dumps({"status": "running"}) + "\n", encoding="utf-8")

    original_read_text = Path.read_text

    def _fake_read_text(self: Path, encoding: str = "utf-8") -> str:
        if self == payload_path:
            raise PermissionError("permission denied")
        return original_read_text(self, encoding=encoding)

    def _fake_subprocess_checked(command: list[str], *, label: str) -> str:
        assert command == ["sudo", "-n", "cat", payload_path.as_posix()]
        assert label == "sudo cat task114 detached artifact"
        return json.dumps({"status": "running"})

    monkeypatch.setattr(Path, "read_text", _fake_read_text)
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task114_qwen_isolated_stages_runtime.subprocess_checked",
        _fake_subprocess_checked,
    )

    assert _load_optional_json(payload_path) == {"status": "running"}


def test_task114_stop_command_writes_stop_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Task 114 stop command should persist deterministic stop metadata."""
    output_root = tmp_path / "verification"
    launch_root = output_root / "task114-row-processing-20260309t120000z"
    launch_root.mkdir(parents=True, exist_ok=True)
    launch = Task114DetachedStageLaunch(
        generated_at="2026-03-09T12:00:00Z",
        launch_id="task114-row-processing-20260309t120000z",
        stage="row-processing",
        container_name="task114-row-processing-20260309t120000z-container",
        container_id="container-id",
        repo_root="/home/paunchygent/apps/sir-convert-a-lot",
        task103_run_root="/srv/scratch/sir-convert-a-lot/build/runs/qwen3-tts-swedish-preprocessing/run-id",
        task103_promoted_root="/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-corpus",
        command=["sudo", "-n", "docker", "run", "-d"],
    )
    (launch_root / "launch.json").write_text(
        json.dumps(
            {
                "generated_at": launch.generated_at,
                "launch_id": launch.launch_id,
                "stage": launch.stage,
                "container_name": launch.container_name,
                "container_id": launch.container_id,
                "repo_root": launch.repo_root,
                "task103_run_root": launch.task103_run_root,
                "task103_promoted_root": launch.task103_promoted_root,
                "command": launch.command,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def _fake_stop_detached_stage(payload: Task114DetachedStageLaunch) -> Task114DetachedStageStop:
        assert payload.launch_id == launch.launch_id
        return Task114DetachedStageStop(
            stopped_at="2026-03-09T12:05:00Z",
            launch_id=payload.launch_id,
            stage=payload.stage,
            container_name=payload.container_name,
            container_id=payload.container_id,
            stop_output=payload.container_name,
        )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.run_task114_hemma_qwen_isolated_stages.stop_detached_stage",
        _fake_stop_detached_stage,
    )

    exit_code = main(
        [
            "stop",
            "--output-root",
            output_root.as_posix(),
            "--launch-root",
            launch_root.as_posix(),
        ]
    )

    assert exit_code == 0
    stop_payload = json.loads((launch_root / "stop.json").read_text(encoding="utf-8"))
    assert stop_payload["launch_id"] == launch.launch_id
    assert stop_payload["container_name"] == launch.container_name
