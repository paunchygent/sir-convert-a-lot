"""Focused tests for bounded Qwen text-gradient RCA helpers.

Purpose:
    Verify that the RCA helpers map non-finite text gradients back to token ids,
    row provenance, and optimizer-step forensic summaries without a live GPU
    run.

Relationships:
    - Exercises `sft_12hz_gradient_rca.py`.
    - Exercises the gradient-aware additions to `sft_12hz_forensics.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    build_microbatch_forensics,
    build_optimizer_step_forensics_window,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_gradient_rca import (
    build_gradient_rca_forensics,
)
from tests.sir_convert_a_lot.ml.qwen.training.training_test_support import _FakeQwenModel


def test_build_gradient_rca_forensics_maps_rows_tokens_and_full_text_context(
    tmp_path: Path,
) -> None:
    """The RCA payload should map non-finite rows back to token ids and text."""
    manifest_path = tmp_path / "manifests/train.jsonl"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps({"text": "Hej världen igen"}) + "\n",
        encoding="utf-8",
    )
    model = _FakeQwenModel(embedding_dim=4)
    input_text_ids = torch.tensor([[1, 2, 3]], dtype=torch.long)
    input_text_embedding = model.talker.get_text_embeddings()(input_text_ids)
    input_text_embedding.retain_grad()
    input_text_embedding.sum().backward()
    assert input_text_embedding.grad is not None
    input_text_embedding.grad[0, 1, 0] = float("nan")
    text_embedding_weight = model.talker.model.text_embedding.embedding.weight
    assert text_embedding_weight.grad is not None
    text_embedding_weight.grad[2, 0] = float("nan")

    payload = build_gradient_rca_forensics(
        model=model,
        input_text_ids=input_text_ids,
        input_text_embedding=input_text_embedding,
        batch_provenance=[
            {
                "row_id": "train#1",
                "manifest_path": manifest_path.as_posix(),
                "manifest_line_number": 1,
                "speaker_id": "speaker-a",
                "text_preview": "Hej världen igen",
            }
        ],
    )

    assert payload["first_non_finite_surface"] == "input_text_embedding.grad"
    assert payload["input_gradient_precedes_parameter_rows"] is None
    parameter_payload = payload["text_embedding_parameter_gradient"]
    assert isinstance(parameter_payload, dict)
    assert parameter_payload["non_finite_row_ids"] == [2]
    input_payload = payload["input_text_embedding_gradient"]
    assert isinstance(input_payload, dict)
    sample_payload = input_payload["samples"][0]
    assert sample_payload["non_finite_token_positions"] == [1]
    assert sample_payload["non_finite_token_ids"] == [2]
    assert sample_payload["parameter_row_ids_present_in_sample"] == [2]
    assert sample_payload["full_text"] == "Hej världen igen"


def test_build_gradient_rca_forensics_flags_upstream_input_gradient_first() -> None:
    """Input-text gradients should win the precedence signal when rows stay finite."""
    model = _FakeQwenModel(embedding_dim=4)
    input_text_ids = torch.tensor([[4, 5, 6]], dtype=torch.long)
    input_text_embedding = model.talker.get_text_embeddings()(input_text_ids)
    input_text_embedding.retain_grad()
    input_text_embedding.sum().backward()
    assert input_text_embedding.grad is not None
    input_text_embedding.grad[0, 2, 0] = float("nan")

    payload = build_gradient_rca_forensics(
        model=model,
        input_text_ids=input_text_ids,
        input_text_embedding=input_text_embedding,
        batch_provenance=None,
    )

    assert payload["first_non_finite_surface"] == "input_text_embedding.grad"
    assert payload["input_gradient_precedes_parameter_rows"] is True
    parameter_payload = payload["text_embedding_parameter_gradient"]
    assert isinstance(parameter_payload, dict)
    assert parameter_payload["non_finite_row_ids"] == []


def test_optimizer_step_forensics_window_surfaces_first_gradient_boundary() -> None:
    """Optimizer-step forensics should expose the first bad gradient microbatch."""
    stable_microbatch = build_microbatch_forensics(
        train_iteration=801,
        microbatch_index_in_optimizer_step=1,
        batch_provenance=None,
        probes=[("main_loss", torch.tensor(1.0, dtype=torch.float32))],
        gradient_forensics={
            "first_non_finite_surface": None,
        },
    )
    failing_microbatch = build_microbatch_forensics(
        train_iteration=804,
        microbatch_index_in_optimizer_step=4,
        batch_provenance=None,
        probes=[("main_loss", torch.tensor(1.0, dtype=torch.float32))],
        gradient_forensics={
            "first_non_finite_surface": "text_embedding.weight.grad",
        },
    )

    payload = build_optimizer_step_forensics_window(
        microbatches=[stable_microbatch, failing_microbatch]
    )

    assert payload["first_non_finite_gradient_surface"] == "text_embedding.weight.grad"
    assert payload["first_non_finite_gradient_train_iteration"] == 804
