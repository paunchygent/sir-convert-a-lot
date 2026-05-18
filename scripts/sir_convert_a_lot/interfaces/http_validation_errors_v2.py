"""Privacy-safe v2 request validation error projection.

Purpose:
    Convert FastAPI/Pydantic request validation failures into bounded v2 error
    details that preserve debugging location and type without echoing submitted
    payload values.

Relationships:
    - Used by `interfaces.http_api` for the global v2 request-validation
      exception handler.
    - Protects rich source-state and overlay request bodies from leaking raw
      student, provider, or source payload fragments in error envelopes.
"""

from __future__ import annotations

from fastapi.exceptions import RequestValidationError


def sanitized_request_validation_errors(
    exc: RequestValidationError,
) -> tuple[dict[str, object], ...]:
    """Return validation errors without raw input or context payload values."""

    return tuple(_sanitize_validation_error(error) for error in exc.errors())


def _sanitize_validation_error(error: object) -> dict[str, object]:
    if not isinstance(error, dict):
        return {"type": "validation_error", "msg": "Request validation failed."}

    sanitized: dict[str, object] = {}
    loc = _sanitize_location(error.get("loc"))
    if loc:
        sanitized["loc"] = loc

    error_type = error.get("type")
    if isinstance(error_type, str) and error_type.strip() != "":
        sanitized["type"] = error_type

    message = error.get("msg")
    if isinstance(message, str) and message.strip() != "":
        sanitized["msg"] = message

    if not sanitized:
        return {"type": "validation_error", "msg": "Request validation failed."}
    return sanitized


def _sanitize_location(value: object) -> tuple[str | int, ...]:
    if not isinstance(value, tuple | list):
        return ()
    parts: list[str | int] = []
    for part in value:
        if isinstance(part, str | int):
            parts.append(part)
        else:
            parts.append(str(part))
    return tuple(parts)
