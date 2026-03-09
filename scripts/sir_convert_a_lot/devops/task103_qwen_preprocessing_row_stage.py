"""Row-processing stage for the staged Qwen Swedish preprocessing pipeline.

Purpose:
    Convert source records into deterministic inventory rows, canonical
    24 kHz audio artifacts, ASR-scored spool rows, and other
    durable row-level outputs used by later finalization.

Relationships:
    - Called by the Task 103 core facade during the `all` and `row-processing`
      stages.
    - Consumes ASR policy from `task103_qwen_preprocessing_asr.py`.
    - Persists durable row results through
      `task103_qwen_preprocessing_storage.py`.
"""

from __future__ import annotations

import hashlib
import tarfile
import tempfile
import wave
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from queue import Queue
from typing import Callable, Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_family_assignment import (
    manifest_targets_for_curated_source,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_asr import (
    admission_decision_for_source,
    normalize_text,
    quality_tier_for_wer,
    speaker_quality_gate_for_source,
    word_error_rate,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    CANONICAL_SAMPLE_RATE_HZ,
    InventoryRow,
    SpoolRow,
    Task103PreprocessingSettings,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    write_jsonl,
    write_spool_row,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import AudioLocator, SourceRecord


def _sha256_hex(path: Path) -> str:
    """Hash one file with SHA256."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _wav_metadata(audio_path: Path) -> tuple[int, float]:
    """Read sample rate and duration for one WAV file."""
    with wave.open(audio_path.as_posix(), "rb") as handle:
        sample_rate_hz = handle.getframerate()
        duration_seconds = handle.getnframes() / sample_rate_hz
    return int(sample_rate_hz), round(duration_seconds, 6)


def inventory_row_for_source(source_record: SourceRecord) -> InventoryRow:
    """Build one inventory row from one adapter-shaped source record."""
    if (
        source_record.source_sample_rate_hz is not None
        and source_record.duration_seconds is not None
    ):
        source_sample_rate_hz = source_record.source_sample_rate_hz
        duration_seconds = source_record.duration_seconds
    elif (
        source_record.source_audio_locator is not None
        and source_record.source_audio_locator.archive_member is None
    ):
        source_sample_rate_hz, duration_seconds = _wav_metadata(
            source_record.source_audio_locator.path
        )
    else:
        raise ValueError(
            "Source record must provide sample-rate and duration hints when audio "
            "metadata cannot be derived from a direct WAV path."
        )

    transcript_normalized = normalize_text(source_record.text_raw)
    speaker_total_hours = source_record.speaker_total_hours
    if speaker_total_hours is None:
        speaker_total_hours = round(duration_seconds / 3600.0, 6)

    notes = source_record.notes
    if (
        source_record.source_audio_locator is not None
        and source_record.source_audio_locator.archive_member is None
    ):
        notes_prefix = f"sha256:{_sha256_hex(source_record.source_audio_locator.path)[:16]}"
        notes = notes_prefix if notes is None else f"{notes_prefix};{notes}"

    return InventoryRow(
        dataset=source_record.dataset,
        source_split=source_record.source_split,
        dataset_row_id=source_record.dataset_row_id,
        source_audio_path=source_record.source_audio_path,
        source_sample_rate_hz=source_sample_rate_hz,
        duration_seconds=round(duration_seconds, 6),
        text_raw=source_record.text_raw,
        text_normalized=transcript_normalized,
        speaker_id=source_record.speaker_id,
        speaker_name=source_record.speaker_name,
        speaker_from_id=source_record.speaker_from_id,
        speaker_total_hours=round(float(speaker_total_hours), 6),
        language=source_record.language,
        has_label_files=source_record.has_label_files,
        speaker_audio_meta_ok=source_record.speaker_audio_meta_ok,
        boilerplate_group=source_record.boilerplate_group,
        notes=notes,
    )


def write_inventory_rows(
    output_root: Path,
    source_records: Sequence[SourceRecord],
) -> list[InventoryRow]:
    """Build and persist deterministic inventory rows grouped by dataset split."""
    inventory_rows = [inventory_row_for_source(source_row) for source_row in source_records]
    inventory_rows_by_dataset_split: dict[str, list[InventoryRow]] = defaultdict(list)
    for inventory_row in inventory_rows:
        dataset_split_key = f"{inventory_row.dataset}-{inventory_row.source_split}"
        inventory_rows_by_dataset_split[dataset_split_key].append(inventory_row)
    inventory_dir = output_root / "inventory"
    for dataset_split_key, rows in inventory_rows_by_dataset_split.items():
        write_jsonl(inventory_dir / f"{dataset_split_key}.jsonl", [asdict(row) for row in rows])
    return inventory_rows


def _resample_and_write_audio(source_path: Path, target_path: Path) -> float:
    """Standardize one waveform to the fixed 24 kHz training-side contract."""
    import librosa
    import numpy as np
    import soundfile

    waveform, sample_rate_hz = soundfile.read(source_path.as_posix(), dtype="float32")
    if getattr(waveform, "ndim", 1) > 1:
        waveform = waveform.mean(axis=1)
    if sample_rate_hz != CANONICAL_SAMPLE_RATE_HZ:
        waveform = librosa.resample(
            np.asarray(waveform, dtype=np.float32),
            orig_sr=sample_rate_hz,
            target_sr=CANONICAL_SAMPLE_RATE_HZ,
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    soundfile.write(target_path.as_posix(), waveform, CANONICAL_SAMPLE_RATE_HZ)
    _, duration_seconds = _wav_metadata(target_path)
    return duration_seconds


def _materialize_audio_locator(audio_locator: AudioLocator, target_path: Path) -> float:
    """Materialize one source audio locator to the canonical 24 kHz target path."""
    if audio_locator.archive_member is None:
        return _resample_and_write_audio(audio_locator.path, target_path)

    with tarfile.open(audio_locator.path, "r:*") as archive:
        extracted = archive.extractfile(audio_locator.archive_member)
        if extracted is None:
            raise FileNotFoundError(
                f"Missing archive member {audio_locator.archive_member} in {audio_locator.path}"
            )
        suffix = Path(audio_locator.archive_member).suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix) as handle:
            handle.write(extracted.read())
            handle.flush()
            return _resample_and_write_audio(Path(handle.name), target_path)


def process_rows_to_spool(
    settings: Task103PreprocessingSettings,
    *,
    output_root: Path,
    source_records: Sequence[SourceRecord],
    scorer_factory: Callable[[str, str], object],
) -> None:
    """Process source rows into durable audio artifacts and spool records."""
    if settings.row_worker_count <= 0:
        raise ValueError("`row_worker_count` must be positive.")
    if settings.gpu_asr_worker_count <= 0:
        raise ValueError("`gpu_asr_worker_count` must be positive.")
    inventory_rows = write_inventory_rows(output_root, source_records)
    inventory_rows_by_key = {
        (row.dataset, row.source_split, row.dataset_row_id): row for row in inventory_rows
    }
    source_rows_with_audio = [
        source_row for source_row in source_records if source_row.source_audio_locator is not None
    ]
    scorer_slots: list[object | None] = []
    if source_rows_with_audio:
        scorer_slots = [
            scorer_factory(settings.asr_model, settings.asr_revision)
            for _ in range(settings.gpu_asr_worker_count)
        ]
    scorer_slot_queue: Queue[int] = Queue()
    for slot_index in range(settings.gpu_asr_worker_count):
        scorer_slot_queue.put(slot_index)

    audio_24k_dir = output_root / "audio_24k"

    def _process_source_row(source_row: SourceRecord) -> None:
        if source_row.source_audio_locator is None:
            return

        inventory_row = inventory_rows_by_key[
            (source_row.dataset, source_row.source_split, source_row.dataset_row_id)
        ]
        utterance_slug = source_row.dataset_row_id.replace("_", "-")
        audio_24k_path = (
            audio_24k_dir
            / source_row.dataset
            / source_row.source_split
            / source_row.speaker_id
            / f"{utterance_slug}.wav"
        )

        duration_seconds = _materialize_audio_locator(
            source_row.source_audio_locator,
            audio_24k_path,
        )
        scorer_slot_index = scorer_slot_queue.get()
        try:
            scorer = scorer_slots[scorer_slot_index]
            if scorer is None:
                raise RuntimeError(
                    "ASR scorer slot was not initialized before row processing started."
                )
            transcribe = getattr(scorer, "transcribe")
            asr_transcript = transcribe(audio_24k_path)
        finally:
            scorer_slot_queue.put(scorer_slot_index)
        asr_wer = word_error_rate(inventory_row.text_normalized, asr_transcript)
        quality_tier = quality_tier_for_wer(asr_wer)
        speaker_quality_gate = speaker_quality_gate_for_source(source_row)
        admission_decision = admission_decision_for_source(quality_tier, speaker_quality_gate)
        manifest_targets = manifest_targets_for_curated_source(
            source_row,
            quality_tier=quality_tier,
            speaker_quality_gate=speaker_quality_gate,
        )

        spool_row = SpoolRow(
            dataset=source_row.dataset,
            source_split=source_row.source_split,
            dataset_row_id=source_row.dataset_row_id,
            speaker_id=source_row.speaker_id,
            speaker_name=source_row.speaker_name,
            speaker_from_id=source_row.speaker_from_id,
            source_audio_path=source_row.source_audio_path,
            audio_24k_path=audio_24k_path.relative_to(output_root).as_posix(),
            duration_seconds=duration_seconds,
            text_normalized=inventory_row.text_normalized,
            reference_audio_24k_paths={},
            asr_model=settings.asr_model,
            asr_revision=settings.asr_revision,
            asr_transcript=asr_transcript,
            asr_wer=asr_wer,
            quality_tier=quality_tier,
            speaker_quality_gate=speaker_quality_gate,
            dedup_applied=False,
            admission_decision=admission_decision,
            manifest_targets=manifest_targets,
        )
        write_spool_row(output_root, spool_row)

    with ThreadPoolExecutor(max_workers=settings.row_worker_count) as executor:
        list(executor.map(_process_source_row, source_records))
