"""Docling runtime inventory for conversion diagnostics.

Purpose:
    Report sanitized package and Torch runtime facts for evidence-driven
    Docling PDF performance investigations.

Relationships:
    - Used by Docling page-window replay page-window replay reports.
    - Complements `infrastructure.docling_formula_diagnostics`.
"""

from __future__ import annotations

import importlib.metadata


def build_docling_runtime_inventory() -> dict[str, object]:
    """Return sanitized package and torch runtime facts for diagnostic replay."""
    payload: dict[str, object] = {
        "packages": {
            name: _package_version(name)
            for name in (
                "docling",
                "docling-core",
                "docling-ibm-models",
                "transformers",
                "torch",
                "accelerate",
            )
        }
    }
    try:
        import torch

        payload["torch"] = {
            "version": _string_or_none(getattr(torch, "__version__", None)),
            "hip": _string_or_none(getattr(getattr(torch, "version", None), "hip", None)),
            "cuda": _string_or_none(getattr(getattr(torch, "version", None), "cuda", None)),
            "cuda_is_available": bool(torch.cuda.is_available()),
            "cuda_device_count": int(torch.cuda.device_count()),
        }
    except Exception as exc:
        payload["torch"] = {"error_type": type(exc).__name__}
    return payload


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    return str(value)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None
