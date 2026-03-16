"""Tests for the recurring Hemma scratch-governance surface.

Purpose:
    Verify the committed Task 204 scratch audit/remediation helpers and runner
    without touching real Hemma disks or real Docker state.

Relationships:
    - Covers `task204_hemma_scratch_policy_runtime.py`.
    - Covers `run_task204_hemma_scratch_policy.py`.
    - Protects the recurring hot-versus-cold storage policy used by Story 29.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops import run_task204_hemma_scratch_policy
from scripts.sir_convert_a_lot.devops.task204_hemma_scratch_policy_runtime import (
    ArchivedScratchPath,
    ScratchAuditReport,
    ScratchConsumer,
    ScratchRemediationReport,
    archive_scratch_paths,
    build_scratch_audit_report,
    directory_size_bytes,
)


def test_archive_scratch_paths_moves_tree_and_symlinks_back(tmp_path: Path) -> None:
    """Task 204 should archive explicit scratch trees and leave a symlink behind."""
    scratch_root = tmp_path / "scratch"
    storage_archive_root = tmp_path / "storage" / "archive"
    source_path = scratch_root / "sir-convert-a-lot" / "build" / "runs" / "cold-root"
    artifact_path = source_path / "report.json"
    artifact_path.parent.mkdir(parents=True)
    artifact_path.write_text("ok", encoding="utf-8")

    archived_paths = archive_scratch_paths(
        [source_path],
        scratch_root=scratch_root,
        storage_archive_root=storage_archive_root,
    )

    assert len(archived_paths) == 1
    archive_path = storage_archive_root / "sir-convert-a-lot" / "build" / "runs" / "cold-root"
    assert source_path.is_symlink() is True
    assert source_path.resolve() == archive_path.resolve()
    assert (archive_path / "report.json").read_text(encoding="utf-8") == "ok"


def test_build_scratch_audit_report_ranks_large_consumers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 204 audit should rank the largest non-symlink consumers deterministically."""
    scratch_root = tmp_path / "scratch"
    repo_root = scratch_root / "sir-convert-a-lot"
    runs_root = repo_root / "build" / "runs"
    verification_root = repo_root / "build" / "verification"
    top_run = runs_root / "big-run"
    top_verification = verification_root / "big-verification"
    cache_root = scratch_root / "cache"
    for root, content in (
        (top_run, "a" * 64),
        (top_verification, "b" * 48),
        (cache_root, "c" * 32),
    ):
        artifact = root / "artifact.bin"
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(content, encoding="utf-8")

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task204_hemma_scratch_policy_runtime._docker_system_df_or_error",
        lambda: "docker ok",
    )

    report = build_scratch_audit_report(
        scratch_root=scratch_root,
        storage_archive_root=tmp_path / "storage" / "archive",
        runs_root=runs_root,
        verification_root=verification_root,
        min_bytes=1,
        required_free_bytes=1,
        top_count=10,
    )

    assert report.meets_required_headroom is True
    assert report.top_level_consumers[0].path == (repo_root).as_posix()
    assert report.run_consumers[0].path == top_run.as_posix()
    assert report.verification_consumers[0].path == top_verification.as_posix()


def test_directory_size_bytes_falls_back_to_sudo_for_permission_protected_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task 204 audit should retry `du` with sudo when plain access is denied."""
    protected_root = tmp_path / "docker"
    protected_root.mkdir()
    calls: list[list[str]] = []

    def fake_run_checked(command: list[str], *, label: str) -> str:
        calls.append(command)
        if command[:4] == ["du", "-s", "-B1", protected_root.as_posix()]:
            raise SystemExit("permission denied")
        return f"4096\t{protected_root.as_posix()}"

    monkeypatch.setattr(
        "scripts.sir_convert_a_lot.devops.task204_hemma_scratch_policy_runtime.run_checked",
        fake_run_checked,
    )

    size_bytes = directory_size_bytes(protected_root)

    assert size_bytes == 4096
    assert calls == [
        ["du", "-s", "-B1", protected_root.as_posix()],
        ["sudo", "-n", "du", "-s", "-B1", protected_root.as_posix()],
    ]


def test_task204_runner_writes_audit_and_remediation_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Task 204 runner should write deterministic audit and remediation artifacts."""
    output_root = tmp_path / "build" / "verification" / "task-204"
    audit_report = ScratchAuditReport(
        checked_at="2026-03-16T20:00:00Z",
        scratch_root="/srv/scratch",
        storage_archive_root="/srv/storage/sir-convert-a-lot/archive/scratch-mirror",
        required_free_bytes=123,
        scratch_total_bytes=1000,
        scratch_used_bytes=700,
        scratch_free_bytes=300,
        meets_required_headroom=True,
        docker_system_df="docker audit",
        top_level_consumers=[ScratchConsumer(path="/srv/scratch/sir-convert-a-lot", size_bytes=99)],
        run_consumers=[],
        verification_consumers=[],
    )
    remediation_report = ScratchRemediationReport(
        checked_at="2026-03-16T20:01:00Z",
        scratch_root="/srv/scratch",
        storage_archive_root="/srv/storage/sir-convert-a-lot/archive/scratch-mirror",
        required_free_bytes=123,
        scratch_free_bytes_before=300,
        scratch_free_bytes_after=900,
        meets_required_headroom_after=True,
        archived_paths=[
            ArchivedScratchPath(
                source_path="/srv/scratch/a",
                archive_path="/srv/storage/sir-convert-a-lot/archive/scratch-mirror/a",
                size_bytes=42,
            )
        ],
        pruned_docker_state=True,
        docker_system_df_before="before",
        docker_system_df_after="after",
    )

    monkeypatch.setattr(
        run_task204_hemma_scratch_policy,
        "build_scratch_audit_report",
        lambda **_: audit_report,
    )
    monkeypatch.setattr(
        run_task204_hemma_scratch_policy,
        "run_scratch_remediation",
        lambda **_: remediation_report,
    )

    audit_exit_code = run_task204_hemma_scratch_policy.main(
        ["audit", "--output-root", output_root.as_posix()]
    )
    remediation_exit_code = run_task204_hemma_scratch_policy.main(
        ["remediate", "--output-root", output_root.as_posix()]
    )

    assert audit_exit_code == 0
    assert remediation_exit_code == 0
    assert (
        json.loads((output_root / "audit.json").read_text(encoding="utf-8"))["scratch_free_bytes"]
        == 300
    )
    assert "Task 204 Hemma Scratch Audit" in (output_root / "audit.md").read_text(encoding="utf-8")
    assert (
        json.loads((output_root / "remediate.json").read_text(encoding="utf-8"))[
            "pruned_docker_state"
        ]
        is True
    )
    assert "Task 204 Hemma Scratch Remediation" in (output_root / "remediate.md").read_text(
        encoding="utf-8"
    )
    rendered_output = capsys.readouterr().out
    assert '"meets_required_headroom": true' in rendered_output
    assert '"pruned_docker_state": true' in rendered_output
