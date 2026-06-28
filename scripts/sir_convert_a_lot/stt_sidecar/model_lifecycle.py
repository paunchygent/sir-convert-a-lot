"""Lazy model residency lifecycle for the STT sidecar runtime.

Purpose:
    Own concurrent loading, active-use accounting, idle unload, and shutdown
    cleanup for the approved FasterWhisper and pyannote model pipelines.

Relationships:
    - Used by `stt_sidecar.runtime.SttSidecarRuntime` around diarization and
      chunk transcription work.
    - Keeps backend-native import and unload details out of the HTTP-facing
      sidecar runtime contract.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Protocol

from scripts.sir_convert_a_lot.stt_sidecar.settings import SttSidecarSettings


class WhisperModelLike(Protocol):
    """Loaded FasterWhisper model accepted by the batched pipeline."""


class BatchedWhisperModelLike(Protocol):
    """Batched FasterWhisper pipeline behavior used by the sidecar runtime."""

    def transcribe(
        self,
        audio: str,
        *,
        beam_size: int,
        batch_size: int,
        word_timestamps: bool,
        language: str | None,
    ) -> tuple[Iterable[object], object]:
        """Return transcription segments and metadata."""


class WhisperModelFactory(Protocol):
    """Callable FasterWhisper model factory."""

    def __call__(
        self,
        model_size_or_path: str,
        *,
        device: str,
        compute_type: str,
    ) -> WhisperModelLike:
        """Build a FasterWhisper model."""


class BatchedInferencePipelineFactory(Protocol):
    """Callable FasterWhisper batched inference pipeline factory."""

    def __call__(self, *, model: WhisperModelLike) -> BatchedWhisperModelLike:
        """Wrap a FasterWhisper model with batched inference."""


class DiarizationPipelineLike(Protocol):
    """pyannote pipeline behavior used by the sidecar runtime."""

    def __call__(
        self,
        file: str,
        *,
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
    ) -> object:
        """Return diarization output for one audio file."""

    def to(self, device: object) -> object:
        """Move the pipeline to a GPU device."""


class DiarizationPipelineFactory(Protocol):
    """Callable pyannote pipeline factory."""

    def from_pretrained(self, checkpoint_path: str, *, token: str) -> DiarizationPipelineLike:
        """Build a pyannote pipeline from a gated checkpoint."""


@dataclass(frozen=True, slots=True)
class LoadedSttModels:
    """Resident STT and diarization model bundle."""

    whisper_model: WhisperModelLike
    stt_model: BatchedWhisperModelLike
    diarization_pipeline: DiarizationPipelineLike


class SttModelLifecycle:
    """Concurrency-safe lazy load and idle unload manager."""

    def __init__(
        self,
        settings: SttSidecarSettings,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._condition = threading.Condition(threading.RLock())
        self._models: LoadedSttModels | None = None
        self._loading = False
        self._active_model_uses = 0
        self._last_used_at: float | None = None

    def gpu_ready(self) -> bool:
        """Return whether the configured GPU runtime is available."""
        torch_module = import_module("torch")
        cuda_obj = getattr(torch_module, "cuda")
        return bool(cuda_obj.is_available())

    def required_secret_present(self) -> bool:
        """Return whether the configured gated-model secret is available."""
        return os.environ.get(self._settings.hf_token_env_name, "").strip() != ""

    @contextmanager
    def use_models(self) -> Iterator[LoadedSttModels]:
        """Yield resident models while protecting them from idle unload."""
        models = self._acquire_models()
        try:
            yield models
        finally:
            self._release_models()

    def unload_idle_models(self) -> Mapping[str, object]:
        """Unload resident models after the configured idle timeout."""
        with self._condition:
            if self._models is None:
                return self._snapshot_locked()
            if self._active_model_uses > 0:
                return self._snapshot_locked()
            if self._last_used_at is None:
                return self._snapshot_locked()
            idle_seconds = self._clock() - self._last_used_at
            if idle_seconds < self._settings.idle_unload_seconds:
                return self._snapshot_locked(idle_seconds=idle_seconds)
            self._drop_models_locked()
            return self._snapshot_locked(idle_seconds=idle_seconds)

    def shutdown(self) -> Mapping[str, object]:
        """Drop resident models during sidecar shutdown."""
        with self._condition:
            self._drop_models_locked()
            return self._snapshot_locked()

    def snapshot(self) -> Mapping[str, object]:
        """Return bounded model residency diagnostics."""
        with self._condition:
            return self._snapshot_locked()

    def _acquire_models(self) -> LoadedSttModels:
        while True:
            self._ensure_models_loaded()
            with self._condition:
                if self._models is not None:
                    self._active_model_uses += 1
                    return self._models

    def _release_models(self) -> None:
        with self._condition:
            self._active_model_uses -= 1
            self._last_used_at = self._clock()
            self._condition.notify_all()

    def _ensure_models_loaded(self) -> None:
        while True:
            with self._condition:
                if self._models is not None:
                    return
                if not self._loading:
                    self._loading = True
                    break
                self._condition.wait()
        try:
            models = self._load_models()
        except Exception:
            with self._condition:
                self._loading = False
                self._condition.notify_all()
            raise
        with self._condition:
            self._models = models
            self._loading = False
            self._last_used_at = None
            self._condition.notify_all()

    def _load_models(self) -> LoadedSttModels:
        torch_module = import_module("torch")
        cuda_obj = getattr(torch_module, "cuda")
        if not bool(cuda_obj.is_available()):
            raise RuntimeError("GPU runtime is required for the STT sidecar.")
        faster_whisper_module = import_module("faster_whisper")
        whisper_factory: WhisperModelFactory = getattr(faster_whisper_module, "WhisperModel")
        try:
            batched_pipeline_factory: BatchedInferencePipelineFactory = getattr(
                faster_whisper_module,
                "BatchedInferencePipeline",
            )
        except AttributeError as exc:
            raise RuntimeError(
                "faster-whisper BatchedInferencePipeline is required for the STT sidecar."
            ) from exc
        whisper_model = whisper_factory(
            self._settings.stt_model_id,
            device="cuda",
            compute_type=self._settings.compute_type,
        )
        stt_model = batched_pipeline_factory(model=whisper_model)
        pyannote_module = import_module("pyannote.audio")
        pipeline_factory: DiarizationPipelineFactory = getattr(pyannote_module, "Pipeline")
        token = os.environ.get(self._settings.hf_token_env_name, "").strip()
        if token == "":
            raise RuntimeError("HF token is required for the STT sidecar diarization profile.")
        diarization_pipeline = pipeline_factory.from_pretrained(
            self._settings.diarization_model_id,
            token=token,
        )
        device_factory = getattr(torch_module, "device")
        diarization_pipeline.to(device_factory("cuda"))
        return LoadedSttModels(
            whisper_model=whisper_model,
            stt_model=stt_model,
            diarization_pipeline=diarization_pipeline,
        )

    def _drop_models_locked(self) -> None:
        if self._models is None:
            return
        self._models = None
        self._last_used_at = None
        self._condition.notify_all()

    def _snapshot_locked(self, *, idle_seconds: float | None = None) -> dict[str, object]:
        resolved_idle_seconds = idle_seconds
        if resolved_idle_seconds is None and self._last_used_at is not None:
            resolved_idle_seconds = self._clock() - self._last_used_at
        return {
            "models_resident": self._models is not None,
            "active_model_uses": self._active_model_uses,
            "idle_seconds": resolved_idle_seconds,
            "idle_unload_seconds": self._settings.idle_unload_seconds,
        }


def cache_root_ready(path: Path) -> bool:
    """Return whether the sidecar cache root is available for lazy model load."""
    return path.is_dir()


def model_artifacts_present(settings: SttSidecarSettings) -> bool:
    """Return whether configured model artifacts are present in the HF cache."""
    return _cached_model_artifact_present(
        model_id=settings.stt_model_id,
        cache_root=settings.hf_cache_container_root,
    ) and _cached_model_artifact_present(
        model_id=settings.diarization_model_id,
        cache_root=settings.hf_cache_container_root,
    )


def _cached_model_artifact_present(*, model_id: str, cache_root: Path) -> bool:
    local_path = Path(model_id)
    if local_path.is_absolute():
        return _directory_contains_file(local_path)
    model_cache_name = f"models--{model_id.replace('/', '--')}"
    for root in _cache_candidate_roots(cache_root):
        if _directory_contains_file(root / model_cache_name / "snapshots"):
            return True
    return False


def _cache_candidate_roots(cache_root: Path) -> tuple[Path, ...]:
    hub_root = cache_root / "hub"
    if cache_root.name == "hub":
        return (cache_root,)
    return (hub_root, cache_root)


def _directory_contains_file(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        return any(child.is_file() for child in path.rglob("*"))
    except OSError:
        return False
