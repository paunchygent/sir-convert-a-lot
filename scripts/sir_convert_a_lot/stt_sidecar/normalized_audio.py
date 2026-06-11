"""Sidecar-owned normalized audio capability storage.

Purpose:
    Track normalized media created by the STT sidecar after probe/normalization
    and resolve it only through opaque request-scoped handles for diarization
    and chunk transcription.

Relationships:
    - Used by `stt_sidecar.runtime` to keep filesystem capabilities out of the
      main Service API v2 runtime contract.
    - Raises `SttSidecarRequestError` for deterministic client-safe failures
      returned by `stt_sidecar.app_factory`.
"""

from __future__ import annotations

import hashlib
import shutil
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError
from scripts.sir_convert_a_lot.stt_sidecar.request_parsing import (
    mapping_at,
    required_string,
)


@dataclass(frozen=True, slots=True)
class NormalizedAudioHandle:
    """Opaque sidecar capability issued after media probe."""

    handle: str
    request_handle: str
    path: Path
    directory: Path
    sha256: str


class NormalizedAudioStore:
    """Track and verify sidecar-owned normalized media handles."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = threading.Lock()
        self._handles: dict[str, NormalizedAudioHandle] = {}

    def path_for(self, *, request_handle: str, source_path: Path) -> Path:
        """Return the deterministic job-scoped normalized path for a source."""

        digest = hashlib.sha256(
            f"{request_handle}:{source_path.as_posix()}".encode("utf-8")
        ).hexdigest()
        normalized_dir = self._root / digest
        normalized_dir.mkdir(parents=True, exist_ok=True)
        return normalized_dir / "normalized.wav"

    def remember(
        self,
        *,
        request_handle: str,
        normalized_path: Path,
    ) -> NormalizedAudioHandle:
        """Record a normalized file and return the opaque capability."""

        normalized_sha = f"sha256:{hashlib.sha256(normalized_path.read_bytes()).hexdigest()}"
        handle = f"sir-stt-normalized:{normalized_path.parent.name}"
        normalized_audio = NormalizedAudioHandle(
            handle=handle,
            request_handle=request_handle,
            path=normalized_path,
            directory=normalized_path.parent,
            sha256=normalized_sha,
        )
        with self._lock:
            self._handles[handle] = normalized_audio
        return normalized_audio

    def resolve(self, request: Mapping[str, object]) -> NormalizedAudioHandle:
        """Resolve and verify the normalized media capability in a request."""

        request_handle = required_string(request, "request_handle")
        normalized_audio = mapping_at(request, "normalized_audio")
        requested_handle = required_string(normalized_audio, "handle")
        requested_sha = required_string(normalized_audio, "sha256")
        with self._lock:
            stored = self._handles.get(requested_handle)
        if stored is None or stored.request_handle != request_handle:
            raise SttSidecarRequestError(
                code="audio_stream_missing",
                message="Normalized audio handle is not available for this request.",
                status_code=422,
            )
        if not stored.path.is_file():
            raise SttSidecarRequestError(
                code="audio_stream_missing",
                message="Normalized audio source is not available to the sidecar.",
                status_code=422,
            )
        actual_sha = f"sha256:{hashlib.sha256(stored.path.read_bytes()).hexdigest()}"
        if requested_sha != stored.sha256 or actual_sha != stored.sha256:
            raise SttSidecarRequestError(
                code="audio_normalization_failed",
                message="Normalized audio hash does not match the probed media.",
                status_code=422,
            )
        return stored

    def finalize(self, request_handle: str) -> int:
        """Remove all normalized media tracked for one terminal request."""

        removed = 0
        with self._lock:
            handles = [
                handle
                for handle in self._handles.values()
                if handle.request_handle == request_handle
            ]
            for handle in handles:
                self._handles.pop(handle.handle, None)
        for handle in handles:
            if handle.directory.exists():
                shutil.rmtree(handle.directory)
                removed += 1
        return removed
