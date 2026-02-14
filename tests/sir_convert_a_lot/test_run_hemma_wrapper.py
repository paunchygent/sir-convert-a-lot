"""Wrapper tests for deterministic remote execution via `run-hemma.sh`.

Purpose:
    Ensure the Hemma wrapper validates remote repo context and executes commands
    in a deterministic shell mode independent of user shell startup behavior.

Relationships:
    - Exercises `scripts/devops/run-hemma.sh`.
    - Protects command-wrapper guarantees referenced in AGENTS and runbooks.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_HEMMA_SCRIPT = REPO_ROOT / "scripts" / "devops" / "run-hemma.sh"


def _write_fake_ssh(script_dir: Path) -> None:
    fake_ssh = script_dir / "ssh"
    fake_ssh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 5 ]]; then
  echo "fake-ssh: unexpected invocation: $*" >&2
  exit 96
fi

host="$1"
shift
if [[ "$1" != "/bin/bash" || "$2" != "--noprofile" || "$3" != "--norc" || "$4" != "-s" ]]; then
  echo "fake-ssh: unexpected shell invocation: $*" >&2
  exit 97
fi
if [[ -z "${host}" ]]; then
  echo "fake-ssh: missing host" >&2
  exit 98
fi

decoded_cmd="$(cat)"
/bin/bash --noprofile --norc -s <<<"${decoded_cmd}"
""",
        encoding="utf-8",
    )
    fake_ssh.chmod(fake_ssh.stat().st_mode | stat.S_IXUSR)


def _run_wrapper(args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(RUN_HEMMA_SCRIPT), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )


def test_run_hemma_requires_arguments() -> None:
    result = subprocess.run(
        ["bash", str(RUN_HEMMA_SCRIPT)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "Usage:" in result.stderr


def test_run_hemma_executes_command_inside_remote_root(tmp_path: Path) -> None:
    remote_root = tmp_path / "remote-repo"
    remote_root.mkdir(parents=True)
    (remote_root / ".git").mkdir()

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_ssh(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["SIR_CONVERT_A_LOT_HEMMA_HOST"] = "fake-host"
    env["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(remote_root)

    result = _run_wrapper(["--", "pwd"], env)

    assert result.returncode == 0
    assert result.stdout.strip() == str(remote_root)


def test_run_hemma_fails_if_remote_root_is_missing(tmp_path: Path) -> None:
    remote_root = tmp_path / "missing-repo"

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_ssh(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["SIR_CONVERT_A_LOT_HEMMA_HOST"] = "fake-host"
    env["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(remote_root)

    result = _run_wrapper(["--", "pwd"], env)

    assert result.returncode == 66
    assert "remote root not found" in result.stderr


def test_run_hemma_fails_if_remote_root_is_not_git_repo(tmp_path: Path) -> None:
    remote_root = tmp_path / "remote-not-repo"
    remote_root.mkdir(parents=True)

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_ssh(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["SIR_CONVERT_A_LOT_HEMMA_HOST"] = "fake-host"
    env["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(remote_root)

    result = _run_wrapper(["--", "pwd"], env)

    assert result.returncode == 67
    assert "remote root is not a git repository" in result.stderr


def test_run_hemma_preserves_literal_argument_boundaries(tmp_path: Path) -> None:
    remote_root = tmp_path / "remote-repo"
    remote_root.mkdir(parents=True)
    (remote_root / ".git").mkdir()

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_ssh(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["SIR_CONVERT_A_LOT_HEMMA_HOST"] = "fake-host"
    env["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(remote_root)

    literal_value = "alpha beta;gamma"
    result = _run_wrapper(["--", "printf", "%s", literal_value], env)

    assert result.returncode == 0
    assert result.stdout == literal_value


def test_run_hemma_shell_mode_uses_same_deterministic_root(tmp_path: Path) -> None:
    remote_root = tmp_path / "remote-repo"
    remote_root.mkdir(parents=True)
    (remote_root / ".git").mkdir()

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_ssh(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["SIR_CONVERT_A_LOT_HEMMA_HOST"] = "fake-host"
    env["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(remote_root)

    result = _run_wrapper(["--shell", "pwd"], env)

    assert result.returncode == 0
    assert result.stdout.strip() == str(remote_root)


def test_run_hemma_shell_mode_executes_operator_chain(tmp_path: Path) -> None:
    remote_root = tmp_path / "remote-repo"
    remote_root.mkdir(parents=True)
    (remote_root / ".git").mkdir()

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    _write_fake_ssh(fake_bin)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["SIR_CONVERT_A_LOT_HEMMA_HOST"] = "fake-host"
    env["SIR_CONVERT_A_LOT_HEMMA_ROOT"] = str(remote_root)

    result = _run_wrapper(["--shell", "pwd; printf '|ok|'"], env)

    assert result.returncode == 0
    assert result.stdout.startswith(f"{remote_root}\n")
    assert result.stdout.rstrip().endswith("|ok|")
