"""Audio transcription sidecar diarization access diagnostic tests.

Purpose:
    Prove the operator-facing pyannote access diagnostic emits bounded reports
    for ready, gated, and missing-token Hugging Face access states.

Relationships:
    - Covers the Task 354 diagnostic command used before rerunning STT sidecar
      live profile proof.
    - Guards the content-safety contract for token values, private cache paths,
      and raw model identifiers.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_diarization_access import (
    DiarizationModelAccessSettings,
    build_diarization_model_access_report,
    write_diarization_model_access_report,
)
from scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_diarization_access import (
    main as run_diarization_access_diagnostic,
)


class ReadyHubAccessClient:
    def whoami(self, *, token: str) -> Mapping[str, object]:
        return {"name": "operator-account"}

    def download_file(self, *, repo_id: str, filename: str, token: str) -> Path:
        return Path("/private/cache/models--pyannote--speaker-diarization-community-1/config.yaml")


class GatedRepoError(Exception):
    pass


class GatedHubAccessClient:
    def whoami(self, *, token: str) -> Mapping[str, object]:
        return {"name": "operator-account"}

    def download_file(self, *, repo_id: str, filename: str, token: str) -> Path:
        raise GatedRepoError("access to gated pyannote artifact denied")


def test_diarization_access_report_accepts_authenticated_gated_artifact_without_leaks(
    tmp_path: Path,
) -> None:
    settings = DiarizationModelAccessSettings(output_root=tmp_path)

    report = build_diarization_model_access_report(
        settings=settings,
        client=ReadyHubAccessClient(),
        environment={"HF_TOKEN": "hf_private_token_value"},
    )
    output_path = write_diarization_model_access_report(report, output_root=tmp_path)
    persisted = output_path.read_text(encoding="utf-8")

    assert report["status"] == "ready"
    assert report["access_status"] == "ready"
    assert report["token_env_var_names"] == ("HF_TOKEN",)
    assert report["token_env_vars_present"] is True
    assert report["authenticated_account_observed"] is True
    assert report["model_family"] == "pyannote_community_diarization"
    assert report["artifact_label"] == "pipeline_config"
    assert report["operator_action"] == ""
    assert report["secret_values_exposed"] is False
    assert report["private_cache_paths_exposed"] is False
    assert report["raw_model_identifiers_exposed"] is False
    assert "hf_private_token_value" not in persisted
    assert "pyannote/speaker-diarization-community-1" not in persisted
    assert "/private/cache" not in persisted


def test_diarization_access_report_names_operator_action_for_gated_artifact() -> None:
    settings = DiarizationModelAccessSettings(output_root=Path("build/verification/access"))

    report = build_diarization_model_access_report(
        settings=settings,
        client=GatedHubAccessClient(),
        environment={"HF_TOKEN": "hf_private_token_value"},
    )

    assert report["status"] == "blocked"
    assert report["access_status"] == "blocked"
    assert report["failure_code"] == "gated_model_access_denied"
    assert report["exception_class"] == "GatedRepoError"
    assert (
        report["operator_action"]
        == "accept_or_request_pyannote_gated_model_access_for_hf_token_account"
    )


def test_diarization_access_report_fails_closed_when_hf_token_is_missing() -> None:
    settings = DiarizationModelAccessSettings(output_root=Path("build/verification/access"))

    report = build_diarization_model_access_report(
        settings=settings,
        client=ReadyHubAccessClient(),
        environment={},
    )

    assert report["status"] == "blocked"
    assert report["access_status"] == "blocked"
    assert report["token_env_vars_present"] is False
    assert report["authenticated_account_observed"] is False
    assert report["failure_code"] == "hf_token_missing"
    assert report["operator_action"] == "configure_hf_token_for_stt_sidecar_operator"


def test_diarization_access_command_is_registered() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    command_module = (
        "scripts.sir_convert_a_lot.devops.run_audio_transcription_sidecar_diarization_access"
    )

    assert f'"diagnose:stt-sidecar-diarization-access" = "python -m {command_module}"' in pyproject


def test_diarization_access_report_writes_json_under_generated_root(tmp_path: Path) -> None:
    report = build_diarization_model_access_report(
        settings=DiarizationModelAccessSettings(output_root=tmp_path),
        client=ReadyHubAccessClient(),
        environment={"HF_TOKEN": "hf_private_token_value"},
    )

    output_path = write_diarization_model_access_report(report, output_root=tmp_path)
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path == tmp_path / "diarization-access.json"
    assert loaded["schema_version"] == "audio_transcription_sidecar_diarization_access_v1"
    assert loaded["status"] == "ready"


def test_diarization_access_command_writes_report_and_returns_ready_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_diarization_access_diagnostic(
        ["--output-root", tmp_path.as_posix()],
        environment={"HF_TOKEN": "hf_private_token_value"},
        client=ReadyHubAccessClient(),
    )
    captured = capsys.readouterr()
    output_path = tmp_path / "diarization-access.json"
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert captured.out.strip() == output_path.as_posix()
    assert loaded["status"] == "ready"
    assert loaded["secret_values_exposed"] is False


def test_diarization_access_command_writes_missing_token_report_and_returns_blocked_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_diarization_access_diagnostic(
        ["--output-root", tmp_path.as_posix()],
        environment={},
        client=ReadyHubAccessClient(),
    )
    captured = capsys.readouterr()
    output_path = tmp_path / "diarization-access.json"
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 2
    assert captured.out.strip() == output_path.as_posix()
    assert loaded["status"] == "blocked"
    assert loaded["failure_code"] == "hf_token_missing"
    assert loaded["operator_action"] == "configure_hf_token_for_stt_sidecar_operator"
    assert loaded["secret_values_exposed"] is False


def test_diarization_access_command_writes_gated_report_and_returns_blocked_exit_code(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_diarization_access_diagnostic(
        ["--output-root", tmp_path.as_posix()],
        environment={"HF_TOKEN": "hf_private_token_value"},
        client=GatedHubAccessClient(),
    )
    captured = capsys.readouterr()
    output_path = tmp_path / "diarization-access.json"
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    persisted = output_path.read_text(encoding="utf-8")

    assert exit_code == 2
    assert captured.out.strip() == output_path.as_posix()
    assert loaded["status"] == "blocked"
    assert loaded["failure_code"] == "gated_model_access_denied"
    assert (
        loaded["operator_action"]
        == "accept_or_request_pyannote_gated_model_access_for_hf_token_account"
    )
    assert "hf_private_token_value" not in persisted
    assert "pyannote/speaker-diarization-community-1" not in persisted
    assert loaded["raw_model_identifiers_exposed"] is False
