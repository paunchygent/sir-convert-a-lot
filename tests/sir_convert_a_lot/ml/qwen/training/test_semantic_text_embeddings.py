"""Focused tests for semantic-only text-embedding assembly.

Purpose:
    Prove the Story 30 Candidate 1 contract locally by showing that only
    semantic text token ids can ever contribute row membership to
    `text_embedding.weight.grad`.

Relationships:
    - Exercises `sft_12hz_semantic_text_embeddings.py`.
    - Complements `test_train_step_runtime.py` and `test_eval_runtime.py` with
      a smaller-signal parameter-gradient proof before any new Hemma replay.
"""

from __future__ import annotations

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_semantic_text_embeddings import (
    assemble_semantic_text_embedding,
)


def _semantic_only_probe_layout() -> tuple[torch.Tensor, torch.Tensor, set[int]]:
    """Return one disjoint semantic/scaffold id layout for gradient proofs."""
    full_text_ids = torch.tensor(
        [[41, 42, 43, 44, 45, 46, 47, 48, 11, 13, 49, 50]],
        dtype=torch.long,
    )
    semantic_text_ids = full_text_ids[:, 8:10].clone()
    scaffold_ids = {int(token_id) for token_id in full_text_ids.view(-1).tolist()}
    scaffold_ids.difference_update({11, 13})
    return full_text_ids, semantic_text_ids, scaffold_ids


def _non_zero_gradient_row_ids(gradient: torch.Tensor) -> set[int]:
    """Return embedding row ids with any non-zero gradient contribution."""
    row_activity = gradient.detach().abs().sum(dim=1) > 0
    return {int(row_id) for row_id in row_activity.nonzero(as_tuple=False).view(-1).tolist()}


def _non_finite_gradient_row_ids(gradient: torch.Tensor) -> set[int]:
    """Return embedding row ids containing any non-finite gradient values."""
    row_activity = ~torch.isfinite(gradient.detach()).all(dim=1)
    return {int(row_id) for row_id in row_activity.nonzero(as_tuple=False).view(-1).tolist()}


def test_semantic_only_assembly_restricts_gradient_row_membership_to_semantic_ids() -> None:
    """Only semantic ids should receive parameter-gradient row membership."""
    _, semantic_text_ids, scaffold_ids = _semantic_only_probe_layout()
    embedding = torch.nn.Embedding(128, 4)
    semantic_text_positions = torch.tensor([[8, 9]], dtype=torch.long)
    semantic_text_mask = torch.tensor([[True, True]])

    assembled = assemble_semantic_text_embedding(
        text_embedding=embedding,
        semantic_text_ids=semantic_text_ids,
        semantic_text_positions=semantic_text_positions,
        semantic_text_mask=semantic_text_mask,
        sequence_length=12,
    )
    upstream_weights = torch.zeros_like(assembled)
    upstream_weights[:, 0, :] = 3.0
    upstream_weights[:, 8, :] = 1.0
    upstream_weights[:, 9, :] = -2.0
    upstream_weights[:, 10, :] = 5.0
    loss = (assembled * upstream_weights).sum()
    loss.backward()

    gradient = embedding.weight.grad
    assert gradient is not None
    assert _non_zero_gradient_row_ids(gradient) == {11, 13}
    assert _non_finite_gradient_row_ids(gradient) == set()
    assert _non_zero_gradient_row_ids(gradient).isdisjoint(scaffold_ids)


def test_scaffold_position_poison_does_not_leak_into_text_embedding_gradient_rows() -> None:
    """Poisoned scaffold-position upstream gradient should not taint embedding rows."""
    _, semantic_text_ids, scaffold_ids = _semantic_only_probe_layout()
    embedding = torch.nn.Embedding(128, 4)
    semantic_text_positions = torch.tensor([[8, 9]], dtype=torch.long)
    semantic_text_mask = torch.tensor([[True, True]])

    assembled = assemble_semantic_text_embedding(
        text_embedding=embedding,
        semantic_text_ids=semantic_text_ids,
        semantic_text_positions=semantic_text_positions,
        semantic_text_mask=semantic_text_mask,
        sequence_length=12,
    )
    poisoned_upstream = torch.zeros_like(assembled)
    poisoned_upstream[:, 0, :] = float("nan")
    poisoned_upstream[:, 10, :] = float("nan")
    poisoned_upstream[:, 8, :] = 1.0
    poisoned_upstream[:, 9, :] = -0.5
    assembled.backward(gradient=poisoned_upstream)

    gradient = embedding.weight.grad
    assert gradient is not None
    assert _non_zero_gradient_row_ids(gradient) == {11, 13}
    assert _non_finite_gradient_row_ids(gradient) == set()
    assert _non_zero_gradient_row_ids(gradient).isdisjoint(scaffold_ids)
