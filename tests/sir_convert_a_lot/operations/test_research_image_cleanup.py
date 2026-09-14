"""Focused tests for Sir-owned Docker cleanup classification and commands."""

from __future__ import annotations

import pytest

from scripts.sir_convert_a_lot.devops import research_image_cleanup

CURRENT_REVISION = "a" * 40


def image(
    digit: str,
    family: str,
    *,
    revision: str | None = None,
) -> dict[str, research_image_cleanup.JsonValue]:
    labels: dict[str, research_image_cleanup.JsonValue] = {
        research_image_cleanup.OWNER_LABEL: "sir-convert-a-lot",
        research_image_cleanup.FAMILY_LABEL: family,
        research_image_cleanup.REBUILDABLE_LABEL: "true",
    }
    if revision is not None:
        labels[research_image_cleanup.REVISION_LABEL] = revision
    return {
        "image_id": "sha256:" + digit * 64,
        "labels": labels,
        "repo_tags": [f"sir-convert-a-lot-{family}:local"],
    }


def inventory(
    *images: dict[str, research_image_cleanup.JsonValue],
    containers: list[research_image_cleanup.JsonValue] | None = None,
) -> dict[str, research_image_cleanup.JsonValue]:
    return {
        "containers": [] if containers is None else containers,
        "images": list(images),
        "revision": CURRENT_REVISION,
    }


def candidate_operations(
    plan: dict[str, research_image_cleanup.JsonValue],
) -> list[tuple[str, str]]:
    candidates = plan["candidates"]
    assert isinstance(candidates, list)
    result: list[tuple[str, str]] = []
    for candidate in candidates:
        assert isinstance(candidate, dict)
        operation = candidate["operation"]
        assert isinstance(operation, str)
        target = candidate.get("container_id", candidate.get("image_id"))
        assert isinstance(target, str)
        result.append((operation, target))
    return result


def test_stopped_container_precedes_its_rebuildable_image() -> None:
    owned = image("1", "qwen")
    image_id = owned["image_id"]
    assert isinstance(image_id, str)
    plan = research_image_cleanup.plan_cleanup(
        inventory(
            owned,
            containers=[
                {
                    "container_id": "stopped-qwen",
                    "image_id": image_id,
                    "state": "exited",
                }
            ],
        )
    )

    assert candidate_operations(plan) == [
        ("remove_container", "stopped-qwen"),
        ("remove_image", image_id),
    ]


def test_running_current_and_pinned_images_are_protected() -> None:
    current = image("1", "runtime", revision=CURRENT_REVISION)
    running = image("2", "stt")
    pinned = image("3", "qwen")
    running_id = running["image_id"]
    pinned_id = pinned["image_id"]
    assert isinstance(running_id, str)
    assert isinstance(pinned_id, str)

    plan = research_image_cleanup.plan_cleanup(
        inventory(
            current,
            running,
            pinned,
            containers=[
                {
                    "container_id": "running-stt",
                    "image_id": running_id,
                    "state": "running",
                }
            ],
        ),
        pinned_image_ids=(pinned_id,),
    )

    assert candidate_operations(plan) == []
    protected = plan["protected"]
    assert isinstance(protected, list)
    reasons = {
        record["reason"]
        for record in protected
        if isinstance(record, dict) and isinstance(record.get("reason"), str)
    }
    assert reasons == {
        "current_runtime_revision",
        "explicitly_pinned",
        "referenced_by_active_container",
    }


def test_dependency_images_remain_owned_by_the_existing_build_hook() -> None:
    plan = research_image_cleanup.plan_cleanup(inventory(image("1", "deps")))

    assert candidate_operations(plan) == []
    assert plan["protected"] == [
        {
            "image_id": "sha256:" + "1" * 64,
            "reason": "dependency_image_managed_by_build_hook",
        }
    ]


def test_unowned_docker_state_does_not_change_the_sir_plan() -> None:
    owned = image("1", "qwen")
    external: dict[str, research_image_cleanup.JsonValue] = {
        "image_id": "sha256:" + "2" * 64,
        "labels": {"another.repository": "true"},
        "repo_tags": ["external:latest"],
    }

    with_external = research_image_cleanup.plan_cleanup(
        inventory(
            owned,
            external,
            containers=[
                {
                    "container_id": "external-container",
                    "image_id": external["image_id"],
                    "state": "running",
                }
            ],
        )
    )
    without_external = research_image_cleanup.plan_cleanup(inventory(owned))

    assert with_external == without_external


def test_removal_commands_use_exact_ids_without_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[tuple[str, ...]] = []

    def run_command(command: tuple[str, ...], **_: bool) -> None:
        commands.append(command)

    monkeypatch.setattr(research_image_cleanup.subprocess, "run", run_command)
    image_id = "sha256:" + "1" * 64

    research_image_cleanup.remove_container("container-1")
    research_image_cleanup.remove_image(image_id)

    assert commands == [
        ("sudo", "-n", "docker", "container", "rm", "container-1"),
        ("sudo", "-n", "docker", "image", "rm", image_id),
    ]
