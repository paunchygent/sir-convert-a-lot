"""STT sidecar lazy model residency behavior tests.

Purpose:
    Prove the sidecar can accept media work without resident STT models, then
    lazy-loads and unloads the approved model pipelines around real model work.

Relationships:
    - Exercises `stt_sidecar.runtime` through its sidecar-facing operations.
    - Protects Task 366 so readiness, first-use loading, idle unload, and
      shutdown cleanup do not drift back to eager model residency.
"""

from __future__ import annotations

import sys
import threading
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.audio_transcription_policy import (
    AudioTranscriptionErrorCode,
    evaluate_stt_sidecar_readiness,
)
from scripts.sir_convert_a_lot.stt_sidecar.model_lifecycle import SttModelLifecycle
from scripts.sir_convert_a_lot.stt_sidecar.runtime import SttSidecarRuntime
from tests.sir_convert_a_lot.stt_sidecar_lazy_lifecycle_support import (
    FakeClock,
    ModelLoadCounters,
    install_stt_modules,
    install_torch_module,
    normalized_request,
    patch_successful_media,
    required_mapping,
    required_string,
    settings,
    transcribe_request,
    write_cached_model_artifacts,
)


def test_startup_health_and_probe_do_not_instantiate_heavy_model_pipelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    install_torch_module(monkeypatch)
    patch_successful_media(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    sidecar_settings = settings(tmp_path)
    write_cached_model_artifacts(sidecar_settings)
    runtime = SttSidecarRuntime(sidecar_settings)

    runtime.startup()

    health = runtime.health()
    assert health["status"] == "ok"
    assert health["ready"] is True
    assert health["models_resident"] is False
    capabilities = runtime.capabilities()
    cache = required_mapping(capabilities, "cache")
    assert cache["model_artifacts_present"] is True
    assert cache["models_resident"] is False
    probe_payload = runtime.probe_media(transcribe_request(source_path=source_path))
    assert required_mapping(probe_payload, "media")
    assert "faster_whisper" not in sys.modules
    assert "pyannote.audio" not in sys.modules


def test_capabilities_fail_readiness_when_cache_root_lacks_model_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_torch_module(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    runtime = SttSidecarRuntime(settings(tmp_path))

    runtime.startup()

    capabilities = runtime.capabilities()
    cache = required_mapping(capabilities, "cache")
    assert cache["cache_roots_ready"] is True
    assert cache["model_artifacts_present"] is False
    readiness = evaluate_stt_sidecar_readiness(
        health_payload=runtime.health(),
        capability_payload=capabilities,
    )
    assert readiness.ready is False
    assert readiness.error_code == AudioTranscriptionErrorCode.MODEL_CACHE_UNAVAILABLE
    assert readiness.details == {"reason": "model_artifacts_missing"}


def test_first_model_using_operations_share_one_lazy_load_under_concurrency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    counters = ModelLoadCounters()
    load_release = threading.Event()
    first_load_entered = threading.Event()
    install_torch_module(monkeypatch)
    install_stt_modules(
        monkeypatch,
        counters=counters,
        first_load_entered=first_load_entered,
        load_release=load_release,
    )
    patch_successful_media(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    sidecar_settings = settings(tmp_path)
    write_cached_model_artifacts(sidecar_settings)
    runtime = SttSidecarRuntime(sidecar_settings)
    runtime.startup()
    assert counters.whisper_loads == 0
    probe_payload = runtime.probe_media(transcribe_request(source_path=source_path))
    media = required_mapping(probe_payload, "media")
    request = {
        **normalized_request(
            request_handle="job-audio",
            handle=required_string(media, "normalized_audio_handle"),
            sha=required_string(media, "normalized_audio_sha256"),
        ),
        "chunk": {
            "chunk_index": 0,
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "overlap_seconds": 0.0,
        },
    }
    start_barrier = threading.Barrier(3)
    results: list[Mapping[str, object]] = []
    failures: list[BaseException] = []

    def _transcribe() -> None:
        try:
            start_barrier.wait(timeout=2.0)
            results.append(runtime.transcribe_chunk(request))
        except BaseException as exc:
            failures.append(exc)

    threads = [threading.Thread(target=_transcribe) for _ in range(2)]
    for thread in threads:
        thread.start()
    start_barrier.wait(timeout=2.0)
    assert first_load_entered.wait(timeout=2.0)
    load_release.set()
    for thread in threads:
        thread.join(timeout=2.0)

    assert failures == []
    assert len(results) == 2
    assert counters.whisper_loads == 1
    assert counters.batched_wraps == 1
    assert counters.diarization_loads == 1
    assert runtime.health()["models_resident"] is True


def test_idle_unload_waits_for_active_model_work_and_shutdown_drops_references(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    counters = ModelLoadCounters()
    transcribe_entered = threading.Event()
    transcribe_release = threading.Event()
    install_torch_module(monkeypatch)
    install_stt_modules(
        monkeypatch,
        counters=counters,
        transcribe_entered=transcribe_entered,
        transcribe_release=transcribe_release,
    )
    patch_successful_media(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    sidecar_settings = settings(tmp_path, idle_unload_seconds=0.0)
    write_cached_model_artifacts(sidecar_settings)
    runtime = SttSidecarRuntime(sidecar_settings)
    runtime.startup()
    probe_payload = runtime.probe_media(transcribe_request(source_path=source_path))
    media = required_mapping(probe_payload, "media")
    request = {
        **normalized_request(
            request_handle="job-audio",
            handle=required_string(media, "normalized_audio_handle"),
            sha=required_string(media, "normalized_audio_sha256"),
        ),
        "chunk": {
            "chunk_index": 0,
            "start_seconds": 0.0,
            "end_seconds": 2.0,
            "overlap_seconds": 0.0,
        },
    }
    failures: list[BaseException] = []

    def _transcribe() -> None:
        try:
            runtime.transcribe_chunk(request)
        except BaseException as exc:
            failures.append(exc)

    thread = threading.Thread(target=_transcribe)
    thread.start()
    assert transcribe_entered.wait(timeout=2.0)

    active_unload = runtime.unload_idle_models()

    assert active_unload["models_resident"] is True
    assert active_unload["active_model_uses"] == 1
    assert counters.unloads == 0
    transcribe_release.set()
    thread.join(timeout=2.0)
    assert failures == []

    idle_unload = runtime.unload_idle_models()

    assert idle_unload["models_resident"] is False
    assert counters.unloads == 1
    runtime.transcribe_chunk(request)
    assert counters.whisper_loads == 2

    runtime.shutdown()

    assert runtime.health()["models_resident"] is False
    assert counters.unloads == 2


def test_health_triggers_idle_unload_after_elapsed_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "meeting.m4a"
    source_path.write_bytes(b"audio bytes")
    counters = ModelLoadCounters()
    clock = FakeClock()
    install_torch_module(monkeypatch)
    install_stt_modules(monkeypatch, counters=counters)
    patch_successful_media(monkeypatch)
    monkeypatch.setenv("HF_TOKEN", "hf_test_token")
    sidecar_settings = settings(tmp_path, idle_unload_seconds=5.0)
    write_cached_model_artifacts(sidecar_settings)
    runtime = SttSidecarRuntime(sidecar_settings)
    runtime._model_lifecycle = SttModelLifecycle(sidecar_settings, clock=clock.monotonic)
    runtime.startup()
    probe_payload = runtime.probe_media(transcribe_request(source_path=source_path))
    media = required_mapping(probe_payload, "media")

    runtime.transcribe_chunk(
        {
            **normalized_request(
                request_handle="job-audio",
                handle=required_string(media, "normalized_audio_handle"),
                sha=required_string(media, "normalized_audio_sha256"),
            ),
            "chunk": {
                "chunk_index": 0,
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "overlap_seconds": 0.0,
            },
        }
    )
    assert runtime.health()["models_resident"] is True

    clock.advance(6.0)
    health = runtime.health()

    assert health["models_resident"] is False
    assert counters.unloads == 1
