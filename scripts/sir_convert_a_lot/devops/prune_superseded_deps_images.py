"""Prune superseded Docker dependency-image tags for service build lanes.

Purpose:
    Provide a repository-agnostic Docker cleanup command that removes only old
    dependency-image tags after callers provide explicit repositories and keep
    tags for the newly built dependency image.

Relationships:
    - Called by Sir Convert-a-Lot service dependency-image builds after a
      successful CPU or ROCm dependency-image build.
    - Safe for other repositories because repository names and keep tags are
      explicit command-line inputs, not Sir Convert defaults.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DockerImage:
    """A tagged Docker image row from the Docker CLI."""

    repository: str
    tag: str
    image_id: str

    @property
    def ref(self) -> str:
        """Return the `repository:tag` Docker reference."""
        return f"{self.repository}:{self.tag}"

    @property
    def is_tagged(self) -> bool:
        """Return whether the row is a named, tagged image."""
        return self.repository != "<none>" and self.tag != "<none>"


@dataclass(frozen=True, slots=True)
class PrunePlan:
    """Refs selected for removal and refs deliberately protected."""

    refs_to_remove: tuple[str, ...]
    protected_refs: tuple[str, ...]


def parse_image_rows(output: str) -> tuple[DockerImage, ...]:
    """Parse Docker image rows emitted as repository, tag, and ID columns."""
    images: list[DockerImage] = []
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        fields = stripped.split("\t")
        if len(fields) != 3:
            raise ValueError(f"Unexpected docker image row: {line}")
        images.append(DockerImage(fields[0], fields[1], fields[2]))
    return tuple(images)


def plan_prune(
    *,
    images: Sequence[DockerImage],
    repositories: set[str],
    keep_tags: set[str],
    protected_image_ids: set[str],
) -> PrunePlan:
    """Select old dependency-image refs while protecting current image IDs."""
    refs_to_remove: list[str] = []
    protected_refs: list[str] = []

    for image in images:
        if not image.is_tagged or image.repository not in repositories:
            continue
        if image.tag in keep_tags or image.image_id in protected_image_ids:
            protected_refs.append(image.ref)
            continue
        refs_to_remove.append(image.ref)

    return PrunePlan(
        refs_to_remove=tuple(sorted(refs_to_remove)),
        protected_refs=tuple(sorted(protected_refs)),
    )


def docker_output(args: Sequence[str]) -> str:
    """Run Docker and return stdout text."""
    completed = subprocess.run(
        list(args),
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def list_local_images() -> tuple[DockerImage, ...]:
    """Return local Docker images with full image IDs."""
    output = docker_output(
        (
            "docker",
            "image",
            "ls",
            "--no-trunc",
            "--format",
            "{{.Repository}}\t{{.Tag}}\t{{.ID}}",
        )
    )
    return parse_image_rows(output)


def inspect_image_id(image_ref: str) -> str | None:
    """Resolve an image reference to a Docker image ID if it exists locally."""
    completed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image_ref],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    image_id = completed.stdout.strip()
    if not image_id:
        return None
    return image_id


def collect_running_image_ids() -> set[str]:
    """Resolve running container image refs to protected Docker image IDs."""
    output = docker_output(("docker", "ps", "--format", "{{.Image}}"))
    protected_ids: set[str] = set()
    for image_ref in output.splitlines():
        stripped = image_ref.strip()
        if not stripped:
            continue
        image_id = inspect_image_id(stripped)
        if image_id is not None:
            protected_ids.add(image_id)
    return protected_ids


def collect_keep_image_ids(repositories: set[str], keep_tags: set[str]) -> set[str]:
    """Resolve explicit repository:tag keep pairs to protected image IDs."""
    protected_ids: set[str] = set()
    for repository in sorted(repositories):
        for tag in sorted(keep_tags):
            image_id = inspect_image_id(f"{repository}:{tag}")
            if image_id is not None:
                protected_ids.add(image_id)
    return protected_ids


def remove_refs(refs: Sequence[str]) -> None:
    """Remove Docker image refs without forcing protected image IDs away."""
    for ref in refs:
        subprocess.run(["docker", "image", "rm", ref], check=True)


def parse_tag_list(raw_tags: Sequence[str]) -> set[str]:
    """Parse repeated or comma-separated tag CLI values."""
    tags: set[str] = set()
    for raw_tag in raw_tags:
        for tag in raw_tag.split(","):
            stripped = tag.strip()
            if stripped:
                tags.add(stripped)
    return tags


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the cleanup helper."""
    parser = argparse.ArgumentParser(
        description=(
            "Prune old tagged Docker dependency images for explicit repositories "
            "after newer keep tags exist."
        )
    )
    parser.add_argument(
        "--repository",
        action="append",
        required=True,
        help="Dependency-image repository to clean; repeat for multiple repos.",
    )
    parser.add_argument(
        "--keep-tag",
        action="append",
        required=True,
        help="Tag to protect, such as local or a newly built content hash.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually remove selected refs. Without this flag, only print a dry run.",
    )
    return parser


def run(argv: Sequence[str]) -> int:
    """Run the cleanup helper and return a process exit code."""
    args = build_parser().parse_args(argv)
    repositories = set(args.repository)
    keep_tags = parse_tag_list(args.keep_tag)
    images = list_local_images()
    protected_image_ids = collect_running_image_ids()
    protected_image_ids.update(collect_keep_image_ids(repositories, keep_tags))
    plan = plan_prune(
        images=images,
        repositories=repositories,
        keep_tags=keep_tags,
        protected_image_ids=protected_image_ids,
    )

    mode = "Removing" if args.execute else "Would remove"
    if not plan.refs_to_remove:
        print("No superseded dependency image tags found.")
        return 0

    for ref in plan.refs_to_remove:
        print(f"{mode} superseded dependency image tag: {ref}")
    if args.execute:
        remove_refs(plan.refs_to_remove)
    return 0


def main() -> None:
    """Process CLI arguments for direct module execution."""
    try:
        raise SystemExit(run(sys.argv[1:]))
    except subprocess.CalledProcessError as exc:
        print(f"Docker command failed with exit code {exc.returncode}.", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc


if __name__ == "__main__":
    main()
