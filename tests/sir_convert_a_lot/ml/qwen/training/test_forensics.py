"""Unit tests for Qwen training forensic payload helpers.

Purpose:
    Keep row-provenance and tensor-finiteness payload coverage focused so
    train-loop integration tests can stay centered on end-to-end failures.

Relationships:
    - Exercises `sft_12hz_forensics.py`.
    - Complements end-to-end failure-path assertions in `test_train_loop.py`
      and `test_reporting.py`.
"""

from __future__ import annotations

import math

import torch

from scripts.devops.qwen_finetuning_patches.sft_12hz_forensics import (
    build_microbatch_forensics,
    build_optimizer_step_forensics_window,
)


def test_build_microbatch_forensics_captures_batch_provenance_and_first_non_finite_tensor() -> None:
    """Microbatch forensics should preserve row identity and ordered tensor probes."""
    payload = build_microbatch_forensics(
        train_iteration=544,
        microbatch_index_in_optimizer_step=2,
        batch_provenance=[
            {
                "row_id": "train.jsonl#L12",
                "manifest_path": "train.jsonl",
                "manifest_line_number": 12,
                "dataset_index": 11,
                "speaker_id": "speaker-a",
                "text_preview": "hej världen",
                "codec_frame_count": 320,
                "ref_audio": "refs/speaker-a/ref.wav",
            }
        ],
        probes=[
            ("speaker_embedding", torch.ones((1, 4), dtype=torch.float32)),
            ("input_embeddings", torch.tensor([1.0, float("nan")], dtype=torch.float32)),
            ("combined_loss", torch.tensor(float("nan"), dtype=torch.float32)),
        ],
    )
    batch_provenance = payload["batch_provenance"]
    assert isinstance(batch_provenance, list)
    assert isinstance(batch_provenance[0], dict)
    tensor_finiteness = payload["tensor_finiteness"]
    assert isinstance(tensor_finiteness, dict)
    tensor_summaries = tensor_finiteness["tensors"]
    assert isinstance(tensor_summaries, dict)
    speaker_embedding_summary = tensor_summaries["speaker_embedding"]
    input_embeddings_summary = tensor_summaries["input_embeddings"]
    assert isinstance(speaker_embedding_summary, dict)
    assert isinstance(input_embeddings_summary, dict)

    assert payload["train_iteration"] == 544
    assert payload["microbatch_index_in_optimizer_step"] == 2
    assert batch_provenance[0]["row_id"] == "train.jsonl#L12"
    assert payload["first_non_finite_tensor"] == "input_embeddings"
    assert tensor_finiteness["probe_order"] == [
        "speaker_embedding",
        "input_embeddings",
        "combined_loss",
    ]
    assert speaker_embedding_summary["is_finite"] is True
    assert input_embeddings_summary["nan_count"] == 1


def test_build_optimizer_step_forensics_window_surfaces_first_bad_microbatch() -> None:
    """Optimizer-step windows should identify the first bad microbatch in order."""
    first_microbatch = build_microbatch_forensics(
        train_iteration=615,
        microbatch_index_in_optimizer_step=3,
        batch_provenance=[],
        probes=[("input_embeddings", torch.ones((1, 2), dtype=torch.float32))],
    )
    second_microbatch = build_microbatch_forensics(
        train_iteration=616,
        microbatch_index_in_optimizer_step=4,
        batch_provenance=[],
        probes=[("talker_hidden_states", torch.tensor([float("inf")], dtype=torch.float32))],
    )

    payload = build_optimizer_step_forensics_window(
        microbatches=[first_microbatch, second_microbatch]
    )
    microbatches = payload["microbatches"]
    assert isinstance(microbatches, list)
    assert isinstance(microbatches[1], dict)
    second_tensor_finiteness = microbatches[1]["tensor_finiteness"]
    assert isinstance(second_tensor_finiteness, dict)
    second_tensor_summaries = second_tensor_finiteness["tensors"]
    assert isinstance(second_tensor_summaries, dict)
    hidden_state_summary = second_tensor_summaries["talker_hidden_states"]
    assert isinstance(hidden_state_summary, dict)

    assert payload["microbatch_count"] == 2
    assert payload["first_non_finite_tensor"] == "talker_hidden_states"
    assert payload["first_non_finite_train_iteration"] == 616
    assert hidden_state_summary["inf_count"] == 1
    max_abs = hidden_state_summary["max_abs"]
    assert isinstance(max_abs, float)
    assert math.isinf(max_abs)
