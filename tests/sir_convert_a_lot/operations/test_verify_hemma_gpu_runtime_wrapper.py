"""Tests for the Hemma GPU verifier shell wrapper.

Purpose:
    Prove the operator-facing GPU verifier delegates remote execution through
    `run-hemma` and resolves the Sir Convert API key through `agent-secrets`
    on Hemma instead of reading or forwarding a local secret.

Relationships:
    - Exercises `scripts/devops/verify-hemma-gpu-runtime.sh`.
    - Complements Hemma deploy verification verifier contract tests by protecting the local
      wrapper-to-Hemma command boundary.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFY_HEMMA_GPU_RUNTIME = REPO_ROOT / "scripts" / "devops" / "verify-hemma-gpu-runtime.sh"


def _write_fake_pdm(script_dir: Path, *, args_path: Path, flag_path: Path) -> None:
    fake_pdm = script_dir / "pdm"
    fake_pdm.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf '%s\\n' \"$*\" > {args_path.as_posix()!r}",
                "printf '%s\\n' "
                '"${SIR_CONVERT_A_LOT_RUN_HEMMA_FORWARD_API_KEY:-missing}" '
                f"> {flag_path.as_posix()!r}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_pdm.chmod(fake_pdm.stat().st_mode | stat.S_IXUSR)


def _write_fake_agent_secrets(script_dir: Path, *, args_path: Path) -> None:
    fake_agent_secrets = script_dir / "agent-secrets"
    fake_agent_secrets.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                f"printf '%s\\n' \"$*\" > {args_path.as_posix()!r}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    fake_agent_secrets.chmod(fake_agent_secrets.stat().st_mode | stat.S_IXUSR)


def _run_wrapper_with_fake_pdm(
    tmp_path: Path,
    *,
    api_key: str | None,
    args: list[str],
) -> tuple[subprocess.CompletedProcess[str], str, str]:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    args_path = tmp_path / "pdm-args.txt"
    flag_path = tmp_path / "forward-flag.txt"
    _write_fake_pdm(fake_bin, args_path=args_path, flag_path=flag_path)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    if api_key is None:
        env.pop("SIR_CONVERT_A_LOT_V2_API_KEY", None)
    else:
        env["SIR_CONVERT_A_LOT_V2_API_KEY"] = api_key

    result = subprocess.run(
        ["bash", str(VERIFY_HEMMA_GPU_RUNTIME), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    return result, args_path.read_text(encoding="utf-8"), flag_path.read_text(encoding="utf-8")


def test_gpu_verifier_wrapper_delegates_remote_run_without_local_secret_use(
    tmp_path: Path,
) -> None:
    result, pdm_args, forward_flag = _run_wrapper_with_fake_pdm(
        tmp_path,
        api_key="local-secret",
        args=["--lane", "host"],
    )

    assert result.returncode == 0
    assert forward_flag.strip() == "missing"
    expected_command = (
        "run-local-pdm run-hemma -- bash "
        "scripts/devops/verify-hemma-gpu-runtime.sh --remote --lane host"
    )
    assert expected_command in pdm_args
    assert "local-secret" not in pdm_args
    assert "--api-key" not in pdm_args


def test_gpu_verifier_wrapper_preserves_explicit_api_key_arg(tmp_path: Path) -> None:
    result, pdm_args, forward_flag = _run_wrapper_with_fake_pdm(
        tmp_path,
        api_key="local-secret",
        args=["--api-key", "explicit-secret", "--lane", "host"],
    )

    assert result.returncode == 0
    assert forward_flag.strip() == "missing"
    assert "--api-key explicit-secret" in pdm_args
    assert "local-secret" not in pdm_args


def test_gpu_verifier_wrapper_without_key_keeps_existing_missing_key_path(tmp_path: Path) -> None:
    result, pdm_args, forward_flag = _run_wrapper_with_fake_pdm(
        tmp_path,
        api_key=None,
        args=["--lane", "host"],
    )

    assert result.returncode == 0
    assert forward_flag.strip() == "missing"
    assert "--remote --lane host" in pdm_args


def test_gpu_verifier_remote_mode_wraps_python_module_in_agent_secrets(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    args_path = tmp_path / "agent-secrets-args.txt"
    _write_fake_agent_secrets(fake_bin, args_path=args_path)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(VERIFY_HEMMA_GPU_RUNTIME), "--remote", "--lane", "host"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert args_path.read_text(encoding="utf-8").strip() == (
        "run --set sir-convert-a-lot-operator -- pdm run python -m "
        "scripts.sir_convert_a_lot.devops.verify_hemma_gpu_runtime --lane host"
    )
