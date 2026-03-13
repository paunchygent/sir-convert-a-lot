"""Waxholm Swedish source adapter for the Qwen corpus pipeline.

Purpose:
    Ingest labeled `KTH/waxholm` rows from raw repository files and `.smp.mix`
    transcript labels.

Relationships:
    - Consumed by the preprocessing pipeline for high-trust control corpus
      enumeration.
    - Uses `huggingface_hub` for snapshot acquisition and emits `SourceRecord`
      rows from `ml.qwen.common.models`.
"""

from __future__ import annotations

import re
import wave
from collections import defaultdict
from pathlib import Path
from typing import Final

from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.ml.qwen.common.models import AudioLocator, SourceRecord

WAXHOLM_DATASET_ID: Final[str] = "KTH/waxholm"
WAXHOLM_LANGUAGE: Final[str] = "sv-SE"
WAXHOLM_TEXT_REPLACEMENTS: Final[dict[str, str]] = {
    "{": "ä",
    "}": "å",
    "|": "ö",
}


def download_waxholm_file(
    *,
    filename: str,
    revision: str | None = None,
    cache_dir: Path | None = None,
) -> Path:
    """Download one revision-pinned Waxholm file via targeted acquisition."""
    downloaded_path = hf_hub_download(
        repo_id=WAXHOLM_DATASET_ID,
        repo_type="dataset",
        revision=revision,
        filename=filename,
        cache_dir=None if cache_dir is None else cache_dir.as_posix(),
    )
    return Path(downloaded_path)


def waxholm_labeled_source_records(snapshot_root: Path) -> list[SourceRecord]:
    """Parse labeled Waxholm rows from one local snapshot root."""
    listing_path = snapshot_root / "alloktrainfiles"
    if not listing_path.is_file():
        raise FileNotFoundError(f"Missing Waxholm listing file: {listing_path}")

    entries = [
        line.strip()
        for line in listing_path.read_text(encoding="utf-8").splitlines()
        if line.strip() != ""
    ]

    raw_rows: list[tuple[Path, str, str]] = []
    speaker_total_seconds: dict[str, float] = defaultdict(float)
    for entry in entries:
        base_stem = entry.removesuffix(".smp")
        speaker_name = base_stem.split(".", 1)[0]
        directory = snapshot_root / "scenes_formatted" / speaker_name
        wav_path = directory / f"{base_stem}.wav"
        mix_path = directory / f"{base_stem}.smp.mix"
        if not wav_path.is_file() or not mix_path.is_file():
            continue
        sample_rate_hz, duration_seconds = _wav_metadata(wav_path)
        speaker_total_seconds[speaker_name] += duration_seconds
        raw_rows.append((wav_path, speaker_name, _parse_waxholm_text(mix_path)))

    source_records: list[SourceRecord] = []
    for wav_path, speaker_name, text_raw in raw_rows:
        sample_rate_hz, duration_seconds = _wav_metadata(wav_path)
        speaker_total_hours = round(speaker_total_seconds[speaker_name] / 3600.0, 6)
        base_stem = wav_path.stem
        source_records.append(
            SourceRecord(
                dataset="waxholm",
                source_split="control",
                dataset_row_id=base_stem,
                speaker_id=f"waxholm_{speaker_name}",
                speaker_name=speaker_name,
                speaker_from_id=True,
                source_audio_path=wav_path.as_posix(),
                source_audio_locator=AudioLocator(wav_path),
                text_raw=text_raw,
                language=WAXHOLM_LANGUAGE,
                speaker_total_hours=speaker_total_hours,
                has_label_files=True,
                speaker_audio_meta_ok=True,
                source_sample_rate_hz=sample_rate_hz,
                duration_seconds=duration_seconds,
            )
        )
    return source_records


def _parse_waxholm_text(mix_path: Path) -> str:
    """Parse and normalize the orthographic `TEXT:` content from one `.smp.mix` file."""
    lines = mix_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines):
        if line == "TEXT:" and index + 1 < len(lines):
            text_line = lines[index + 1]
            text_line = re.sub(r"X[^X]+X", " ", text_line)
            for source_char, target_char in WAXHOLM_TEXT_REPLACEMENTS.items():
                text_line = text_line.replace(source_char, target_char)
            return re.sub(r"\s+", " ", text_line).strip()
    raise ValueError(f"Could not find Waxholm TEXT block in {mix_path}")


def _wav_metadata(audio_path: Path) -> tuple[int, float]:
    """Read the sample rate and duration from one Waxholm WAV file."""
    with wave.open(audio_path.as_posix(), "rb") as handle:
        sample_rate_hz = handle.getframerate()
        duration_seconds = handle.getnframes() / sample_rate_hz
    return int(sample_rate_hz), round(duration_seconds, 6)
