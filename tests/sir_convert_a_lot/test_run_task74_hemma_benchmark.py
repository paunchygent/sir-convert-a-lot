"""Tests for the canonical Hemma Task 74 benchmark runner.

Purpose:
    Validate the env-contract parsing and revision checks that gate the Hemma
    Task 74 workflow before any long-running benchmark is started.

Relationships:
    - Tests `scripts.sir_convert_a_lot.devops.run_task74_hemma_benchmark`.
    - Protects the canonical Hemma workflow used to prepare env/runtime parity
      before invoking the Task 74 harness.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_task74_hemma_benchmark


def test_verify_env_contract_accepts_canonical_symlink(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    canonical_env = tmp_path / "sir-convert-a-lot.env"
    canonical_env.write_text(
        "\n".join(
            [
                "SIR_CONVERT_A_LOT_V2_API_KEY=secret-key",
                "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE=easyocr",
                "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES=sv,en",
                "SIR_CONVERT_A_LOT_EASYOCR_MODEL_STORAGE_DIR=/opt/easyocr-models",
                "SIR_CONVERT_A_LOT_ENABLE_PARALLEL_PDF_CHUNKS=1",
                "SIR_CONVERT_A_LOT_MAX_CHUNK_WORKERS=2",
                "SIR_CONVERT_A_LOT_PDF_CHUNK_SIZE_PAGES=4",
                "SIR_CONVERT_A_LOT_GPU_STAGE_MAX_CONCURRENCY=2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    repo_env_link = tmp_path / ".env"
    repo_env_link.symlink_to(canonical_env)

    monkeypatch.setattr(run_task74_hemma_benchmark, "CANONICAL_ENV_PATH", canonical_env)
    monkeypatch.setattr(run_task74_hemma_benchmark, "CANONICAL_ENV_LINK", repo_env_link)
    monkeypatch.setattr(
        run_task74_hemma_benchmark,
        "_run_command",
        lambda argv, *, label, cwd=run_task74_hemma_benchmark.CANONICAL_REPO_ROOT, redactions=(): (
            ""
        ),
    )

    contract = run_task74_hemma_benchmark._verify_env_contract()

    assert contract.api_key == "secret-key"
    assert contract.default_ocr_engine == "easyocr"
    assert contract.default_ocr_languages == ("sv", "en")
    assert contract.deployed_profile.profile_name == "production_service_current"
    assert contract.deployed_profile.parallel_enabled is True
    assert contract.deployed_profile.max_chunk_workers == 2
    assert contract.deployed_profile.chunk_size_pages == 4
    assert contract.deployed_profile.gpu_stage_max_concurrency == 2


def test_verify_env_contract_rejects_missing_required_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    canonical_env = tmp_path / "sir-convert-a-lot.env"
    canonical_env.write_text("SIR_CONVERT_A_LOT_V2_API_KEY=secret-key\n", encoding="utf-8")
    repo_env_link = tmp_path / ".env"
    repo_env_link.symlink_to(canonical_env)

    monkeypatch.setattr(run_task74_hemma_benchmark, "CANONICAL_ENV_PATH", canonical_env)
    monkeypatch.setattr(run_task74_hemma_benchmark, "CANONICAL_ENV_LINK", repo_env_link)
    monkeypatch.setattr(
        run_task74_hemma_benchmark,
        "_run_command",
        lambda argv, *, label, cwd=run_task74_hemma_benchmark.CANONICAL_REPO_ROOT, redactions=(): (
            ""
        ),
    )

    with pytest.raises(SystemExit, match="missing required Task 74 keys"):
        run_task74_hemma_benchmark._verify_env_contract()


def test_verify_expected_revision_rejects_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        run_task74_hemma_benchmark,
        "_run_command",
        lambda argv, *, label, cwd=run_task74_hemma_benchmark.CANONICAL_REPO_ROOT, redactions=(): (
            "remote-sha\n"
        ),
    )

    with pytest.raises(SystemExit, match="does not match expected revision"):
        run_task74_hemma_benchmark._verify_expected_revision("expected-sha")


def test_parse_args_switches_to_two_worker_sweep_defaults() -> None:
    settings = run_task74_hemma_benchmark._parse_args(
        [
            "--expected-revision",
            "abc1234",
            "--two-worker-sweep",
        ]
    )

    assert settings.two_worker_sweep is True
    assert settings.output_json == run_task74_hemma_benchmark.DEFAULT_SWEEP_OUTPUT_JSON
    assert settings.output_report == run_task74_hemma_benchmark.DEFAULT_SWEEP_OUTPUT_REPORT
    assert settings.corpus_root == run_task74_hemma_benchmark.DEFAULT_SWEEP_CORPUS_ROOT
    assert settings.data_root == run_task74_hemma_benchmark.DEFAULT_SWEEP_DATA_ROOT
    assert settings.two_worker_chunk_sizes == "2,3,4,6,8"
    assert settings.two_worker_gpu_stage_caps == "1,2"


def test_main_stdout_excludes_performance_metrics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    output_json = tmp_path / "task74.json"
    output_report = tmp_path / "task74.md"

    def execute_workflow_stub(
        settings: run_task74_hemma_benchmark.Task74HemmaSettings,
    ) -> dict[str, object]:
        assert settings.output_json == output_json
        return {
            "comparison": {
                "recommended_profile": "parallel_conservative",
                "p50_improvement_percent": 41.7,
                "meets_target": True,
            },
            "runtime_parity": {"parity_proven": True},
            "runtime_surface": {"mode": "production_service"},
            "dirty_corpus": {
                "all_profiles_safe": True,
                "manifest": {"source_hashes_verified": True},
            },
        }

    monkeypatch.setattr(
        run_task74_hemma_benchmark,
        "execute_workflow",
        execute_workflow_stub,
    )

    exit_code = run_task74_hemma_benchmark.main(
        [
            "--expected-revision",
            "abc1234",
            "--output-json",
            output_json.as_posix(),
            "--output-report",
            output_report.as_posix(),
            "--dirty-corpus-manifest",
            "metadata-only-manifest.json",
            "--dirty-corpus-source-root",
            "private-pdf-root",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    summary = json.loads(output)
    assert summary == {
        "dirty_corpus_all_profiles_safe": True,
        "dirty_corpus_manifest_loaded": True,
        "dirty_corpus_source_hashes_verified": True,
        "output_json": output_json.as_posix(),
        "output_report": output_report.as_posix(),
        "runtime_parity_proven": True,
        "runtime_surface_mode": "production_service",
    }
    assert "recommended_profile" not in output
    assert "p50" not in output
    assert "improvement" not in output
    assert "meets_target" not in output


def test_run_task74_benchmark_uses_scratch_backed_miopen_cache(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured_env: dict[str, str] = {}
    commands: list[list[str]] = []
    monkeypatch.setattr(
        run_task74_hemma_benchmark,
        "DEFAULT_MIOPEN_USER_DB_PATH",
        tmp_path / "miopen" / "user-db",
    )
    monkeypatch.setattr(
        run_task74_hemma_benchmark,
        "DEFAULT_MIOPEN_KERNEL_CACHE_DIR",
        tmp_path / "miopen" / "kernel-cache",
    )

    def run_command_stub(
        argv: list[str],
        *,
        label: str,
        cwd: Path = run_task74_hemma_benchmark.CANONICAL_REPO_ROOT,
        redactions: tuple[str, ...] = (),
        env_overrides: dict[str, str] | None = None,
    ) -> str:
        del label, cwd, redactions
        commands.append(argv)
        if env_overrides is not None:
            captured_env.update(env_overrides)
        return ""

    monkeypatch.setattr(run_task74_hemma_benchmark, "_run_command", run_command_stub)
    settings = run_task74_hemma_benchmark._parse_args(
        [
            "--expected-revision",
            "abc1234",
            "--output-json",
            (tmp_path / "out.json").as_posix(),
            "--output-report",
            (tmp_path / "out.md").as_posix(),
        ]
    )

    run_task74_hemma_benchmark._run_task74_benchmark(
        settings,
        api_key="secret-key",
        remote_revision="abc1234",
        service_revision="abc1234",
        default_ocr_engine="easyocr",
        default_ocr_languages=("sv", "en"),
        deployed_profile=run_task74_hemma_benchmark.ProfileSpec(
            profile_name="production_service_current",
            parallel_enabled=True,
            max_chunk_workers=2,
            chunk_size_pages=4,
            gpu_stage_max_concurrency=2,
        ),
    )

    assert commands[-1][:3] == ["pdm", "run", "benchmark:task-74"]
    assert "--runtime-mode" in commands[-1]
    assert commands[-1][commands[-1].index("--runtime-mode") + 1] == "production_service"
    assert "in_process_app" not in commands[-1]
    assert "--service-profile-name" in commands[-1]
    assert commands[-1][commands[-1].index("--service-profile-name") + 1] == (
        "production_service_current"
    )
    assert "--service-profile-parallel-enabled" in commands[-1]
    assert captured_env == {
        "MIOPEN_FIND_MODE": "FAST",
        "MIOPEN_USER_DB_PATH": (tmp_path / "miopen" / "user-db").as_posix(),
        "MIOPEN_CUSTOM_CACHE_DIR": (tmp_path / "miopen" / "kernel-cache").as_posix(),
    }
    assert (tmp_path / "miopen" / "user-db").is_dir()
    assert (tmp_path / "miopen" / "kernel-cache").is_dir()
