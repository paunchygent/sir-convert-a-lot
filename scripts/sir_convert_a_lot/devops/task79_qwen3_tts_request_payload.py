"""Request payload and input-evidence helpers for the Task 79 Qwen benchmark.

Purpose:
    Keep Qwen3-TTS request construction plus deterministic input preparation
    separate from the large Hemma runtime orchestrator so the benchmark stays
    readable while supporting both CustomVoice and Base clone lanes.

Relationships:
    - Used by `run_task79_hemma_tts_sidecar_benchmark`.
    - Used by `task79_hemma_tts_sidecar_runtime`.
    - Used by `task79_hemma_tts_sidecar_reporting` through the prepared input
      evidence dataclass defined here.
"""

from __future__ import annotations

import base64
import hashlib
import mimetypes
import shutil
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PreparedRequestInputs:
    """Deterministic on-disk copies plus metadata for one benchmark request."""

    probe_text_path: str
    instructions_path: str | None
    reference_audio_path: str | None
    reference_audio_sha256: str | None
    reference_audio_duration_seconds: float | None
    reference_transcript_path: str | None


def resolve_text_input(
    *,
    direct_value: str | None,
    file_path: Path | None,
    label: str,
) -> str | None:
    """Resolve one optional text input from either direct text or one file."""
    if direct_value is not None and file_path is not None:
        raise SystemExit(f"Provide either `{label}` or `{label} file`, not both.")
    if file_path is not None:
        return file_path.read_text(encoding="utf-8").strip()
    if direct_value is None:
        return None
    return direct_value.strip()


def prepare_request_inputs(
    *,
    inputs_dir: Path,
    probe_text: str,
    instructions: str | None,
    reference_audio: Path | None,
    reference_transcript: str | None,
) -> PreparedRequestInputs:
    """Copy benchmark inputs into the deterministic evidence directory."""
    source_reference_audio_bytes: bytes | None = None
    source_reference_audio_suffix = ""
    if reference_audio is not None:
        source_reference_audio_bytes = reference_audio.read_bytes()
        source_reference_audio_suffix = reference_audio.suffix.lower()

    inputs_dir.mkdir(parents=True, exist_ok=True)
    for existing in sorted(inputs_dir.iterdir()):
        if existing.is_dir():
            shutil.rmtree(existing)
            continue
        existing.unlink()

    probe_text_path = inputs_dir / "probe_text.txt"
    probe_text_path.write_text(probe_text + "\n", encoding="utf-8")

    instructions_path: Path | None = None
    if instructions is not None:
        instructions_path = inputs_dir / "instructions.txt"
        instructions_path.write_text(instructions + "\n", encoding="utf-8")

    reference_audio_path: Path | None = None
    reference_audio_sha256: str | None = None
    reference_audio_duration_seconds: float | None = None
    if source_reference_audio_bytes is not None:
        reference_audio_path = inputs_dir / f"reference_audio{source_reference_audio_suffix}"
        reference_audio_path.write_bytes(source_reference_audio_bytes)
        reference_audio_bytes = reference_audio_path.read_bytes()
        reference_audio_sha256 = hashlib.sha256(reference_audio_bytes).hexdigest()
        reference_audio_duration_seconds = _read_wav_duration_seconds(reference_audio_path)

    reference_transcript_path: Path | None = None
    if reference_transcript is not None:
        reference_transcript_path = inputs_dir / "reference_transcript.txt"
        reference_transcript_path.write_text(reference_transcript + "\n", encoding="utf-8")

    return PreparedRequestInputs(
        probe_text_path=probe_text_path.as_posix(),
        instructions_path=instructions_path.as_posix() if instructions_path is not None else None,
        reference_audio_path=(
            reference_audio_path.as_posix() if reference_audio_path is not None else None
        ),
        reference_audio_sha256=reference_audio_sha256,
        reference_audio_duration_seconds=reference_audio_duration_seconds,
        reference_transcript_path=(
            reference_transcript_path.as_posix() if reference_transcript_path is not None else None
        ),
    )


def build_speech_payload(
    *,
    model: str,
    probe_text: str,
    response_format: str,
    task_type: str,
    language: str,
    voice: str | None,
    instructions: str | None,
    reference_audio: Path | None,
    reference_transcript: str | None,
) -> dict[str, str]:
    """Build one official OpenAI-compatible Qwen3-TTS request payload."""
    payload: dict[str, str] = {
        "model": model,
        "input": probe_text,
        "response_format": response_format,
        "task_type": task_type,
        "language": language,
    }
    if instructions is not None:
        payload["instructions"] = instructions
    if task_type == "CustomVoice":
        if voice is None or voice.strip() == "":
            raise SystemExit("Task 79 CustomVoice requests require a configured voice.")
        payload["voice"] = voice
        return payload
    if task_type == "Base":
        if reference_audio is None:
            raise SystemExit("Task 79 Base requests require `--reference-audio`.")
        if reference_transcript is None or reference_transcript.strip() == "":
            raise SystemExit(
                "Task 79 Base requests require `--reference-transcript` or "
                "`--reference-transcript-file`."
            )
        payload["ref_audio"] = encode_audio_to_data_url(reference_audio)
        payload["ref_text"] = reference_transcript
        return payload
    raise SystemExit(f"Unsupported Task 79 task type: {task_type}")


def encode_audio_to_data_url(audio_path: Path) -> str:
    """Encode one local audio file as a data URL accepted by vLLM/Qwen."""
    audio_bytes = audio_path.read_bytes()
    mime_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(audio_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _read_wav_duration_seconds(audio_path: Path) -> float | None:
    """Return one rounded WAV duration when the copied reference is a WAV file."""
    if audio_path.suffix.lower() != ".wav":
        return None
    with wave.open(audio_path.as_posix(), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
    return round(frame_count / float(frame_rate), 6)
