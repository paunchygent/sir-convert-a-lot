"""Tests for Story 30 backward-lineage mini-bundle materialization.

Purpose:
    Prove the T212 mini-bundle copier preserves the exact selected prepared
    rows and bundle-local assets for the bounded backward-lineage probe.

Relationships:
    - Exercises `story30_backward_lineage_bundle.py`.
    - Keeps the backward-lineage proof surface grounded in a real bundle subset.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_input_contract import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_bundle import (
    materialize_backward_lineage_bundle,
)


def test_materialize_backward_lineage_bundle_copies_selected_rows_and_assets(
    tmp_path: Path,
) -> None:
    """The backward-lineage mini-bundle should preserve the exact selected source rows."""
    train_source_bundle = tmp_path / "train-source-bundle"
    _write_manifest(
        train_source_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl",
        [_row_payload(index) for index in range(1, 6)],
    )
    target_bundle = tmp_path / "target-bundle"

    payload = materialize_backward_lineage_bundle(
        source_bundle_root=train_source_bundle,
        target_bundle_root=target_bundle,
        manifest_family="swedish_pilot_train",
        selected_source_lines=(4, 2),
    )

    assert payload.source_bundle_root == train_source_bundle.as_posix()
    assert payload.selected_source_lines == (4, 2)
    assert payload.selected_rows[0].speaker_id == "speaker-4"
    manifest_lines = (
        (target_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    )
    assert len(manifest_lines) == 2
    first_row = json.loads(manifest_lines[0])
    second_row = json.loads(manifest_lines[1])
    assert first_row["story30_source_manifest_line_number"] == 4
    assert second_row["story30_source_manifest_line_number"] == 2
    assert (target_bundle / first_row["audio"]).exists() is True
    assert (target_bundle / first_row["ref_audio"]).exists() is True
    assert (target_bundle / first_row["precomputed_ref_input_path"]).exists() is True


def test_materialize_backward_lineage_bundle_resolves_dated_source_bundle_root(
    tmp_path: Path,
) -> None:
    """The backward-lineage mini-bundle should resolve the canonical dated bundle root."""
    placeholder_train_bundle = tmp_path / "qwen3-tts-swedish-task101-pilot-bundle"
    dated_train_bundle = tmp_path / "qwen3-tts-swedish-task101-pilot-bundle-20260314T111615Z-refmel"
    _write_manifest(
        dated_train_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl",
        [_row_payload(index) for index in range(1, 3)],
    )
    target_bundle = tmp_path / "target-bundle"

    payload = materialize_backward_lineage_bundle(
        source_bundle_root=placeholder_train_bundle,
        target_bundle_root=target_bundle,
        manifest_family="swedish_pilot_train",
        selected_source_lines=(2, 1),
    )

    assert payload.source_bundle_root == dated_train_bundle.as_posix()
    assert (target_bundle / "manifests" / "swedish_pilot_train.prepared.jsonl").exists() is True


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
