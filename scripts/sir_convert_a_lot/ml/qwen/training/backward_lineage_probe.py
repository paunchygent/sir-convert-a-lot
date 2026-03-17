"""In-container backward-lineage probe for Story 30 fresh-start failures.

Purpose:
    Reproduce the exact fresh-start failing row pair from the Candidate 1 lane,
    split backward behavior by loss branch, and record the earliest
    instrumented tensor or talker-core hook that becomes non-finite before any
    optimizer step occurs.

Relationships:
    - Executed inside the Qwen training image by
      `story30_backward_lineage_runner.py`.
    - Reuses the patched dataset, semantic-only assembly, shared forward
      surfaces, and gradient RCA helpers from the live training lane.
    - Delegates case sequencing and hook plumbing to smaller Story 30 lineage
      helper modules.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
from dataclasses import asdict
from pathlib import Path

import torch
from accelerate import Accelerator
from transformers import AutoConfig

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

from scripts.devops.qwen_finetuning_patches.dataset import TTSDataset, require_batch_tensors
from scripts.devops.qwen_finetuning_patches.sft_12hz_forward_surfaces import (
    ForwardBatchInputs,
    TalkerForwardSurfaces,
    execute_talker_forward_pass,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_gradient_rca import (
    build_gradient_rca_forensics,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_optimizer_guard_probes import (
    capture_targeted_gradient_probes,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_mel_cache import RefMelCache
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_core_stabilization import (
    TALKER_CORE_STABILIZATION_CHOICES,
    TALKER_CORE_STABILIZATION_OFF,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_training_rows import _load_training_rows
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_cases import (
    build_branch_summaries as _branch_summaries,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_cases import (
    build_case_specs as _case_specs,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_cases import (
    build_report,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_cases import (
    load_source_line_numbers as _load_source_line_numbers,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_cases import (
    parse_source_lines as _parse_source_lines,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_contracts import (
    BackwardLineageProbeReport,
    BranchInteractionSummary,
    FirstNonFiniteHookObservation,
    ProbeCaseResult,
    ProbeCaseSpec,
    TensorGradientObservation,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_hooks import (
    BASELINE_HOOK_PROFILE,
    HOOK_PROFILE_CHOICES,
    build_gradient_hook_session,
    talker_core_prefix,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    TEXT_EMBEDDING_MASK_POLICY_CHOICES,
)

_SOURCE_LINE_FIELD = "story30_source_manifest_line_number"

__all__ = [
    "BackwardLineageProbeReport",
    "BranchInteractionSummary",
    "FirstNonFiniteHookObservation",
    "ProbeCaseResult",
    "ProbeCaseSpec",
    "TensorGradientObservation",
    "main",
    "_branch_summaries",
    "_case_specs",
    "_load_source_line_numbers",
    "_parse_source_lines",
]


def _build_parser() -> argparse.ArgumentParser:
    """Build the in-container backward-lineage probe parser."""
    parser = argparse.ArgumentParser(description="Run the Story 30 backward-lineage probe.")
    parser.add_argument("--model-id", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument(
        "--text-embedding-mask-policy",
        choices=TEXT_EMBEDDING_MASK_POLICY_CHOICES,
        default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    )
    parser.add_argument("--source-lines", default="13,4")
    parser.add_argument(
        "--hook-profile",
        choices=HOOK_PROFILE_CHOICES,
        default=BASELINE_HOOK_PROFILE,
    )
    parser.add_argument(
        "--talker-core-stabilization-variant",
        choices=TALKER_CORE_STABILIZATION_CHOICES,
        default=TALKER_CORE_STABILIZATION_OFF,
    )
    return parser


def _loss_tensor(forward_surfaces: TalkerForwardSurfaces, *, loss_kind: str) -> torch.Tensor:
    """Resolve the requested branch loss from the shared forward surfaces."""
    if loss_kind == "main_loss":
        return forward_surfaces.main_loss
    if loss_kind == "sub_talker_loss":
        return forward_surfaces.sub_talker_loss
    if loss_kind == "combined_loss":
        return forward_surfaces.combined_loss
    raise SystemExit(f"Unsupported loss kind: `{loss_kind}`.")


def _move_tensor(value: torch.Tensor, *, device: torch.device) -> torch.Tensor:
    """Move one batch tensor to the model device without changing dtype."""
    return value.to(device=device, non_blocking=False)


def _build_forward_batch(
    batch: object,
    *,
    device: torch.device,
) -> tuple[ForwardBatchInputs, list[dict[str, object]], torch.Tensor]:
    """Normalize one collated batch into forward inputs plus provenance."""
    resolved_batch = require_batch_tensors(batch)
    return (
        ForwardBatchInputs(
            input_ids=_move_tensor(resolved_batch["input_ids"], device=device),
            codec_ids=_move_tensor(resolved_batch["codec_ids"], device=device),
            semantic_text_ids=_move_tensor(resolved_batch["semantic_text_ids"], device=device),
            semantic_text_positions=_move_tensor(
                resolved_batch["semantic_text_positions"],
                device=device,
            ),
            semantic_text_mask=_move_tensor(resolved_batch["semantic_text_mask"], device=device),
            text_embedding_mask=_move_tensor(
                resolved_batch["text_embedding_mask"],
                device=device,
            ),
            ref_mels=resolved_batch["ref_mels"],
            codec_embedding_mask=_move_tensor(
                resolved_batch["codec_embedding_mask"],
                device=device,
            ),
            attention_mask=_move_tensor(resolved_batch["attention_mask"], device=device),
            codec_0_labels=_move_tensor(resolved_batch["codec_0_labels"], device=device),
            codec_mask=_move_tensor(resolved_batch["codec_mask"], device=device),
        ),
        [dict(entry) for entry in resolved_batch["batch_provenance"]],
        _move_tensor(resolved_batch["input_ids"], device=device)[:, :, 0],
    )


def _run_case(
    *,
    model,
    accelerator: Accelerator,
    dataset: TTSDataset,
    case: ProbeCaseSpec,
    hook_profile: str,
    talker_core_stabilization_variant: str,
) -> ProbeCaseResult:
    """Execute one backward-lineage case without attempting an optimizer step."""
    model.zero_grad(set_to_none=True)
    collated_batch = dataset.collate_fn([dataset[index] for index in case.dataset_indices])
    forward_batch, batch_provenance, input_text_ids = _build_forward_batch(
        collated_batch,
        device=model.device,
    )
    hook_session = build_gradient_hook_session(hook_profile=hook_profile)
    hook_session.install_pre_forward_hooks(model=model)
    forward_surfaces = execute_talker_forward_pass(
        model=model,
        batch=forward_batch,
        non_blocking_transfer=False,
        talker_core_stabilization_variant=talker_core_stabilization_variant,
    )
    hook_session.attach_forward_surfaces(forward_surfaces)
    loss = _loss_tensor(forward_surfaces, loss_kind=case.loss_kind)
    accelerator.backward(loss)
    gradient_rca = build_gradient_rca_forensics(
        model=model,
        input_text_ids=input_text_ids,
        input_text_embedding=forward_surfaces.input_text_embedding,
        batch_provenance=batch_provenance,
    )
    parameter_gradient_probes = capture_targeted_gradient_probes(model=model)
    anomaly_trace = _run_case_with_detect_anomaly(
        model=model,
        accelerator=accelerator,
        dataset=dataset,
        case=case,
        talker_core_stabilization_variant=talker_core_stabilization_variant,
    )
    first_non_finite = hook_session.first_non_finite_observation()
    first_non_finite_talker_core = hook_session.first_non_finite_matching_prefix(
        talker_core_prefix()
    )
    hook_session.close()
    model.zero_grad(set_to_none=True)
    return ProbeCaseResult(
        case_id=case.case_id,
        loss_kind=case.loss_kind,
        source_line_numbers=case.source_line_numbers,
        batch_size=len(case.dataset_indices),
        loss_value=float(loss.detach().float().item()),
        main_loss_value=float(forward_surfaces.main_loss.detach().float().item()),
        sub_talker_loss_value=float(forward_surfaces.sub_talker_loss.detach().float().item()),
        first_non_finite_hook_tensor=first_non_finite.tensor_name,
        first_non_finite_hook_order=first_non_finite.hook_order,
        first_non_finite_talker_core_hook_tensor=first_non_finite_talker_core.tensor_name,
        first_non_finite_talker_core_hook_order=first_non_finite_talker_core.hook_order,
        hooked_tensor_gradients=hook_session.ordered_observations(),
        gradient_rca=gradient_rca,
        parameter_gradient_probes=parameter_gradient_probes,
        anomaly_trace=anomaly_trace,
        batch_provenance=tuple(batch_provenance),
    )


def _run_case_with_detect_anomaly(
    *,
    model,
    accelerator: Accelerator,
    dataset: TTSDataset,
    case: ProbeCaseSpec,
    talker_core_stabilization_variant: str,
) -> str | None:
    """Rerun one case with anomaly detection and return the first raised trace."""
    model.zero_grad(set_to_none=True)
    collated_batch = dataset.collate_fn([dataset[index] for index in case.dataset_indices])
    forward_batch, _, _ = _build_forward_batch(collated_batch, device=model.device)
    try:
        with torch.autograd.detect_anomaly(check_nan=True):
            forward_surfaces = execute_talker_forward_pass(
                model=model,
                batch=forward_batch,
                non_blocking_transfer=False,
                talker_core_stabilization_variant=talker_core_stabilization_variant,
            )
            loss = _loss_tensor(forward_surfaces, loss_kind=case.loss_kind)
            accelerator.backward(loss)
    except RuntimeError as exc:
        model.zero_grad(set_to_none=True)
        return str(exc)
    model.zero_grad(set_to_none=True)
    return None


def main(argv: list[str] | None = None) -> int:
    """Run the in-container Story 30 backward-lineage probe and emit JSON."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    source_line_numbers = _parse_source_lines(str(args.source_lines))
    manifest_source_lines = _load_source_line_numbers(
        Path(args.train_jsonl),
        source_line_field=_SOURCE_LINE_FIELD,
    )
    if manifest_source_lines != source_line_numbers:
        raise SystemExit(
            "Backward-lineage manifest source lines did not match the prepared proof package. "
            f"manifest={manifest_source_lines} expected={source_line_numbers}."
        )
    accelerator = Accelerator(mixed_precision="bf16")
    qwen3tts = Qwen3TTSModel.from_pretrained(
        str(args.model_id),
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    config = AutoConfig.from_pretrained(str(args.model_id))
    train_rows = _load_training_rows(
        Path(args.train_jsonl),
        require_precomputed_ref_inputs=True,
    )
    if len(train_rows) != 2:
        raise SystemExit("Backward-lineage probe expects exactly two prepared train rows.")
    dataset = TTSDataset(
        train_rows,
        qwen3tts.processor,
        config,
        ref_mel_cache=RefMelCache(enabled=True, max_items=32),
        data_path_attribution=None,
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
    )
    model = accelerator.prepare(qwen3tts.model)
    model.train()
    cases = [
        _run_case(
            model=model,
            accelerator=accelerator,
            dataset=dataset,
            case=case,
            hook_profile=str(args.hook_profile),
            talker_core_stabilization_variant=str(args.talker_core_stabilization_variant),
        )
        for case in _case_specs(source_line_numbers)
    ]
    report = build_report(
        model_id=str(args.model_id),
        train_jsonl=Path(args.train_jsonl),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        hook_profile=str(args.hook_profile),
        cases=cases,
        source_line_numbers=source_line_numbers,
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
