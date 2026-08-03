"""Tests for Hemma storage remediation.

Purpose:
    Verify the migration helpers and committed runner for the Hemma storage
    remediation lane without touching real Docker state or real server disks.

Relationships:
    - Covers `hemma_storage_runtime.py`.
    - Covers `run_hemma_storage_remediation.py`.
    - Protects the storage-tier contract introduced by Hemma storage remediation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_hemma_storage_remediation
from scripts.sir_convert_a_lot.devops.hemma_storage_runtime import (
    HemmaStorageReport,
    HemmaStorageSettings,
    build_storage_report,
    cleanup_non_active_docker_state,
    migrate_qwen_data_to_storage,
    migrate_repo_build_to_scratch,
)


def _settings(tmp_path: Path) -> HemmaStorageSettings:
    """Build one deterministic Hemma storage remediation settings object for tests."""
    repo_root = tmp_path / "repo"
    return HemmaStorageSettings(
        repo_root=repo_root,
        repo_build_root=repo_root / "build",
        scratch_build_root=tmp_path / "scratch" / "sir-convert-a-lot" / "build",
        old_qwen_data_root=tmp_path / "scratch" / "sir-convert-a-lot" / "data" / "qwen",
        new_qwen_data_root=tmp_path / "storage" / "sir-convert-a-lot" / "data" / "qwen",
        migrate_repo_build=True,
        migrate_qwen_data=True,
        cleanup_docker_state=True,
    )


def test_migrate_repo_build_to_scratch_moves_and_symlinks(tmp_path: Path) -> None:
    """Hemma storage remediation moves the repo build tree onto scratch."""
    settings = _settings(tmp_path)
    artifact_path = settings.repo_build_root / "reference" / "artifact.txt"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("ok", encoding="utf-8")

    migrate_repo_build_to_scratch(settings)

    assert settings.repo_build_root.is_symlink()
    assert settings.repo_build_root.resolve() == settings.scratch_build_root.resolve()
    assert (settings.scratch_build_root / "reference" / "artifact.txt").read_text(
        encoding="utf-8"
    ) == "ok"


def test_migrate_qwen_data_to_storage_moves_and_symlinks(tmp_path: Path) -> None:
    """Hemma storage remediation should move raw corpus data onto storage and symlink it back."""
    settings = _settings(tmp_path)
    asset_path = settings.old_qwen_data_root / "raw" / "asset.parquet"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_text("rows", encoding="utf-8")

    migrate_qwen_data_to_storage(settings)

    assert settings.old_qwen_data_root.is_symlink()
    assert settings.old_qwen_data_root.resolve() == settings.new_qwen_data_root.resolve()
    assert (settings.new_qwen_data_root / "raw" / "asset.parquet").read_text(
        encoding="utf-8"
    ) == "rows"


def test_migrate_repo_build_to_scratch_allows_identical_duplicate_files(tmp_path: Path) -> None:
    """Hemma storage remediation should absorb identical duplicate files during build migration."""
    settings = _settings(tmp_path)
    source_artifact = settings.repo_build_root / "reference" / "artifact.txt"
    target_artifact = settings.scratch_build_root / "reference" / "artifact.txt"
    source_artifact.parent.mkdir(parents=True)
    target_artifact.parent.mkdir(parents=True)
    source_artifact.write_text("same", encoding="utf-8")
    target_artifact.write_text("same", encoding="utf-8")

    migrate_repo_build_to_scratch(settings)

    assert settings.repo_build_root.is_symlink()
    assert target_artifact.read_text(encoding="utf-8") == "same"


def test_cleanup_non_active_docker_state_prunes_expected_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Hemma storage remediation cleanup should prune containers, images, volumes, and builder cache.
    """
    seen: list[tuple[list[str], str]] = []

    def _fake_run_checked(command: list[str], *, label: str) -> str:
        seen.append((command, label))
        return "ok"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.hemma_storage_runtime.run_checked",
        _fake_run_checked,
    )

    cleanup_non_active_docker_state()

    assert seen == [
        (
            ["sudo", "-n", "docker", "container", "prune", "-f"],
            "docker container prune hemma-storage",
        ),
        (["sudo", "-n", "docker", "image", "prune", "-af"], "docker image prune hemma-storage"),
        (["sudo", "-n", "docker", "volume", "prune", "-f"], "docker volume prune hemma-storage"),
        (["sudo", "-n", "docker", "builder", "prune", "-af"], "docker builder prune hemma-storage"),
    ]


def test_build_storage_report_resolves_symlink_targets(tmp_path: Path) -> None:
    """Hemma storage remediation reports capture symlink targets deterministically."""
    settings = _settings(tmp_path)
    settings.repo_root.mkdir(parents=True)
    settings.scratch_build_root.mkdir(parents=True)
    settings.new_qwen_data_root.mkdir(parents=True)
    settings.repo_build_root.symlink_to(settings.scratch_build_root)
    settings.old_qwen_data_root.parent.mkdir(parents=True)
    settings.old_qwen_data_root.symlink_to(settings.new_qwen_data_root)

    report = build_storage_report(
        settings,
        docker_system_df_before_text="before docker",
        docker_system_df_after_text="after docker",
        filesystem_df_before_text="before fs",
        filesystem_df_after_text="after fs",
    )

    assert report.repo_build_is_symlink is True
    assert report.repo_build_target == settings.scratch_build_root.resolve().as_posix()
    assert report.old_qwen_data_is_symlink is True
    assert report.old_qwen_data_target == settings.new_qwen_data_root.resolve().as_posix()


def test_runner_writes_report_after_remediation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hemma storage remediation writes deterministic report files after remediation."""
    output_root = tmp_path / "build" / "verification" / "hemma-storage"
    expected_report = HemmaStorageReport(
        repo_build_root="/repo/build",
        repo_build_is_symlink=True,
        repo_build_target="/srv/scratch/sir-convert-a-lot/build",
        scratch_build_root="/srv/scratch/sir-convert-a-lot/build",
        old_qwen_data_root="/srv/scratch/sir-convert-a-lot/data/qwen3-tts-swedish-corpus",
        old_qwen_data_is_symlink=True,
        old_qwen_data_target="/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus",
        new_qwen_data_root="/srv/storage/sir-convert-a-lot/data/qwen3-tts-swedish-corpus",
        migrated_repo_build=True,
        migrated_qwen_data=True,
        cleaned_docker_state=True,
        docker_system_df_before="docker before",
        docker_system_df_after="docker after",
        filesystem_df_before="fs before",
        filesystem_df_after="fs after",
    )
    calls: list[HemmaStorageSettings] = []

    def _fake_run(settings: HemmaStorageSettings) -> HemmaStorageReport:
        calls.append(settings)
        return expected_report

    monkeypatch.setattr(
        run_hemma_storage_remediation,
        "run_storage_remediation",
        _fake_run,
    )

    exit_code = run_hemma_storage_remediation.main(["--output-root", output_root.as_posix()])

    assert exit_code == 0
    assert len(calls) == 1
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    assert json.loads(report_json_path.read_text(encoding="utf-8"))["repo_build_is_symlink"] is True
    assert "Hemma Storage Remediation Report" in report_md_path.read_text(encoding="utf-8")
    assert '"cleaned_docker_state": true' in capsys.readouterr().out
