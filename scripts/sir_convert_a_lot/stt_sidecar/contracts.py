"""Typed contracts for the internal STT sidecar.

Purpose:
    Define the protocol between the FastAPI sidecar app and backend runtimes so
    tests can exercise the HTTP surface without importing speech model
    dependencies.

Relationships:
    - Implemented by `stt_sidecar.runtime.SttSidecarRuntime`.
    - Consumed by `stt_sidecar.app_factory` to expose health, capability,
      media probe, diarization, chunk transcription, and cancellation
      endpoints.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class SttSidecarRequestError(RuntimeError):
    """Client-safe STT sidecar request failure."""

    def __init__(self, *, code: str, message: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SttSidecarBackend(Protocol):
    """Backend contract implemented by STT sidecar runtime adapters."""

    def startup(self) -> None:
        """Prepare the runtime to accept sidecar work."""

    def shutdown(self) -> None:
        """Release runtime-owned resources during sidecar shutdown."""

    def health(self) -> Mapping[str, object]:
        """Return the bounded health payload consumed by the main service."""

    def capabilities(self) -> Mapping[str, object]:
        """Return the bounded capability payload consumed by the main service."""

    def probe_media(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Probe and normalize one local-upload media request."""

    def diarize(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Run global diarization for normalized media."""

    def transcribe_chunk(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Transcribe one deterministic normalized-media chunk."""

    def cancel(self, request_handle: str) -> Mapping[str, object]:
        """Request cancellation for an in-flight transcription handle."""

    def finalize(self, request_handle: str) -> Mapping[str, object]:
        """Remove sidecar-owned normalized media for a terminal request."""
