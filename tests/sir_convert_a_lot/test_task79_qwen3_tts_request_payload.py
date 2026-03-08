"""Tests for Task 79 Qwen request payload and input-evidence helpers.

Purpose:
    Protect the Base-clone request shape and deterministic input-evidence
    preparation added for the Qwen Hemma benchmark.

Relationships:
    - Exercises `task79_qwen3_tts_request_payload`.
    - Complements the higher-level Task 79 benchmark tests.
"""

from __future__ import annotations

import base64
import wave
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task79_qwen3_tts_request_payload import (
    build_speech_payload,
    encode_audio_to_data_url,
    prepare_request_inputs,
    resolve_text_input,
)


def _write_wav(path: Path, *, sample_rate_hz: int = 24000, duration_seconds: float = 1.0) -> None:
    """Write one tiny mono WAV file for deterministic fixture use."""
    frame_count = int(sample_rate_hz * duration_seconds)
    with wave.open(path.as_posix(), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate_hz)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def test_resolve_text_input_rejects_direct_and_file(tmp_path: Path) -> None:
    transcript_path = tmp_path / "transcript.txt"
    transcript_path.write_text("hello\n", encoding="utf-8")

    with pytest.raises(
        SystemExit,
        match=("Provide either `reference transcript` or `reference transcript file`"),
    ):
        resolve_text_input(
            direct_value="hi",
            file_path=transcript_path,
            label="reference transcript",
        )


def test_encode_audio_to_data_url_uses_wav_mime_type(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.wav"
    _write_wav(reference_path, duration_seconds=0.25)

    data_url = encode_audio_to_data_url(reference_path)

    assert data_url.startswith("data:audio/x-wav;base64,") or data_url.startswith(
        "data:audio/wav;base64,"
    )
    encoded_payload = data_url.split(",", 1)[1]
    assert base64.b64decode(encoded_payload)


def test_build_speech_payload_for_base_lane_includes_clone_fields(tmp_path: Path) -> None:
    reference_path = tmp_path / "reference.wav"
    _write_wav(reference_path, duration_seconds=0.5)

    payload = build_speech_payload(
        model="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
        probe_text="hello there",
        response_format="wav",
        task_type="Base",
        language="English",
        voice=None,
        instructions="Brag in a lively way.",
        reference_audio=reference_path,
        reference_transcript="Reference transcript",
    )

    assert payload["task_type"] == "Base"
    assert payload["language"] == "English"
    assert payload["instructions"] == "Brag in a lively way."
    assert payload["ref_text"] == "Reference transcript"
    assert payload["ref_audio"].startswith("data:")
    assert "voice" not in payload


def test_prepare_request_inputs_copies_files_and_measures_reference_duration(
    tmp_path: Path,
) -> None:
    inputs_dir = tmp_path / "inputs"
    reference_path = tmp_path / "reference.wav"
    _write_wav(reference_path, duration_seconds=0.5)

    prepared = prepare_request_inputs(
        inputs_dir=inputs_dir,
        probe_text="probe",
        instructions="instructions",
        reference_audio=reference_path,
        reference_transcript="transcript",
    )

    assert (inputs_dir / "probe_text.txt").read_text(encoding="utf-8").strip() == "probe"
    assert (inputs_dir / "instructions.txt").read_text(encoding="utf-8").strip() == "instructions"
    assert (inputs_dir / "reference_transcript.txt").read_text(
        encoding="utf-8"
    ).strip() == "transcript"
    assert prepared.reference_audio_path is not None
    assert prepared.reference_audio_sha256 is not None
    assert prepared.reference_audio_duration_seconds == 0.5


def test_prepare_request_inputs_preserves_reference_when_source_is_inside_inputs_dir(
    tmp_path: Path,
) -> None:
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    reference_path = inputs_dir / "reference_audio.wav"
    _write_wav(reference_path, duration_seconds=0.25)

    prepared = prepare_request_inputs(
        inputs_dir=inputs_dir,
        probe_text="probe",
        instructions=None,
        reference_audio=reference_path,
        reference_transcript="transcript",
    )

    assert Path(prepared.reference_audio_path or "").exists()
    assert prepared.reference_audio_duration_seconds == 0.25
