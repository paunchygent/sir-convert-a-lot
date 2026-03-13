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

from collections.abc import Mapping, Sequence
from typing import NotRequired, Protocol, TypeAlias, TypedDict

import librosa
import numpy as np
import numpy.typing as npt
import torch
from qwen_tts.core.models.configuration_qwen3_tts import Qwen3TTSConfig
from qwen_tts.core.models.modeling_qwen3_tts import mel_spectrogram
from sft_12hz_ref_mel_cache import RefMelCache, canonical_ref_audio_cache_key
from torch.utils.data import Dataset

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

        self.spk_id_map: dict[str, int] = {}
        for item in self.data_list:
            speaker_id = item.get("speaker_id", "default_speaker")
            if speaker_id not in self.spk_id_map:
                self.spk_id_map[speaker_id] = len(self.spk_id_map)

    def __len__(self) -> int:
        return len(self.data_list)

    def _load_audio_to_np(self, path: str) -> AudioWithRate:
        audio, sample_rate = librosa.load(path, sr=None, mono=True)
        if audio.ndim > 1:
            audio = np.mean(audio, axis=-1)
        normalized_audio = audio.astype(np.float32, copy=False)
        return normalized_audio, int(sample_rate)

    def _normalize_audio_inputs(self, audios: AudioInputs) -> list[AudioWithRate]:
        """Normalize audio inputs into `(waveform, sample_rate)` tuples."""
        if isinstance(audios, list):
            items = list(audios)
        else:
            items = [audios]
        normalized_items: list[AudioWithRate] = []
        for audio_input in items:
            if isinstance(audio_input, str):
                normalized_items.append(self._load_audio_to_np(audio_input))
                continue
            waveform, sample_rate = audio_input
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
        if sample_rate != 24000:
            raise ValueError("Only support 24kHz audio.")
        return mel_spectrogram(
            torch.from_numpy(audio).unsqueeze(0),
            n_fft=1024,
            num_mels=128,
            sampling_rate=24000,
            hop_size=256,
            win_size=1024,
            fmin=0,
            fmax=12000,
        ).transpose(1, 2)

    def _extract_ref_mel(self, ref_audio_value: AudioInputs) -> torch.Tensor:
        """Return one extracted ref-mel tensor from a row ref-audio field."""
        normalized_audio_inputs = self._normalize_audio_inputs(ref_audio_value)
        waveform, sample_rate = normalized_audio_inputs[0]
        return self.extract_mels(audio=waveform, sample_rate=sample_rate)

    def __getitem__(self, idx: int) -> DatasetItem:
        item = self.data_list[idx]
        text = self._build_assistant_text(item["text"])
        text_ids = self._tokenize_texts(text)
        audio_codes = torch.tensor(item["audio_codes"], dtype=torch.long)

        speaker_id = item.get("speaker_id", "default_speaker")
        mapped_speaker_id = self.spk_id_map[speaker_id]

        ref_audio_value = item["ref_audio"]
        cache_key = canonical_ref_audio_cache_key(ref_audio_value)
        if self.ref_mel_cache is not None and cache_key is not None:
            cached_ref_mel = self.ref_mel_cache.get(cache_key)
            if cached_ref_mel is None:
                ref_mel = self._extract_ref_mel(ref_audio_value)
                self.ref_mel_cache.put(cache_key, ref_mel)
            else:
                ref_mel = cached_ref_mel
        else:
            ref_mel = self._extract_ref_mel(ref_audio_value)

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

        ref_mels = torch.cat([data["ref_mel"] for data in batch], dim=0)

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
