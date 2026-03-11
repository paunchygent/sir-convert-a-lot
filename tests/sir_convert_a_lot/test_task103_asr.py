"""Task 103 ASR runtime tests.

Purpose:
    Cover the isolated `WhisperStrictScorer` runtime contract so ASR loading
    and concurrency behavior can evolve without being buried inside broader
    preprocessing tests.

Relationships:
    - Tests `task103_qwen_preprocessing_core.WhisperStrictScorer`.
    - Complements the processing and runner test modules without owning broader
      row-processing orchestration behavior.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    WhisperStrictScorer,
)


def test_whisper_strict_scorer_transcribes_with_pipeline(
    tmp_path: Path,
) -> None:
    """The ASR scorer should delegate transcription to the cached pipeline."""

    class _FakePipeline:
        def __call__(
            self,
            inputs: object,
            *,
            generate_kwargs: dict[str, object] | None = None,
        ) -> dict[str, object]:
            assert inputs == (tmp_path / "audio.wav").as_posix()
            assert generate_kwargs == {"task": "transcribe"}
            return {"text": "Hej från Sverige."}

    scorer = WhisperStrictScorer(
        model_id="KBLab/kb-whisper-large",
        revision="strict",
        _pipeline=_FakePipeline(),
    )

    transcript = scorer.transcribe(tmp_path / "audio.wav")

    assert transcript == "Hej från Sverige."


def test_whisper_strict_scorer_uses_pipeline_gpu_loading_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CUDA pipeline loading should use the documented GPU pipeline surface."""

    class _FakeTorchCuda:
        @staticmethod
        def is_available() -> bool:
            return True

    class _FakeTorch:
        cuda = _FakeTorchCuda()
        float16 = "float16"
        float32 = "float32"

        @staticmethod
        def device(name: str) -> object:
            return type("_FakeDevice", (), {"type": name})()

    captured_kwargs: dict[str, object] = {}

    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        type(
            "_FakeTransformersModule",
            (),
            {
                "pipeline": staticmethod(
                    lambda **kwargs: captured_kwargs.update(kwargs) or object()
                ),
            },
        )(),
    )

    scorer = WhisperStrictScorer(model_id="KBLab/kb-whisper-large", revision="strict")
    scorer._ensure_loaded()

    assert captured_kwargs["revision"] == "strict"
    assert captured_kwargs["dtype"] == "float16"
    assert captured_kwargs["device"] == 0
    assert captured_kwargs["task"] == "automatic-speech-recognition"


def test_whisper_strict_scorer_serializes_pipeline_initialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Concurrent scorer calls should initialize one cached pipeline per scorer."""

    class _FakeTorchCuda:
        @staticmethod
        def is_available() -> bool:
            return False

    class _FakeTorch:
        cuda = _FakeTorchCuda()
        float16 = "float16"
        float32 = "float32"

    load_call_count = 0
    load_call_lock = threading.Lock()

    class _FakePipeline:
        def __call__(
            self,
            inputs: object,
            *,
            generate_kwargs: dict[str, object] | None = None,
        ) -> dict[str, object]:
            assert generate_kwargs == {"task": "transcribe"}
            return {"text": f"transcribed:{inputs}"}

    def _fake_pipeline(**_: object) -> _FakePipeline:
        nonlocal load_call_count
        with load_call_lock:
            load_call_count += 1
        return _FakePipeline()

    monkeypatch.setitem(sys.modules, "torch", _FakeTorch())
    monkeypatch.setitem(
        sys.modules,
        "transformers",
        type("_FakeTransformersModule", (), {"pipeline": staticmethod(_fake_pipeline)})(),
    )

    scorer = WhisperStrictScorer(model_id="KBLab/kb-whisper-large", revision="strict")
    audio_path = Path("/tmp/example.wav")

    first_thread = threading.Thread(target=scorer.transcribe, args=(audio_path,))
    second_thread = threading.Thread(target=scorer.transcribe, args=(audio_path,))
    first_thread.start()
    second_thread.start()
    first_thread.join()
    second_thread.join()

    assert load_call_count == 1
