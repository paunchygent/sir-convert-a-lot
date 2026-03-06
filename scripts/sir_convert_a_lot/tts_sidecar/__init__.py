"""Normalized internal TTS sidecar adapters.

Purpose:
    Provide the reusable internal contract and backend-specific adapter apps
    used to benchmark and eventually integrate sidecar-backed text-to-speech
    services with Sir Convert-a-Lot.

Relationships:
    - Implements the ADR-0007 internal capability contract for sidecars.
    - Keeps backend-native runtime details out of the main v2 HTTP service.
"""
