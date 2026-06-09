"""Detached-status markdown renderer scaffold for Qwen control-plane flows.

Purpose:
    Host the bounded rendering implementation that projects `DetachedStatus`
    into deterministic operator-facing markdown.

Relationships:
    - Implements `StatusMarkdownRendererPort`.
    - Used by status-use-case artifact persistence surfaces.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.models import DetachedStatus

from .metadata_ports import StatusMarkdownRendererPort


class DetachedStatusMarkdownRenderer(StatusMarkdownRendererPort):
    """Renderer implementation scaffold for detached status markdown output.

    This scaffold intentionally has no runtime wiring yet. launch metadata persistence owns the
    bounded markdown rendering implementation for detached status payloads.
    """

    def render(self, status: DetachedStatus) -> str:
        """Render one detached status markdown summary."""
        del status
        raise NotImplementedError("Detached status markdown rendering implementation is pending.")
