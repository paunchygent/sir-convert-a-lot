"""DI-friendly metadata service bundle for Qwen control-plane composition.

Purpose:
    Group metadata ports into one dependency object that can be wired by the
    CLI composition root (including future Dishka provider wiring).

Relationships:
    - Consumed by control-plane command handlers during dependency wiring.
    - Depends on contracts from `metadata_ports`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .metadata_ports import (
    ArtifactWriterPort,
    LaunchMetadataLoaderPort,
    LaunchPointerResolverPort,
    StatusMarkdownRendererPort,
)


@dataclass(frozen=True)
class MetadataServices:
    """Container for metadata-related control-plane dependencies."""

    launch_loader: LaunchMetadataLoaderPort
    pointer_resolver: LaunchPointerResolverPort
    artifact_writer: ArtifactWriterPort
    status_renderer: StatusMarkdownRendererPort
