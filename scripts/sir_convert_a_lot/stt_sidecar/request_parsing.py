"""Request parsing helpers for the STT sidecar.

Purpose:
    Validate the internal JSON request shape received from the main service
    before the speech runtime touches local media paths or backend pipelines.

Relationships:
    - Used by `stt_sidecar.runtime`.
    - Raises `SttSidecarRequestError` so the FastAPI factory can return
      deterministic client-safe errors.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError


def mapping_at(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    """Return a nested mapping or raise a client-safe validation error."""
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise SttSidecarRequestError(
            code="invalid_request",
            message=f"{key} must be an object.",
            status_code=422,
        )
    return {str(nested_key): nested_value for nested_key, nested_value in value.items()}


def required_string(payload: Mapping[str, object], key: str) -> str:
    """Return a non-empty string field or raise a validation error."""
    value = payload.get(key)
    if isinstance(value, str) and value.strip() != "":
        return value
    raise SttSidecarRequestError(
        code="invalid_request",
        message=f"{key} is required.",
        status_code=422,
    )


def optional_int(payload: Mapping[str, object], key: str) -> int | None:
    """Return an optional integer field or raise a validation error."""
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    raise SttSidecarRequestError(
        code="invalid_request",
        message=f"{key} must be an integer when provided.",
        status_code=422,
    )


def source_path(request: Mapping[str, object]) -> Path:
    """Resolve the shared local-upload path from a transcribe request."""
    source = mapping_at(request, "source")
    if required_string(source, "kind") != "local_upload":
        raise SttSidecarRequestError(
            code="audio_input_protocol_unsupported",
            message="Only local_upload sources are supported.",
            status_code=422,
        )
    path = Path(required_string(source, "path"))
    if not path.is_file():
        raise SttSidecarRequestError(
            code="audio_stream_missing",
            message="Uploaded audio source is not available to the sidecar.",
            status_code=422,
        )
    return path


def language_option(options: Mapping[str, object]) -> str | None:
    """Return the backend language hint for public language options."""
    language = required_string(options, "language")
    if language == "auto":
        return None
    if language in {"sv", "en"}:
        return language
    raise SttSidecarRequestError(
        code="audio_public_options_unsupported",
        message="Unsupported language option.",
        status_code=422,
    )
