"""Audio transcription sidecar runtime probe output behavior.

Purpose:
    Keep third-party backend output away from the JSON stdout stream consumed by
    live observation ingestion.

Relationships:
    - Exercises the benchmark-sidecar runtime probe CLI boundary.
    - Protects the live observation producer from backend libraries that write
      warnings or access guidance before the final sanitized payload.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from importlib.machinery import ModuleSpec
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


def test_runtime_probe_classifies_backend_exceptions_without_raw_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    probe = _runtime_probe_module()
    raw_model_id = "pyannote/speaker-diarization-community-1"
    raw_token_value = "hf_private_token_value"
    private_fixture_root = "/private/operator/fixtures"
    raw_transcript_text = "raw transcript text must not persist"
    _install_blocking_backend_modules(
        monkeypatch,
        raw_model_id=raw_model_id,
        raw_token_value=raw_token_value,
        private_fixture_root=private_fixture_root,
        raw_transcript_text=raw_transcript_text,
    )
    monkeypatch.setenv("HF_TOKEN", raw_token_value)

    exit_code = probe.main(
        [
            "--english-fixture",
            f"{private_fixture_root}/english-dialogue-two-speakers.mp3",
            "--swedish-fixture",
            f"{private_fixture_root}/swedish-monologue-one-speaker.m4a",
            "--diarization-model",
            raw_model_id,
        ],
    )

    captured = capsys.readouterr()
    payload = _read_json_object(captured.out)
    stt = _mapping_at(payload, "stt")
    diarization = _mapping_at(payload, "diarization")
    assert exit_code == 0
    assert _mapping_at(stt, "failure") == {
        "exception_class": "RuntimeError",
        "failure_code": "gpu_backend_runtime_unavailable",
    }
    assert _mapping_at(diarization, "failure") == {
        "exception_class": "GatedRepoError",
        "failure_code": "gated_model_access_denied",
    }
    assert "CUDA failed with error" not in captured.out
    assert raw_model_id not in captured.out
    assert raw_token_value not in captured.out
    assert private_fixture_root not in captured.out
    assert raw_transcript_text not in captured.out


def _runtime_probe_module() -> ModuleType:
    return importlib.import_module(
        "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_runtime_probe"
    )


def _install_blocking_backend_modules(
    monkeypatch: pytest.MonkeyPatch,
    *,
    raw_model_id: str,
    raw_token_value: str,
    private_fixture_root: str,
    raw_transcript_text: str,
) -> None:
    faster_whisper = ModuleType("faster_whisper")

    class BlockingWhisperModel:
        def __init__(
            self,
            model_id: str,
            *,
            device: str,
            compute_type: str,
        ) -> None:
            del model_id, device, compute_type
            raise RuntimeError(
                "CUDA failed with error CUDA driver version is insufficient "
                f"for CUDA runtime version at {private_fixture_root} "
                f"with token {raw_token_value} and transcript {raw_transcript_text}"
            )

    setattr(faster_whisper, "WhisperModel", BlockingWhisperModel)
    _install_module(monkeypatch, "faster_whisper", faster_whisper)
    pyannote = ModuleType("pyannote")
    pyannote_audio = ModuleType("pyannote.audio")

    class GatedRepoError(Exception):
        pass

    class BlockingPipeline:
        @classmethod
        def from_pretrained(cls, model_id: str, *, token: str) -> object:
            del cls
            if model_id != raw_model_id or token != raw_token_value:
                raise AssertionError("probe did not pass the configured backend inputs")
            raise GatedRepoError(
                f"Access denied for {model_id} with token {token} under {private_fixture_root}"
            )

    setattr(pyannote_audio, "Pipeline", BlockingPipeline)
    setattr(pyannote, "audio", pyannote_audio)
    setattr(pyannote, "__path__", [])
    _install_module(monkeypatch, "pyannote", pyannote)
    _install_module(monkeypatch, "pyannote.audio", pyannote_audio)
    _install_module(monkeypatch, "huggingface_hub", ModuleType("huggingface_hub"))
    torch_module = ModuleType("torch")

    class FakeCuda:
        @staticmethod
        def is_available() -> bool:
            return True

    class FakeVersion:
        hip = "6.2"

    def device(value: str) -> str:
        return value

    setattr(torch_module, "cuda", FakeCuda())
    setattr(torch_module, "version", FakeVersion())
    setattr(torch_module, "device", device)
    _install_module(monkeypatch, "torch", torch_module)


def _install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    module.__spec__ = ModuleSpec(name, loader=None)
    monkeypatch.setitem(sys.modules, name, module)


def _read_json_object(payload_text: str) -> dict[str, object]:
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise AssertionError("runtime probe stdout must contain a JSON object")
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def _mapping_at(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload[key]
    if not isinstance(value, dict):
        raise AssertionError(f"{key} must be a JSON object")
    return {str(item_key): item for item_key, item in value.items() if isinstance(item_key, str)}
