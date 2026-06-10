"""Audio transcription sidecar live observation runtime.

Purpose:
    Produce sanitized live Hemma observations for the speech-to-text sidecar
    profile proof from codec, runtime, Hugging Face, GPU, STT, diarization, and
    long-job lifecycle probes.

Relationships:
    - Used by the `benchmark:stt-sidecar-live-observation` operator command.
    - Emits the JSON envelope consumed by
      `audio_transcription_sidecar_live_observations`.
    - Keeps backend libraries in the benchmark runtime instead of the main
      Sir Convert service dependency path.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from scripts.sir_convert_a_lot.benchmarking.output_policy import (
    enforce_generated_output_path,
)
from scripts.sir_convert_a_lot.devops import (
    audio_transcription_sidecar_live_observation_cache as cache_mounts,
)
from scripts.sir_convert_a_lot.devops import (
    audio_transcription_sidecar_live_observation_lifecycle as lifecycle,
)
from scripts.sir_convert_a_lot.devops import (
    audio_transcription_sidecar_live_observation_projection as projection,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_commands import (
    CommandRunner,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observations import (
    LIVE_OBSERVATION_SCHEMA_VERSION,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_proof import (
    REQUIRED_COMMON_AUDIO_CODECS,
    REQUIRED_HF_CACHE_ENV_VARS,
    REQUIRED_HF_TOKEN_ENV_VARS,
    REQUIRED_PYTHON_PACKAGES,
    REQUIRED_SIDECAR_COMPOSE_SERVICE,
    REQUIRED_SYSTEM_TOOLS,
)

RuntimeMode = Literal["host", "docker"]
CONTAINER_HF_HOME = "/cache/huggingface"
CONTAINER_HF_HUB_CACHE = f"{CONTAINER_HF_HOME}/hub"
DEFAULT_OUTPUT_ROOT = Path("build/verification/stt-sidecar-live-observation")
DEFAULT_DOCKERFILE_PATH = Path("containers/stt-sidecar-benchmark/Dockerfile")
DEFAULT_HF_HOME = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_HUB_CACHE = DEFAULT_HF_HOME / "hub"
DEFAULT_IMAGE_TAG = "benchmark"
RUNTIME_PROBE_MODULE = "scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_runtime_probe"


@dataclass(frozen=True, slots=True)
class LiveObservationSettings:
    """Normalized settings for one live STT sidecar observation run."""

    output_root: Path
    runtime_mode: RuntimeMode
    english_fixture: Path
    swedish_fixture: Path
    sidecar_launch_observed: bool
    dockerfile_path: Path
    image_name: str
    image_tag: str
    hf_home: Path
    hf_hub_cache: Path
    hf_cache_home_mount: Path
    english_speakers: int
    swedish_speakers: int
    min_speakers: int
    max_speakers: int
    runtime_timeout_seconds: float
    ffprobe_timeout_seconds: float


def build_live_observation(
    *,
    settings: LiveObservationSettings,
    command_runner: CommandRunner,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Build the sanitized live observation JSON payload."""

    enforce_generated_output_path(settings.output_root, label="output_root")
    settings.output_root.mkdir(parents=True, exist_ok=True)
    image = f"{settings.image_name}:{settings.image_tag}"
    if settings.runtime_mode == "docker":
        _build_sidecar_image(settings=settings, command_runner=command_runner, image=image)
    effective_hf_cache_mount = cache_mounts.effective_hf_cache_mount(
        runtime_mode=settings.runtime_mode,
        hf_home=settings.hf_home,
        hf_cache_home_mount=settings.hf_cache_home_mount,
        command_runner=command_runner,
        image=image,
    )
    codec_boundary = _codec_boundary(
        settings=settings,
        command_runner=command_runner,
        image=image,
    )
    runtime_payload = _runtime_probe_payload(
        settings=settings,
        command_runner=command_runner,
        environment=environment,
        image=image,
        effective_hf_cache_mount=effective_hf_cache_mount,
    )
    lifecycle_evidence = lifecycle.exercise_synthetic_duration_lifecycle()
    observation: dict[str, object] = {
        "schema_version": LIVE_OBSERVATION_SCHEMA_VERSION,
        "evidence_mode": "live_hemma",
        "observation_failure_reasons": projection.failure_reasons(
            codec_boundary=codec_boundary,
            runtime_payload=runtime_payload,
            environment=environment,
            sidecar_launch_observed=settings.sidecar_launch_observed,
            hf_home=settings.hf_home,
            hf_hub_cache=settings.hf_hub_cache,
        ),
        "sidecar_launch": _sidecar_launch(settings),
        "codec_boundary": codec_boundary,
        "backend_dependencies": projection.backend_dependencies(runtime_payload),
        "huggingface_readiness": projection.huggingface_readiness(
            runtime_payload=runtime_payload,
            environment=environment,
            hf_home=settings.hf_home,
            hf_hub_cache=settings.hf_hub_cache,
        ),
        "profiles": projection.profiles(runtime_payload),
        "runtime": projection.runtime_evidence(
            runtime_payload=runtime_payload,
            hf_home=settings.hf_home,
            hf_hub_cache=settings.hf_hub_cache,
        ),
        "language_evidence": projection.language_evidence(runtime_payload),
        "speaker_hints": projection.speaker_hints(runtime_payload),
        "duration": projection.duration(lifecycle_evidence),
        "batch_lifecycle": projection.batch_lifecycle(lifecycle_evidence),
        "content_safety": projection.content_safety(),
    }
    return observation


def write_live_observation(
    observation: Mapping[str, object],
    *,
    output_root: Path,
) -> Path:
    """Write the sanitized live observation under the generated output root."""

    enforce_generated_output_path(output_root, label="output_root")
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "live-observation.json"
    output_path.write_text(
        json.dumps(observation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _sidecar_launch(settings: LiveObservationSettings) -> dict[str, object]:
    return {
        "image_name": settings.image_name,
        "image_tag": settings.image_tag,
        "compose_service": REQUIRED_SIDECAR_COMPOSE_SERVICE,
        "build_contract": "buildkit",
        "launch_observed": settings.sidecar_launch_observed,
        "isolated_runtime_marker": True,
        "required_system_tools": REQUIRED_SYSTEM_TOOLS,
        "required_python_packages": REQUIRED_PYTHON_PACKAGES,
        "gpu_acceleration_required": True,
        "hf_token_env_var_names": REQUIRED_HF_TOKEN_ENV_VARS,
        "hf_cache_env_var_names": REQUIRED_HF_CACHE_ENV_VARS,
        "environment_values_exposed": False,
        "private_paths_exposed": False,
        "raw_model_identifiers_exposed": False,
    }


def _codec_boundary(
    *,
    settings: LiveObservationSettings,
    command_runner: CommandRunner,
    image: str,
) -> dict[str, object]:
    ffmpeg_available = _version_command_ready(
        command_runner=command_runner,
        command=_tool_command(settings, image=image, tool="ffmpeg", args=("-version",)),
        timeout_seconds=settings.ffprobe_timeout_seconds,
    )
    ffprobe_available = _version_command_ready(
        command_runner=command_runner,
        command=_tool_command(settings, image=image, tool="ffprobe", args=("-version",)),
        timeout_seconds=settings.ffprobe_timeout_seconds,
    )
    valid_probes = (
        _ffprobe_audio_ready(settings, command_runner, image, settings.english_fixture),
        _ffprobe_audio_ready(settings, command_runner, image, settings.swedish_fixture),
    )
    invalid_root = settings.output_root / "media-boundary"
    invalid_root.mkdir(parents=True, exist_ok=True)
    bad_media = invalid_root / "bad-media.bin"
    no_audio = invalid_root / "no-audio.txt"
    unsupported = invalid_root / "unsupported-media.xyz"
    bad_media.write_bytes(b"not an audio stream")
    no_audio.write_text("text only\n", encoding="utf-8")
    unsupported.write_bytes(b"unsupported audio placeholder")
    return {
        "ffmpeg_available": ffmpeg_available,
        "ffprobe_available": ffprobe_available,
        "supported_audio_codecs": REQUIRED_COMMON_AUDIO_CODECS,
        "valid_audio_probe_exercised": all(valid_probes),
        "bad_media_fails_closed": not _ffprobe_audio_ready(
            settings,
            command_runner,
            image,
            bad_media,
        ),
        "no_audio_fails_closed": not _ffprobe_audio_ready(
            settings,
            command_runner,
            image,
            no_audio,
        ),
        "unsupported_media_fails_closed": not _ffprobe_audio_ready(
            settings,
            command_runner,
            image,
            unsupported,
        ),
        "bounded_metadata_projected": all(valid_probes),
    }


def _tool_command(
    settings: LiveObservationSettings,
    *,
    image: str,
    tool: str,
    args: Sequence[str],
) -> tuple[str, ...]:
    if settings.runtime_mode == "host":
        return (tool, *args)
    return ("sudo", "-n", "docker", "run", "--rm", "--entrypoint", tool, image, *args)


def _version_command_ready(
    *,
    command_runner: CommandRunner,
    command: Sequence[str],
    timeout_seconds: float,
) -> bool:
    return command_runner.run(command, timeout_seconds=timeout_seconds).returncode == 0


def _ffprobe_audio_ready(
    settings: LiveObservationSettings,
    command_runner: CommandRunner,
    image: str,
    media_path: Path,
) -> bool:
    command = _ffprobe_command(settings=settings, image=image, media_path=media_path)
    result = command_runner.run(command, timeout_seconds=settings.ffprobe_timeout_seconds)
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return _has_audio_stream(payload)


def _ffprobe_command(
    *,
    settings: LiveObservationSettings,
    image: str,
    media_path: Path,
) -> tuple[str, ...]:
    args = (
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=codec_name,sample_rate,channels:format=format_name,duration,size",
        "-of",
        "json",
    )
    if settings.runtime_mode == "host":
        return ("ffprobe", *args, media_path.as_posix())
    return (
        "sudo",
        "-n",
        "docker",
        "run",
        "--rm",
        "-v",
        f"{media_path.resolve().parent.as_posix()}:/input:ro",
        "--entrypoint",
        "ffprobe",
        image,
        *args,
        f"/input/{media_path.name}",
    )


def _has_audio_stream(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    streams = payload.get("streams")
    if not isinstance(streams, list):
        return False
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        if isinstance(stream.get("codec_name"), str):
            return True
    return False


def _build_sidecar_image(
    *,
    settings: LiveObservationSettings,
    command_runner: CommandRunner,
    image: str,
) -> None:
    command_runner.run(
        (
            "sudo",
            "-n",
            "docker",
            "buildx",
            "build",
            "--load",
            "-t",
            image,
            "-f",
            settings.dockerfile_path.as_posix(),
            settings.dockerfile_path.parent.as_posix(),
        ),
        timeout_seconds=settings.runtime_timeout_seconds,
    )


def _runtime_probe_payload(
    *,
    settings: LiveObservationSettings,
    command_runner: CommandRunner,
    environment: Mapping[str, str],
    image: str,
    effective_hf_cache_mount: Path,
) -> Mapping[str, object]:
    command = _runtime_probe_command(
        settings=settings,
        environment=environment,
        image=image,
        effective_hf_cache_mount=effective_hf_cache_mount,
    )
    result = command_runner.run(command, timeout_seconds=settings.runtime_timeout_seconds)
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(key, str)}


def _runtime_probe_command(
    *,
    settings: LiveObservationSettings,
    environment: Mapping[str, str],
    image: str,
    effective_hf_cache_mount: Path,
) -> tuple[str, ...]:
    probe_args = _runtime_probe_args(settings)
    if settings.runtime_mode == "host":
        return (sys.executable, "-m", RUNTIME_PROBE_MODULE, *probe_args)
    repo_root = Path.cwd().resolve()
    env_args = [
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-e",
        f"HF_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
    ]
    if environment.get("HF_TOKEN", "").strip():
        env_args.extend(["-e", "HF_TOKEN"])
    command = [
        "sudo",
        "-n",
        "docker",
        "run",
        "--rm",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--group-add",
        "video",
        "--group-add",
        "render",
        "--ipc=host",
        "--cap-add=SYS_PTRACE",
        "--security-opt",
        "seccomp=unconfined",
        *env_args,
        "-v",
        f"{repo_root.as_posix()}:/workspace/repo:ro",
        "-v",
        f"{settings.english_fixture.resolve().parent.as_posix()}:/input:ro",
        "-v",
        f"{effective_hf_cache_mount.as_posix()}:{CONTAINER_HF_HOME}",
        "-w",
        "/workspace/repo",
        "--entrypoint",
        "python",
        image,
        "-m",
        RUNTIME_PROBE_MODULE,
    ]
    return tuple(command + list(_runtime_probe_args(settings, container_paths=True)))


def _runtime_probe_args(
    settings: LiveObservationSettings,
    *,
    container_paths: bool = False,
) -> tuple[str, ...]:
    english_fixture = (
        f"/input/{settings.english_fixture.name}"
        if container_paths
        else settings.english_fixture.as_posix()
    )
    swedish_fixture = (
        f"/input/{settings.swedish_fixture.name}"
        if container_paths
        else settings.swedish_fixture.as_posix()
    )
    return (
        "--english-fixture",
        english_fixture,
        "--swedish-fixture",
        swedish_fixture,
        "--english-speakers",
        str(settings.english_speakers),
        "--swedish-speakers",
        str(settings.swedish_speakers),
        "--min-speakers",
        str(settings.min_speakers),
        "--max-speakers",
        str(settings.max_speakers),
    )
