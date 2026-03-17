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
from scripts.devops.qwen_finetuning_patches.sft_12hz_data_path_attribution import (
    build_data_path_attribution_collector,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_inputs import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
    save_persisted_ref_mel,
)
from scripts.devops.qwen_finetuning_patches.sft_12hz_training_rows import _load_training_rows
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY,
    TextEmbeddingMaskPolicy,
    TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    resolve_active_text_embedding_span,
    resolve_semantic_text_embedding_span,
)
from tests.sir_convert_a_lot.ml.qwen.preprocessing.test_support import write_test_wav


@dataclass
class _FakeConfig:
    """Minimal config stub for dataset compatibility tests."""

    tts_pad_token_id: int = 0
    tts_bos_token_id: int = 1
    tts_eos_token_id: int = 2
    talker_config: object = None

    def __post_init__(self) -> None:
        """Populate the minimal nested talker-config surface used in collation."""
        if self.talker_config is None:
            self.talker_config = _FakeTalkerConfig()


@dataclass
class _FakeTalkerConfig:
    """Minimal nested talker-config stub for dataset collation tests."""

    codec_nothink_id: int = 3
    codec_think_bos_id: int = 4
    codec_think_eos_id: int = 5
    codec_pad_id: int = 6
    codec_bos_id: int = 7
    codec_eos_token_id: int = 8


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


class _LongTokenProcessor:
    """Processor stub that leaves a meaningful post-trim text span for mask tests."""

    def __call__(
        self,
        *,
        text: str,
        return_tensors: str,
        padding: bool,
    ) -> dict[str, torch.Tensor]:
        del text, return_tensors, padding
        return {"input_ids": torch.tensor([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]], dtype=torch.long)}


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
    assert rows[0]["row_id"] == f"{manifest_path.as_posix()}#L1"
    assert rows[0]["manifest_path"] == manifest_path.as_posix()
    assert rows[0]["manifest_line_number"] == 1
    assert "precomputed_ref_input_path" not in rows[0]


def test_load_training_rows_requires_precomputed_ref_inputs_when_enforced(
    tmp_path: Path,
) -> None:
    """Rebuilt-bundle enforcement should fail closed on legacy rows without persisted refs."""
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

    with pytest.raises(ValueError, match="missing required persisted reference-input metadata"):
        _load_training_rows(
            manifest_path,
            require_precomputed_ref_inputs=True,
        )


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
    assert item["batch_row_provenance"]["row_id"] == "dataset-row-0"
    assert item["batch_row_provenance"]["speaker_id"] == "speaker-a"
    assert item["batch_row_provenance"]["codec_frame_count"] == 1


def test_build_data_path_attribution_collector_rejects_multiworker_proof_mode() -> None:
    """Proof mode should fail closed when worker-side counters would be ambiguous."""
    with pytest.raises(ValueError, match="dataloader_num_workers=0"):
        build_data_path_attribution_collector(
            proof_mode_enabled=True,
            dataloader_num_workers=4,
        )


def test_dataset_records_runtime_ref_mel_extraction_in_proof_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy runtime extraction should be counted during authoritative proof runs."""
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    collector = build_data_path_attribution_collector(
        proof_mode_enabled=True,
        dataloader_num_workers=0,
    )
    assert collector is not None
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
        data_path_attribution=collector,
    )
    monkeypatch.setattr(
        TTSDataset,
        "extract_mels",
        lambda self, audio, sample_rate: torch.ones((1, 4, 8), dtype=torch.float32),
    )

    dataset[0]

    payload = collector.payload()
    assert payload["proof_mode_enabled"] is True
    assert payload["authoritative"] is True
    assert payload["runtime_ref_mel_extraction_count"] == 1
    assert payload["persisted_ref_mel_load_count"] == 0
    assert payload["getitem_call_count"] == 1


def test_dataset_records_persisted_ref_mel_load_in_proof_mode(tmp_path: Path) -> None:
    """Persisted ref-mel loads should be counted separately from runtime extraction."""
    persisted_ref_path = tmp_path / "precomputed" / "speaker-a" / "ref_mel.pt"
    save_persisted_ref_mel(
        persisted_ref_path,
        torch.ones((1, 4, 8), dtype=torch.float32),
    )
    collector = build_data_path_attribution_collector(
        proof_mode_enabled=True,
        dataloader_num_workers=0,
    )
    assert collector is not None
    dataset = TTSDataset(
        data_list=[
            {
                "text": "hej",
                "audio_codes": [[1, 2]],
                "ref_audio": "refs/speaker-a/ref.wav",
                "precomputed_ref_input_path": persisted_ref_path.as_posix(),
                "precomputed_ref_input_kind": PRECOMPUTED_REF_INPUT_KIND,
                "precomputed_ref_input_version": PRECOMPUTED_REF_INPUT_VERSION,
                "precomputed_ref_input_source_audio": "refs/speaker-a/ref.wav",
                "speaker_id": "speaker-a",
            }
        ],
        processor=_FakeProcessor(),
        config=_FakeConfig(),
        data_path_attribution=collector,
    )

    item = dataset[0]

    assert item["ref_mel"].shape == (1, 4, 8)
    payload = collector.payload()
    assert payload["runtime_ref_mel_extraction_count"] == 0
    assert payload["persisted_ref_mel_load_count"] == 1
    assert payload["getitem_call_count"] == 1


def test_collate_ref_mels_pads_variable_length_reference_inputs() -> None:
    """Batch collation should pad variable-length ref-mels for aggressive batches."""
    batch: list[DatasetItem] = [
        {
            "text_ids": torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long),
            "audio_codes": torch.tensor([[1, 2]], dtype=torch.long),
            "ref_mel": torch.full((1, 2, 3), 1.0, dtype=torch.float32),
            "speaker_id": 0,
            "batch_row_provenance": {
                "row_id": "train.jsonl#L1",
                "manifest_path": "train.jsonl",
                "manifest_line_number": 1,
                "dataset_index": 0,
                "speaker_id": "speaker-a",
                "text_preview": "hej",
                "codec_frame_count": 1,
                "ref_audio": "refs/speaker-a/ref.wav",
            },
        },
        {
            "text_ids": torch.tensor([[1, 2, 3, 4, 5, 6]], dtype=torch.long),
            "audio_codes": torch.tensor([[1, 2]], dtype=torch.long),
            "ref_mel": torch.full((1, 4, 3), 2.0, dtype=torch.float32),
            "speaker_id": 1,
            "batch_row_provenance": {
                "row_id": "train.jsonl#L2",
                "manifest_path": "train.jsonl",
                "manifest_line_number": 2,
                "dataset_index": 1,
                "speaker_id": "speaker-b",
                "text_preview": "världen",
                "codec_frame_count": 1,
                "ref_audio": "refs/speaker-b/ref.wav",
            },
        },
    ]

    ref_mels = _collate_ref_mels(batch)

    assert ref_mels.shape == (2, 4, 3)
    assert torch.equal(ref_mels[0, :2], torch.full((2, 3), 1.0, dtype=torch.float32))
    assert torch.equal(ref_mels[0, 2:], torch.zeros((2, 3), dtype=torch.float32))
    assert torch.equal(ref_mels[1], torch.full((4, 3), 2.0, dtype=torch.float32))


def test_collate_fn_preserves_batch_row_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The collated batch should preserve stable row provenance for forensics."""
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    dataset = TTSDataset(
        data_list=[
            {
                "text": "hej världen",
                "audio_codes": [list(range(16))],
                "ref_audio": ref_audio_path.as_posix(),
                "row_id": "train.jsonl#L1",
                "manifest_path": "train.jsonl",
                "manifest_line_number": 1,
                "speaker_id": "speaker-a",
            }
        ],
        processor=_FakeProcessor(),
        config=_FakeConfig(),
    )
    monkeypatch.setattr(
        TTSDataset,
        "extract_mels",
        lambda self, audio, sample_rate: torch.ones((1, 4, 8), dtype=torch.float32),
    )

    collated = dataset.collate_fn([dataset[0]])

    assert collated["batch_provenance"] == [
        {
            "row_id": "train.jsonl#L1",
            "manifest_path": "train.jsonl",
            "manifest_line_number": 1,
            "dataset_index": 0,
            "speaker_id": "speaker-a",
            "text_preview": "hej världen",
            "codec_frame_count": 1,
            "ref_audio": ref_audio_path.as_posix(),
        }
    ]


@pytest.mark.parametrize(
    ("policy", "expected_active_length"),
    [
        (LEGACY_CODEC_SPAN_TEXT_EMBEDDING_MASK_POLICY, 16),
        (TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY, 2),
    ],
)
def test_collate_fn_applies_the_configured_text_embedding_mask_policy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: TextEmbeddingMaskPolicy,
    expected_active_length: int,
) -> None:
    """Collation should respect the explicit text-embedding mask policy."""
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    dataset = TTSDataset(
        data_list=[
            {
                "text": "hej världen igen",
                "audio_codes": [list(range(16)), list(range(16, 32)), list(range(32, 48))],
                "ref_audio": ref_audio_path.as_posix(),
                "speaker_id": "speaker-a",
            }
        ],
        processor=_LongTokenProcessor(),
        config=_FakeConfig(),
        text_embedding_mask_policy=policy,
    )
    monkeypatch.setattr(
        TTSDataset,
        "extract_mels",
        lambda self, audio, sample_rate: torch.ones((1, 4, 8), dtype=torch.float32),
    )

    batch_item = dataset[0]
    collated = dataset.collate_fn([batch_item])

    mask = collated["text_embedding_mask"][0, :, 0]
    resolved_span = resolve_active_text_embedding_span(
        policy=policy,
        text_ids_len=batch_item["text_ids"].shape[1],
        codec_ids_len=batch_item["audio_codes"].shape[0],
    )
    assert int(mask.sum().item()) == expected_active_length
    assert torch.equal(
        mask[resolved_span.start_index : resolved_span.end_index_exclusive],
        torch.ones(expected_active_length, dtype=torch.bool),
    )
    assert torch.equal(
        mask[: resolved_span.start_index],
        torch.zeros(resolved_span.start_index, dtype=torch.bool),
    )
    assert torch.equal(
        mask[resolved_span.end_index_exclusive :],
        torch.zeros(mask.shape[0] - resolved_span.end_index_exclusive, dtype=torch.bool),
    )


def test_collate_fn_text_span_only_masks_only_semantic_text_positions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`text_span_only` should exclude prefix controls, pads, BOS, and EOS."""
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    dataset = TTSDataset(
        data_list=[
            {
                "text": "hej världen igen",
                "audio_codes": [list(range(16)), list(range(16, 32)), list(range(32, 48))],
                "ref_audio": ref_audio_path.as_posix(),
                "speaker_id": "speaker-a",
            }
        ],
        processor=_LongTokenProcessor(),
        config=_FakeConfig(),
        text_embedding_mask_policy=TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    )
    monkeypatch.setattr(
        TTSDataset,
        "extract_mels",
        lambda self, audio, sample_rate: torch.ones((1, 4, 8), dtype=torch.float32),
    )

    collated = dataset.collate_fn([dataset[0]])

    mask = collated["text_embedding_mask"][0, :, 0]
    assert torch.equal(mask[:8], torch.zeros(8, dtype=torch.bool))
    assert torch.equal(mask[8:10], torch.ones(2, dtype=torch.bool))
    assert mask[10].item() is False
    assert torch.equal(collated["semantic_text_ids"][0], torch.tensor([4, 5], dtype=torch.long))
    assert torch.equal(
        collated["semantic_text_positions"][0],
        torch.tensor([8, 9], dtype=torch.long),
    )
    assert torch.equal(
        collated["semantic_text_mask"][0],
        torch.ones(2, dtype=torch.bool),
    )


def test_collate_fn_emits_semantic_text_contract_as_first_class_batch_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Collation should expose semantic ids and positions without inference."""
    ref_audio_path = tmp_path / "refs" / "speaker-a" / "ref.wav"
    ref_audio_path.parent.mkdir(parents=True, exist_ok=True)
    write_test_wav(ref_audio_path, sample_rate_hz=24_000, duration_seconds=1.0)
    dataset = TTSDataset(
        data_list=[
            {
                "text": "hej världen igen",
                "audio_codes": [list(range(16)), list(range(16, 32)), list(range(32, 48))],
                "ref_audio": ref_audio_path.as_posix(),
                "speaker_id": "speaker-a",
            }
        ],
        processor=_LongTokenProcessor(),
        config=_FakeConfig(),
        text_embedding_mask_policy=TEXT_SPAN_ONLY_TEXT_EMBEDDING_MASK_POLICY,
    )
    monkeypatch.setattr(
        TTSDataset,
        "extract_mels",
        lambda self, audio, sample_rate: torch.ones((1, 4, 8), dtype=torch.float32),
    )

    batch_item = dataset[0]
    collated = dataset.collate_fn([batch_item])
    semantic_span = resolve_semantic_text_embedding_span(
        text_ids_len=batch_item["text_ids"].shape[1]
    )

    assert torch.equal(collated["semantic_text_ids"], torch.tensor([[4, 5]], dtype=torch.long))
    assert torch.equal(
        collated["semantic_text_positions"],
        torch.tensor(
            [[semantic_span.start_index, semantic_span.end_index_exclusive - 1]],
            dtype=torch.long,
        ),
    )
    assert torch.equal(collated["semantic_text_mask"], torch.tensor([[True, True]]))
