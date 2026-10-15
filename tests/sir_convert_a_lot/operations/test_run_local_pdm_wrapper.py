"""Exercise the real wrapper and PDM declaration with private dotenv fixtures."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WRAPPER_PATH = Path("scripts/devops/run-local-pdm.sh")


@pytest.fixture
def wrapper_project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "project with spaces"
    wrapper = root / WRAPPER_PATH
    wrapper.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / WRAPPER_PATH, wrapper)
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    declaration = project["tool"]["pdm"]["scripts"]["run-local-pdm"]
    (root / "pyproject.toml").write_text(
        '[project]\nname = "wrapper-fixture"\nversion = "0.0.0"\n'
        'requires-python = ">=3.12"\ndependencies = []\n'
        "[tool.pdm]\ndistribution = false\n[tool.pdm.scripts]\n"
        f"run-local-pdm.cmd = {json.dumps(declaration['cmd'])}\n"
        f"run-local-pdm.env_file.override = {json.dumps(declaration['env_file']['override'])}\n"
        'dump = "python dump.py"\n',
        encoding="utf-8",
    )
    (root / "dump.py").write_text(
        "import json, os, sys\n"
        "print(json.dumps({'value': os.getenv('WRAPPER_VALUE'), "
        "'quoted': os.getenv('WRAPPER_QUOTED'), 'literal': os.getenv('WRAPPER_LITERAL'), "
        "'override': os.getenv('WRAPPER_OVERRIDE'), 'argv': sys.argv[1:], "
        "'cwd': os.getcwd()}))\n"
        "sys.exit(int(os.getenv('WRAPPER_EXIT', '0')))\n",
        encoding="utf-8",
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PDM_", "WRAPPER_"))
        and key not in {"PYTHONPATH", "PEP582_PACKAGES", "VIRTUAL_ENV"}
    }
    env.update(
        PDM_PYTHON=sys.executable,
        PDM_IGNORE_ACTIVE_VENV="1",
        PDM_USE_VENV="0",
        PDM_CHECK_UPDATE="false",
        WRAPPER_OVERRIDE="process value",
    )
    return root, env


def _run(root: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["pdm", "run", "--project", str(root), "run-local-pdm", *args],
        cwd=root.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _payload(result: subprocess.CompletedProcess[str]) -> object:
    payload: object = json.loads(
        next(line for line in result.stdout.splitlines() if line.startswith("{"))
    )
    return payload


def test_dotenv_is_data_and_arguments_remain_literal(
    wrapper_project: tuple[Path, dict[str, str]],
) -> None:
    root, env = wrapper_project
    marker = root / "must-not-exist"
    literal = f"$(touch '{marker}')"
    (root / ".env").write_text(
        "WRAPPER_VALUE=alpha __not_a_shell_command__\n"
        'WRAPPER_QUOTED="double quoted value"\n'
        "WRAPPER_OVERRIDE='dotenv value'\n"
        f"WRAPPER_LITERAL={literal}\n",
        encoding="utf-8",
    )
    args = ["space arg", "semi;colon", "$HOME", "$(false)", "*", "", "single'quote", 'double"quote']
    result = _run(root, env, "dump", *args)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert not marker.exists()
    assert _payload(result) == {
        "value": "alpha __not_a_shell_command__",
        "quoted": "double quoted value",
        "literal": literal,
        "override": "dotenv value",
        "argv": args,
        "cwd": str(root),
    }


def test_absent_dotenv_preserves_process_environment_and_child_exit(
    wrapper_project: tuple[Path, dict[str, str]],
) -> None:
    root, env = wrapper_project
    env["WRAPPER_EXIT"] = "37"
    result = _run(root, env, "dump", "literal argument")
    assert result.returncode == 37, (result.stdout, result.stderr)
    assert _payload(result) == {
        "value": None,
        "quoted": None,
        "literal": None,
        "override": "process value",
        "argv": ["literal argument"],
        "cwd": str(root),
    }


def test_missing_command_reports_usage(wrapper_project: tuple[Path, dict[str, str]]) -> None:
    root, env = wrapper_project
    result = _run(root, env)
    assert result.returncode == 2
    assert "Usage: pdm run run-local-pdm <pdm-script> [args...]" in result.stderr
