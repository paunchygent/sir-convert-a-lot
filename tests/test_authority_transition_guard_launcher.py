"""Contract tests for the Sir Convert-a-Lot shared guard adapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.docs_as_code import docs_validate


def _launcher() -> str:
    return str(
        Path.home()
        / ".codex/skill-repository/scripts/docs_as_code/run_authority_transition_guard.sh"
    )


def test_aggregate_validation_exercises_subprocess_boundary(monkeypatch, capsys) -> None:
    calls: list[tuple[list[str], Path, bool, bool, bool]] = []

    def fake_run(command, *, cwd, check, text, capture_output):
        command_list = list(command)
        calls.append((command_list, cwd, check, text, capture_output))
        if len(calls) == 3:
            return subprocess.CompletedProcess(command_list, 13, "guard-stdout\n", "guard-stderr\n")
        return subprocess.CompletedProcess(
            command_list, 0, "validator-stdout\n", "validator-stderr\n"
        )

    monkeypatch.setattr(docs_validate.subprocess, "run", fake_run)

    assert docs_validate._run_aggregate_validation() == 1
    assert calls[-1] == (
        [_launcher(), "--repo-root", str(docs_validate.ROOT)],
        docs_validate.ROOT,
        False,
        True,
        True,
    )
    captured = capsys.readouterr()
    assert "guard-stdout" in captured.out
    assert "guard-stderr" in captured.err
    assert all(call[1] == docs_validate.ROOT for call in calls)


def test_scoped_validation_forwards_paths_streams_and_exit(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    calls: list[tuple[list[str], Path, bool, bool, bool]] = []

    def fake_run(command, *, cwd, check, text, capture_output):
        command_list = list(command)
        calls.append((command_list, cwd, check, text, capture_output))
        return subprocess.CompletedProcess(command_list, 17, "scoped-stdout\n", "scoped-stderr\n")

    monkeypatch.setattr(docs_validate.subprocess, "run", fake_run)
    monkeypatch.setattr(docs_validate, "_validate_backlog_paths", lambda paths: 0)
    monkeypatch.setattr(docs_validate, "_validate_non_backlog_paths", lambda paths: 0)

    path = tmp_path / "docs" / "with space.md"
    path.parent.mkdir()
    path.write_text("---\ntype: task\n---\n", encoding="utf-8")
    result = docs_validate._run_scoped_validation([path])

    assert result == 1
    assert calls == [
        (
            [_launcher(), "--repo-root", str(docs_validate.ROOT), path.as_posix()],
            docs_validate.ROOT,
            False,
            True,
            True,
        )
    ]
    captured = capsys.readouterr()
    assert "scoped-stdout" in captured.out
    assert "scoped-stderr" in captured.err
