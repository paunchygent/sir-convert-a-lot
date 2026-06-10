"""Media normalization helpers for the STT sidecar.

Purpose:
    Convert accepted local-upload audio into the normalized WAV contract used by
    the STT runtime and report bounded media duration metadata.

Relationships:
    - Used only inside `stt_sidecar.runtime`.
    - Keeps ffmpeg and ffprobe failure mapping aligned with the audio route's
      deterministic public error language.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from pathlib import Path

from scripts.sir_convert_a_lot.stt_sidecar.contracts import SttSidecarRequestError

NORMALIZATION_PROFILE = "wav_16khz_mono_s16"
NORMALIZED_SAMPLE_RATE_HZ = 16_000
NORMALIZED_CHANNELS = 1


def normalize_audio(*, source_path: Path, target_path: Path) -> None:
    """Normalize one source media file to the sidecar WAV contract."""
    command = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-i",
        source_path.as_posix(),
        "-vn",
        "-ac",
        str(NORMALIZED_CHANNELS),
        "-ar",
        str(NORMALIZED_SAMPLE_RATE_HZ),
        "-sample_fmt",
        "s16",
        target_path.as_posix(),
    ]
    _run_media_command(command=command, error_code="audio_normalization_failed")


def duration_seconds(path: Path) -> float:
    """Return bounded media duration from ffprobe JSON output."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        path.as_posix(),
    ]
    completed = _run_media_command(command=command, error_code="audio_probe_failed")
    parsed = json.loads(completed.stdout)
    if isinstance(parsed, Mapping):
        format_obj = parsed.get("format")
        if isinstance(format_obj, Mapping):
            duration_obj = format_obj.get("duration")
            if isinstance(duration_obj, str):
                return max(0.0, float(duration_obj))
    raise SttSidecarRequestError(
        code="audio_probe_failed",
        message="Audio duration could not be determined.",
        status_code=422,
    )


def _run_media_command(*, command: list[str], error_code: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120.0,
        )
    except subprocess.TimeoutExpired as exc:
        raise SttSidecarRequestError(
            code=error_code,
            message="Audio media operation timed out.",
            status_code=504,
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SttSidecarRequestError(
            code=error_code,
            message="Audio media operation failed.",
            status_code=422,
        ) from exc
