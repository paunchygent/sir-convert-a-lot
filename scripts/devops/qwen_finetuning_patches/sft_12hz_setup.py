"""Training-setup helpers for the patched Qwen fine-tuning trainer.

Purpose:
    Prepare the trainer runtime, dataloader, tracker config, and loop-control
    state outside the public `sft_12hz.py` facade so the facade can stay below
    the repo's LoC ceiling.

Relationships:
    - Imported by `sft_12hz.py`.
    - Reuses the patch-directory dataloader, profiling, tracking, and loop
      control helpers.
"""

from __future__ import annotations

import argparse
import contextlib
import io
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

import torch
from accelerate import Accelerator
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoConfig

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel

from scripts.devops.qwen_finetuning_patches.dataset import TTSDataset
from scripts.devops.qwen_finetuning_patches.sft_12hz_batch_occupancy import (
    BatchOccupancySummary,
    summarize_batch_occupancy,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import BucketedBatchSampler
from scripts.devops.qwen_finetuning_patches.sft_12hz_data_path_attribution import (
    DataPathAttributionCollector,
    build_data_path_attribution_collector,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_dataloader import (
    DEFAULT_DATALOADER_NUM_WORKERS,
    DEFAULT_DATALOADER_PERSISTENT_WORKERS,
    DEFAULT_DATALOADER_PIN_MEMORY,
    DEFAULT_DATALOADER_PREFETCH_FACTOR,
    DEFAULT_NON_BLOCKING_TRANSFER,
    DataloaderTuning,
    resolve_dataloader_tuning,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_diagnostic_window import (
    DiagnosticWindowConfig,
    build_diagnostic_window_config,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_eval import (
    DEFAULT_EVAL_INTERVAL_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_loop_controls import (
    DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
    DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
    AsyncLossObserver,
    FiniteLossGuardConfig,
    FiniteLossGuardState,
    TrainingHeartbeatPolicy,
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
from scripts.devops.qwen_finetuning_patches.sft_12hz_step_semantics import (
    GRADIENT_ACCUMULATION_STEPS,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_talker_runtime import (
    talker_runtime_fingerprint,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_tracking import (
    TrainingTrackerConfig,
    build_training_tracker_config,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_training_rows import (
    _load_training_rows,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    load_optional_training_bundle_summary,
)
from scripts.sir_convert_a_lot.ml.qwen.training.throughput_profiles import (
    DEFAULT_THROUGHPUT_PROFILE_LABEL,
    ThroughputBatchPolicy,
    resolve_throughput_batch_policy,
    throughput_policy_payload,
)


class QwenWrapperProtocol(Protocol):
    """Minimal loaded Qwen wrapper surface needed by the trainer."""

    processor: object
    model: "TrainableQwenModelProtocol"


class CodePredictorProtocol(Protocol):
    """Minimal codec-predictor surface used by the patched trainer."""

    def get_input_embeddings(self) -> Sequence[torch.nn.Module]:
        """Return the auxiliary codebook embeddings."""


class EmbeddingLayerProtocol(Protocol):
    """Callable embedding surface used by the patched trainer."""

    def __call__(self, indices: torch.Tensor) -> torch.Tensor:
        """Embed one integer tensor."""


class ProjectionLayerProtocol(Protocol):
    """Callable projection surface used by the patched trainer."""

    def __call__(self, values: torch.Tensor) -> torch.Tensor:
        """Project one dense tensor."""


class TalkerModelProtocol(Protocol):
    """Minimal talker-model embedding surface used by the patched trainer."""

    text_embedding: EmbeddingLayerProtocol
    codec_embedding: EmbeddingLayerProtocol


class TalkerOutputsProtocol(Protocol):
    """Minimal talker forward-output surface used by the patched trainer."""

    loss: torch.Tensor
    hidden_states: Sequence[Sequence[torch.Tensor]]


class TalkerProtocol(Protocol):
    """Minimal talker surface used by the patched trainer."""

    model: TalkerModelProtocol
    code_predictor: CodePredictorProtocol
    text_projection: ProjectionLayerProtocol

    def get_input_embeddings(self) -> object:
        """Return the canonical codec/input embedding surface."""

    def get_text_embeddings(self) -> object:
        """Return the canonical text embedding surface."""

    def __call__(
        self,
        *,
        inputs_embeds: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: torch.Tensor,
        output_hidden_states: bool,
    ) -> TalkerOutputsProtocol:
        """Run one forward pass."""

    def forward_sub_talker_finetune(
        self,
        talker_codec_ids: torch.Tensor,
        talker_hidden_states: torch.Tensor,
    ) -> tuple[object | None, torch.Tensor]:
        """Run the auxiliary talker path."""


class TrainableQwenModelProtocol(Protocol):
    """Minimal Qwen model surface consumed by the patched trainer."""

    device: torch.device
    dtype: torch.dtype
    training: bool
    talker: TalkerProtocol

    def parameters(self, recurse: bool = True) -> Iterator[torch.nn.Parameter]:
        """Return trainable parameters."""

    def train(self, mode: bool = True) -> object:
        """Toggle training mode."""

    def eval(self) -> object:
        """Toggle eval mode."""

    def speaker_encoder(self, ref_mels: torch.Tensor) -> torch.Tensor:
        """Encode reference mels into speaker embeddings."""


@dataclass(frozen=True)
class PreparedTrainingRun:
    """Resolved training runtime and loop-control dependencies."""

    args: argparse.Namespace
    output_model_path: Path
    model_path: str
    qwen3tts: QwenWrapperProtocol
    accelerator: Accelerator
    model: TrainableQwenModelProtocol
    checkpointable_model: torch.nn.Module
    optimizer: AdamW
    train_dataloader: DataLoader[object] | Sequence[object]
    eval_dataloader: DataLoader[object] | Sequence[object]
    dataloader_length: int
    eval_dataloader_length: int
    effective_dataloader_tuning: DataloaderTuning
    throughput_batch_policy: ThroughputBatchPolicy
    throughput_profile_payload: dict[str, object]
    batch_occupancy_summary: BatchOccupancySummary
    data_path_attribution: DataPathAttributionCollector | None
    ref_mel_cache: RefMelCache
    torch_profiler_session: TorchProfilerSession
    tracker_config: TrainingTrackerConfig
    talker_runtime: dict[str, object]
    diagnostic_window: DiagnosticWindowConfig | None
    heartbeat_policy: TrainingHeartbeatPolicy
    loss_observer: AsyncLossObserver
    finite_loss_guard: FiniteLossGuardState


def prepare_training_run(args: argparse.Namespace) -> PreparedTrainingRun:
    """Validate args and prepare one bounded Qwen training runtime."""
    if args.max_steps is not None and args.max_steps <= 0:
        raise ValueError("`--max_steps` must be positive when provided.")
    if int(args.checkpoint_interval_steps) <= 0:
        raise ValueError("`--checkpoint_interval_steps` must be positive.")
    if int(getattr(args, "eval_interval_steps", DEFAULT_EVAL_INTERVAL_STEPS)) <= 0:
        raise ValueError("`--eval_interval_steps` must be positive.")
    if int(args.durable_checkpoint_retention) <= 0:
        raise ValueError("`--durable-checkpoint-retention` must be positive.")
    if int(args.durable_checkpoint_min_free_bytes) <= 0:
        raise ValueError("`--durable-checkpoint-min-free-bytes` must be positive.")

    heartbeat_policy = TrainingHeartbeatPolicy(
        interval_optimizer_steps=int(
            getattr(
                args,
                "heartbeat_interval_optimizer_steps",
                DEFAULT_HEARTBEAT_INTERVAL_OPTIMIZER_STEPS,
            )
        )
    )
    finite_loss_guard = FiniteLossGuardState(
        config=FiniteLossGuardConfig(
            max_consecutive_non_finite_steps=int(
                getattr(
                    args,
                    "finite_loss_max_consecutive_steps",
                    DEFAULT_FINITE_LOSS_MAX_CONSECUTIVE_STEPS,
                )
            )
        )
    )
    loss_observer = AsyncLossObserver()
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
    data_path_proof_mode = bool(getattr(args, "data_path_proof_mode", False))
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
            getattr(
                args,
                "throughput_profile_label",
                DEFAULT_THROUGHPUT_PROFILE_LABEL,
            )
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
    data_path_attribution = build_data_path_attribution_collector(
        proof_mode_enabled=data_path_proof_mode,
        dataloader_num_workers=dataloader_num_workers,
    )
    output_model_path = Path(args.output_model_path)
    torch_profiler_trace_dir_raw = getattr(args, "torch_profiler_trace_dir", None)
    torch_profiler_trace_dir = (
        output_model_path.parent / "profiling" / "pytorch"
        if torch_profiler_trace_dir_raw in (None, "")
        else Path(str(torch_profiler_trace_dir_raw))
    )
    torch_profiler_config = resolve_torch_profiler_config(
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
            getattr(args, "torch_profiler_profile_memory", DEFAULT_TORCH_PROFILER_PROFILE_MEMORY)
        ),
        with_stack=bool(
            getattr(args, "torch_profiler_with_stack", DEFAULT_TORCH_PROFILER_WITH_STACK)
        ),
    )
    torch_profiler_session = TorchProfilerSession(torch_profiler_config)
    tracker_config = build_training_tracker_config(
        output_model_path=output_model_path,
        tracker_run_name=(
            None
            if getattr(args, "tracker_run_name", None) in (None, "")
            else str(args.tracker_run_name)
        ),
        tracker_project_name=(
            None
            if getattr(args, "tracker_project_name", None) in (None, "")
            else str(args.tracker_project_name)
        ),
        mlflow_experiment_name=(
            None
            if getattr(args, "mlflow_experiment_name", None) in (None, "")
            else str(args.mlflow_experiment_name)
        ),
        mlflow_tracking_uri=(
            None
            if getattr(args, "mlflow_tracking_uri", None) in (None, "")
            else str(args.mlflow_tracking_uri)
        ),
        mlflow_artifact_root=(
            None
            if getattr(args, "mlflow_artifact_root", None) in (None, "")
            else str(args.mlflow_artifact_root)
        ),
        tensorboard_logging_dir=(
            None
            if getattr(args, "tensorboard_logging_dir", None) in (None, "")
            else str(args.tensorboard_logging_dir)
        ),
    )
    accelerator = Accelerator(
        gradient_accumulation_steps=GRADIENT_ACCUMULATION_STEPS,
        mixed_precision="bf16",
        log_with=list(tracker_config.tracker_backends),
        project_dir=tracker_config.tensorboard_logging_dir,
    )
    model_path = args.init_model_path
    qwen3tts = Qwen3TTSModel.from_pretrained(
        model_path,
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    talker_runtime = talker_runtime_fingerprint(qwen3tts.model)
    diagnostic_window = build_diagnostic_window_config(args)
    config = AutoConfig.from_pretrained(model_path)
    bundle_summary = (
        None
        if getattr(args, "pilot_bundle_root", None) in (None, "")
        else load_optional_training_bundle_summary(Path(str(args.pilot_bundle_root)))
    )
    train_data = _load_training_rows(
        Path(args.train_jsonl),
        require_precomputed_ref_inputs=bundle_summary is not None,
    )
    eval_data = _load_training_rows(
        Path(args.eval_jsonl),
        require_precomputed_ref_inputs=bundle_summary is not None,
    )
    if len(eval_data) == 0:
        raise ValueError("`--eval_jsonl` must contain at least one prepared row.")
    dataset = TTSDataset(
        train_data,
        qwen3tts.processor,
        config,
        ref_mel_cache=ref_mel_cache,
        data_path_attribution=data_path_attribution,
    )
    eval_dataset = TTSDataset(
        eval_data,
        qwen3tts.processor,
        config,
        ref_mel_cache=ref_mel_cache,
        data_path_attribution=None,
    )
    row_metrics = dataset.batch_metrics()
    eval_row_metrics = eval_dataset.batch_metrics()
    batch_sampler = BucketedBatchSampler(
        row_metrics=row_metrics,
        policy=throughput_batch_policy,
        shuffle=True,
        shuffle_seed=0,
    )
    eval_batch_sampler = BucketedBatchSampler(
        row_metrics=eval_row_metrics,
        policy=throughput_batch_policy,
        shuffle=False,
        shuffle_seed=0,
    )
    batch_occupancy_summary = summarize_batch_occupancy(
        row_metrics=row_metrics,
        planned_batches=batch_sampler.planned_batches(),
    )
    train_dataloader = _build_dataloader(
        dataset=dataset,
        batch_sampler=batch_sampler,
        tuning=effective_dataloader_tuning,
    )
    eval_dataloader = _build_dataloader(
        dataset=eval_dataset,
        batch_sampler=eval_batch_sampler,
        tuning=effective_dataloader_tuning,
    )
    optimizer = AdamW(qwen3tts.model.parameters(), lr=args.lr, weight_decay=0.01)
    model, optimizer, train_dataloader, eval_dataloader = accelerator.prepare(
        qwen3tts.model,
        optimizer,
        train_dataloader,
        eval_dataloader,
    )
    return PreparedTrainingRun(
        args=args,
        output_model_path=output_model_path,
        model_path=model_path,
        qwen3tts=qwen3tts,
        accelerator=accelerator,
        model=model,
        checkpointable_model=qwen3tts.model,
        optimizer=optimizer,
        train_dataloader=train_dataloader,
        eval_dataloader=eval_dataloader,
        dataloader_length=len(train_dataloader),
        eval_dataloader_length=len(eval_dataloader),
        effective_dataloader_tuning=effective_dataloader_tuning,
        throughput_batch_policy=throughput_batch_policy,
        throughput_profile_payload=throughput_policy_payload(
            throughput_batch_policy,
            batch_occupancy=batch_occupancy_summary.payload(),
        ),
        batch_occupancy_summary=batch_occupancy_summary,
        data_path_attribution=data_path_attribution,
        ref_mel_cache=ref_mel_cache,
        torch_profiler_session=torch_profiler_session,
        tracker_config=tracker_config,
        talker_runtime=talker_runtime,
        diagnostic_window=diagnostic_window,
        heartbeat_policy=heartbeat_policy,
        loss_observer=loss_observer,
        finite_loss_guard=finite_loss_guard,
    )


def _build_dataloader(
    *,
    dataset: TTSDataset,
    batch_sampler: BucketedBatchSampler,
    tuning: DataloaderTuning,
) -> DataLoader[object]:
    """Build one canonical dataloader for train or held-out eval rows."""
    if tuning.num_workers > 0:
        return DataLoader(
            dataset,
            batch_sampler=batch_sampler,
            collate_fn=dataset.collate_fn,
            num_workers=tuning.num_workers,
            pin_memory=tuning.pin_memory,
            persistent_workers=tuning.persistent_workers,
            prefetch_factor=tuning.prefetch_factor,
        )
    return DataLoader(
        dataset,
        batch_sampler=batch_sampler,
        collate_fn=dataset.collate_fn,
        num_workers=0,
        pin_memory=tuning.pin_memory,
    )
