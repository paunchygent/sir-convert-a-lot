"""Forensic helpers for bounded Qwen training instability investigation.

Purpose:
    Build JSON-safe batch-provenance and tensor-finiteness payloads so the
    training loop can explain exactly which microbatches and tensor families
    went bad without inlining bulky probe logic into `sft_12hz_loop.py`.

Relationships:
    - Imported by `sft_12hz_loop.py` to capture per-microbatch tensor
      finiteness before the finite-loss guard trips.
    - Its payloads are persisted through `sft_12hz_loop_controls.py` into the
      detached status and report artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

import torch

BatchProvenanceEntry: TypeAlias = Mapping[str, object]
TensorProbe: TypeAlias = tuple[str, torch.Tensor | None]


def build_optimizer_step_forensics_window(
    *,
    microbatches: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Return one JSON-safe forensic window for a completed optimizer step."""
    first_non_finite_tensor = None
    first_non_finite_train_iteration = None
    first_non_finite_gradient_surface = None
    first_non_finite_gradient_train_iteration = None
    for microbatch in microbatches:
        candidate = microbatch.get("first_non_finite_tensor")
        if not isinstance(candidate, str):
            pass
        elif first_non_finite_tensor is None:
            first_non_finite_tensor = candidate
            train_iteration = microbatch.get("train_iteration")
            if isinstance(train_iteration, int):
                first_non_finite_train_iteration = train_iteration
        gradient_forensics = microbatch.get("gradient_forensics")
        if isinstance(gradient_forensics, Mapping) and first_non_finite_gradient_surface is None:
            gradient_candidate = gradient_forensics.get("first_non_finite_surface")
            if isinstance(gradient_candidate, str):
                first_non_finite_gradient_surface = gradient_candidate
                train_iteration = microbatch.get("train_iteration")
                if isinstance(train_iteration, int):
                    first_non_finite_gradient_train_iteration = train_iteration
        if first_non_finite_tensor is not None and first_non_finite_gradient_surface is not None:
            break
    return {
        "microbatch_count": len(microbatches),
        "first_non_finite_tensor": first_non_finite_tensor,
        "first_non_finite_train_iteration": first_non_finite_train_iteration,
        "first_non_finite_gradient_surface": first_non_finite_gradient_surface,
        "first_non_finite_gradient_train_iteration": (first_non_finite_gradient_train_iteration),
        "microbatches": [dict(microbatch) for microbatch in microbatches],
    }


def build_microbatch_forensics(
    *,
    train_iteration: int,
    microbatch_index_in_optimizer_step: int,
    batch_provenance: Sequence[BatchProvenanceEntry] | None,
    probes: Sequence[TensorProbe],
    gradient_forensics: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Return one JSON-safe forensic payload for one microbatch."""
    tensor_finiteness = build_tensor_finiteness_payload(probes=probes)
    return {
        "train_iteration": train_iteration,
        "microbatch_index_in_optimizer_step": microbatch_index_in_optimizer_step,
        "batch_provenance": (
            []
            if batch_provenance is None
            else [dict(provenance) for provenance in batch_provenance]
        ),
        "tensor_finiteness": tensor_finiteness,
        "first_non_finite_tensor": tensor_finiteness["first_non_finite_tensor"],
        "gradient_forensics": (None if gradient_forensics is None else dict(gradient_forensics)),
    }


def build_tensor_finiteness_payload(
    *,
    probes: Sequence[TensorProbe],
) -> dict[str, object]:
    """Return ordered tensor-finiteness summaries for one probe sequence."""
    summaries: dict[str, dict[str, object]] = {}
    probe_order: list[str] = []
    first_non_finite_tensor = None
    for name, tensor in probes:
        if tensor is None:
            continue
        probe_order.append(name)
        summary = summarize_tensor_finiteness(tensor)
        summaries[name] = summary
        if first_non_finite_tensor is None and summary["is_finite"] is False:
            first_non_finite_tensor = name
    return {
        "probe_order": probe_order,
        "first_non_finite_tensor": first_non_finite_tensor,
        "tensors": summaries,
    }


def summarize_tensor_finiteness(tensor: torch.Tensor) -> dict[str, object]:
    """Return one compact JSON-safe finiteness summary for a tensor."""
    detached = tensor.detach()
    element_count = int(detached.numel())
    float_view = detached.to(dtype=torch.float32)
    is_finite = bool(torch.isfinite(float_view).all().item())
    nan_count = int(torch.isnan(float_view).sum().item())
    inf_count = int(torch.isinf(float_view).sum().item())
    max_abs = None if element_count == 0 else float(float_view.abs().max().item())
    return {
        "dtype": str(detached.dtype),
        "shape": [int(dimension) for dimension in detached.shape],
        "element_count": element_count,
        "is_finite": is_finite,
        "nan_count": nan_count,
        "inf_count": inf_count,
        "max_abs": max_abs,
    }
