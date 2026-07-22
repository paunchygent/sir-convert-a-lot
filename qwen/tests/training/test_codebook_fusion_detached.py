"""Tests for the detached Qwen codebook-fusion proof codebook-fusion proof surface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.sir_convert_a_lot.cli.ml.qwen_codebook_fusion_proof_detached import (
    main as detached_cli_main,
)
from scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_detached import (
    DetachedCodebookFusionLaunch,
    DetachedCodebookFusionStatus,
    build_detached_worker_command,
    inspect_detached_codebook_fusion_proof,
    launch_detached_codebook_fusion_proof,
    normalize_proof_args,
)


def test_normalize_proof_args_injects_output_root_and_strips_separator(tmp_path: Path) -> None:
    """Detached proof args should always resolve to one explicit output root."""
    proof_args = normalize_proof_args(tmp_path, ["--", "--skip-build", "--dtypes", "bf16"])

    assert proof_args == (
        "--output-root",
        tmp_path.as_posix(),
        "--skip-build",
        "--dtypes",
        "bf16",
    )


def test_build_detached_worker_command_uses_committed_worker(tmp_path: Path) -> None:
    """The detached surface should launch the committed background worker module."""
    command = build_detached_worker_command(tmp_path, ["--skip-build"])

    assert command[1:4] == [
        "-m",
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_detached_worker",
        "--output-root",
    ]
    assert command[4] == tmp_path.as_posix()
    assert command[5] == "--"
    assert "--skip-build" in command


def test_launch_detached_codebook_fusion_proof_records_background_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Launching the detached proof should record the normalized worker command."""

    class _FakeProcess:
        """Minimal detached worker process stub for launch tests."""

        pid = 4321

    captured: dict[str, object] = {}

    def fake_popen(
        args: list[str],
        *,
        cwd: Path,
        stdout: object,
        stderr: int,
        text: bool,
        start_new_session: bool,
    ) -> _FakeProcess:
        captured["args"] = list(args)
        captured["cwd"] = cwd
        captured["stderr"] = stderr
        captured["text"] = text
        captured["start_new_session"] = start_new_session
        assert stdout is not None
        return _FakeProcess()

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_detached.subprocess.Popen",
        fake_popen,
    )

    launch = launch_detached_codebook_fusion_proof(
        output_root=tmp_path,
        repo_root=Path("/repo/root"),
        proof_args=["--", "--skip-build", "--benchmark-iterations", "7"],
        launch_id="codebook-fusion-test",
    )

    assert launch.launch_id == "codebook-fusion-test"
    assert launch.pid == 4321
    assert captured["cwd"] == Path("/repo/root")
    assert captured["start_new_session"] is True
    assert captured["stderr"] == -2
    assert captured["text"] is True
    command = captured["args"]
    assert isinstance(command, list)
    assert "--skip-build" in command
    assert "--benchmark-iterations" in command
    assert launch.proof_args[0:2] == ["--output-root", tmp_path.as_posix()]


def test_inspect_detached_codebook_fusion_proof_reads_worker_and_report_artifacts(
    tmp_path: Path,
) -> None:
    """Detached status inspection should project the worker/report artifacts."""
    launch = DetachedCodebookFusionLaunch(
        generated_at="2026-03-16T20:00:00Z",
        launch_id="codebook-fusion-test",
        pid=4321,
        repo_root="/repo/root",
        output_root=tmp_path.as_posix(),
        log_path=(tmp_path / "proof.log").as_posix(),
        worker_status_path=(tmp_path / "worker-status.json").as_posix(),
        report_path=(tmp_path / "report.json").as_posix(),
        failure_path=(tmp_path / "failure.txt").as_posix(),
        proof_args=["--output-root", tmp_path.as_posix(), "--skip-build"],
        command=["python", "-m", "worker"],
    )
    (tmp_path / "proof.log").write_text("line one\nline two\n", encoding="utf-8")
    (tmp_path / "report.json").write_text(
        json.dumps({"device_name": "AMD Radeon", "dtype_summaries": []}),
        encoding="utf-8",
    )
    (tmp_path / "worker-status.json").write_text(
        json.dumps({"finished_at": "2026-03-16T20:05:00Z", "exit_code": 0}),
        encoding="utf-8",
    )

    status = inspect_detached_codebook_fusion_proof(launch)

    assert status.running is False
    assert status.exit_code == 0
    assert status.finished_at == "2026-03-16T20:05:00Z"
    assert status.report_found is True
    assert status.failure_found is False
    assert status.report == {"device_name": "AMD Radeon", "dtype_summaries": []}
    assert status.logs_tail == "line one\nline two"


def test_detached_cli_writes_launch_and_status_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The detached CLI should persist launch and status artifacts deterministically."""
    launch = DetachedCodebookFusionLaunch(
        generated_at="2026-03-16T20:00:00Z",
        launch_id="codebook-fusion-test",
        pid=4321,
        repo_root="/repo/root",
        output_root=tmp_path.as_posix(),
        log_path=(tmp_path / "proof.log").as_posix(),
        worker_status_path=(tmp_path / "worker-status.json").as_posix(),
        report_path=(tmp_path / "report.json").as_posix(),
        failure_path=(tmp_path / "failure.txt").as_posix(),
        proof_args=["--output-root", tmp_path.as_posix(), "--skip-build"],
        command=["python", "-m", "worker"],
    )
    status = DetachedCodebookFusionStatus(
        checked_at="2026-03-16T20:06:00Z",
        launch_id="codebook-fusion-test",
        pid=4321,
        running=False,
        exit_code=0,
        started_at="2026-03-16T20:00:00Z",
        finished_at="2026-03-16T20:05:00Z",
        report_found=True,
        failure_found=False,
        report={"device_name": "AMD Radeon"},
        failure_text=None,
        logs_tail="tail line",
    )

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_codebook_fusion_proof_detached.launch_detached_codebook_fusion_proof",
        lambda *, output_root, repo_root, proof_args, launch_id: launch,
    )
    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.cli.ml.qwen_codebook_fusion_proof_detached.inspect_detached_codebook_fusion_proof",
        lambda loaded_launch: status,
    )

    launch_result = detached_cli_main(
        ["launch", "--output-root", tmp_path.as_posix(), "--", "--skip-build"]
    )
    status_result = detached_cli_main(["status", "--output-root", tmp_path.as_posix()])
    capsys.readouterr()

    assert launch_result == 0
    assert status_result == 0
    launch_payload = json.loads((tmp_path / "launch.json").read_text(encoding="utf-8"))
    status_payload = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert launch_payload["pid"] == 4321
    assert status_payload["exit_code"] == 0
    assert (tmp_path / "status.md").exists() is True
