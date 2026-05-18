"""Structured provider failure diagnostics.

Purpose:
    Define redacted provider-error diagnostics that preserve operational
    routing evidence without storing prompts, item text, raw images, API keys,
    request payloads, or raw provider responses.

Relationships:
    - Attached to `StructuredLLMProviderError` values raised by HTTP provider
      adapters.
    - Serialized by answer-key advisory and microprobe reports when provider
      execution fails before a structured response can be decoded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StructuredLLMProviderErrorDiagnostic:
    """Redacted provider HTTP error fields for operator triage."""

    status_code: int | None
    request_id: str | None
    error_type: str | None
    error_code: str | None
    error_param: str | None
    message_sha256: str | None
