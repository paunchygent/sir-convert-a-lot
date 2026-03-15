"""Shared Qwen talker-surface resolution helpers for patched training code.

Purpose:
    Centralize how the patched training, evaluation, and optimizer-guard
    surfaces resolve text/codec embedding and projection modules so runtime
    assumptions stay aligned with the upstream Qwen talker layout.

Relationships:
    - Imported by `sft_12hz_train_step.py`, `sft_12hz_eval.py`, and
      `sft_12hz_optimizer_guard.py`.
    - Mirrors the upstream talker contract where embeddings are exposed via
      accessor methods and `text_projection` lives on `talker`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

import torch


@runtime_checkable
class _TensorCallable(Protocol):
    """Callable tensor surface used by the talker runtime resolvers."""

    def __call__(self, values: torch.Tensor) -> torch.Tensor:
        """Resolve one tensor-valued transformation."""


def resolve_talker_text_embedding(model: object) -> Callable[[torch.Tensor], torch.Tensor]:
    """Return the canonical text-embedding callable for one Qwen talker."""
    resolved = _resolve_talker_embedding_surface(
        model=model,
        accessor_name="get_text_embeddings",
        fallback_attribute_name="text_embedding",
    )
    if resolved is None:
        raise AttributeError("Qwen talker does not expose a usable text-embedding surface.")
    return resolved


def resolve_talker_codec_embedding(model: object) -> Callable[[torch.Tensor], torch.Tensor]:
    """Return the canonical codec/input embedding callable for one Qwen talker."""
    resolved = _resolve_talker_embedding_surface(
        model=model,
        accessor_name="get_input_embeddings",
        fallback_attribute_name="codec_embedding",
    )
    if resolved is None:
        raise AttributeError("Qwen talker does not expose a usable codec-embedding surface.")
    return resolved


def resolve_talker_text_projection(
    model: object,
) -> Callable[[torch.Tensor], torch.Tensor] | None:
    """Return the optional text-projection callable for one Qwen talker."""
    talker = getattr(model, "talker", None)
    if talker is None:
        return None
    projection = getattr(talker, "text_projection", None)
    resolved_projection = _as_tensor_callable(projection)
    if resolved_projection is not None:
        return resolved_projection
    talker_model = getattr(talker, "model", None)
    fallback_projection = None if talker_model is None else getattr(talker_model, "text_projection", None)
    resolved_fallback_projection = _as_tensor_callable(fallback_projection)
    if resolved_fallback_projection is not None:
        return resolved_fallback_projection
    return None


def resolve_talker_text_embedding_module(model: object) -> torch.nn.Module | None:
    """Return the text-embedding module when the surface is probeable."""
    return _callable_to_module(resolve_talker_text_embedding(model))


def resolve_talker_text_projection_module(model: object) -> torch.nn.Module | None:
    """Return the optional text-projection module when the surface is probeable."""
    return _callable_to_module(resolve_talker_text_projection(model))


def _resolve_talker_embedding_surface(
    *,
    model: object,
    accessor_name: str,
    fallback_attribute_name: str,
) -> Callable[[torch.Tensor], torch.Tensor] | None:
    """Resolve one talker embedding surface from the upstream accessor or fallback."""
    talker = getattr(model, "talker", None)
    if talker is None:
        return None
    accessor = getattr(talker, accessor_name, None)
    if callable(accessor):
        resolved = accessor()
        resolved_callable = _as_tensor_callable(resolved)
        if resolved_callable is not None:
            return resolved_callable
    talker_model = getattr(talker, "model", None)
    fallback = None if talker_model is None else getattr(talker_model, fallback_attribute_name, None)
    resolved_fallback = _as_tensor_callable(fallback)
    if resolved_fallback is not None:
        return resolved_fallback
    return None


def _callable_to_module(
    resolved: Callable[[torch.Tensor], torch.Tensor] | None,
) -> torch.nn.Module | None:
    """Return the module when the resolved callable is probeable as a module."""
    if isinstance(resolved, torch.nn.Module):
        return resolved
    return None


def _as_tensor_callable(candidate: object) -> _TensorCallable | None:
    """Return the candidate when it matches the expected tensor callable shape."""
    if isinstance(candidate, _TensorCallable):
        return candidate
    return None
