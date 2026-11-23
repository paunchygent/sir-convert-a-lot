"""Tests for the agent-secrets operator command wiring.

Purpose:
    Prove every devops surface that reads `SIR_CONVERT_A_LOT_V2_API_KEY` or
    `HF_TOKEN` reaches the secret through
    `agent-secrets run --set <set>`, that no code path falls back to `.env`
    for those names, and that the retired prod env mirror is gone.

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
REMOTE_PROOF_SET = "sir-convert-a-lot-remote-proof"


def _pdm_scripts() -> dict[str, object]:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = pyproject["tool"]["pdm"]["scripts"]
    assert isinstance(scripts, dict)
    return scripts


def test_secret_reading_pdm_scripts_run_through_agent_secrets() -> None:
    scripts = _pdm_scripts()
    expected_wrapped = {
        "benchmark:pdf-throughput-hemma": (
            OPERATOR_SET,
            "python -m scripts.sir_convert_a_lot.devops.run_pdf_throughput_hemma_benchmark",
        ),
        "benchmark:pdf-throughput-two-worker-sweep-hemma": (
            OPERATOR_SET,
            "python -m "
            "scripts.sir_convert_a_lot.devops.run_pdf_throughput_hemma_benchmark "
            "--two-worker-sweep",
        ),
        "benchmark:tts-sidecar": (
            OPERATOR_SET,
            "python -m scripts.sir_convert_a_lot.devops.run_tts_sidecar_hemma_benchmark",
        ),
        "benchmark:stt-sidecar-preflight": (
            OPERATOR_SET,
            "python -m "
            "scripts.sir_convert_a_lot.devops."
            "run_audio_transcription_sidecar_benchmark_preflight",
        ),
        "benchmark:stt-sidecar-live-observation": (
            OPERATOR_SET,
            "python -m "
            "scripts.sir_convert_a_lot.devops."
            "run_audio_transcription_sidecar_live_observation",
        ),
        "diagnose:stt-sidecar-diarization-access": (
            OPERATOR_SET,
            "python -m "
            "scripts.sir_convert_a_lot.devops."
            "run_audio_transcription_sidecar_diarization_access",
        ),
        "proof:remote-proof-audio-transcript": (
            REMOTE_PROOF_SET,
            "python -m scripts.sir_convert_a_lot.devops.remote_proof_audio_transcript_evidence",
        ),
    }
    for name, (secret_set, inner) in expected_wrapped.items():
        entry = scripts[name]
        command = entry["cmd"] if isinstance(entry, dict) else entry
        assert command == (f"agent-secrets run --set {secret_set} -- {inner}"), (
            f"pdm script {name} is not wrapped in agent-secrets"
        )


def test_client_deploy_coordinator_needs_no_secret_store() -> None:
    scripts = _pdm_scripts()

    assert scripts["hemma-deploy-and-verify"] == (
        "python -m scripts.sir_convert_a_lot.devops.hemma_deploy_and_verify"
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


def test_operator_environment_merges_dotenv_keys_absent_from_environment(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HF_HOME=/srv/scratch/hf\n", encoding="utf-8")

    merged = merged_operator_environment({"PATH": "/usr/bin"}, env_file=env_file)

    assert merged["HF_HOME"] == "/srv/scratch/hf"
    assert merged["PATH"] == "/usr/bin"


def test_operator_environment_never_overrides_process_value(
    tmp_path: Path,
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("HF_TOKEN=file-hf-token\nHF_HOME=/srv/other/hf\n", encoding="utf-8")

    merged = merged_operator_environment(
        {"HF_TOKEN": "agent-secrets-hf-token", "HF_HOME": "/srv/scratch/hf"},
        env_file=env_file,
    )

    assert merged["HF_TOKEN"] == "agent-secrets-hf-token"
    assert merged["HF_HOME"] == "/srv/scratch/hf"
