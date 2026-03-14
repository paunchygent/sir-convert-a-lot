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
"""Speaker-aware Qwen fine-tuning dataset helpers.

This module adapts the upstream Qwen TTS dataset flow for the repo's planned
multi-speaker Swedish language-expansion lane. It keeps the official text/audio
packing shape, adds deterministic dataset-scoped speaker mapping, and emits the
reference-mel plus speaker-aware tensors expected by the patched
`sft_12hz.py` training entrypoint in the same directory.
"""

from __future__ import annotations

import contextlib
import io
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import NotRequired, Protocol, TypeAlias, TypedDict

import numpy as np
import numpy.typing as npt
import torch
from torch.utils.data import Dataset

with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSConfig

from scripts.devops.qwen_finetuning_patches.sft_12hz_batching import TrainingRowBatchMetrics
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_inputs import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
    extract_ref_mel,
    load_audio_to_np,
    load_persisted_ref_mel,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_mel_cache import (
    RefMelCache,
    canonical_ref_audio_cache_key,
)

AudioArray: TypeAlias = npt.NDArray[np.float32]
AudioWithRate: TypeAlias = tuple[AudioArray, int]
AudioInput: TypeAlias = str | AudioWithRate
AudioInputs: TypeAlias = str | AudioWithRate | list[str] | list[AudioWithRate]
TokenizerInputIds: TypeAlias = torch.Tensor | Sequence[int] | Sequence[Sequence[int]]


class ProcessorProtocol(Protocol):
    """Minimal processor surface used by the patched dataset."""

    def __call__(
        self,
        *,
        text: str,
        return_tensors: str,
        padding: bool,
    ) -> Mapping[str, TokenizerInputIds]:
        """Tokenize text into the upstream input-id surface."""


class TrainingRow(TypedDict):
    """One Qwen fine-tuning manifest row."""

    text: str
    audio_codes: list[list[int]]
    ref_audio: str | list[str]
    precomputed_ref_input_path: NotRequired[str]
    precomputed_ref_input_kind: NotRequired[str]
    precomputed_ref_input_version: NotRequired[str]
    precomputed_ref_input_source_audio: NotRequired[str]
    speaker_id: NotRequired[str]


class DatasetItem(TypedDict):
    """One fully prepared training item returned by `__getitem__`."""

    text_ids: torch.Tensor
    audio_codes: torch.Tensor
    ref_mel: torch.Tensor
    speaker_id: int


class BatchTensors(TypedDict):
    """One collated training batch consumed by `sft_12hz.py`."""

    input_ids: torch.Tensor
    ref_mels: torch.Tensor
    attention_mask: torch.Tensor
    text_embedding_mask: torch.Tensor
    codec_embedding_mask: torch.Tensor
    codec_0_labels: torch.Tensor
    codec_ids: torch.Tensor
    codec_mask: torch.Tensor
    speaker_ids: torch.Tensor


def _collate_ref_mels(batch: Sequence[DatasetItem]) -> torch.Tensor:
    """Pad variable-length reference mels into one batch tensor."""
    if not batch:
        raise ValueError("Cannot collate an empty reference-mel batch.")
    ref_mels = [item["ref_mel"] for item in batch]
    first_ref_mel = ref_mels[0]
    if first_ref_mel.ndim != 3 or first_ref_mel.shape[0] != 1:
        raise ValueError("Reference mels must have shape `[1, frames, mel_bins]`.")
    mel_bin_count = int(first_ref_mel.shape[2])
    max_frame_count = max(int(ref_mel.shape[1]) for ref_mel in ref_mels)
    padded_ref_mels = first_ref_mel.new_zeros((len(ref_mels), max_frame_count, mel_bin_count))
    for batch_index, ref_mel in enumerate(ref_mels):
        if ref_mel.ndim != 3 or ref_mel.shape[0] != 1:
            raise ValueError("Reference mels must have shape `[1, frames, mel_bins]`.")
        if int(ref_mel.shape[2]) != mel_bin_count:
            raise ValueError("Reference mels in one batch must share the same mel-bin count.")
        frame_count = int(ref_mel.shape[1])
        padded_ref_mels[batch_index, :frame_count, :] = ref_mel[0]
    return padded_ref_mels


class TTSDataset(Dataset[DatasetItem]):
    """Dataset adapter for multi-speaker Qwen TTS fine-tuning."""

    def __init__(
        self,
        data_list: Sequence[TrainingRow],
        processor: ProcessorProtocol,
        config: Qwen3TTSConfig,
        lag_num: int = -1,
        ref_mel_cache: RefMelCache | None = None,
    ) -> None:
        self.data_list = list(data_list)
        self.processor = processor
        self.lag_num = lag_num
        self.config = config
        self.ref_mel_cache = ref_mel_cache
        self._tokenized_text_ids = [
            self._tokenize_texts(self._build_assistant_text(item["text"]))
            for item in self.data_list
        ]
        self._row_batch_metrics = [
            TrainingRowBatchMetrics(
                text_token_count=int(text_ids[:, :-5].shape[1]),
                codec_frame_count=len(item["audio_codes"]),
            )
            for item, text_ids in zip(self.data_list, self._tokenized_text_ids, strict=True)
        ]

        self.spk_id_map: dict[str, int] = {}
        for item in self.data_list:
            speaker_id = item.get("speaker_id", "default_speaker")
            if speaker_id not in self.spk_id_map:
                self.spk_id_map[speaker_id] = len(self.spk_id_map)

    def __len__(self) -> int:
        return len(self.data_list)

    def batch_metrics(self) -> list[TrainingRowBatchMetrics]:
        """Return the precomputed batching metrics for the loaded rows."""
        return list(self._row_batch_metrics)

    def _normalize_audio_inputs(self, audios: AudioInputs) -> list[AudioWithRate]:
        """Normalize audio inputs into `(waveform, sample_rate)` tuples."""
        if isinstance(audios, list):
            items = list(audios)
        else:
            items = [audios]
        normalized_items: list[AudioWithRate] = []
        for audio_input in items:
            if isinstance(audio_input, str):
                normalized_items.append(load_audio_to_np(Path(audio_input)))
                continue
            waveform, sample_rate = audio_input
            if not isinstance(waveform, np.ndarray):
                raise ValueError("Expected audio waveform arrays after normalization.")
            if not isinstance(sample_rate, int):
                raise ValueError("Expected integer sample rates after normalization.")
            normalized_items.append((waveform.astype(np.float32, copy=False), int(sample_rate)))
        return normalized_items

    def _build_assistant_text(self, text: str) -> str:
        return f"<|im_start|>assistant\n{text}<|im_end|>\n<|im_start|>assistant\n"

    def _tokenize_texts(self, text: str) -> torch.Tensor:
        encoded = self.processor(text=text, return_tensors="pt", padding=True)
        input_ids = encoded["input_ids"]
        if isinstance(input_ids, torch.Tensor):
            return input_ids.unsqueeze(0) if input_ids.dim() == 1 else input_ids
        return self._sequence_input_ids_to_tensor(input_ids)

    def _sequence_input_ids_to_tensor(
        self,
        input_ids: Sequence[int] | Sequence[Sequence[int]],
    ) -> torch.Tensor:
        if not input_ids:
            raise ValueError("Tokenized text did not include any input ids.")

        first_item = input_ids[0]
        if isinstance(first_item, Sequence) and not isinstance(first_item, (str, bytes)):
            batched_ids: list[list[int]] = []
            for row in input_ids:
                if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
                    raise ValueError("Expected tokenized ids to be batched integer sequences.")
                batched_ids.append([int(token_id) for token_id in row])
            return torch.tensor(batched_ids, dtype=torch.long)

        token_ids: list[int] = []
        for token_id in input_ids:
            if not isinstance(token_id, int):
                raise ValueError("Expected tokenized ids to be integers.")
            token_ids.append(int(token_id))
        return torch.tensor([token_ids], dtype=torch.long)

    @torch.inference_mode()
    def extract_mels(self, audio: AudioArray, sample_rate: int) -> torch.Tensor:
        return extract_ref_mel(audio, sample_rate=sample_rate)

    def _extract_ref_mel(self, ref_audio_value: AudioInputs) -> torch.Tensor:
        """Return one extracted ref-mel tensor from a row ref-audio field."""
        normalized_audio_inputs = self._normalize_audio_inputs(ref_audio_value)
        waveform, sample_rate = normalized_audio_inputs[0]
        return self.extract_mels(audio=waveform, sample_rate=sample_rate)

    def _load_precomputed_ref_mel(self, item: TrainingRow) -> torch.Tensor:
        """Load one persisted precomputed ref-mel tensor from a manifest row."""
        precomputed_ref_input_path = item.get("precomputed_ref_input_path")
        if not isinstance(precomputed_ref_input_path, str):
            raise ValueError(
                "Training row did not include a persisted `precomputed_ref_input_path`."
            )
        if item["precomputed_ref_input_kind"] != PRECOMPUTED_REF_INPUT_KIND:
            raise ValueError(
                "Training row referenced unsupported precomputed reference input kind "
                f"`{item['precomputed_ref_input_kind']}`."
            )
        if item["precomputed_ref_input_version"] != PRECOMPUTED_REF_INPUT_VERSION:
            raise ValueError(
                "Training row referenced unsupported precomputed reference input version "
                f"`{item['precomputed_ref_input_version']}`."
            )
        return load_persisted_ref_mel(Path(precomputed_ref_input_path))

    def _load_ref_mel(self, item: TrainingRow) -> torch.Tensor:
        """Load one row ref-mel from the preferred persisted or legacy fallback path."""
        precomputed_ref_input_path = item.get("precomputed_ref_input_path")
        if isinstance(precomputed_ref_input_path, str):
            return self._load_precomputed_ref_mel(item)
        return self._extract_ref_mel(item["ref_audio"])

    def _cache_key_for_item(self, item: TrainingRow) -> str | None:
        """Return the stable cache key for one row ref-mel source."""
        precomputed_ref_input_path = item.get("precomputed_ref_input_path")
        if isinstance(precomputed_ref_input_path, str):
            return canonical_ref_audio_cache_key(precomputed_ref_input_path)
        return canonical_ref_audio_cache_key(item["ref_audio"])

    def __getitem__(self, idx: int) -> DatasetItem:
        item = self.data_list[idx]
        text_ids = self._tokenized_text_ids[idx]
        audio_codes = torch.tensor(item["audio_codes"], dtype=torch.long)

        speaker_id = item.get("speaker_id", "default_speaker")
        mapped_speaker_id = self.spk_id_map[speaker_id]

        cache_key = self._cache_key_for_item(item)
        if self.ref_mel_cache is not None and cache_key is not None:
            cached_ref_mel = self.ref_mel_cache.get(cache_key)
            if cached_ref_mel is None:
                ref_mel = self._load_ref_mel(item)
                self.ref_mel_cache.put(cache_key, ref_mel)
            else:
                ref_mel = cached_ref_mel
        else:
            ref_mel = self._load_ref_mel(item)

        return {
            "text_ids": text_ids[:, :-5],
            "audio_codes": audio_codes,
            "ref_mel": ref_mel,
            "speaker_id": mapped_speaker_id,
        }

    def collate_fn(self, batch: list[DatasetItem]) -> BatchTensors:
        if self.lag_num != -1:
            raise ValueError("Only lag_num=-1 is supported by the Qwen patch set.")

        item_lengths = [item["text_ids"].shape[1] + item["audio_codes"].shape[0] for item in batch]
        max_length = max(item_lengths) + 8
        batch_size = len(batch)

        input_ids = torch.zeros((batch_size, max_length, 2), dtype=torch.long)
        codec_ids = torch.zeros((batch_size, max_length, 16), dtype=torch.long)
        text_embedding_mask = torch.zeros((batch_size, max_length), dtype=torch.bool)
        codec_embedding_mask = torch.zeros((batch_size, max_length), dtype=torch.bool)
        codec_mask = torch.zeros((batch_size, max_length), dtype=torch.bool)
        attention_mask = torch.zeros((batch_size, max_length), dtype=torch.long)
        codec_0_labels = torch.full((batch_size, max_length), -100, dtype=torch.long)
        speaker_ids = torch.zeros(batch_size, dtype=torch.long)

        for batch_index, data in enumerate(batch):
            text_ids = data["text_ids"]
            audio_codes = data["audio_codes"]
            audio_codec_0 = audio_codes[:, 0]
            speaker_ids[batch_index] = data["speaker_id"]

            text_ids_len = text_ids.shape[1]
            codec_ids_len = audio_codec_0.shape[0]

            input_ids[batch_index, :3, 0] = text_ids[0, :3]
            input_ids[batch_index, 3:7, 0] = self.config.tts_pad_token_id
            input_ids[batch_index, 7, 0] = self.config.tts_bos_token_id
            input_ids[batch_index, 8 : 8 + text_ids_len - 3, 0] = text_ids[0, 3:]
            input_ids[batch_index, 8 + text_ids_len - 3, 0] = self.config.tts_eos_token_id
            input_ids[
                batch_index,
                8 + text_ids_len - 2 : 8 + text_ids_len + codec_ids_len,
                0,
            ] = self.config.tts_pad_token_id
            text_embedding_mask[batch_index, : 8 + text_ids_len + codec_ids_len] = True

            input_ids[batch_index, 3:8, 1] = torch.tensor(
                [
                    self.config.talker_config.codec_nothink_id,
                    self.config.talker_config.codec_think_bos_id,
                    self.config.talker_config.codec_think_eos_id,
                    0,
                    self.config.talker_config.codec_pad_id,
                ],
                dtype=torch.long,
            )
            input_ids[
                batch_index,
                8 : 8 + text_ids_len - 3,
                1,
            ] = self.config.talker_config.codec_pad_id
            input_ids[
                batch_index,
                8 + text_ids_len - 3,
                1,
            ] = self.config.talker_config.codec_pad_id
            input_ids[
                batch_index,
                8 + text_ids_len - 2,
                1,
            ] = self.config.talker_config.codec_bos_id
            input_ids[
                batch_index,
                8 + text_ids_len - 1 : 8 + text_ids_len - 1 + codec_ids_len,
                1,
            ] = audio_codec_0
            input_ids[
                batch_index,
                8 + text_ids_len - 1 + codec_ids_len,
                1,
            ] = self.config.talker_config.codec_eos_token_id

            codec_0_labels[
                batch_index,
                8 + text_ids_len - 1 : 8 + text_ids_len - 1 + codec_ids_len,
            ] = audio_codec_0
            codec_0_labels[
                batch_index,
                8 + text_ids_len - 1 + codec_ids_len,
            ] = self.config.talker_config.codec_eos_token_id

            codec_ids[
                batch_index,
                8 + text_ids_len - 1 : 8 + text_ids_len - 1 + codec_ids_len,
                :,
            ] = audio_codes

            codec_embedding_mask[batch_index, 3 : 8 + text_ids_len + codec_ids_len] = True
            codec_embedding_mask[batch_index, 6] = False

            codec_mask[
                batch_index,
                8 + text_ids_len - 1 : 8 + text_ids_len - 1 + codec_ids_len,
            ] = True
            attention_mask[batch_index, : 8 + text_ids_len + codec_ids_len] = 1

        ref_mels = _collate_ref_mels(batch)

        return {
            "input_ids": input_ids,
            "ref_mels": ref_mels,
            "attention_mask": attention_mask,
            "text_embedding_mask": text_embedding_mask.unsqueeze(-1),
            "codec_embedding_mask": codec_embedding_mask.unsqueeze(-1),
            "codec_0_labels": codec_0_labels,
            "codec_ids": codec_ids,
            "codec_mask": codec_mask,
            "speaker_ids": speaker_ids,
        }
