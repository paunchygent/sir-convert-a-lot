"""Focused tests for shared Qwen talker-runtime resolution.

Purpose:
    Verify that the centralized talker-runtime resolver reports the resolved
    surface paths and probeability truth for the supported compatibility
    shapes.

Relationships:
    - Exercises `sft_12hz_talker_runtime.py` directly.
    - Guards the shared runtime contract used by train, eval, and optimizer
      probes.
"""

from __future__ import annotations

from types import SimpleNamespace

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    resolve_talker_text_projection,
    resolve_talker_text_projection_module,
    talker_runtime_fingerprint,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
)


class _CallableProjection:
    """Callable projection double that is not probeable as an nn.Module."""

    def __call__(self, values: torch.Tensor) -> torch.Tensor:
        return values


class _FakeTalkerModel:
    """Minimal talker-model surface for talker-runtime resolver tests."""

    def __init__(self) -> None:
        self.text_embedding = torch.nn.Embedding(8, 4)
        self.codec_embedding = torch.nn.Embedding(8, 4)


class _FakeTalker:
    """Minimal talker surface with configurable projection placement."""

    def __init__(self) -> None:
        self.model = _FakeTalkerModel()
        self.text_projection: object | None = None

    def get_text_embeddings(self) -> object:
        return self.model.text_embedding

    def get_input_embeddings(self) -> object:
        return self.model.codec_embedding


def _build_model() -> SimpleNamespace:
    """Build one compact fake Qwen model namespace."""
    return SimpleNamespace(talker=_FakeTalker())


def _required_mapping(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return one nested mapping from a fingerprint payload."""
    resolved = payload[key]
    assert isinstance(resolved, dict)
    return resolved


def test_talker_runtime_fingerprint_prefers_talker_level_projection() -> None:
    """Fingerprinting should prefer the upstream talker-level projection path."""
    model = _build_model()
    projection = torch.nn.Linear(4, 4)
    model.talker.text_projection = projection
    model.talker.model.text_projection = torch.nn.Linear(4, 4)

    payload = talker_runtime_fingerprint(
        model,
        text_embedding_assembly_mode=FULL_CHANNEL_MASKED_TEXT_EMBEDDING_ASSEMBLY_MODE,
        text_embedding_mask_policy=TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    )
    text_embedding = _required_mapping(payload, "text_embedding")
    codec_embedding = _required_mapping(payload, "codec_embedding")
    text_projection = _required_mapping(payload, "text_projection")

    assert payload["text_embedding_assembly_mode"] == "full_channel_masked"
    assert payload["text_embedding_mask_policy"] == "text_span_only"
    assert text_embedding["resolved_path"] == "model.talker.get_text_embeddings()"
    assert codec_embedding["resolved_path"] == "model.talker.get_input_embeddings()"
    assert text_projection["resolved_path"] == "model.talker.text_projection"
    assert text_projection["probeable_as_module"] is True
    assert resolve_talker_text_projection(model) is projection


def test_talker_runtime_fingerprint_falls_back_to_nested_projection() -> None:
    """Fingerprinting should report the nested compatibility path when needed."""
    model = _build_model()
    projection = torch.nn.Linear(4, 4)
    model.talker.model.text_projection = projection

    payload = talker_runtime_fingerprint(model)
    text_projection = _required_mapping(payload, "text_projection")

    assert payload["text_embedding_assembly_mode"] == "semantic_only"
    assert payload["text_embedding_mask_policy"] == "legacy_codec_span"
    assert text_projection["available"] is True
    assert text_projection["resolved_path"] == "model.talker.model.text_projection"
    assert text_projection["probeable_as_module"] is True
    assert resolve_talker_text_projection(model) is projection


def test_talker_runtime_fingerprint_reports_missing_projection() -> None:
    """Fingerprinting should make an absent projection surface explicit."""
    model = _build_model()

    payload = talker_runtime_fingerprint(model)
    text_projection = _required_mapping(payload, "text_projection")

    assert payload["text_embedding_assembly_mode"] == "semantic_only"
    assert payload["text_embedding_mask_policy"] == "legacy_codec_span"
    assert text_projection == {
        "available": False,
        "resolved_path": None,
        "probeable_as_module": False,
    }
    assert resolve_talker_text_projection(model) is None
    assert resolve_talker_text_projection_module(model) is None


def test_talker_runtime_fingerprint_marks_non_module_projection_unprobeable() -> None:
    """A callable projection should still resolve even when the guard cannot probe it."""
    model = _build_model()
    projection = _CallableProjection()
    model.talker.text_projection = projection

    payload = talker_runtime_fingerprint(model)
    text_projection = _required_mapping(payload, "text_projection")

    assert payload["text_embedding_assembly_mode"] == "semantic_only"
    assert payload["text_embedding_mask_policy"] == "legacy_codec_span"
    assert text_projection["available"] is True
    assert text_projection["resolved_path"] == "model.talker.text_projection"
    assert text_projection["probeable_as_module"] is False
    assert resolve_talker_text_projection(model) is projection
    assert resolve_talker_text_projection_module(model) is None
