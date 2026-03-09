# coding=utf-8
# Copyright 2026 The Alibaba Qwen team.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Patched Qwen `sft_12hz.py` entrypoint for Swedish multi-speaker training.

This module keeps the upstream Qwen training loop shape but preserves the
speaker encoder, keeps exported checkpoints in base-model form, and applies the
text-projection fix needed by the repo's planned Swedish language-expansion
lane. It is paired with the speaker-aware `dataset.py` patch in the same
directory and is intended for the Task 100 runtime rather than the serving
sidecar lane.
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import torch
from accelerate import Accelerator
from dataset import TrainingRow, TTSDataset
from huggingface_hub import hf_hub_download, snapshot_download
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel
from safetensors.torch import save_file
from torch.optim import AdamW
from torch.utils.data import DataLoader
from transformers import AutoConfig

EXPORT_METADATA_PATTERNS = (
    "*.json",
    "*.model",
    "*.py",
    "*.tiktoken",
    "*.txt",
)


@dataclass(frozen=True)
class TrainingSummary:
    """Machine-readable summary for one bounded Qwen fine-tuning run."""

    init_model_path: str
    output_model_path: str
    train_jsonl: str
    batch_size: int
    lr: float
    num_epochs: int
    max_steps: int | None
    checkpoint_interval_steps: int
    optimizer_steps_completed: int
    last_loss: float | None
    peak_memory_allocated_bytes: int | None
    peak_memory_reserved_bytes: int | None
    resumed_from_checkpoint_path: str | None
    latest_durable_checkpoint_path: str | None
    latest_durable_checkpoint_step: int | None
    latest_durable_checkpoint_epoch: int | None
    durable_checkpoint_paths: list[str]
    checkpoint_paths: list[str]


@dataclass(frozen=True)
class DurableCheckpointMetadata:
    """Resume cursor metadata for one durable trainer-state checkpoint."""

    checkpoint_path: str
    saved_at: str
    reason: str
    optimizer_steps_completed: int
    epoch: int
    next_epoch: int
    next_step_in_epoch: int


class CheckpointAccelerator(Protocol):
    """Minimal accelerator protocol required for durable checkpoint persistence."""

    is_main_process: bool

    def wait_for_everyone(self) -> None:
        """Synchronize checkpointing across processes."""

    def save_state(self, output_dir: str | None = None, safe_serialization: bool = True) -> None:
        """Persist full trainer state to the selected checkpoint directory."""


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init_model_path", type=str, default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--output_model_path", type=str, default="output")
    parser.add_argument("--train_jsonl", type=str, required=True)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num_epochs", type=int, default=3)
    parser.add_argument("--max_steps", type=int, default=None)
    parser.add_argument("--checkpoint_interval_steps", type=int, default=100)
    parser.add_argument("--resume_from_checkpoint", type=str, default=None)
    parser.add_argument("--metrics_output_json", type=str, default=None)
    parser.add_argument(
        "--speaker_name",
        type=str,
        default="speaker_test",
        help=(
            "Compatibility-only argument kept for existing runner surfaces. "
            "The multi-speaker patch set does not use it."
        ),
    )
    return parser.parse_args()


def _load_training_rows(train_jsonl_path: Path) -> list[TrainingRow]:
    rows: list[TrainingRow] = []
    with train_jsonl_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError("Expected each training JSONL row to be a JSON object.")
            rows.append(_resolve_training_row_paths(train_jsonl_path, row))
    return rows


def _resolve_training_row_paths(train_jsonl_path: Path, row: dict[str, object]) -> TrainingRow:
    """Resolve manifest-relative training paths into absolute paths."""
    manifest_root = train_jsonl_path.parent
    ref_audio_value = row.get("ref_audio")
    resolved_ref_audio: str | list[str]
    if isinstance(ref_audio_value, str):
        resolved_ref_audio = _resolve_manifest_path(manifest_root, ref_audio_value)
    elif isinstance(ref_audio_value, list):
        resolved_ref_audio_list: list[str] = []
        for item in ref_audio_value:
            if not isinstance(item, str):
                raise ValueError("Expected `ref_audio` list values to be strings.")
            resolved_ref_audio_list.append(_resolve_manifest_path(manifest_root, item))
        resolved_ref_audio = resolved_ref_audio_list
    else:
        raise ValueError("Training row is missing a valid `ref_audio` value.")
    text_value = row.get("text")
    if not isinstance(text_value, str):
        raise ValueError("Training row is missing a valid `text` value.")
    audio_codes_value = row.get("audio_codes")
    if not isinstance(audio_codes_value, list):
        raise ValueError("Training row is missing a valid `audio_codes` value.")
    speaker_id_value = row.get("speaker_id")
    resolved_row: TrainingRow = {
        "text": text_value,
        "audio_codes": audio_codes_value,
        "ref_audio": resolved_ref_audio,
    }
    if isinstance(speaker_id_value, str):
        resolved_row["speaker_id"] = speaker_id_value
    return resolved_row


def _resolve_manifest_path(manifest_root: Path, raw_path: str) -> str:
    """Resolve one manifest-relative path against the training manifest root."""
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate.as_posix()
    manifest_relative = manifest_root / candidate
    run_root_relative = manifest_root.parent / candidate
    if manifest_relative.exists():
        return manifest_relative.resolve().as_posix()
    if run_root_relative.exists():
        return run_root_relative.resolve().as_posix()
    return run_root_relative.resolve().as_posix()


def _load_config_dict(model_path: str) -> dict[str, object]:
    config_path = _resolve_model_config_path(model_path)
    with config_path.open("r", encoding="utf-8") as handle:
        config_dict_raw = json.load(handle)
    if not isinstance(config_dict_raw, dict):
        raise ValueError("Expected config.json to contain a JSON object.")
    return {str(key): value for key, value in config_dict_raw.items()}


def _resolve_model_config_path(model_path: str) -> Path:
    local_model_path = Path(model_path)
    if local_model_path.is_dir():
        return local_model_path / "config.json"

    return Path(hf_hub_download(repo_id=model_path, filename="config.json"))


def _resolve_model_export_source_path(model_path: str) -> Path:
    local_model_path = Path(model_path)
    if local_model_path.is_dir():
        return local_model_path

    snapshot_path = snapshot_download(
        repo_id=model_path,
        allow_patterns=list(EXPORT_METADATA_PATTERNS),
    )
    return Path(snapshot_path)


def _save_checkpoint(
    *,
    accelerator: Accelerator,
    model: torch.nn.Module,
    model_path: str,
    output_dir: Path,
) -> str:
    """Export one checkpoint directory from the current training state."""
    resolved_model_path = _resolve_model_export_source_path(model_path)
    shutil.copytree(resolved_model_path, output_dir, dirs_exist_ok=True)

    config_dict = _load_config_dict(model_path)
    config_dict["tts_model_type"] = "base"

    output_config_path = output_dir / "config.json"
    with output_config_path.open("w", encoding="utf-8") as handle:
        json.dump(config_dict, handle, indent=2, ensure_ascii=False)

    unwrapped_model = accelerator.unwrap_model(model)
    state_dict = {
        key: value.detach().to("cpu") for key, value in unwrapped_model.state_dict().items()
    }
    save_file(state_dict, (output_dir / "model.safetensors").as_posix())
    return output_dir.as_posix()


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _latest_checkpoint_pointer_path(output_model_path: Path) -> Path:
    """Return the run-root pointer that tracks the latest durable checkpoint."""
    return output_model_path.parent / "latest_checkpoint.json"


def _durable_checkpoint_metadata_path(checkpoint_dir: Path) -> Path:
    """Return the metadata path stored alongside one durable checkpoint."""
    return checkpoint_dir / "training_state.json"


def _durable_checkpoint_dir(output_model_path: Path, optimizer_steps_completed: int) -> Path:
    """Return the durable checkpoint directory for one optimizer step."""
    return output_model_path / f"state-step-{optimizer_steps_completed:08d}"


def _checkpoint_resume_cursor(
    *,
    epoch: int,
    step_in_epoch: int,
    dataloader_length: int,
) -> tuple[int, int]:
    """Return the next epoch and intra-epoch step after one completed batch."""
    next_step_in_epoch = step_in_epoch + 1
    next_epoch = epoch
    if next_step_in_epoch >= dataloader_length:
        next_epoch = epoch + 1
        next_step_in_epoch = 0
    return next_epoch, next_step_in_epoch


def _save_durable_checkpoint(
    *,
    accelerator: CheckpointAccelerator,
    output_model_path: Path,
    optimizer_steps_completed: int,
    epoch: int,
    step_in_epoch: int,
    dataloader_length: int,
    reason: str,
) -> DurableCheckpointMetadata:
    """Persist one resumable trainer-state checkpoint and update the latest pointer."""
    checkpoint_dir = _durable_checkpoint_dir(output_model_path, optimizer_steps_completed)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    accelerator.wait_for_everyone()
    accelerator.save_state(checkpoint_dir.as_posix())
    next_epoch, next_step_in_epoch = _checkpoint_resume_cursor(
        epoch=epoch,
        step_in_epoch=step_in_epoch,
        dataloader_length=dataloader_length,
    )
    metadata = DurableCheckpointMetadata(
        checkpoint_path=checkpoint_dir.as_posix(),
        saved_at=_utc_now_iso(),
        reason=reason,
        optimizer_steps_completed=optimizer_steps_completed,
        epoch=epoch,
        next_epoch=next_epoch,
        next_step_in_epoch=next_step_in_epoch,
    )
    if accelerator.is_main_process:
        _write_json(_durable_checkpoint_metadata_path(checkpoint_dir), asdict(metadata))
        _write_json(_latest_checkpoint_pointer_path(output_model_path), asdict(metadata))
    accelerator.wait_for_everyone()
    return metadata


def _load_durable_checkpoint_metadata(checkpoint_path: Path) -> DurableCheckpointMetadata:
    """Load durable checkpoint metadata required for exact resume."""
    payload = json.loads(
        _durable_checkpoint_metadata_path(checkpoint_path).read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise ValueError("Expected durable checkpoint metadata to be a JSON object.")
    return DurableCheckpointMetadata(
        checkpoint_path=str(payload["checkpoint_path"]),
        saved_at=str(payload["saved_at"]),
        reason=str(payload["reason"]),
        optimizer_steps_completed=int(payload["optimizer_steps_completed"]),
        epoch=int(payload["epoch"]),
        next_epoch=int(payload["next_epoch"]),
        next_step_in_epoch=int(payload["next_step_in_epoch"]),
    )


def train_with_args(args: argparse.Namespace) -> TrainingSummary:
    """Run one bounded Qwen fine-tuning job and return machine-readable metrics."""
    if args.max_steps is not None and args.max_steps <= 0:
        raise ValueError("`--max_steps` must be positive when provided.")
    if int(args.checkpoint_interval_steps) <= 0:
        raise ValueError("`--checkpoint_interval_steps` must be positive.")

    accelerator = Accelerator(
        gradient_accumulation_steps=4,
        mixed_precision="bf16",
        log_with="tensorboard",
        project_dir=Path(args.output_model_path).resolve().as_posix(),
    )

    model_path = args.init_model_path
    qwen3tts = Qwen3TTSModel.from_pretrained(
        model_path,
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    config = AutoConfig.from_pretrained(model_path)

    train_data = _load_training_rows(Path(args.train_jsonl))
    dataset = TTSDataset(train_data, qwen3tts.processor, config)
    train_dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=True,
        collate_fn=dataset.collate_fn,
    )
    optimizer = AdamW(qwen3tts.model.parameters(), lr=args.lr, weight_decay=0.01)

    model, optimizer, train_dataloader = accelerator.prepare(
        qwen3tts.model,
        optimizer,
        train_dataloader,
    )

    output_model_path = Path(args.output_model_path)
    dataloader_length = len(train_dataloader)
    durable_checkpoint_paths: list[str] = []
    latest_durable_checkpoint: DurableCheckpointMetadata | None = None
    resumed_from_checkpoint_path: str | None = None
    starting_epoch = 0
    resume_step_in_epoch = 0
    model.train()
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    optimizer_steps_completed = 0
    last_loss: float | None = None
    checkpoint_paths: list[str] = []
    if args.resume_from_checkpoint is not None:
        resume_checkpoint_path = Path(args.resume_from_checkpoint)
        latest_durable_checkpoint = _load_durable_checkpoint_metadata(resume_checkpoint_path)
        accelerator.load_state(resume_checkpoint_path.as_posix())
        resumed_from_checkpoint_path = resume_checkpoint_path.as_posix()
        optimizer_steps_completed = latest_durable_checkpoint.optimizer_steps_completed
        starting_epoch = latest_durable_checkpoint.next_epoch
        resume_step_in_epoch = latest_durable_checkpoint.next_step_in_epoch
        durable_checkpoint_paths.append(resume_checkpoint_path.as_posix())
    reached_max_steps = False
    epoch = starting_epoch
    step = 0
    for epoch in range(starting_epoch, args.num_epochs):
        epoch_dataloader = train_dataloader
        epoch_start_step = 0
        if epoch == starting_epoch and resume_step_in_epoch > 0:
            epoch_dataloader = accelerator.skip_first_batches(
                train_dataloader,
                resume_step_in_epoch,
            )
            epoch_start_step = resume_step_in_epoch
        for step, batch in enumerate(epoch_dataloader, start=epoch_start_step):
            with accelerator.accumulate(model):
                input_ids = batch["input_ids"]
                codec_ids = batch["codec_ids"]
                ref_mels = batch["ref_mels"]
                text_embedding_mask = batch["text_embedding_mask"]
                codec_embedding_mask = batch["codec_embedding_mask"]
                attention_mask = batch["attention_mask"]
                codec_0_labels = batch["codec_0_labels"]
                codec_mask = batch["codec_mask"]

                speaker_embedding = model.speaker_encoder(
                    ref_mels.to(model.device).to(model.dtype)
                ).detach()

                input_text_ids = input_ids[:, :, 0]
                input_codec_ids = input_ids[:, :, 1]

                input_text_embedding = (
                    model.talker.model.text_embedding(input_text_ids) * text_embedding_mask
                )
                if hasattr(model.talker.model, "text_projection"):
                    input_text_embedding = model.talker.model.text_projection(input_text_embedding)

                input_codec_embedding = (
                    model.talker.model.codec_embedding(input_codec_ids) * codec_embedding_mask
                )
                input_codec_embedding[:, 6, :] = speaker_embedding
                input_embeddings = input_text_embedding + input_codec_embedding

                for codec_index in range(1, 16):
                    codec_i_embedding = model.talker.code_predictor.get_input_embeddings()[
                        codec_index - 1
                    ](codec_ids[:, :, codec_index])
                    codec_i_embedding = codec_i_embedding * codec_mask.unsqueeze(-1)
                    input_embeddings = input_embeddings + codec_i_embedding

                outputs = model.talker(
                    inputs_embeds=input_embeddings[:, :-1, :],
                    attention_mask=attention_mask[:, :-1],
                    labels=codec_0_labels[:, 1:],
                    output_hidden_states=True,
                )

                hidden_states = outputs.hidden_states[0][-1]
                talker_hidden_states = hidden_states[codec_mask[:, 1:]]
                talker_codec_ids = codec_ids[codec_mask]

                _, sub_talker_loss = model.talker.forward_sub_talker_finetune(
                    talker_codec_ids,
                    talker_hidden_states,
                )
                loss = outputs.loss + 0.3 * sub_talker_loss

                accelerator.backward(loss)
                if accelerator.sync_gradients:
                    accelerator.clip_grad_norm_(model.parameters(), 1.0)

                optimizer.step()
                optimizer.zero_grad()
                optimizer_steps_completed += 1
                last_loss = float(loss.item())

            if step % 10 == 0:
                accelerator.print(f"Epoch {epoch} | Step {step} | Loss: {loss.item():.4f}")
            if optimizer_steps_completed % int(args.checkpoint_interval_steps) == 0:
                latest_durable_checkpoint = _save_durable_checkpoint(
                    accelerator=accelerator,
                    output_model_path=output_model_path,
                    optimizer_steps_completed=optimizer_steps_completed,
                    epoch=epoch,
                    step_in_epoch=step,
                    dataloader_length=dataloader_length,
                    reason="interval",
                )
                durable_checkpoint_paths.append(latest_durable_checkpoint.checkpoint_path)
            if args.max_steps is not None and optimizer_steps_completed >= args.max_steps:
                reached_max_steps = True
                break

        if accelerator.is_main_process:
            output_dir = output_model_path / f"checkpoint-epoch-{epoch}"
            checkpoint_paths.append(
                _save_checkpoint(
                    accelerator=accelerator,
                    model=model,
                    model_path=model_path,
                    output_dir=output_dir,
                )
            )
        if reached_max_steps:
            break

    if optimizer_steps_completed > 0 and (
        latest_durable_checkpoint is None
        or latest_durable_checkpoint.optimizer_steps_completed != optimizer_steps_completed
    ):
        latest_durable_checkpoint = _save_durable_checkpoint(
            accelerator=accelerator,
            output_model_path=output_model_path,
            optimizer_steps_completed=optimizer_steps_completed,
            epoch=epoch,
            step_in_epoch=step,
            dataloader_length=dataloader_length,
            reason="final-step",
        )
        durable_checkpoint_paths.append(latest_durable_checkpoint.checkpoint_path)

    if accelerator.is_main_process:
        final_output_dir = output_model_path / "checkpoint-final"
        checkpoint_paths.append(
            _save_checkpoint(
                accelerator=accelerator,
                model=model,
                model_path=model_path,
                output_dir=final_output_dir,
            )
        )

    peak_memory_allocated_bytes = (
        int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None
    )
    peak_memory_reserved_bytes = (
        int(torch.cuda.max_memory_reserved()) if torch.cuda.is_available() else None
    )
    return TrainingSummary(
        init_model_path=str(args.init_model_path),
        output_model_path=str(args.output_model_path),
        train_jsonl=str(args.train_jsonl),
        batch_size=int(args.batch_size),
        lr=float(args.lr),
        num_epochs=int(args.num_epochs),
        max_steps=None if args.max_steps is None else int(args.max_steps),
        checkpoint_interval_steps=int(args.checkpoint_interval_steps),
        optimizer_steps_completed=optimizer_steps_completed,
        last_loss=last_loss,
        peak_memory_allocated_bytes=peak_memory_allocated_bytes,
        peak_memory_reserved_bytes=peak_memory_reserved_bytes,
        resumed_from_checkpoint_path=resumed_from_checkpoint_path,
        latest_durable_checkpoint_path=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.checkpoint_path
        ),
        latest_durable_checkpoint_step=(
            None
            if latest_durable_checkpoint is None
            else latest_durable_checkpoint.optimizer_steps_completed
        ),
        latest_durable_checkpoint_epoch=(
            None if latest_durable_checkpoint is None else latest_durable_checkpoint.epoch
        ),
        durable_checkpoint_paths=durable_checkpoint_paths,
        checkpoint_paths=checkpoint_paths,
    )


def train() -> None:
    args = _parse_args()
    summary = train_with_args(args)
    if args.metrics_output_json is not None:
        metrics_output_path = Path(args.metrics_output_json)
        metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_output_path.open("w", encoding="utf-8") as handle:
            json.dump(asdict(summary), handle, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    train()
