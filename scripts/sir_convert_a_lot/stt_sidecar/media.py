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
PROBE_TIMEOUT_SECONDS = 30.0
MIN_NORMALIZATION_TIMEOUT_SECONDS = 300.0
MAX_NORMALIZATION_TIMEOUT_SECONDS = 1_800.0


def normalize_audio(
    *,
    source_path: Path,
    target_path: Path,
    media_duration_seconds: float,
) -> None:
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
    _run_media_command(
        command=command,
        operation_timeout_seconds=normalization_timeout_seconds(media_duration_seconds),
        error_code="audio_normalization_failed",
        timeout_code="audio_normalization_timeout",
    )


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
    completed = _run_media_command(
        command=command,
        operation_timeout_seconds=PROBE_TIMEOUT_SECONDS,
        error_code="audio_probe_failed",
        timeout_code="audio_probe_timeout",
    )
    try:
        parsed = json.loads(completed.stdout)
    except (ValueError, TypeError) as exc:
        raise SttSidecarRequestError(
            code="audio_probe_failed",
            message="Audio duration could not be determined.",
            status_code=422,
        ) from exc
    if isinstance(parsed, Mapping):
        format_obj = parsed.get("format")
        if isinstance(format_obj, Mapping):
            duration_obj = format_obj.get("duration")
            if isinstance(duration_obj, str):
                try:
                    return max(0.0, float(duration_obj))
                except ValueError as exc:
                    raise SttSidecarRequestError(
                        code="audio_probe_failed",
                        message="Audio duration could not be determined.",
                        status_code=422,
                    ) from exc
    raise SttSidecarRequestError(
        code="audio_probe_failed",
        message="Audio duration could not be determined.",
        status_code=422,
    )


def normalization_timeout_seconds(media_duration_seconds: float) -> float:
    """Return the governed normalization timeout for a probed media duration."""
    duration = max(0.0, media_duration_seconds)
    return min(
        MAX_NORMALIZATION_TIMEOUT_SECONDS,
        max(MIN_NORMALIZATION_TIMEOUT_SECONDS, (2.0 * duration) + 120.0),
    )


def _run_media_command(
    *,
    command: list[str],
    operation_timeout_seconds: float,
    error_code: str,
    timeout_code: str,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=operation_timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SttSidecarRequestError(
            code=timeout_code,
            message="Audio media operation timed out.",
            status_code=504,
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise SttSidecarRequestError(
            code=error_code,
            message="Audio media operation failed.",
            status_code=422,
        ) from exc
