"""Audio transcription sidecar runtime probe output behavior.

Purpose:
    Prove that the STT sidecar runtime probe keeps third-party backend output
    away from the JSON stdout stream consumed by live observation ingestion.

Relationships:
    - Exercises the benchmark-sidecar runtime probe CLI boundary.
    - Protects the live observation producer from backend libraries that write
      warnings or access guidance before the final sanitized payload.
"""

from __future__ import annotations

import argparse
import importlib
import json
from types import ModuleType

import pytest


def test_runtime_probe_stdout_contains_only_final_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    probe = _runtime_probe_module()

    def noisy_probe_payload(
        *,
        args: argparse.Namespace,
        environment: dict[str, str],
    ) -> dict[str, object]:
        del args, environment
        print("backend access guidance")
        return {
            "schema_version": "audio_transcription_sidecar_runtime_probe_v1",
            "packages": {
                "faster_whisper": True,
                "pyannote_audio": True,
                "huggingface_hub": True,
                "torch": True,
            },
        }

    monkeypatch.setattr(probe, "_probe_payload", noisy_probe_payload)

    exit_code = probe.main(
        [
            "--english-fixture",
            "english-dialogue-two-speakers.mp3",
            "--swedish-fixture",
            "swedish-monologue-one-speaker.m4a",
        ],
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["schema_version"] == "audio_transcription_sidecar_runtime_probe_v1"
    assert "backend access guidance" not in captured.out
    assert "backend access guidance" in captured.err


def _runtime_probe_module() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_runtime_probe"
    )
