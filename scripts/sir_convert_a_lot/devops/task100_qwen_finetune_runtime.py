"""Runtime helpers for the Task 100 Qwen fine-tuning smoke surface.

Purpose:
    Keep the Task 100 runner small by isolating Docker BuildKit, Hemma cache
    mounting, and in-container smoke-probe execution for the dedicated Qwen
    fine-tuning image.

Relationships:
    - Used by `run_task100_hemma_qwen_finetune_smoke.py`.
    - Runs the in-container probe implemented by
      `task100_qwen_finetune_smoke_probe.py`.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from json import JSONDecodeError, JSONDecoder
from pathlib import Path

CONTAINER_HF_HOME = "/cache/huggingface"
CONTAINER_HF_HUB_CACHE = f"{CONTAINER_HF_HOME}/hub"
CONTAINER_TORCH_HOME = f"{CONTAINER_HF_HOME}/torch"


@dataclass(frozen=True)
class MountResolution:
    """Resolved host path used for one Docker-visible persistent cache."""

    canonical_root: Path
    effective_root: Path
    used_home_mount: bool


@dataclass(frozen=True)
class Task100SmokeSettings:
    """Normalized settings for the Task 100 smoke runner."""

    output_root: Path
    dockerfile_path: Path
    image: str
    model_id: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    build_image: bool


@dataclass(frozen=True)
class SmokeProbeResult:
    """Parsed JSON payload emitted by the in-container smoke probe."""

    model_id: str
    resolved_model_path: str
    resolved_config_path: str
    tts_model_type: str | None
    torch_version: str | None
    torchaudio_version: str | None
    torch_cuda_available: bool
    torch_cuda_device_count: int
    torch_hip_version: str | None
    flash_attn_importable: bool
    flash_attn_version: str | None
    flash_attn_model_load_ok: bool
    dependency_versions: dict[str, str | None]


def _optional_string(payload: dict[str, object], key: str) -> str | None:
    """Return one optional string field from a JSON object."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SystemExit(f"Task 100 smoke probe returned a malformed `{key}` value.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean field from a JSON object."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SystemExit(f"Task 100 smoke probe returned a malformed `{key}` value.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON object."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Task 100 smoke probe returned a malformed `{key}` value.")
    return value


def _parse_smoke_probe_payload(raw_output: str) -> dict[str, object]:
    """Extract one JSON object from mixed probe stdout."""
    decoder = JSONDecoder()
    for start_index, char in enumerate(raw_output):
        if char != "{":
            continue
        try:
            payload_obj, _ = decoder.raw_decode(raw_output[start_index:])
        except JSONDecodeError:
            continue
        if isinstance(payload_obj, dict):
            return payload_obj
    raise SystemExit(
        "Task 100 smoke probe did not emit a parseable JSON object. "
        f"Raw stdout was:\n{raw_output}"
    )


def run_checked(command: list[str], *, label: str) -> str:
    """Run one subprocess command and return stdout or raise with diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def docker_checked(args: list[str], *, label: str) -> str:
    """Run one Docker command through `sudo -n docker`."""
    return run_checked(["sudo", "-n", "docker", *args], label=label)


def _probe_docker_bind_mount(cache_dir: Path, *, image: str) -> bool:
    """Return whether Docker can bind-mount one host cache path on Hemma."""
    try:
        docker_checked(
            [
                "run",
                "--rm",
                "-v",
                f"{cache_dir.as_posix()}:/cache-probe",
                "--entrypoint",
                "python",
                image,
                "-c",
                (
                    "from pathlib import Path; "
                    "probe = Path('/cache-probe/.task100_probe'); "
                    "probe.write_text('ok', encoding='utf-8'); "
                    "print(probe.read_text(encoding='utf-8')); "
                    "probe.unlink()"
                ),
            ],
            label="docker run task100 cache probe",
        )
    except SystemExit:
        return False
    return True


def _best_effort_unmount(path: Path) -> None:
    """Unmount one previous home-backed bind mount when it exists."""
    subprocess.run(
        ["sudo", "-n", "umount", path.as_posix()],
        check=False,
        capture_output=True,
        text=True,
    )


def _is_srv_cache_path(cache_dir: Path) -> bool:
    """Return whether one cache path lives on Hemma's persistent data disk."""
    return str(cache_dir).startswith("/srv/")


def _sync_home_cache_into_data_disk(canonical_dir: Path, home_mount: Path) -> None:
    """Copy any existing home-backed cache files into the canonical cache root."""
    if not home_mount.exists():
        return
    for source in sorted(home_mount.iterdir()):
        target = canonical_dir / source.name
        if target.exists():
            continue
        if source.is_dir():
            subprocess.run(
                ["cp", "-a", source.as_posix(), target.as_posix()],
                check=True,
                capture_output=True,
                text=True,
            )
            continue
        target.write_bytes(source.read_bytes())


def _ensure_home_bind_mount(canonical_dir: Path, home_mount: Path) -> None:
    """Expose one canonical `/srv` cache root through a Docker-visible home path."""
    run_checked(
        ["sudo", "-n", "mkdir", "-p", canonical_dir.as_posix()],
        label="sudo mkdir task100 cache",
    )
    run_checked(["mkdir", "-p", home_mount.as_posix()], label="mkdir task100 home cache")
    _sync_home_cache_into_data_disk(canonical_dir, home_mount)
    _best_effort_unmount(home_mount)
    run_checked(
        [
            "sudo",
            "-n",
            "mount",
            "--bind",
            canonical_dir.as_posix(),
            home_mount.as_posix(),
        ],
        label="sudo mount --bind task100 cache",
    )


def resolve_effective_hf_cache_dir(settings: Task100SmokeSettings) -> MountResolution:
    """Return the Docker-mountable host cache path for Task 100 model assets."""
    settings.hf_cache_dir.mkdir(parents=True, exist_ok=True)
    if _probe_docker_bind_mount(settings.hf_cache_dir, image=settings.image):
        return MountResolution(
            canonical_root=settings.hf_cache_dir,
            effective_root=settings.hf_cache_dir,
            used_home_mount=False,
        )
    if _is_srv_cache_path(settings.hf_cache_dir):
        _ensure_home_bind_mount(settings.hf_cache_dir, settings.hf_cache_home_mount)
        if _probe_docker_bind_mount(settings.hf_cache_home_mount, image=settings.image):
            return MountResolution(
                canonical_root=settings.hf_cache_dir,
                effective_root=settings.hf_cache_home_mount,
                used_home_mount=True,
            )
    raise SystemExit(
        "Task 100 could not establish a Docker-mountable Hugging Face cache path on Hemma."
    )


def ensure_image_present(settings: Task100SmokeSettings) -> tuple[bool, str]:
    """Build the Task 100 image with BuildKit when needed and return its image id."""
    image_present = True
    try:
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect task100",
        )
    except SystemExit:
        image_present = False
        image_id = ""
    build_performed = settings.build_image or not image_present
    if build_performed:
        docker_checked(["buildx", "version"], label="docker buildx version task100")
        docker_checked(
            [
                "buildx",
                "build",
                "--load",
                "-t",
                settings.image,
                "-f",
                settings.dockerfile_path.resolve().as_posix(),
                ".",
            ],
            label="docker buildx build task100 image",
        )
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect task100 after build",
        )
    return build_performed, image_id.strip()


def build_smoke_probe_command(
    settings: Task100SmokeSettings,
    *,
    hf_mount: MountResolution,
) -> list[str]:
    """Build the Docker command that runs the in-container smoke probe."""
    return [
        "run",
        "--rm",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--ipc=host",
        "--cap-add=SYS_PTRACE",
        "--security-opt",
        "seccomp=unconfined",
        "-e",
        "HF_HUB_DISABLE_XET=1",
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-e",
        f"HUGGINGFACE_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
        "-e",
        f"TORCH_HOME={CONTAINER_TORCH_HOME}",
        "-e",
        f"SIR_QWEN_TRAINING_HF_CACHE_HOST_ROOT={hf_mount.canonical_root.as_posix()}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "--entrypoint",
        "python",
        settings.image,
        "-m",
        "scripts.sir_convert_a_lot.devops.task100_qwen_finetune_smoke_probe",
        "--model-id",
        settings.model_id,
    ]


def run_smoke_probe(
    settings: Task100SmokeSettings,
    *,
    hf_mount: MountResolution,
) -> tuple[SmokeProbeResult, list[str]]:
    """Run the in-container smoke probe and parse its JSON payload."""
    command = build_smoke_probe_command(settings, hf_mount=hf_mount)
    output = docker_checked(command, label="docker run task100 smoke probe")
    payload_raw = _parse_smoke_probe_payload(output)
    dependency_versions = payload_raw.get("dependency_versions")
    if not isinstance(dependency_versions, dict):
        raise SystemExit("Task 100 smoke probe did not include dependency_versions.")
    result = SmokeProbeResult(
        model_id=str(payload_raw.get("model_id", "")),
        resolved_model_path=str(payload_raw.get("resolved_model_path", "")),
        resolved_config_path=str(payload_raw.get("resolved_config_path", "")),
        tts_model_type=_optional_string(payload_raw, "tts_model_type"),
        torch_version=_optional_string(payload_raw, "torch_version"),
        torchaudio_version=_optional_string(payload_raw, "torchaudio_version"),
        torch_cuda_available=_required_bool(payload_raw, "torch_cuda_available"),
        torch_cuda_device_count=_required_int(payload_raw, "torch_cuda_device_count"),
        torch_hip_version=_optional_string(payload_raw, "torch_hip_version"),
        flash_attn_importable=_required_bool(payload_raw, "flash_attn_importable"),
        flash_attn_version=_optional_string(payload_raw, "flash_attn_version"),
        flash_attn_model_load_ok=_required_bool(payload_raw, "flash_attn_model_load_ok"),
        dependency_versions={
            str(key): (None if value is None else str(value))
            for key, value in dependency_versions.items()
        },
    )
    return result, ["sudo", "-n", "docker", *command]
