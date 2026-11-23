"""Tests for the agent-secrets operator command wiring.

Purpose:
    Prove every devops surface that reads `SIR_CONVERT_A_LOT_V2_API_KEY` or
    `HF_TOKEN` reaches the secret through
    `agent-secrets run --set sir-convert-a-lot-operator`, that no code path
    falls back to `.env` for those names, and that the retired prod env
    mirror is gone.

Relationships:
    - Exercises `pyproject.toml` pdm script declarations.
    - Exercises `scripts/devops/verify-hemma-v2-conversions.sh` remote mode.
    - Exercises `audio_transcription_sidecar_operator_environment`.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tomllib
from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_operator_environment import (
    merged_operator_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
VERIFY_HEMMA_V2_CONVERSIONS = REPO_ROOT / "scripts" / "devops" / "verify-hemma-v2-conversions.sh"
OPERATOR_SET = "sir-convert-a-lot-operator"


def _pdm_scripts() -> dict[str, object]:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["tool"]["pdm"]["scripts"]
    assert isinstance(scripts, dict)
    return scripts


def test_secret_reading_pdm_scripts_run_through_agent_secrets() -> None:
    scripts = _pdm_scripts()
    expected_wrapped = {
        "benchmark:pdf-throughput-hemma": (
            "python -m scripts.sir_convert_a_lot.devops.run_pdf_throughput_hemma_benchmark"
        ),
        "benchmark:pdf-throughput-two-worker-sweep-hemma": (
            "python -m "
            "scripts.sir_convert_a_lot.devops.run_pdf_throughput_hemma_benchmark "
            "--two-worker-sweep"
        ),
        "benchmark:tts-sidecar": (
            "python -m scripts.sir_convert_a_lot.devops.run_tts_sidecar_hemma_benchmark"
        ),
        "benchmark:stt-sidecar-preflight": (
            "python -m "
            "scripts.sir_convert_a_lot.devops."
            "run_audio_transcription_sidecar_benchmark_preflight"
        ),
        "benchmark:stt-sidecar-live-observation": (
            "python -m "
            "scripts.sir_convert_a_lot.devops."
            "run_audio_transcription_sidecar_live_observation"
        ),
        "diagnose:stt-sidecar-diarization-access": (
            "python -m "
            "scripts.sir_convert_a_lot.devops."
            "run_audio_transcription_sidecar_diarization_access"
        ),
    }
    for name, inner in expected_wrapped.items():
        entry = scripts[name]
        command = entry["cmd"] if isinstance(entry, dict) else entry
        assert command == (f"agent-secrets run --set {OPERATOR_SET} -- {inner}"), (
            f"pdm script {name} is not wrapped in agent-secrets"
        )


def test_pdf_throughput_hemma_scripts_keep_dotenv_for_configuration() -> None:
    scripts = _pdm_scripts()
    for name in (
        "benchmark:pdf-throughput-hemma",
        "benchmark:pdf-throughput-two-worker-sweep-hemma",
    ):
        entry = scripts[name]
        assert isinstance(entry, dict)
        assert entry["env_file"] == {"override": ".env"}


def test_prod_env_mirror_script_and_pdm_entry_are_removed() -> None:
    scripts = _pdm_scripts()
    assert "hemma-sync-prod-env-mirror" not in scripts
    assert not (REPO_ROOT / "scripts" / "devops" / "sync-prod-env-mirror.sh").exists()


def test_v2_conversions_remote_mode_wraps_python_module_in_agent_secrets(
    tmp_path: Path,
) -> None:
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir(parents=True)
    args_path = tmp_path / "agent-secrets-args.txt"
    fake_agent_secrets = fake_bin / "agent-secrets"
    fake_agent_secrets.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"printf '%s\\n' \"$*\" > {args_path.as_posix()!r}\n",
        encoding="utf-8",
    )
    fake_agent_secrets.chmod(fake_agent_secrets.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(VERIFY_HEMMA_V2_CONVERSIONS), "--remote", "--lane", "host"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert args_path.read_text(encoding="utf-8").strip() == (
        "run --set sir-convert-a-lot-operator -- pdm run python -m "
        "scripts.sir_convert_a_lot.devops.verify_hemma_v2_conversions --lane host"
    )


def test_operator_environment_loads_dotenv_configuration_but_never_secret_names(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "HF_TOKEN=file-hf-token\n"
        "SIR_CONVERT_A_LOT_V2_API_KEY=file-api-key\n"
        "HF_HOME=/srv/scratch/hf\n",
        encoding="utf-8",
    )

    merged = merged_operator_environment({}, env_file=env_file)

    assert merged["HF_HOME"] == "/srv/scratch/hf"
    assert "HF_TOKEN" not in merged
    assert "SIR_CONVERT_A_LOT_V2_API_KEY" not in merged


def test_operator_environment_keeps_process_secret_over_dotenv_value(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HF_TOKEN=file-hf-token\n", encoding="utf-8")

    merged = merged_operator_environment({"HF_TOKEN": "agent-secrets-hf-token"}, env_file=env_file)

    assert merged["HF_TOKEN"] == "agent-secrets-hf-token"
