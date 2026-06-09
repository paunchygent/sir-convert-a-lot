"""Tests for the Hemma GPU verifier shell wrapper.

Purpose:
    Prove the operator-facing GPU verifier can reuse the local Sir Convert API
    key without requiring each session to rediscover the `--api-key` flag.

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

REPO_ROOT = Path(__file__).resolve().parents[2]
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


def test_gpu_verifier_wrapper_opts_into_api_key_forwarding_without_arg_secret(
    tmp_path: Path,
) -> None:
    result, pdm_args, forward_flag = _run_wrapper_with_fake_pdm(
        tmp_path,
        api_key="local-secret",
        args=["--lane", "host"],
    )

    assert result.returncode == 0
    assert forward_flag.strip() == "1"
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
