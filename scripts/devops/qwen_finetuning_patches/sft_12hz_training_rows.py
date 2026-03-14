"""Training-manifest helpers for the patched Qwen `sft_12hz.py` trainer.

Purpose:
    Resolve Task 101 training JSONL rows into validated `TrainingRow` payloads
    with absolute manifest-relative paths before the trainer constructs the
    dataset.

Relationships:
    - Imported by `sft_12hz.py`, which owns the training loop orchestration.
    - Shares the `TrainingRow` contract from the patched `dataset.py` module in
      the same directory.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.dataset import TrainingRow
from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_inputs import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
)


def _load_training_rows(train_jsonl_path: Path) -> list[TrainingRow]:
    """Load and validate one Task 101 training JSONL manifest."""
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
    precomputed_ref_input_path = row.get("precomputed_ref_input_path")
    if not isinstance(precomputed_ref_input_path, str):
        raise ValueError(
            "Training row is missing `precomputed_ref_input_path`; rebuild the training bundle "
            "with persisted precomputed reference inputs before launching training."
        )
    precomputed_ref_input_kind = row.get("precomputed_ref_input_kind")
    if precomputed_ref_input_kind != PRECOMPUTED_REF_INPUT_KIND:
        raise ValueError(
            "Training row referenced unsupported `precomputed_ref_input_kind`; "
            f"expected `{PRECOMPUTED_REF_INPUT_KIND}`."
        )
    precomputed_ref_input_version = row.get("precomputed_ref_input_version")
    if precomputed_ref_input_version != PRECOMPUTED_REF_INPUT_VERSION:
        raise ValueError(
            "Training row referenced unsupported `precomputed_ref_input_version`; "
            f"expected `{PRECOMPUTED_REF_INPUT_VERSION}`."
        )
    precomputed_ref_input_source_audio = row.get("precomputed_ref_input_source_audio")
    if not isinstance(precomputed_ref_input_source_audio, str):
        raise ValueError("Training row is missing `precomputed_ref_input_source_audio`.")
    resolved_row: TrainingRow = {
        "text": text_value,
        "audio_codes": audio_codes_value,
        "ref_audio": resolved_ref_audio,
        "precomputed_ref_input_path": _resolve_manifest_path(
            manifest_root,
            precomputed_ref_input_path,
        ),
        "precomputed_ref_input_kind": PRECOMPUTED_REF_INPUT_KIND,
        "precomputed_ref_input_version": PRECOMPUTED_REF_INPUT_VERSION,
        "precomputed_ref_input_source_audio": _resolve_manifest_path(
            manifest_root,
            precomputed_ref_input_source_audio,
        ),
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
