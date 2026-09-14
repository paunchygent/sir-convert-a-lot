"""Plan and apply exact cleanup of repository-owned Sir Docker assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Final

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]

PROVIDER: Final = "sir-convert-a-lot-images"
SCHEMA: Final = "sir-convert-a-lot.hemma-image-cleanup.v1"
DOCKER_COMMAND: Final = ("sudo", "-n", "docker")
OWNER_LABEL: Final = "org.sir_convert_a_lot.owner"
FAMILY_LABEL: Final = "org.sir_convert_a_lot.image_family"
REBUILDABLE_LABEL: Final = "org.sir_convert_a_lot.rebuildable"
REVISION_LABEL: Final = "org.opencontainers.image.revision"
OWNED_FAMILIES: Final = frozenset(("runtime", "runtime-local", "stt", "qwen", "deps"))
_IMAGE_ID = re.compile(r"^sha256:[0-9a-f]{64}$")


class CleanupRefusal(ValueError):
    """Signal malformed or changed cleanup facts."""


def command_output(command: Sequence[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def current_revision() -> str:
    return command_output(("git", "rev-parse", "HEAD")).strip()


def collect_inventory() -> dict[str, JsonValue]:
    image_ids = _lines(
        command_output((*DOCKER_COMMAND, "image", "ls", "--quiet", "--no-trunc")),
        unique=True,
    )
    container_ids = _lines(command_output((*DOCKER_COMMAND, "ps", "-aq", "--no-trunc")))
    images: list[JsonValue] = [_inspect_image(image_id) for image_id in image_ids]
    containers: list[JsonValue] = [
        _inspect_container(container_id) for container_id in container_ids
    ]
    return {
        "containers": sorted(containers, key=_container_sort_key),
        "images": sorted(images, key=_image_sort_key),
        "revision": current_revision(),
    }


def plan_cleanup(
    inventory: dict[str, JsonValue],
    *,
    pinned_image_ids: Iterable[str] = (),
) -> dict[str, JsonValue]:
    pins = tuple(sorted(set(pinned_image_ids)))
    if any(_IMAGE_ID.fullmatch(image_id) is None for image_id in pins):
        raise CleanupRefusal("pins must contain full Docker image IDs")
    images = _records(inventory.get("images"), "images")
    containers = _records(inventory.get("containers"), "containers")
    revision = _required_string(inventory.get("revision"), "revision")

    owned_images: dict[str, dict[str, JsonValue]] = {}
    protected: list[JsonValue] = []
    evidence: list[JsonValue] = []
    for image in images:
        image_id = _required_image_id(image.get("image_id"))
        labels = _string_map(image.get("labels"))
        family = labels.get(FAMILY_LABEL) if labels is not None else None
        if (
            labels is None
            or labels.get(OWNER_LABEL) != "sir-convert-a-lot"
            or labels.get(REBUILDABLE_LABEL) != "true"
            or family not in OWNED_FAMILIES
        ):
            continue
        owned_images[image_id] = image

    candidates: list[JsonValue] = []
    referenced: set[str] = set()
    for container in containers:
        container_id = _required_string(container.get("container_id"), "container_id")
        image_id = _required_image_id(container.get("image_id"))
        state = _required_string(container.get("state"), "container state")
        owned_image = owned_images.get(image_id)
        if owned_image is not None and state == "exited":
            candidates.append(
                {
                    "container_id": container_id,
                    "image_id": image_id,
                    "operation": "remove_container",
                    "reason": "stopped_rebuildable_sir_container",
                }
            )
        else:
            referenced.add(image_id)

    for image_id, image in owned_images.items():
        labels = _string_map(image.get("labels"))
        if labels is None:
            raise CleanupRefusal("owned image labels disappeared")
        family = _required_string(labels.get(FAMILY_LABEL), "image family")
        reason: str | None = None
        if image_id in pins:
            reason = "explicitly_pinned"
        elif image_id in referenced:
            reason = "referenced_by_active_container"
        elif family == "deps":
            reason = "dependency_image_managed_by_build_hook"
        elif family == "runtime" and labels.get(REVISION_LABEL) == revision:
            reason = "current_runtime_revision"
        if reason is not None:
            protected.append({"image_id": image_id, "reason": reason})
            continue
        candidates.append(
            {
                "image_id": image_id,
                "operation": "remove_image",
                "reason": "unreferenced_rebuildable_sir_image",
            }
        )

    scoped_inventory: dict[str, JsonValue] = {
        "containers": sorted(
            [container for container in containers if container.get("image_id") in owned_images],
            key=_container_sort_key,
        ),
        "images": sorted(owned_images.values(), key=_image_sort_key),
        "revision": revision,
    }
    state_digest = _digest(scoped_inventory)
    plan: dict[str, JsonValue] = {
        "candidates": sorted(candidates, key=_candidate_sort_key),
        "evidence": sorted(evidence, key=_evidence_sort_key),
        "explicit_pin_image_ids": list(pins),
        "input_state_digest": state_digest,
        "protected": sorted(protected, key=_evidence_sort_key),
        "provider": PROVIDER,
        "schema": SCHEMA,
        "terminal_status": "planned",
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def remove_container(container_id: str) -> None:
    subprocess.run(
        (*DOCKER_COMMAND, "container", "rm", container_id),
        check=True,
        capture_output=True,
        text=True,
    )


def remove_image(image_id: str) -> None:
    subprocess.run(
        (*DOCKER_COMMAND, "image", "rm", image_id),
        check=True,
        capture_output=True,
        text=True,
    )


def run(argv: Sequence[str]) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.mode == "plan":
            if args.plan is not None:
                raise CleanupRefusal("plan mode does not accept --plan")
            _emit(plan_cleanup(collect_inventory(), pinned_image_ids=args.pin_image_id))
            return 0
        if args.pin_image_id:
            raise CleanupRefusal("apply obtains pins from its persisted plan")
        if args.plan is None:
            raise CleanupRefusal("apply requires --plan")
        return _apply(args.plan)
    except CleanupRefusal as error:
        _emit({"failure": str(error), "terminal_status": "refused"})
        return 2
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        _emit({"failure": str(error), "terminal_status": "refused"})
        return 1


def _apply(plan_path: Path) -> int:
    persisted = _read_plan(plan_path)
    _verify_plan(persisted)
    pins = _string_list(persisted.get("explicit_pin_image_ids"), "pins")
    fresh = plan_cleanup(collect_inventory(), pinned_image_ids=pins)
    if fresh.get("plan_digest") != persisted.get("plan_digest"):
        raise CleanupRefusal("Docker inventory or repository revision changed")
    actions: list[JsonValue] = []
    for candidate in _records(fresh.get("candidates"), "candidates"):
        operation = candidate.get("operation")
        try:
            if operation == "remove_container":
                target_name = "container_id"
                target_id = _required_string(candidate.get(target_name), target_name)
                remove_container(target_id)
            elif operation == "remove_image":
                target_name = "image_id"
                target_id = _required_image_id(candidate.get(target_name))
                remove_image(target_id)
            else:
                raise CleanupRefusal("candidate operation is invalid")
        except subprocess.CalledProcessError as error:
            actions.append(
                {
                    target_name: target_id,
                    "operation": operation if isinstance(operation, str) else "invalid",
                    "status": "failed",
                }
            )
            result = dict(fresh)
            result.update({"actions": actions, "failure": str(error), "terminal_status": "refused"})
            _emit(result)
            return 1
        actions.append({target_name: target_id, "operation": operation, "status": "removed"})
    result = dict(fresh)
    result.update({"actions": actions, "terminal_status": "succeeded"})
    _emit(result)
    return 0


def _inspect_image(image_id: str) -> dict[str, JsonValue]:
    document = _inspect((*DOCKER_COMMAND, "image", "inspect", image_id))
    config = document.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    string_labels = _string_map(labels)
    json_labels: dict[str, JsonValue] | None = (
        None if string_labels is None else {key: value for key, value in string_labels.items()}
    )
    return {
        "image_id": _required_image_id(document.get("Id")),
        "labels": json_labels,
        "repo_tags": list(_string_list(document.get("RepoTags"), "repo tags", allow_none=True)),
    }


def _inspect_container(container_id: str) -> dict[str, JsonValue]:
    document = _inspect((*DOCKER_COMMAND, "container", "inspect", container_id))
    state = document.get("State")
    return {
        "container_id": _required_string(document.get("Id"), "container ID"),
        "image_id": _required_image_id(document.get("Image")),
        "state": _required_string(
            state.get("Status") if isinstance(state, dict) else None,
            "container state",
        ),
    }


def _inspect(command: Sequence[str]) -> dict[str, JsonValue]:
    value = json.loads(command_output(command))
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise CleanupRefusal("Docker inspect must return exactly one record")
    return value[0]


def _verify_plan(plan: dict[str, JsonValue]) -> None:
    digest = plan.get("plan_digest")
    if plan.get("provider") != PROVIDER or plan.get("schema") != SCHEMA:
        raise CleanupRefusal("persisted plan provider or schema is invalid")
    if not isinstance(digest, str):
        raise CleanupRefusal("persisted plan digest is invalid")
    unsigned = dict(plan)
    del unsigned["plan_digest"]
    if _digest(unsigned) != digest:
        raise CleanupRefusal("persisted plan digest does not match its facts")


def _read_plan(path: Path) -> dict[str, JsonValue]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise CleanupRefusal("persisted plan must be an object")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean repository-owned Sir Docker assets")
    parser.add_argument("mode", choices=("plan", "apply"), nargs="?", default="plan")
    parser.add_argument("--pin-image-id", action="append", default=[])
    parser.add_argument("--plan", type=Path)
    return parser


def _digest(value: dict[str, JsonValue]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _records(value: JsonValue | None, name: str) -> list[dict[str, JsonValue]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise CleanupRefusal(f"{name} must be a list of objects")
    return [item for item in value if isinstance(item, dict)]


def _string_map(value: JsonValue | None) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(item, str) for key, item in value.items()
    ):
        return None
    return {key: item for key, item in value.items() if isinstance(item, str)}


def _string_list(
    value: JsonValue | None,
    name: str,
    *,
    allow_none: bool = False,
) -> tuple[str, ...]:
    if allow_none and value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise CleanupRefusal(f"{name} must be a list of strings")
    return tuple(item for item in value if isinstance(item, str))


def _required_string(value: JsonValue | None, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise CleanupRefusal(f"{name} is missing")
    return value


def _required_image_id(value: JsonValue | None) -> str:
    image_id = _required_string(value, "image ID")
    if _IMAGE_ID.fullmatch(image_id) is None:
        raise CleanupRefusal("image ID is malformed")
    return image_id


def _lines(value: str, *, unique: bool = False) -> tuple[str, ...]:
    lines = tuple(line.strip() for line in value.splitlines() if line.strip())
    return tuple(sorted(set(lines))) if unique else lines


def _image_sort_key(value: JsonValue) -> str:
    if not isinstance(value, dict):
        raise CleanupRefusal("image record is malformed")
    return _required_image_id(value.get("image_id"))


def _container_sort_key(value: JsonValue) -> str:
    if not isinstance(value, dict):
        raise CleanupRefusal("container record is malformed")
    return _required_string(value.get("container_id"), "container ID")


def _candidate_sort_key(value: JsonValue) -> tuple[int, str]:
    if not isinstance(value, dict):
        raise CleanupRefusal("candidate record is malformed")
    operation = value.get("operation")
    if operation == "remove_container":
        return 0, _required_string(value.get("container_id"), "container ID")
    if operation == "remove_image":
        return 1, _required_image_id(value.get("image_id"))
    raise CleanupRefusal("candidate operation is invalid")


def _evidence_sort_key(value: JsonValue) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise CleanupRefusal("evidence record is malformed")
    return (
        _required_image_id(value.get("image_id")),
        _required_string(value.get("reason"), "reason"),
    )


def _emit(value: dict[str, JsonValue]) -> None:
    json.dump(value, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
