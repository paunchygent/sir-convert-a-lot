"""Tests for dependency-image cleanup after Sir Convert deps builds.

Purpose:
    Prove that Sir Convert-a-Lot removes only superseded dependency-image tags
    after a successful CPU or ROCm dependency-image build.

Relationships:
    - Guards Task 340's Docker storage cleanup contract.
    - Complements Task 255 dependency-image cache contract tests.
"""

from __future__ import annotations

from pathlib import Path

import scripts.sir_convert_a_lot.devops.prune_superseded_deps_images as cleanup
from scripts.sir_convert_a_lot.devops.prune_superseded_deps_images import (
    DockerImage,
    plan_prune,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE_DEPS_SCRIPT = REPO_ROOT / "scripts" / "devops" / "service-deps-image.sh"


def test_plan_prune_targets_only_configured_old_dependency_refs() -> None:
    """Cleanup must stay scoped to the caller-selected dependency repository."""
    images = [
        DockerImage("sir-convert-a-lot-deps-cpu", "new-hash", "sha256:new-cpu"),
        DockerImage("sir-convert-a-lot-deps-cpu", "local", "sha256:new-cpu"),
        DockerImage("sir-convert-a-lot-deps-cpu", "old-hash", "sha256:old-cpu"),
        DockerImage("sir-convert-a-lot-deps-rocm", "old-hash", "sha256:old-rocm"),
        DockerImage("huleedu-deps-core", "old-hash", "sha256:huleedu"),
        DockerImage("sir-convert-a-lot-prod", "old-hash", "sha256:service"),
    ]

    plan = plan_prune(
        images=images,
        repositories={"sir-convert-a-lot-deps-cpu"},
        keep_tags={"local", "new-hash"},
        protected_image_ids={"sha256:new-cpu"},
    )

    assert plan.refs_to_remove == ("sir-convert-a-lot-deps-cpu:old-hash",)
    assert plan.protected_refs == (
        "sir-convert-a-lot-deps-cpu:local",
        "sir-convert-a-lot-deps-cpu:new-hash",
    )


def test_plan_prune_protects_running_old_dependency_image_ids() -> None:
    """Running dependency image IDs must not be removed even when their tag is old."""
    images = [
        DockerImage("sir-convert-a-lot-deps-cpu", "new-hash", "sha256:new-cpu"),
        DockerImage("sir-convert-a-lot-deps-cpu", "old-hash", "sha256:old-cpu"),
    ]

    plan = plan_prune(
        images=images,
        repositories={"sir-convert-a-lot-deps-cpu"},
        keep_tags={"local", "new-hash"},
        protected_image_ids={"sha256:new-cpu", "sha256:old-cpu"},
    )

    assert plan.refs_to_remove == ()
    assert plan.protected_refs == (
        "sir-convert-a-lot-deps-cpu:new-hash",
        "sir-convert-a-lot-deps-cpu:old-hash",
    )


def test_run_defaults_to_dry_run_without_removing_refs(monkeypatch, capsys) -> None:
    """Dry-run output should be useful without mutating Docker images."""
    removed_refs: list[str] = []

    monkeypatch.setattr(
        cleanup,
        "list_local_images",
        lambda: (
            DockerImage("sir-convert-a-lot-deps-cpu", "new-hash", "sha256:new-cpu"),
            DockerImage("sir-convert-a-lot-deps-cpu", "old-hash", "sha256:old-cpu"),
        ),
    )
    monkeypatch.setattr(cleanup, "collect_running_image_ids", lambda: set())
    monkeypatch.setattr(
        cleanup,
        "collect_keep_image_ids",
        lambda repositories, keep_tags: {"sha256:new-cpu"},
    )
    monkeypatch.setattr(cleanup, "remove_refs", removed_refs.extend)

    exit_code = cleanup.run(
        [
            "--repository",
            "sir-convert-a-lot-deps-cpu",
            "--keep-tag",
            "new-hash",
            "--keep-tag",
            "local",
        ]
    )

    assert exit_code == 0
    assert removed_refs == []
    assert (
        "Would remove superseded dependency image tag: sir-convert-a-lot-deps-cpu:old-hash"
    ) in capsys.readouterr().out


def test_run_execute_removes_only_planned_refs(monkeypatch, capsys) -> None:
    """Execute mode should remove exactly the planned superseded refs."""
    removed_refs: list[str] = []

    monkeypatch.setattr(
        cleanup,
        "list_local_images",
        lambda: (
            DockerImage("sir-convert-a-lot-deps-cpu", "new-hash", "sha256:new-cpu"),
            DockerImage("sir-convert-a-lot-deps-cpu", "old-hash", "sha256:old-cpu"),
        ),
    )
    monkeypatch.setattr(cleanup, "collect_running_image_ids", lambda: set())
    monkeypatch.setattr(
        cleanup,
        "collect_keep_image_ids",
        lambda repositories, keep_tags: {"sha256:new-cpu"},
    )
    monkeypatch.setattr(cleanup, "remove_refs", removed_refs.extend)

    exit_code = cleanup.run(
        [
            "--execute",
            "--repository",
            "sir-convert-a-lot-deps-cpu",
            "--keep-tag",
            "new-hash",
            "--keep-tag",
            "local",
        ]
    )

    assert exit_code == 0
    assert removed_refs == ["sir-convert-a-lot-deps-cpu:old-hash"]
    assert (
        "Removing superseded dependency image tag: sir-convert-a-lot-deps-cpu:old-hash"
    ) in capsys.readouterr().out


def test_service_deps_image_build_hook_prunes_after_successful_build() -> None:
    """The service deps lane should invoke cleanup after a build has completed."""
    script = SERVICE_DEPS_SCRIPT.read_text(encoding="utf-8")

    assert "python -m scripts.sir_convert_a_lot.devops.prune_superseded_deps_images" in script
    assert "SIR_CONVERT_A_LOT_PRUNE_SUPERSEDED_DEPS_IMAGES" in script
    assert "--repository" in script
    assert '"${IMAGE_REPOSITORY}"' in script
    assert "--keep-tag local" in script
    assert '--keep-tag "${DEPENDENCY_IMAGE_HASH}"' in script
    build_then_prune = '"${build_args[@]}"\n  prune_superseded_dependency_images'
    assert build_then_prune in script
