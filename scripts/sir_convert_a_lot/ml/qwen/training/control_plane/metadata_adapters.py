"""File-backed metadata adapter implementations for control-plane ports.

Purpose:
    Provide concrete file-backed adapter classes for metadata ports in the
    Qwen training control plane.

Relationships:
    - Implements `ArtifactWriterPort` and `LaunchPointerResolverPort`.
    - Reused by command handlers via composition-root dependency wiring.
"""

from __future__ import annotations

from pathlib import Path

from .artifact_writers import write_json, write_latest_pointer, write_markdown
from .launch_pointer_resolution import (
    load_latest_checkpoint,
    resolve_launch_root,
    validate_resume_checkpoint_path,
)
from .metadata_ports import ArtifactWriterPort, LaunchPointerResolverPort


class FileArtifactWriter(ArtifactWriterPort):
    """Concrete file-backed implementation of artifact writing ports."""

    def write_json(self, path: Path, payload: object) -> None:
        """Write one deterministic JSON artifact."""
        write_json(path, payload)

    def write_markdown(self, path: Path, markdown: str) -> None:
        """Write one deterministic markdown artifact."""
        write_markdown(path, markdown)

    def write_latest_pointer(self, output_root: Path, launch_root_path: Path) -> None:
        """Persist the latest-launch pointer for detached training control-plane commands."""
        write_latest_pointer(output_root, launch_root_path)


class FileLaunchPointerResolver(LaunchPointerResolverPort):
    """Concrete file-backed implementation of launch/checkpoint pointer resolution."""

    def resolve_launch_root(self, output_root: Path, launch_root_arg: Path | None) -> Path:
        """Resolve the effective launch root from args or latest-launch pointer."""
        return resolve_launch_root(output_root, launch_root_arg)

    def load_latest_checkpoint(self, run_root: Path) -> Path:
        """Resolve the latest-checkpoint pointer for one source run root."""
        return load_latest_checkpoint(run_root)

    def validate_resume_checkpoint_path(self, run_root: Path, checkpoint_path: Path) -> Path:
        """Validate explicit resume checkpoint ownership against one run root."""
        return validate_resume_checkpoint_path(run_root, checkpoint_path)
