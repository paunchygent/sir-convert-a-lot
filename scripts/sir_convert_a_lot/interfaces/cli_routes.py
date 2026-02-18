"""CLI route registry for Sir Convert-a-Lot.

Purpose:
    Define the canonical conversion route taxonomy used by the local CLI for
    selecting between service-backed, local, and hybrid pipelines.

Relationships:
    - Used by `scripts.sir_convert_a_lot.interfaces.cli_app` for route selection,
      `convert-a-lot routes`, and `--dry-run` diagnostics.
    - Must not expand the locked PDF-to-MD service v1 contract; multi-format
      routes are implemented via service API v2.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class SourceFormat(str, Enum):
    """Supported CLI source formats."""

    PDF = "pdf"
    MD = "md"
    HTML = "html"
    DOCX = "docx"


class TargetFormat(str, Enum):
    """Supported CLI target formats."""

    MD = "md"
    PDF = "pdf"
    DOCX = "docx"


class PipelineKind(str, Enum):
    """Execution kind for a CLI route."""

    SERVICE = "service"
    LOCAL = "local"
    HYBRID = "hybrid"


@dataclass(frozen=True)
class CliRoute:
    """Describes one CLI-visible conversion route."""

    source: SourceFormat
    target: TargetFormat
    pipeline_kind: PipelineKind
    implemented: bool
    pipeline_steps: tuple[str, ...]

    @property
    def key(self) -> tuple[str, str]:
        """Return a stable lookup key for the route."""

        return (self.source.value, self.target.value)

    @property
    def requires_service(self) -> bool:
        """Return whether this route requires calling the service."""

        return self.pipeline_kind in {PipelineKind.SERVICE, PipelineKind.HYBRID}


_ROUTES: tuple[CliRoute, ...] = (
    CliRoute(
        source=SourceFormat.PDF,
        target=TargetFormat.MD,
        pipeline_kind=PipelineKind.SERVICE,
        implemented=True,
        pipeline_steps=("service: pdf -> md (v1)",),
    ),
    CliRoute(
        source=SourceFormat.PDF,
        target=TargetFormat.DOCX,
        pipeline_kind=PipelineKind.SERVICE,
        implemented=True,
        pipeline_steps=("service: pdf -> docx (v2)",),
    ),
    CliRoute(
        source=SourceFormat.MD,
        target=TargetFormat.PDF,
        pipeline_kind=PipelineKind.SERVICE,
        implemented=True,
        pipeline_steps=("service: md -> pdf (v2)",),
    ),
    CliRoute(
        source=SourceFormat.MD,
        target=TargetFormat.DOCX,
        pipeline_kind=PipelineKind.SERVICE,
        implemented=True,
        pipeline_steps=("service: md -> docx (v2)",),
    ),
    CliRoute(
        source=SourceFormat.HTML,
        target=TargetFormat.PDF,
        pipeline_kind=PipelineKind.SERVICE,
        implemented=True,
        pipeline_steps=("service: html -> pdf (v2)",),
    ),
    CliRoute(
        source=SourceFormat.HTML,
        target=TargetFormat.DOCX,
        pipeline_kind=PipelineKind.SERVICE,
        implemented=True,
        pipeline_steps=("service: html -> docx (v2)",),
    ),
)


def list_routes() -> list[CliRoute]:
    """Return all known routes in a stable order."""

    return list(_ROUTES)


def resolve_route(*, source: SourceFormat, target: TargetFormat) -> CliRoute | None:
    """Resolve one route from source and target formats."""

    for route in _ROUTES:
        if route.source == source and route.target == target:
            return route
    return None


def infer_source_format_from_path(path: Path) -> SourceFormat | None:
    """Infer source format from a file path extension."""

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return SourceFormat.PDF
    if suffix in {".md", ".markdown"}:
        return SourceFormat.MD
    if suffix in {".html", ".htm"}:
        return SourceFormat.HTML
    if suffix == ".docx":
        return SourceFormat.DOCX
    return None
