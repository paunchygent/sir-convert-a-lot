"""Standalone eval setup for the patched Qwen fine-tuning trainer.

Purpose:
    Prepare the minimal runtime needed to restore one durable Qwen checkpoint
    and run a real held-out evaluation pass without entering the training loop.

Relationships:
    - Imported by `sft_12hz.py` for standalone held-out eval.
    - Reuses model, dataloader, and runtime helpers from `sft_12hz_setup.py`.
    - Consumed by `sft_12hz_eval.py` when executing standalone eval.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import torch
from accelerate import Accelerator
from torch.utils.data import DataLoader

from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import BucketedBatchSampler
from scripts.devops.qwen_finetuning_patches.sft_12hz_checkpointing import (
    DurableCheckpointMetadata,
    load_durable_checkpoint_metadata,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    DataloaderTuning,
    resolve_dataloader_tuning,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_profiling import (
    DEFAULT_TORCH_PROFILER_ACTIVE_STEPS,
    DEFAULT_TORCH_PROFILER_ENABLED,
    DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
    DEFAULT_TORCH_PROFILER_RECORD_SHAPES,
    DEFAULT_TORCH_PROFILER_REPEAT,
    DEFAULT_TORCH_PROFILER_WAIT_STEPS,
    DEFAULT_TORCH_PROFILER_WARMUP_STEPS,
    DEFAULT_TORCH_PROFILER_WITH_STACK,
    TorchProfilerSession,
    resolve_torch_profiler_config,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_mel_cache import (
    DEFAULT_REF_MEL_CACHE_ENABLED,
    DEFAULT_REF_MEL_CACHE_MAX_ITEMS,
    RefMelCache,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_setup import (
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_NON_BLOCKING_TRANSFER,
    AutoConfig,
    Qwen3TTSModel,
    TrainableQwenModelProtocol,
    TTSDataset,
    _build_dataloader,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_training_rows import (
    _load_training_rows,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    load_optional_training_bundle_summary,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    resolve_text_embedding_mask_policy,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    ThroughputBatchPolicy,
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)


@dataclass(frozen=True)
class PreparedStandaloneEvalRun:
    """Resolved runtime state for one standalone held-out evaluation pass."""

    args: argparse.Namespace
    accelerator: Accelerator
    model: TrainableQwenModelProtocol
    eval_dataloader: DataLoader[object] | Sequence[dict[str, torch.Tensor]]
    eval_dataloader_length: int
    effective_dataloader_tuning: DataloaderTuning
    throughput_batch_policy: ThroughputBatchPolicy
    throughput_profile_payload: dict[str, object]
    ref_mel_cache: RefMelCache
    torch_profiler_session: TorchProfilerSession
    checkpoint_metadata: DurableCheckpointMetadata


def prepare_standalone_eval_run(args: argparse.Namespace) -> PreparedStandaloneEvalRun:
    """Prepare the bounded standalone eval runtime from argparse-style args."""
    checkpoint_path = Path(str(args.resume_from_checkpoint))
    if not checkpoint_path.exists():
        raise ValueError(f"`--resume_from_checkpoint` did not exist: {checkpoint_path.as_posix()}")

    dataloader_num_workers = int(
        getattr(args, "dataloader_num_workers", DEFAULT_DATALOADER_NUM_WORKERS)
    )
    dataloader_pin_memory = bool(
        getattr(args, "dataloader_pin_memory", DEFAULT_DATALOADER_PIN_MEMORY)
    )
    dataloader_persistent_workers = bool(
        getattr(args, "dataloader_persistent_workers", DEFAULT_DATALOADER_PERSISTENT_WORKERS)
    )
    dataloader_prefetch_factor = int(
        getattr(args, "dataloader_prefetch_factor", DEFAULT_DATALOADER_PREFETCH_FACTOR)
    )
    non_blocking_transfer = bool(
        getattr(args, "non_blocking_transfer", DEFAULT_NON_BLOCKING_TRANSFER)
    )
    ref_mel_cache_enabled = bool(
        getattr(args, "ref_mel_cache_enabled", DEFAULT_REF_MEL_CACHE_ENABLED)
    )
    ref_mel_cache_max_items = int(
        getattr(args, "ref_mel_cache_max_items", DEFAULT_REF_MEL_CACHE_MAX_ITEMS)
    )
    if ref_mel_cache_max_items <= 0:
        raise ValueError("`--ref_mel_cache_max_items` must be positive.")

    throughput_batch_policy = resolve_throughput_batch_policy(
        profile_label=str(
            getattr(args, "throughput_profile_label", DEFAULT_THROUGHPUT_PROFILE_LABEL)
        ),
        max_batch_size=int(args.batch_size),
    )
    effective_dataloader_tuning = resolve_dataloader_tuning(
        num_workers=dataloader_num_workers,
        pin_memory=dataloader_pin_memory,
        persistent_workers=dataloader_persistent_workers,
        prefetch_factor=dataloader_prefetch_factor,
        non_blocking_transfer=non_blocking_transfer,
    )
    ref_mel_cache = RefMelCache(
        enabled=ref_mel_cache_enabled,
        max_items=ref_mel_cache_max_items,
    )

    output_model_path = Path(str(getattr(args, "output_model_path", checkpoint_path.parent)))
    torch_profiler_trace_dir_raw = getattr(args, "torch_profiler_trace_dir", None)
    torch_profiler_trace_dir = (
        output_model_path.parent / "profiling" / "pytorch"
        if torch_profiler_trace_dir_raw in (None, "")
        else Path(str(torch_profiler_trace_dir_raw))
    )
    torch_profiler_session = TorchProfilerSession(
        resolve_torch_profiler_config(
            enabled=bool(getattr(args, "torch_profiler_enabled", DEFAULT_TORCH_PROFILER_ENABLED)),
            trace_dir=torch_profiler_trace_dir,
            wait_steps=int(
                getattr(args, "torch_profiler_wait_steps", DEFAULT_TORCH_PROFILER_WAIT_STEPS)
            ),
            warmup_steps=int(
                getattr(args, "torch_profiler_warmup_steps", DEFAULT_TORCH_PROFILER_WARMUP_STEPS)
            ),
            active_steps=int(
                getattr(args, "torch_profiler_active_steps", DEFAULT_TORCH_PROFILER_ACTIVE_STEPS)
            ),
            repeat=int(getattr(args, "torch_profiler_repeat", DEFAULT_TORCH_PROFILER_REPEAT)),
            record_shapes=bool(
                getattr(args, "torch_profiler_record_shapes", DEFAULT_TORCH_PROFILER_RECORD_SHAPES)
            ),
            profile_memory=bool(
                getattr(
                    args,
                    "torch_profiler_profile_memory",
                    DEFAULT_TORCH_PROFILER_PROFILE_MEMORY,
                )
            ),
            with_stack=bool(
                getattr(args, "torch_profiler_with_stack", DEFAULT_TORCH_PROFILER_WITH_STACK)
            ),
        )
    )
    accelerator = Accelerator(mixed_precision="bf16")
    checkpoint_metadata = load_durable_checkpoint_metadata(checkpoint_path)
    bundle_summary = (
        None
        if getattr(args, "pilot_bundle_root", None) in (None, "")
        else load_optional_training_bundle_summary(Path(str(args.pilot_bundle_root)))
    )
    eval_data = _load_training_rows(
        Path(str(args.eval_jsonl)),
        require_precomputed_ref_inputs=bundle_summary is not None,
    )
    if len(eval_data) == 0:
        raise ValueError("`--eval_jsonl` must contain at least one prepared row.")

    qwen3tts = Qwen3TTSModel.from_pretrained(
        str(args.init_model_path),
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    config = AutoConfig.from_pretrained(str(args.init_model_path))
    text_embedding_mask_policy = resolve_text_embedding_mask_policy(
        getattr(args, "text_embedding_mask_policy", None),
        default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    )
    eval_dataset = TTSDataset(
        eval_data,
        qwen3tts.processor,
        config,
        ref_mel_cache=ref_mel_cache,
        data_path_attribution=None,
        text_embedding_mask_policy=text_embedding_mask_policy,
    )
    eval_batch_sampler = BucketedBatchSampler(
        row_metrics=eval_dataset.batch_metrics(),
        policy=throughput_batch_policy,
    )
    eval_dataloader = _build_dataloader(
        dataset=eval_dataset,
        batch_sampler=eval_batch_sampler,
        tuning=effective_dataloader_tuning,
    )
    model, eval_dataloader = accelerator.prepare(qwen3tts.model, eval_dataloader)
    accelerator.load_state(checkpoint_path.as_posix())
    return PreparedStandaloneEvalRun(
        args=args,
        accelerator=accelerator,
        model=model,
        eval_dataloader=eval_dataloader,
        eval_dataloader_length=len(eval_dataloader),
        effective_dataloader_tuning=effective_dataloader_tuning,
        throughput_batch_policy=throughput_batch_policy,
        throughput_profile_payload=throughput_policy_payload(throughput_batch_policy),
        ref_mel_cache=ref_mel_cache,
        torch_profiler_session=torch_profiler_session,
        checkpoint_metadata=checkpoint_metadata,
    )
