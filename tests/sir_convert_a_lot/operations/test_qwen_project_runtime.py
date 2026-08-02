"""Tests for the isolated Qwen project command boundary.

Purpose:
    Prove root Qwen commands fail closed when the nested project environment is
    missing or stale and otherwise execute through the nested PDM project.

Relationships:
    - Covers `qwen_project_runtime.py`.
    - Protects the TASK-383 environment-ownership boundary.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.qwen_project_runtime import (
    _qwen_environment_matches_lock,
    run_qwen_project,
)


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


def _fresh_environment(_: Path) -> bool:
    return True


_LOCK_EXPORT_COMMAND = ("pdm", "export", "-p", "qwen", "-G", "dev", "--without-hashes")
_INSTALLED_LIST_COMMAND = (
    "pdm",
    "list",
    "-p",
    "qwen",
    "--json",
    "--fields",
    "name,version",
)
_MARKER_ENVIRONMENT_MODULE = "scripts.sir_convert_a_lot.devops.qwen_marker_environment"
_NESTED_MARKER_ENVIRONMENT = {
    "implementation_name": "cpython",
    "implementation_version": "3.13.1",
    "os_name": "posix",
    "platform_machine": "arm64",
    "platform_release": "24.6.0",
    "platform_system": "Darwin",
    "platform_version": "Darwin Kernel Version",
    "platform_python_implementation": "CPython",
    "python_full_version": "3.13.1",
    "python_version": "3.13",
    "sys_platform": "darwin",
}
_CLEAN_REQUIREMENTS = """
# Generated lock selection.
alpha==1.0
beta-extra==2.0; python_version >= \"0\"
skipped==9.0; python_version < \"0\"
"""
_CLEAN_INSTALLED = '[{"name": "Alpha", "version": "1.0"}, {"name": "beta_extra", "version": "2.0"}]'


def _marker_environment_command(project_root: Path) -> tuple[str, ...]:
    return (
        str(project_root / "qwen" / ".venv" / "bin" / "python"),
        "-m",
        _MARKER_ENVIRONMENT_MODULE,
    )


def _structured_runner(
    responses: dict[tuple[str, ...], subprocess.CompletedProcess[str]],
    observed_commands: list[tuple[str, ...]],
) -> Callable[[tuple[str, ...], Path], subprocess.CompletedProcess[str]]:
    def run_command(command: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
        observed_commands.append(command)
        return responses[command]

    return run_command


def _successful_structured_responses(
    project_root: Path,
) -> dict[tuple[str, ...], subprocess.CompletedProcess[str]]:
    marker_command = _marker_environment_command(project_root)
    return {
        marker_command: subprocess.CompletedProcess(
            marker_command,
            0,
            stdout=json.dumps(_NESTED_MARKER_ENVIRONMENT),
            stderr="",
        ),
        _LOCK_EXPORT_COMMAND: subprocess.CompletedProcess(
            _LOCK_EXPORT_COMMAND,
            0,
            stdout=_CLEAN_REQUIREMENTS,
            stderr="",
        ),
        _INSTALLED_LIST_COMMAND: subprocess.CompletedProcess(
            _INSTALLED_LIST_COMMAND,
            0,
            stdout=_CLEAN_INSTALLED,
            stderr="",
        ),
    }


def test_qwen_environment_freshness_uses_clean_structured_equality(
    tmp_path: Path,
) -> None:
    observed_commands: list[tuple[str, ...]] = []

    is_fresh = _qwen_environment_matches_lock(
        tmp_path,
        _structured_runner(_successful_structured_responses(tmp_path), observed_commands),
    )

    assert is_fresh is True
    assert observed_commands == [
        _marker_environment_command(tmp_path),
        _LOCK_EXPORT_COMMAND,
        _INSTALLED_LIST_COMMAND,
    ]


def test_qwen_environment_freshness_evaluates_markers_with_nested_interpreter(
    tmp_path: Path,
) -> None:
    observed_commands: list[tuple[str, ...]] = []
    requirements = """
root-branch==1.0; python_version == \"3.12\"
nested-branch==2.0; python_version == \"3.13\"
"""
    installed = '[{"name": "nested-branch", "version": "2.0"}]'
    responses = _successful_structured_responses(tmp_path)
    responses[_LOCK_EXPORT_COMMAND] = subprocess.CompletedProcess(
        _LOCK_EXPORT_COMMAND,
        0,
        stdout=requirements,
        stderr="",
    )
    responses[_INSTALLED_LIST_COMMAND] = subprocess.CompletedProcess(
        _INSTALLED_LIST_COMMAND,
        0,
        stdout=installed,
        stderr="",
    )

    is_fresh = _qwen_environment_matches_lock(
        tmp_path,
        _structured_runner(responses, observed_commands),
    )

    assert is_fresh is True
    assert observed_commands == [
        _marker_environment_command(tmp_path),
        _LOCK_EXPORT_COMMAND,
        _INSTALLED_LIST_COMMAND,
    ]


@pytest.mark.parametrize(
    "installed",
    (
        '[{"name": "Alpha", "version": "1.0"}]',
        (
            '[{"name": "Alpha", "version": "1.0"}, '
            '{"name": "beta-extra", "version": "2.0"}, '
            '{"name": "unexpected", "version": "3.0"}]'
        ),
        '[{"name": "Alpha", "version": "1.1"}, {"name": "beta-extra", "version": "2.0"}]',
    ),
    ids=("missing", "extra", "wrong-version"),
)
def test_qwen_environment_freshness_rejects_structured_distribution_drift(
    tmp_path: Path,
    installed: str,
) -> None:
    observed_commands: list[tuple[str, ...]] = []
    responses = _successful_structured_responses(tmp_path)
    responses[_INSTALLED_LIST_COMMAND] = subprocess.CompletedProcess(
        _INSTALLED_LIST_COMMAND,
        0,
        stdout=installed,
        stderr="",
    )

    is_fresh = _qwen_environment_matches_lock(
        tmp_path,
        _structured_runner(responses, observed_commands),
    )

    assert is_fresh is False
    assert observed_commands == [
        _marker_environment_command(tmp_path),
        _LOCK_EXPORT_COMMAND,
        _INSTALLED_LIST_COMMAND,
    ]


@pytest.mark.parametrize(
    "returncode,marker_environment",
    (
        (1, json.dumps(_NESTED_MARKER_ENVIRONMENT)),
        (0, "not-json"),
        (0, '{"python_version": "3.13"}'),
    ),
    ids=("command-failed", "malformed-json", "incomplete-schema"),
)
def test_qwen_environment_freshness_rejects_failed_or_malformed_marker_environment(
    tmp_path: Path,
    returncode: int,
    marker_environment: str,
) -> None:
    observed_commands: list[tuple[str, ...]] = []
    marker_command = _marker_environment_command(tmp_path)
    responses = _successful_structured_responses(tmp_path)
    responses[marker_command] = subprocess.CompletedProcess(
        marker_command,
        returncode,
        stdout=marker_environment,
        stderr="",
    )

    is_fresh = _qwen_environment_matches_lock(
        tmp_path,
        _structured_runner(responses, observed_commands),
    )

    assert is_fresh is False
    assert observed_commands == [marker_command]


@pytest.mark.parametrize(
    "export_returncode,requirements,list_returncode,installed,expects_list",
    (
        (1, _CLEAN_REQUIREMENTS, 0, _CLEAN_INSTALLED, False),
        (0, "alpha>=1.0\n", 0, _CLEAN_INSTALLED, False),
        (0, _CLEAN_REQUIREMENTS, 1, _CLEAN_INSTALLED, True),
        (0, _CLEAN_REQUIREMENTS, 0, "not-json", True),
        (0, _CLEAN_REQUIREMENTS, 0, '[{"name": "alpha"}]', True),
    ),
    ids=(
        "export-failed",
        "malformed-requirement",
        "list-failed",
        "malformed-json",
        "malformed-record",
    ),
)
def test_qwen_environment_freshness_rejects_failed_or_malformed_structured_data(
    tmp_path: Path,
    export_returncode: int,
    requirements: str,
    list_returncode: int,
    installed: str,
    expects_list: bool,
) -> None:
    observed_commands: list[tuple[str, ...]] = []
    responses = _successful_structured_responses(tmp_path)
    responses.update(
        {
            _LOCK_EXPORT_COMMAND: subprocess.CompletedProcess(
                _LOCK_EXPORT_COMMAND,
                export_returncode,
                stdout=requirements,
                stderr="",
            ),
            _INSTALLED_LIST_COMMAND: subprocess.CompletedProcess(
                _INSTALLED_LIST_COMMAND,
                list_returncode,
                stdout=installed,
                stderr="",
            ),
        }
    )

    is_fresh = _qwen_environment_matches_lock(
        tmp_path,
        _structured_runner(responses, observed_commands),
    )

    assert is_fresh is False
    expected_commands = [_marker_environment_command(tmp_path), _LOCK_EXPORT_COMMAND]
    if expects_list:
        expected_commands.append(_INSTALLED_LIST_COMMAND)
    assert observed_commands == expected_commands


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


def test_qwen_project_command_stops_before_dispatch_when_environment_drifted(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project_root = _seed_project(tmp_path)
    observed_commands: list[tuple[str, ...]] = []

    def stale_environment(_: Path) -> bool:
        return False

    exit_code = run_qwen_project(
        project_root,
        ("qwen-smoke",),
        _successful_recorder(observed_commands),
        stale_environment,
    )

    assert exit_code == 2
    assert observed_commands == [("pdm", "lock", "-p", "qwen", "--check")]
    assert "pdm install -p qwen -G dev" in capsys.readouterr().err


def test_qwen_project_command_checks_lock_then_dispatches_through_nested_pdm(
    tmp_path: Path,
) -> None:
    project_root = _seed_project(tmp_path)
    observed_commands: list[tuple[str, ...]] = []

    exit_code = run_qwen_project(
        project_root,
        ("qwen-smoke", "--help"),
        _successful_recorder(observed_commands),
        _fresh_environment,
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
