"""Tests for training-manifest compatibility in the patched Qwen trainer.

Purpose:
    Verify that the trainer still accepts legacy Task 101 manifests while also
    supporting the newer persisted-ref-input contract.

Relationships:
    - Exercises `sft_12hz_training_rows.py` and `dataset.py`.
    - Protects the minimal compatibility fix that unblocks `T172` validation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import torch

from scripts.devops.qwen_finetuning_patches.dataset import (
    DatasetItem,
    TTSDataset,
    _collate_ref_mels,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_training_rows import _load_training_rows
from tests.sir_convert_a_lot.ml.qwen.preprocessing.test_support import write_test_wav


@dataclass
class _FakeConfig:
    """Minimal config stub for dataset compatibility tests."""

    tts_pad_token_id: int = 0
    tts_bos_token_id: int = 1
    tts_eos_token_id: int = 2


class _FakeProcessor:
    """Minimal processor stub that returns deterministic token ids."""

    def __call__(
        self,
        *,
        text: str,
        return_tensors: str,
        padding: bool,
    ) -> dict[str, torch.Tensor]:
        del text, return_tensors, padding
        return {"input_ids": torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long)}


def test_load_training_rows_accepts_legacy_manifest_without_precomputed_ref_input(
    tmp_path: Path,
) -> None:
    """Legacy manifests without persisted-ref-input fields should still load."""
    manifest_path = tmp_path / "train.prepared.jsonl"
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    manifest_path.write_text(
        json.dumps(
            {
                "text": "hej",
                "audio_codes": [[1, 2]],
                "ref_audio": ref_audio_path.relative_to(tmp_path).as_posix(),
                "speaker_id": "speaker-a",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = _load_training_rows(manifest_path)

    assert rows[0]["ref_audio"] == ref_audio_path.as_posix()
    assert "precomputed_ref_input_path" not in rows[0]


def test_dataset_uses_legacy_ref_audio_fallback_without_precomputed_ref_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dataset items should still extract ref-mels from legacy `ref_audio` rows."""
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    dataset = TTSDataset(
        data_list=[
            {
                "text": "hej",
                "audio_codes": [[1, 2]],
                "ref_audio": ref_audio_path.as_posix(),
                "speaker_id": "speaker-a",
            }
        ],
        processor=_FakeProcessor(),
        config=_FakeConfig(),
    )
    expected_ref_mel = torch.ones((1, 4, 8), dtype=torch.float32)
    monkeypatch.setattr(
        TTSDataset,
        "extract_mels",
        lambda self, audio, sample_rate: expected_ref_mel,
    )

    item = dataset[0]

    assert torch.equal(item["ref_mel"], expected_ref_mel)


def test_collate_ref_mels_pads_variable_length_reference_inputs() -> None:
    """Batch collation should pad variable-length ref-mels for aggressive batches."""
    batch: list[DatasetItem] = [
        {
            "text_ids": torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long),
            "audio_codes": torch.tensor([[1, 2]], dtype=torch.long),
            "ref_mel": torch.full((1, 2, 3), 1.0, dtype=torch.float32),
            "speaker_id": 0,
        },
        {
            "text_ids": torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long),
            "audio_codes": torch.tensor([[1, 2]], dtype=torch.long),
            "ref_mel": torch.full((1, 4, 3), 2.0, dtype=torch.float32),
            "speaker_id": 1,
        },
    ]

    ref_mels = _collate_ref_mels(batch)

    assert ref_mels.shape == (2, 4, 3)
    assert torch.equal(ref_mels[0, :2], torch.full((2, 3), 1.0, dtype=torch.float32))
    assert torch.equal(ref_mels[0, 2:], torch.zeros((2, 3), dtype=torch.float32))
    assert torch.equal(ref_mels[1], torch.full((4, 3), 2.0, dtype=torch.float32))
