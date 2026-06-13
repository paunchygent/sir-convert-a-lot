"""Environment settings for the STT sidecar runtime.

Purpose:
    Resolve deployment configuration for the isolated speech-to-text sidecar
    without exposing backend-native model choices through HTTP payloads.

Relationships:
    - Consumed by `stt_sidecar.app` and `stt_sidecar.runtime`.
    - Keeps deployment defaults close to the accepted FasterWhisper plus
      pyannote profile while leaving public capability labels provider-neutral.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SttSidecarSettings:
    """Environment-derived settings for the isolated STT runtime."""

    backend_profile_id: str
    backend_version: str
    stt_profile_label: str
    diarization_profile_label: str
    stt_model_id: str
    diarization_model_id: str
    compute_type: str
    hf_token_env_name: str
    hf_cache_container_root: Path
    hf_cache_host_label: str
    hf_cache_container_label: str
    acceleration_family: str
    beam_size: int
    batch_size: int

    @classmethod
    def from_env(cls) -> "SttSidecarSettings":
        """Build STT sidecar settings from environment variables."""
        return cls(
            backend_profile_id=_env("SIR_STT_SIDECAR_BACKEND_PROFILE_ID", "stt_sv_en_primary"),
            backend_version=_env(
                "SIR_STT_SIDECAR_BACKEND_VERSION",
                "faster_whisper_pyannote_profile",
            ),
            stt_profile_label=_env("SIR_STT_SIDECAR_STT_PROFILE_LABEL", "stt_sv_en_primary"),
            diarization_profile_label=_env(
                "SIR_STT_SIDECAR_DIARIZATION_PROFILE_LABEL",
                "diarization_sv_en_primary",
            ),
            stt_model_id=_env("SIR_STT_SIDECAR_STT_MODEL_ID", "Systran/faster-whisper-large-v3"),
            diarization_model_id=_env(
                "SIR_STT_SIDECAR_DIARIZATION_MODEL_ID",
                "pyannote/speaker-diarization-community-1",
            ),
            compute_type=_env("SIR_STT_SIDECAR_COMPUTE_TYPE", "float16"),
            hf_token_env_name=_env("SIR_STT_SIDECAR_HF_TOKEN_ENV_NAME", "HF_TOKEN"),
            hf_cache_container_root=Path(_env("HF_HOME", "/cache/huggingface")),
            hf_cache_host_label=_env(
                "SIR_STT_SIDECAR_HF_CACHE_HOST_LABEL",
                "persistent_huggingface_cache",
            ),
            hf_cache_container_label=_env(
                "SIR_STT_SIDECAR_HF_CACHE_CONTAINER_LABEL",
                "huggingface_cache_mount",
            ),
            acceleration_family=_env("SIR_STT_SIDECAR_ACCELERATION_FAMILY", "rocm"),
            beam_size=_positive_int_env("SIR_STT_SIDECAR_BEAM_SIZE", 5),
            batch_size=_positive_int_env("SIR_STT_SIDECAR_BATCH_SIZE", 8),
        )


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value if value != "" else default


def _positive_int_env(name: str, default: int) -> int:
    raw_value = _env(name, str(default))
    value = int(raw_value)
    if value < 1:
        raise ValueError(f"{name} must be a positive integer.")
    return value
