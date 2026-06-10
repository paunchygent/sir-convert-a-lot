"""Internal STT sidecar client boundary for transcript-bundle execution.

Purpose:
    Define the provider-neutral sidecar port used by the main Service API v2
    runtime to check readiness, request transcription, and propagate
    cancellation without importing speech model or diarization runtimes.

Relationships:
    - Consumed by `infrastructure.audio_transcript_bundle_runtime`.
    - Instantiated by `infrastructure.runtime_engine_v2` from service config.
    - Maps HTTP transport failures to governed audio route errors.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

import httpx

from scripts.sir_convert_a_lot.domain.audio_transcription_contracts import (
    AudioTranscriptionErrorCode,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceError


class AudioTranscriptionSidecarClient(Protocol):
    """Provider-neutral main-service port for the internal STT sidecar."""

    def health(self) -> Mapping[str, object]:
        """Return sidecar health/readiness truth."""

    def capabilities(self) -> Mapping[str, object]:
        """Return sidecar capability truth."""

    def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
        """Run one transcription request and return deterministic JSON."""

    def cancel(self, request_handle: str) -> None:
        """Request cancellation for an in-flight sidecar handle."""


class UnconfiguredAudioTranscriptionSidecarClient:
    """Fail-closed sidecar port used when no internal sidecar URL is configured."""

    def health(self) -> Mapping[str, object]:
        raise _sidecar_unavailable("sidecar_base_url_not_configured")

    def capabilities(self) -> Mapping[str, object]:
        raise _sidecar_unavailable("sidecar_base_url_not_configured")

    def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
        del request
        raise _sidecar_unavailable("sidecar_base_url_not_configured")

    def cancel(self, request_handle: str) -> None:
        del request_handle


class HttpAudioTranscriptionSidecarClient:
    """Synchronous HTTP adapter for the internal STT sidecar contract."""

    def __init__(self, *, base_url: str, timeout_seconds: float) -> None:
        normalized_base_url = base_url.rstrip("/")
        self._base_url = normalized_base_url
        bounded_timeout_seconds = max(0.1, timeout_seconds)
        self._timeout = httpx.Timeout(
            bounded_timeout_seconds,
            connect=min(5.0, bounded_timeout_seconds),
            read=bounded_timeout_seconds,
            write=bounded_timeout_seconds,
            pool=min(5.0, bounded_timeout_seconds),
        )

    def health(self) -> Mapping[str, object]:
        return self._get_json("/health")

    def capabilities(self) -> Mapping[str, object]:
        return self._get_json("/capabilities")

    def transcribe(self, request: Mapping[str, object]) -> Mapping[str, object]:
        return self._post_json("/transcribe", payload=request)

    def cancel(self, request_handle: str) -> None:
        try:
            self._post_json("/cancel", payload={"request_handle": request_handle})
        except ServiceError:
            return

    def _get_json(self, path: str) -> Mapping[str, object]:
        with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
            try:
                response = client.get(path)
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise _sidecar_unavailable("sidecar_timeout") from exc
            except httpx.RequestError as exc:
                raise _sidecar_unavailable("sidecar_request_failed") from exc
            except httpx.HTTPStatusError as exc:
                raise _sidecar_unavailable(
                    "sidecar_http_status",
                    status_code=str(exc.response.status_code),
                ) from exc
        return _response_json_object(response)

    def _post_json(self, path: str, *, payload: Mapping[str, object]) -> Mapping[str, object]:
        with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
            try:
                response = client.post(path, json=dict(payload))
                response.raise_for_status()
            except httpx.TimeoutException as exc:
                raise _sidecar_unavailable("sidecar_timeout") from exc
            except httpx.RequestError as exc:
                raise _sidecar_unavailable("sidecar_request_failed") from exc
            except httpx.HTTPStatusError as exc:
                raise _sidecar_unavailable(
                    "sidecar_http_status",
                    status_code=str(exc.response.status_code),
                ) from exc
        return _response_json_object(response)


def build_audio_transcription_sidecar_client(
    *,
    base_url: str | None,
    timeout_seconds: float,
) -> AudioTranscriptionSidecarClient:
    """Build the configured STT sidecar client, failing closed when absent."""

    if base_url is None or base_url.strip() == "":
        return UnconfiguredAudioTranscriptionSidecarClient()
    return HttpAudioTranscriptionSidecarClient(
        base_url=base_url.strip(),
        timeout_seconds=timeout_seconds,
    )


def _response_json_object(response: httpx.Response) -> Mapping[str, object]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise _sidecar_unavailable("sidecar_non_json_response") from exc
    if not isinstance(payload, Mapping):
        raise _sidecar_unavailable("sidecar_json_response_not_object")
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def _sidecar_unavailable(reason: str, **details: str) -> ServiceError:
    normalized_details: dict[str, object] = {"reason": reason}
    normalized_details.update(details)
    return ServiceError(
        status_code=503,
        code=AudioTranscriptionErrorCode.SIDECAR_UNAVAILABLE.value,
        message="Audio transcription sidecar is unavailable.",
        retryable=True,
        details=normalized_details,
    )
