"""Tests for the isolated Qwen project command boundary.

Purpose:
    Prove root Qwen commands fail closed when the nested project environment is
    missing or stale and otherwise execute through the nested PDM project.

Relationships:
    - Covers `qwen_project_runtime.py`.
    - Protects the TASK-383 environment-ownership boundary.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.qwen_project_runtime import run_qwen_project


def _seed_project(tmp_path: Path, *, include_environment: bool = True) -> Path:
    project_root = tmp_path / "repo"
    qwen_root = project_root / "qwen"
    qwen_root.mkdir(parents=True)
    (qwen_root / "pyproject.toml").write_text("[project]\nname = 'qwen'\n", encoding="utf-8")
    (qwen_root / "pdm.lock").write_text("[metadata]\nlock_version = '4.5'\n", encoding="utf-8")
    if include_environment:
        interpreter = qwen_root / ".venv" / "bin" / "python"
        interpreter.parent.mkdir(parents=True)
        interpreter.write_text("", encoding="utf-8")
    return project_root


def _successful_recorder(
    observed_commands: list[tuple[str, ...]],
) -> Callable[[tuple[str, ...], Path], int]:
    def run_command(command: tuple[str, ...], cwd: Path) -> int:
        observed_commands.append(command)
        return 0

    return run_command


def test_qwen_project_command_fails_closed_without_nested_environment(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = _seed_project(tmp_path, include_environment=False)
    observed_commands: list[tuple[str, ...]] = []

    exit_code = run_qwen_project(
        project_root,
        ("qwen-smoke", "--help"),
        _successful_recorder(observed_commands),
    )

    assert exit_code == 2
    assert observed_commands == []
    assert "nested Qwen environment is missing" in capsys.readouterr().err


def test_qwen_project_command_checks_lock_then_dispatches_through_nested_pdm(
    tmp_path: Path,
) -> None:
    project_root = _seed_project(tmp_path)
    observed_commands: list[tuple[str, ...]] = []

    exit_code = run_qwen_project(
        project_root,
        ("qwen-smoke", "--help"),
        _successful_recorder(observed_commands),
    )

    assert exit_code == 0
    assert observed_commands == [
        ("pdm", "lock", "-p", "qwen", "--check"),
        ("pdm", "run", "-p", "qwen", "qwen-smoke", "--help"),
    ]


def test_qwen_project_command_stops_when_nested_lock_is_stale(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = _seed_project(tmp_path)
    observed_commands: list[tuple[str, ...]] = []

    def run_command(command: tuple[str, ...], cwd: Path) -> int:
        observed_commands.append(command)
        return 1

    exit_code = run_qwen_project(project_root, ("qwen-smoke",), run_command)

    assert exit_code == 2
    assert observed_commands == [("pdm", "lock", "-p", "qwen", "--check")]
    assert "nested Qwen lock is stale" in capsys.readouterr().err
