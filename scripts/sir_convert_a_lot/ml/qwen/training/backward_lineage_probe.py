"""In-container backward-lineage probe for the Story 30 fresh-start failure.

Purpose:
    Reproduce the exact fresh-start failing row pair from the Candidate 1 lane,
    split backward behavior by loss branch, and record the earliest instrumented
    backward tensor that becomes non-finite before any optimizer step occurs.

Relationships:
    - Executed inside the Qwen training image by
      `story30_backward_lineage_runner.py`.
    - Reuses the patched dataset, semantic-only assembly, shared forward
      surfaces, and gradient RCA helpers from the live training lane.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
from accelerate import Accelerator
from transformers import AutoConfig

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

from scripts.devops.qwen_finetuning_patches.dataset import TTSDataset, require_batch_tensors
from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    summarize_tensor_finiteness,
)
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
from scripts.devops.qwen_finetuning_patches.sft_12hz_training_rows import _load_training_rows
from scripts.sir_convert_a_lot.ml.qwen.training.reporting.artifact_io import utc_now_iso
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    TEXT_EMBEDDING_MASK_POLICY_CHOICES,
)

_SOURCE_LINE_FIELD = "story30_source_manifest_line_number"
_TENSOR_HOOK_ORDER = (
    "semantic_text_embeddings",
    "input_text_embedding",
    "input_codec_embedding",
    "fused_auxiliary_embedding",
    "input_embeddings",
    "hidden_states",
    "talker_hidden_states",
)


@dataclass(frozen=True)
class ProbeCaseSpec:
    """One deterministic loss/row selection case for the backward probe."""

    case_id: str
    loss_kind: str
    dataset_indices: tuple[int, ...]
    source_line_numbers: tuple[int, ...]


@dataclass(frozen=True)
class TensorGradientObservation:
    """One instrumented tensor-gradient observation for a backward hook."""

    tensor_name: str
    hook_order: int
    is_finite: bool
    nan_count: int
    inf_count: int
    max_abs: float | None


@dataclass(frozen=True)
class FirstNonFiniteHookObservation:
    """Earliest non-finite tensor-gradient hook observed in one backward pass."""

    tensor_name: str | None
    hook_order: int | None


@dataclass
class _FirstNonFiniteHookState:
    """Mutable state holder for the earliest non-finite gradient hook."""

    tensor_name: str | None = None
    hook_order: int | None = None


@dataclass(frozen=True)
class ProbeCaseResult:
    """Result for one backward-lineage loss/row selection case."""

    case_id: str
    loss_kind: str
    source_line_numbers: tuple[int, ...]
    batch_size: int
    loss_value: float
    main_loss_value: float
    sub_talker_loss_value: float
    first_non_finite_hook_tensor: str | None
    first_non_finite_hook_order: int | None
    hooked_tensor_gradients: tuple[TensorGradientObservation, ...]
    gradient_rca: dict[str, object]
    parameter_gradient_probes: dict[str, object]
    anomaly_trace: str | None
    batch_provenance: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class BranchInteractionSummary:
    """Per-loss-kind interaction summary for pair and isolated row cases."""

    loss_kind: str
    pair_has_non_finite: bool
    first_row_has_non_finite: bool
    second_row_has_non_finite: bool
    interaction_mode: str


@dataclass(frozen=True)
class BackwardLineageProbeReport:
    """Machine-readable result for the Story 30 backward-lineage probe."""

    generated_at: str
    model_id: str
    train_jsonl: str
    text_embedding_mask_policy: str
    source_line_numbers: tuple[int, int]
    cases: tuple[ProbeCaseResult, ...]
    branch_summaries: tuple[BranchInteractionSummary, ...]


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
    return parser


def _parse_source_lines(raw_value: str) -> tuple[int, int]:
    """Parse the two canonical source lines for the backward-lineage probe."""
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 2:
        raise SystemExit("Backward-lineage probe requires exactly two source lines.")
    return int(pieces[0]), int(pieces[1])


def _load_source_line_numbers(train_jsonl: Path) -> tuple[int, ...]:
    """Load the preserved source line numbers from the mini-bundle manifest."""
    source_lines: list[int] = []
    with train_jsonl.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise SystemExit("Backward-lineage manifest row was not a JSON object.")
            source_line = payload.get(_SOURCE_LINE_FIELD)
            if not isinstance(source_line, int):
                raise SystemExit(
                    "Backward-lineage manifest row was missing "
                    "`story30_source_manifest_line_number`."
                )
            source_lines.append(source_line)
    return tuple(source_lines)


def _case_specs(source_line_numbers: tuple[int, int]) -> tuple[ProbeCaseSpec, ...]:
    """Return the fixed branch-ordered probe sequence requested for T212."""
    first_line, second_line = source_line_numbers
    return (
        ProbeCaseSpec(
            case_id="pair-main-loss",
            loss_kind="main_loss",
            dataset_indices=(0, 1),
            source_line_numbers=(first_line, second_line),
        ),
        ProbeCaseSpec(
            case_id="pair-sub-talker-loss",
            loss_kind="sub_talker_loss",
            dataset_indices=(0, 1),
            source_line_numbers=(first_line, second_line),
        ),
        ProbeCaseSpec(
            case_id="pair-combined-loss",
            loss_kind="combined_loss",
            dataset_indices=(0, 1),
            source_line_numbers=(first_line, second_line),
        ),
        ProbeCaseSpec(
            case_id=f"line-{first_line}-main-loss",
            loss_kind="main_loss",
            dataset_indices=(0,),
            source_line_numbers=(first_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{second_line}-main-loss",
            loss_kind="main_loss",
            dataset_indices=(1,),
            source_line_numbers=(second_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{first_line}-sub-talker-loss",
            loss_kind="sub_talker_loss",
            dataset_indices=(0,),
            source_line_numbers=(first_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{second_line}-sub-talker-loss",
            loss_kind="sub_talker_loss",
            dataset_indices=(1,),
            source_line_numbers=(second_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{first_line}-combined-loss",
            loss_kind="combined_loss",
            dataset_indices=(0,),
            source_line_numbers=(first_line,),
        ),
        ProbeCaseSpec(
            case_id=f"line-{second_line}-combined-loss",
            loss_kind="combined_loss",
            dataset_indices=(1,),
            source_line_numbers=(second_line,),
        ),
    )


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
                resolved_batch["semantic_text_positions"], device=device
            ),
            semantic_text_mask=_move_tensor(resolved_batch["semantic_text_mask"], device=device),
            ref_mels=resolved_batch["ref_mels"],
            codec_embedding_mask=_move_tensor(
                resolved_batch["codec_embedding_mask"], device=device
            ),
            attention_mask=_move_tensor(resolved_batch["attention_mask"], device=device),
            codec_0_labels=_move_tensor(resolved_batch["codec_0_labels"], device=device),
            codec_mask=_move_tensor(resolved_batch["codec_mask"], device=device),
        ),
        [dict(entry) for entry in resolved_batch["batch_provenance"]],
        _move_tensor(resolved_batch["input_ids"], device=device)[:, :, 0],
    )


def _register_gradient_hooks(
    forward_surfaces: TalkerForwardSurfaces,
) -> tuple[
    list[torch.utils.hooks.RemovableHandle],
    dict[str, TensorGradientObservation],
    FirstNonFiniteHookObservation,
]:
    """Attach gradient hooks to the key backward tensors in the shared graph."""
    observations: dict[str, TensorGradientObservation] = {}
    first_non_finite = _FirstNonFiniteHookState()
    handles: list[torch.utils.hooks.RemovableHandle] = []
    hook_counter = 0

    def attach(name: str, tensor: torch.Tensor) -> None:
        nonlocal hook_counter
        tensor.retain_grad()

        def on_grad(gradient: torch.Tensor) -> torch.Tensor:
            nonlocal hook_counter
            hook_counter += 1
            summary = summarize_tensor_finiteness(gradient)
            observation = TensorGradientObservation(
                tensor_name=name,
                hook_order=hook_counter,
                is_finite=_required_summary_bool(summary, "is_finite"),
                nan_count=_required_summary_int(summary, "nan_count"),
                inf_count=_required_summary_int(summary, "inf_count"),
                max_abs=_optional_summary_float(summary, "max_abs"),
            )
            observations[name] = observation
            if (not observation.is_finite) and first_non_finite.tensor_name is None:
                first_non_finite.tensor_name = name
                first_non_finite.hook_order = hook_counter
            return gradient

        handles.append(tensor.register_hook(on_grad))

    attach("semantic_text_embeddings", forward_surfaces.semantic_text_embeddings)
    attach("input_text_embedding", forward_surfaces.input_text_embedding)
    attach("input_codec_embedding", forward_surfaces.input_codec_embedding)
    attach("fused_auxiliary_embedding", forward_surfaces.fused_auxiliary_embedding)
    attach("input_embeddings", forward_surfaces.input_embeddings)
    attach("hidden_states", forward_surfaces.hidden_states)
    attach("talker_hidden_states", forward_surfaces.talker_hidden_states)
    return (
        handles,
        observations,
        FirstNonFiniteHookObservation(
            tensor_name=first_non_finite.tensor_name,
            hook_order=first_non_finite.hook_order,
        ),
    )


def _run_case(
    *,
    model,
    accelerator: Accelerator,
    dataset: TTSDataset,
    case: ProbeCaseSpec,
) -> ProbeCaseResult:
    """Execute one backward-lineage case without attempting an optimizer step."""
    model.zero_grad(set_to_none=True)
    collated_batch = dataset.collate_fn([dataset[index] for index in case.dataset_indices])
    forward_batch, batch_provenance, input_text_ids = _build_forward_batch(
        collated_batch,
        device=model.device,
    )
    forward_surfaces = execute_talker_forward_pass(
        model=model,
        batch=forward_batch,
        non_blocking_transfer=False,
    )
    handles, observations, first_non_finite = _register_gradient_hooks(forward_surfaces)
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
    )
    for handle in handles:
        handle.remove()
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
        hooked_tensor_gradients=tuple(
            observations[name] for name in _TENSOR_HOOK_ORDER if name in observations
        ),
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
) -> str | None:
    """Rerun one case with anomaly detection and return the first raised trace text."""
    model.zero_grad(set_to_none=True)
    collated_batch = dataset.collate_fn([dataset[index] for index in case.dataset_indices])
    forward_batch, _, _ = _build_forward_batch(collated_batch, device=model.device)
    try:
        with torch.autograd.detect_anomaly(check_nan=True):
            forward_surfaces = execute_talker_forward_pass(
                model=model,
                batch=forward_batch,
                non_blocking_transfer=False,
            )
            loss = _loss_tensor(forward_surfaces, loss_kind=case.loss_kind)
            accelerator.backward(loss)
    except RuntimeError as exc:
        model.zero_grad(set_to_none=True)
        return str(exc)
    model.zero_grad(set_to_none=True)
    return None


def _required_summary_bool(summary: dict[str, object], key: str) -> bool:
    """Return one required boolean field from a tensor-finiteness summary."""
    value = summary.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Backward-lineage tensor summary returned malformed `{key}`.")
    return value


def _required_summary_int(summary: dict[str, object], key: str) -> int:
    """Return one required integer field from a tensor-finiteness summary."""
    value = summary.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Backward-lineage tensor summary returned malformed `{key}`.")
    return value


def _optional_summary_float(summary: dict[str, object], key: str) -> float | None:
    """Return one optional numeric field from a tensor-finiteness summary."""
    value = summary.get(key)
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        raise SystemExit(f"Backward-lineage tensor summary returned malformed `{key}`.")
    return float(value)


def _branch_summaries(
    cases: Sequence[ProbeCaseResult],
    source_line_numbers: tuple[int, int],
) -> tuple[BranchInteractionSummary, ...]:
    """Summarize pair-vs-single-row non-finite outcomes for each loss branch."""
    first_line, second_line = source_line_numbers
    summaries: list[BranchInteractionSummary] = []
    for loss_kind in ("main_loss", "sub_talker_loss", "combined_loss"):
        pair_case = _required_case(cases, f"pair-{loss_kind.replace('_', '-')}")
        first_case = _required_case(cases, f"line-{first_line}-{loss_kind.replace('_', '-')}")
        second_case = _required_case(cases, f"line-{second_line}-{loss_kind.replace('_', '-')}")
        pair_has_non_finite = _case_has_non_finite(pair_case)
        first_row_has_non_finite = _case_has_non_finite(first_case)
        second_row_has_non_finite = _case_has_non_finite(second_case)
        interaction_mode = _interaction_mode(
            pair_has_non_finite=pair_has_non_finite,
            first_row_has_non_finite=first_row_has_non_finite,
            second_row_has_non_finite=second_row_has_non_finite,
        )
        summaries.append(
            BranchInteractionSummary(
                loss_kind=loss_kind,
                pair_has_non_finite=pair_has_non_finite,
                first_row_has_non_finite=first_row_has_non_finite,
                second_row_has_non_finite=second_row_has_non_finite,
                interaction_mode=interaction_mode,
            )
        )
    return tuple(summaries)


def _required_case(cases: Sequence[ProbeCaseResult], case_id: str) -> ProbeCaseResult:
    """Return one recorded case result by id or raise with context."""
    for case in cases:
        if case.case_id == case_id:
            return case
    raise SystemExit(f"Backward-lineage case result `{case_id}` was missing.")


def _case_has_non_finite(case: ProbeCaseResult) -> bool:
    """Return whether one case surfaced non-finite gradients."""
    if case.first_non_finite_hook_tensor is not None:
        return True
    gradient_rca_surface = case.gradient_rca.get("first_non_finite_surface")
    if isinstance(gradient_rca_surface, str):
        return True
    probe_surface = case.parameter_gradient_probes.get("first_non_finite_surface")
    return isinstance(probe_surface, str)


def _interaction_mode(
    *,
    pair_has_non_finite: bool,
    first_row_has_non_finite: bool,
    second_row_has_non_finite: bool,
) -> str:
    """Classify row-local versus pair-only non-finite behavior for one branch."""
    if not pair_has_non_finite and not first_row_has_non_finite and not second_row_has_non_finite:
        return "none"
    if pair_has_non_finite and not first_row_has_non_finite and not second_row_has_non_finite:
        return "pair_only"
    if first_row_has_non_finite and second_row_has_non_finite:
        return "both_rows"
    if first_row_has_non_finite:
        return "first_row_only"
    if second_row_has_non_finite:
        return "second_row_only"
    return "mixed"


def build_report(
    *,
    model_id: str,
    train_jsonl: Path,
    text_embedding_mask_policy: str,
    cases: Sequence[ProbeCaseResult],
    source_line_numbers: tuple[int, int],
) -> BackwardLineageProbeReport:
    """Build the machine-readable backward-lineage report."""
    return BackwardLineageProbeReport(
        generated_at=utc_now_iso(),
        model_id=model_id,
        train_jsonl=train_jsonl.as_posix(),
        text_embedding_mask_policy=text_embedding_mask_policy,
        source_line_numbers=source_line_numbers,
        cases=tuple(cases),
        branch_summaries=_branch_summaries(cases, source_line_numbers),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the in-container Story 30 backward-lineage probe and emit JSON."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    source_line_numbers = _parse_source_lines(str(args.source_lines))
    manifest_source_lines = _load_source_line_numbers(Path(args.train_jsonl))
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
        )
        for case in _case_specs(source_line_numbers)
    ]
    report = build_report(
        model_id=str(args.model_id),
        train_jsonl=Path(args.train_jsonl),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        cases=cases,
        source_line_numbers=source_line_numbers,
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
