"""Tests for Story 30 fresh-start mini-bundle materialization.

Purpose:
    Prove the discriminant mini-bundle copier preserves truthful prepared rows
    and the required bundle-local asset contract for the short fresh-start
    Candidate 1 probe.

Relationships:
    - Exercises `story30_freshstart_bundle.py`.
    - Keeps the fresh-start proof surface grounded in a real bundle subset.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_input_contract import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_bundle import (
    materialize_mini_bundle,
)


def test_materialize_mini_bundle_copies_selected_rows_and_assets(tmp_path: Path) -> None:
    """The mini-bundle copier should preserve selected rows and bundle-local assets."""
    source_bundle = tmp_path / "source-bundle"
    _write_manifest(
        source_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl",
        [_row_payload(index) for index in range(1, 5)],
    )
    _write_manifest(
        source_bundle / "manifests" / "swedish_checkpoint_dev.prepared.jsonl",
        [_row_payload(101), _row_payload(102)],
    )
    target_bundle = tmp_path / "target-bundle"

    payload = materialize_mini_bundle(
        source_bundle_root=source_bundle,
        target_bundle_root=target_bundle,
        train_manifest_family="swedish_pilot_train",
        eval_manifest_family="swedish_checkpoint_dev",
        train_line_start=2,
        train_line_end=3,
        eval_line_start=1,
        eval_line_end=1,
    )

    assert payload.train_row_count == 2
    assert payload.eval_row_count == 1
    train_lines = (
        (target_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    eval_lines = (
        (target_bundle / "manifests" / "swedish_checkpoint_dev.prepared.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert len(train_lines) == 2
    assert len(eval_lines) == 1
    copied_row = json.loads(train_lines[0])
    assert copied_row["speaker_id"] == "speaker-2"
    assert (target_bundle / copied_row["audio"]).exists() is True
    assert (target_bundle / copied_row["ref_audio"]).exists() is True
    assert (target_bundle / copied_row["precomputed_ref_input_path"]).exists() is True


def _row_payload(index: int) -> dict[str, object]:
    relative_audio = Path("audio") / f"row-{index}.wav"
    relative_ref = Path("refs") / f"row-{index}.wav"
    relative_ref_input = Path("ref_mels") / f"row-{index}.pt"
    return {
        "audio": relative_audio.as_posix(),
        "ref_audio": relative_ref.as_posix(),
        "precomputed_ref_input_path": relative_ref_input.as_posix(),
        "precomputed_ref_input_kind": PRECOMPUTED_REF_INPUT_KIND,
        "precomputed_ref_input_version": PRECOMPUTED_REF_INPUT_VERSION,
        "precomputed_ref_input_source_audio": relative_ref.as_posix(),
        "speaker_id": f"speaker-{index}",
        "text": f"row {index}",
        "audio_codes": [1, 2, 3],
    }


def _write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for row in rows:
        audio_path = path.parent.parent / str(row["audio"])
        ref_path = path.parent.parent / str(row["ref_audio"])
        ref_input_path = path.parent.parent / str(row["precomputed_ref_input_path"])
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_input_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"audio")
        ref_path.write_bytes(b"ref")
        ref_input_path.write_bytes(b"ref-mel")
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
