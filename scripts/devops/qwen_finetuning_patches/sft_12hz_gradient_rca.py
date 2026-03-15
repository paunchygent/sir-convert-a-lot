"""Gradient RCA helpers for bounded Qwen diagnostic windows.

Purpose:
    Map targeted non-finite text-embedding gradients back to token ids and
    row provenance so operators can debug one failing optimizer-step window
    without repeating long live replays.

Relationships:
    - Imported by `sft_12hz_train_step.py` for targeted per-microbatch RCA.
    - Reuses `sft_12hz_talker_runtime.py` to resolve the active text-embedding
      module on the truthful no-projection training graph.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    resolve_talker_text_embedding_module,
)


def build_gradient_rca_forensics(
    *,
    model: object,
    input_text_ids: torch.Tensor,
    input_text_embedding: torch.Tensor,
    batch_provenance: Sequence[Mapping[str, object]] | None,
) -> dict[str, object]:
    """Build one JSON-safe RCA payload for the accumulated text gradient state."""
    text_embedding_module = resolve_talker_text_embedding_module(model)
    parameter_gradient = _text_embedding_parameter_gradient(text_embedding_module)
    non_finite_row_ids = _non_finite_parameter_row_ids(parameter_gradient)
    input_gradient = input_text_embedding.grad
    sample_payloads = _sample_gradient_payloads(
        input_text_ids=input_text_ids,
        input_gradient=input_gradient,
        batch_provenance=batch_provenance,
        non_finite_parameter_row_ids=non_finite_row_ids,
    )
    input_grad_any_non_finite = any(
        bool(sample_payload["input_gradient_has_non_finite"]) for sample_payload in sample_payloads
    )
    parameter_grad_any_non_finite = bool(non_finite_row_ids)
    return {
        "first_non_finite_surface": _first_non_finite_surface(
            input_grad_any_non_finite=input_grad_any_non_finite,
            parameter_grad_any_non_finite=parameter_grad_any_non_finite,
        ),
        "input_text_embedding_gradient": {
            "available": input_gradient is not None,
            "has_non_finite": input_grad_any_non_finite,
            "sample_count": len(sample_payloads),
            "samples": sample_payloads,
        },
        "text_embedding_parameter_gradient": {
            "available": parameter_gradient is not None,
            "has_non_finite": parameter_grad_any_non_finite,
            "first_non_finite_row_id": (
                None if not non_finite_row_ids else int(non_finite_row_ids[0])
            ),
            "non_finite_row_count": len(non_finite_row_ids),
            "non_finite_row_ids": non_finite_row_ids,
        },
        "input_gradient_precedes_parameter_rows": (
            True
            if input_grad_any_non_finite and not parameter_grad_any_non_finite
            else False
            if parameter_grad_any_non_finite and not input_grad_any_non_finite
            else None
        ),
    }


def _text_embedding_parameter_gradient(
    text_embedding_module: torch.nn.Module | None,
) -> torch.Tensor | None:
    """Return the resolved text-embedding parameter gradient when available."""
    if text_embedding_module is None:
        return None
    weight = getattr(text_embedding_module, "weight", None)
    if isinstance(weight, torch.nn.Parameter):
        return weight.grad
    for parameter in text_embedding_module.parameters(recurse=True):
        return parameter.grad
    return None


def _non_finite_parameter_row_ids(parameter_gradient: torch.Tensor | None) -> list[int]:
    """Return all text-embedding row ids whose accumulated grad is non-finite."""
    if parameter_gradient is None:
        return []
    if parameter_gradient.ndim == 0:
        return [0] if not bool(torch.isfinite(parameter_gradient).item()) else []
    if parameter_gradient.ndim == 1:
        non_finite_mask = ~torch.isfinite(parameter_gradient)
    else:
        non_finite_mask = ~torch.isfinite(parameter_gradient).all(dim=1)
    row_ids = torch.nonzero(non_finite_mask, as_tuple=False).flatten()
    return [int(row_id) for row_id in row_ids.cpu().tolist()]


def _sample_gradient_payloads(
    *,
    input_text_ids: torch.Tensor,
    input_gradient: torch.Tensor | None,
    batch_provenance: Sequence[Mapping[str, object]] | None,
    non_finite_parameter_row_ids: Sequence[int],
) -> list[dict[str, object]]:
    """Return per-sample token and gradient RCA payloads."""
    if input_text_ids.ndim != 2:
        return []
    parameter_row_id_set = {int(row_id) for row_id in non_finite_parameter_row_ids}
    gradient_mask = _input_gradient_mask(input_gradient)
    sample_payloads: list[dict[str, object]] = []
    for batch_index in range(input_text_ids.shape[0]):
        sample_token_ids = [int(token_id) for token_id in input_text_ids[batch_index].tolist()]
        non_finite_positions = _non_finite_positions_for_sample(
            gradient_mask=gradient_mask,
            batch_index=batch_index,
        )
        non_finite_token_ids = [sample_token_ids[position] for position in non_finite_positions]
        provenance = _sample_provenance(batch_provenance, batch_index=batch_index)
        sample_payloads.append(
            {
                "batch_index": batch_index,
                **provenance,
                "token_ids": sample_token_ids,
                "unique_token_ids": sorted(set(sample_token_ids)),
                "input_gradient_has_non_finite": bool(non_finite_positions),
                "non_finite_token_positions": non_finite_positions,
                "non_finite_token_ids": non_finite_token_ids,
                "parameter_row_ids_present_in_sample": sorted(
                    token_id
                    for token_id in set(sample_token_ids)
                    if token_id in parameter_row_id_set
                ),
            }
        )
    return sample_payloads


def _input_gradient_mask(input_gradient: torch.Tensor | None) -> torch.Tensor | None:
    """Return one `[batch, tokens]` mask for non-finite input gradients."""
    if input_gradient is None:
        return None
    if input_gradient.ndim < 2:
        return ~torch.isfinite(input_gradient)
    if input_gradient.ndim == 2:
        return ~torch.isfinite(input_gradient)
    return ~torch.isfinite(input_gradient).all(dim=-1)


def _non_finite_positions_for_sample(
    *,
    gradient_mask: torch.Tensor | None,
    batch_index: int,
) -> list[int]:
    """Return the non-finite token positions for one batch sample."""
    if gradient_mask is None:
        return []
    if gradient_mask.ndim != 2 or batch_index >= gradient_mask.shape[0]:
        return []
    positions = torch.nonzero(gradient_mask[batch_index], as_tuple=False).flatten()
    return [int(position) for position in positions.cpu().tolist()]


def _sample_provenance(
    batch_provenance: Sequence[Mapping[str, object]] | None,
    *,
    batch_index: int,
) -> dict[str, object]:
    """Return stable provenance and text context for one sample."""
    if batch_provenance is None or batch_index >= len(batch_provenance):
        return {
            "row_id": None,
            "manifest_path": None,
            "manifest_line_number": None,
            "speaker_id": None,
            "text_preview": None,
            "full_text": None,
        }
    provenance = batch_provenance[batch_index]
    manifest_path = _optional_str(provenance, "manifest_path")
    manifest_line_number = _optional_int(provenance, "manifest_line_number")
    return {
        "row_id": _optional_str(provenance, "row_id"),
        "manifest_path": manifest_path,
        "manifest_line_number": manifest_line_number,
        "speaker_id": _optional_str(provenance, "speaker_id"),
        "text_preview": _optional_str(provenance, "text_preview"),
        "full_text": _full_text_context(
            manifest_path=manifest_path,
            manifest_line_number=manifest_line_number,
        ),
    }


def _first_non_finite_surface(
    *,
    input_grad_any_non_finite: bool,
    parameter_grad_any_non_finite: bool,
) -> str | None:
    """Return the earliest non-finite surface visible in the RCA payload."""
    if input_grad_any_non_finite:
        return "input_text_embedding.grad"
    if parameter_grad_any_non_finite:
        return "text_embedding.weight.grad"
    return None


def _optional_str(payload: Mapping[str, object], key: str) -> str | None:
    """Return one optional string field from a generic mapping."""
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _optional_int(payload: Mapping[str, object], key: str) -> int | None:
    """Return one optional integer field from a generic mapping."""
    value = payload.get(key)
    return value if isinstance(value, int) else None


def _full_text_context(
    *,
    manifest_path: str | None,
    manifest_line_number: int | None,
) -> str | None:
    """Return the full manifest text for one provenance entry when available."""
    if manifest_path is None or manifest_line_number is None or manifest_line_number <= 0:
        return None
    return _load_manifest_text(Path(manifest_path), manifest_line_number)


@lru_cache(maxsize=512)
def _load_manifest_text(manifest_path: Path, manifest_line_number: int) -> str | None:
    """Load the full row text from one manifest-path/line-number pair."""
    if not manifest_path.is_file():
        return None
    try:
        manifest_line = manifest_path.read_text(encoding="utf-8").splitlines()[
            manifest_line_number - 1
        ]
    except IndexError:
        return None
    try:
        payload = json.loads(manifest_line)
    except json.JSONDecodeError:
        return None
    text = payload.get("text")
    return text if isinstance(text, str) else None
