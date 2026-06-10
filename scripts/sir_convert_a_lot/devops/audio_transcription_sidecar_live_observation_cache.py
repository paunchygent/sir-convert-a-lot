"""Audio transcription sidecar cache mount resolution.

Purpose:
    Resolve the Docker-visible Hugging Face cache mount used by the isolated
    speech-to-text benchmark runtime while preserving the canonical Hemma
    scratch cache as the source of truth.

Relationships:
    - Used by the live observation runtime before Docker runtime probes.
    - Mirrors the cache-access pattern used by other Hemma sidecar benchmarks.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_commands import (
    CommandRunner,
)

DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")


def effective_hf_cache_mount(
    *,
    runtime_mode: str,
    hf_home: Path,
    hf_cache_home_mount: Path,
    command_runner: CommandRunner,
    image: str,
) -> Path:
    """Return a Docker-mountable cache path for the benchmark container."""

    if runtime_mode == "host":
        return hf_home
    if _docker_cache_mount_ready(
        cache_dir=hf_home,
        command_runner=command_runner,
        image=image,
    ):
        return hf_home
    if _is_srv_cache_path(hf_home):
        _ensure_home_cache_bind_mount(
            hf_home=hf_home,
            hf_cache_home_mount=hf_cache_home_mount,
            command_runner=command_runner,
        )
        if _docker_cache_mount_ready(
            cache_dir=hf_cache_home_mount,
            command_runner=command_runner,
            image=image,
        ):
            return hf_cache_home_mount
    return hf_home


def _docker_cache_mount_ready(
    *,
    cache_dir: Path,
    command_runner: CommandRunner,
    image: str,
) -> bool:
    result = command_runner.run(
        (
            "sudo",
            "-n",
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cache_dir.as_posix()}:/cache-probe",
            "--entrypoint",
            "python",
            image,
            "-V",
        ),
        timeout_seconds=60.0,
    )
    return result.returncode == 0


def _ensure_home_cache_bind_mount(
    *,
    hf_home: Path,
    hf_cache_home_mount: Path,
    command_runner: CommandRunner,
) -> None:
    command_runner.run(
        ("sudo", "-n", "mkdir", "-p", hf_home.as_posix()),
        timeout_seconds=30.0,
    )
    command_runner.run(
        ("mkdir", "-p", hf_cache_home_mount.as_posix()),
        timeout_seconds=30.0,
    )
    mounted = command_runner.run(
        ("findmnt", hf_cache_home_mount.as_posix()),
        timeout_seconds=30.0,
    )
    if mounted.returncode == 0:
        return
    command_runner.run(
        (
            "sudo",
            "-n",
            "mount",
            "--bind",
            hf_home.as_posix(),
            hf_cache_home_mount.as_posix(),
        ),
        timeout_seconds=30.0,
    )


def _is_srv_cache_path(cache_dir: Path) -> bool:
    return cache_dir.as_posix().startswith("/srv/")
