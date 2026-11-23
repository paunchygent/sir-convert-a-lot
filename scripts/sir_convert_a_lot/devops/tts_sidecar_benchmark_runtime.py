"""Docker launch and readiness runtime for the Hemma TTS sidecar benchmark.

Purpose:
    Keep the benchmark entrypoint small by isolating the Docker container
    launch, readiness, and in-container inspection operations needed to
    validate the sidecar on Hemma.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.run_tts_sidecar_hemma_benchmark`.
    - Cache, measurement, and audio-probe operations live in
      `scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_probes`.
    - Emits typed evidence objects from
      `scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_reporting`.
"""

from __future__ import annotations

import json
import subprocess
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_reporting import (
    SidecarRuntime,
)

CONTAINER_HF_HOME = "/cache/huggingface"
CONTAINER_HF_HUB_CACHE = f"{CONTAINER_HF_HOME}/hub"


@dataclass(frozen=True)
class BenchmarkSettings:
    """Normalized CLI settings for the TTS sidecar benchmark run."""

    output_root: Path
    image: str
    model: str
    task_type: str
    language: str
    tokenizer_model: str
    hf_cache_home_mount: Path
    network: str
    network_alias: str
    container_name: str
    service_container: str
    container_port: int
    host_port: int
    voice: str
    response_formats: tuple[str, ...]
    startup_timeout_seconds: float
    hf_cache_dir: Path
    probe_text: str
    instructions: str | None
    reference_audio: Path | None
    reference_transcript: str | None
    hf_token_present: bool
    pull_image: bool
    retain_container: bool
    stage_config_path: Path
    use_triton_flash_attn: bool


def run_checked(command: list[str], *, label: str) -> str:
    """Run a subprocess command and return stdout or raise with diagnostics."""
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"{label} failed (exit={result.returncode}).\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def docker_checked(
    args: list[str],
    *,
    label: str,
    preserve_env: tuple[str, ...] = (),
) -> str:
    """Run one Docker command through `sudo -n docker`.

    `preserve_env` carries the named environment variables across the sudo
    boundary so Docker `-e NAME` lookups still resolve; values never appear
    on the command line.
    """
    command = ["sudo", "-n"]
    if preserve_env:
        command.append(f"--preserve-env={','.join(preserve_env)}")
    command.extend(["docker", *args])
    return run_checked(command, label=label)


def _build_service_probe_python(base_url: str) -> str:
    """Return the Python one-liner used inside the service container."""
    return (
        "import json, urllib.request; "
        f"response = urllib.request.urlopen('{base_url}/v1/audio/voices', timeout=30); "
        "payload=json.loads(response.read().decode('utf-8')); "
        "voices = payload.get('voices', payload.get('data', payload)) if "
        "isinstance(payload, dict) else payload; "
        "count = len(voices) if isinstance(voices, list) else 0; "
        "print(json.dumps({'count': count, 'payload': payload}, sort_keys=True))"
    )


def _build_runtime_metadata_probe_python() -> str:
    """Return the Python snippet used to inspect versions and cache env vars in-container."""
    return textwrap.dedent(
        """
        import importlib.metadata as md
        import json
        import os
        import sys

        def version_or_none(name: str) -> str | None:
            try:
                return md.version(name)
            except md.PackageNotFoundError:
                return None

        targets = ("vllm", "vllm-omni", "vllm_omni")
        payload = {
            "python_version": sys.version.split()[0],
            "package_versions": {name: version_or_none(name) for name in targets},
            "hf_home": os.environ.get("HF_HOME"),
            "hf_hub_cache": os.environ.get("HF_HUB_CACHE"),
            "transformers_cache": os.environ.get("TRANSFORMERS_CACHE"),
            "vllm_use_triton_flash_attn": os.environ.get("VLLM_USE_TRITON_FLASH_ATTN"),
        }
        print(json.dumps(payload, sort_keys=True))
        """
    ).strip()


def _vllm_use_triton_flash_attn_env(settings: BenchmarkSettings) -> str:
    """Return the explicit Triton flash-attention environment assignment."""
    return f"VLLM_USE_TRITON_FLASH_ATTN={'1' if settings.use_triton_flash_attn else '0'}"


def ensure_sidecar_preconditions(settings: BenchmarkSettings) -> None:
    """Fail early if the expected Docker network and service container are missing."""
    if not settings.stage_config_path.resolve().exists():
        raise SystemExit(
            f"TTS sidecar benchmark stage config is missing: {settings.stage_config_path}"
        )
    docker_checked(["network", "inspect", settings.network], label="docker network inspect")
    running = docker_checked(["ps", "--format", "{{.Names}}"], label="docker ps").splitlines()
    if settings.service_container not in running:
        raise SystemExit(
            f"Expected service container `{settings.service_container}` to be running on Hemma."
        )


def remove_existing_benchmark_container(container_name: str) -> None:
    """Remove a stale benchmark container if one already exists."""
    existing = docker_checked(
        ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
        label="docker ps -a",
    )
    if existing.strip() == container_name:
        docker_checked(["rm", "-f", container_name], label="docker rm -f stale benchmark")


def ensure_image_present(settings: BenchmarkSettings) -> tuple[bool, str]:
    """Pull the benchmark image when requested and return the resolved image id."""
    image_present = True
    try:
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect",
        )
    except SystemExit:
        image_present = False
        image_id = ""
    pull_performed = settings.pull_image or not image_present
    if pull_performed:
        docker_checked(["pull", settings.image], label="docker pull tts-sidecar image")
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect after pull",
        )
    return pull_performed, image_id.strip()


def prefetch_qwen3_tts_assets(settings: BenchmarkSettings) -> None:
    """Prime the shared cache with tokenizer assets expected by stage-1 startup."""
    main_model_cache_key = settings.model.replace("/", "--")
    tokenizer_cache_key = settings.tokenizer_model.replace("/", "--")
    prefetch_script = textwrap.dedent(
        f"""
        from pathlib import Path
        import json
        import shutil

        from huggingface_hub import snapshot_download

        cache_dir = Path({CONTAINER_HF_HOME!r})
        model_id = {settings.model!r}
        tokenizer_id = {settings.tokenizer_model!r}
        model_snapshot = Path(snapshot_download(model_id, cache_dir=str(cache_dir)))
        tokenizer_snapshot = Path(snapshot_download(tokenizer_id, cache_dir=str(cache_dir)))
        copied_targets = []
        for prefix in (cache_dir, cache_dir / "hub"):
            snapshots_root = prefix / {("models--" + main_model_cache_key)!r} / "snapshots"
            if not snapshots_root.exists():
                continue
            for snapshot_dir in sorted(path for path in snapshots_root.iterdir() if path.is_dir()):
                speech_dir = snapshot_dir / "speech_tokenizer"
                speech_dir.mkdir(parents=True, exist_ok=True)
                for source in sorted(tokenizer_snapshot.iterdir()):
                    target = speech_dir / source.name
                    if target.exists():
                        continue
                    if source.is_dir():
                        shutil.copytree(source, target, dirs_exist_ok=True)
                    else:
                        shutil.copy2(source, target)
                copied_targets.append(str(speech_dir))
        print(
            json.dumps(
                {{
                    "model_snapshot": str(model_snapshot),
                    "tokenizer_snapshot": str(tokenizer_snapshot),
                    "copied_targets": copied_targets,
                    "tokenizer_cache_key": {tokenizer_cache_key!r},
                }},
                sort_keys=True,
            )
        )
        """
    ).strip()
    docker_checked(
        [
            "run",
            "--rm",
            "-e",
            f"HF_HOME={CONTAINER_HF_HOME}",
            "-e",
            f"HF_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
            "-e",
            f"TRANSFORMERS_CACHE={CONTAINER_HF_HOME}",
            "-e",
            _vllm_use_triton_flash_attn_env(settings),
            "-v",
            f"{settings.hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}",
            "--entrypoint",
            "python",
            settings.image,
            "-c",
            prefetch_script,
        ],
        label="docker run tts-sidecar tokenizer prefetch",
    )


def start_sidecar(settings: BenchmarkSettings) -> None:
    """Launch the benchmark sidecar container with the committed stage config."""
    run_args = [
        "run",
        "-d",
        "--name",
        settings.container_name,
        "--network",
        settings.network,
        "--network-alias",
        settings.network_alias,
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
        "-p",
        f"127.0.0.1:{settings.host_port}:{settings.container_port}",
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-e",
        f"HF_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
        "-e",
        f"TRANSFORMERS_CACHE={CONTAINER_HF_HOME}",
        "-e",
        _vllm_use_triton_flash_attn_env(settings),
        "-v",
        f"{settings.hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}",
        "-v",
        f"{settings.stage_config_path.resolve().as_posix()}:/workspace/tts-sidecar-stage-config.yaml:ro",
    ]
    if settings.hf_token_present:
        run_args.extend(["-e", "HF_TOKEN"])
    run_args.extend(
        [
            "--entrypoint",
            "vllm",
            settings.image,
            "serve",
            settings.model,
            "--port",
            str(settings.container_port),
            "--host",
            "0.0.0.0",
            "--omni",
            "--enforce-eager",
            "--trust-remote-code",
            "--stage-configs-path",
            "/workspace/tts-sidecar-stage-config.yaml",
        ]
    )
    docker_checked(
        run_args,
        label="docker run tts-sidecar sidecar",
        preserve_env=("HF_TOKEN",) if settings.hf_token_present else (),
    )


def wait_for_voices(settings: BenchmarkSettings) -> tuple[float, object]:
    """Poll the host-bound voices endpoint until it becomes ready."""
    base_url = f"http://127.0.0.1:{settings.host_port}"
    deadline = time.monotonic() + settings.startup_timeout_seconds
    last_error = "sidecar not yet ready"
    with httpx.Client(timeout=30.0) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(f"{base_url}/v1/audio/voices")
                response.raise_for_status()
                payload: object = response.json()
                readiness_seconds = round(
                    settings.startup_timeout_seconds - (deadline - time.monotonic()),
                    3,
                )
                return readiness_seconds, payload
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)
                time.sleep(5.0)
    raise SystemExit(
        f"Timed out waiting for TTS sidecar benchmark sidecar readiness after "
        f"{settings.startup_timeout_seconds} seconds: {last_error}"
    )


def inspect_runtime(settings: BenchmarkSettings, image_id: str) -> SidecarRuntime:
    """Read Python and package versions from inside the sidecar container."""
    metadata_output = docker_checked(
        [
            "exec",
            settings.container_name,
            "python",
            "-c",
            _build_runtime_metadata_probe_python(),
        ],
        label="docker exec metadata probe",
    )
    payload_obj = json.loads(metadata_output)
    if not isinstance(payload_obj, dict):
        raise SystemExit(
            "TTS sidecar benchmark sidecar metadata probe returned an unexpected payload."
        )
    python_version_obj = payload_obj.get("python_version")
    package_versions_obj = payload_obj.get("package_versions")
    hf_home_obj = payload_obj.get("hf_home")
    hf_hub_cache_obj = payload_obj.get("hf_hub_cache")
    transformers_cache_obj = payload_obj.get("transformers_cache")
    triton_flash_attn_obj = payload_obj.get("vllm_use_triton_flash_attn")
    if not isinstance(python_version_obj, str) or not isinstance(package_versions_obj, dict):
        raise SystemExit("TTS sidecar benchmark sidecar metadata probe payload is malformed.")
    if hf_home_obj is not None and not isinstance(hf_home_obj, str):
        raise SystemExit(
            "TTS sidecar benchmark sidecar metadata probe returned a malformed HF_HOME value."
        )
    if hf_hub_cache_obj is not None and not isinstance(hf_hub_cache_obj, str):
        raise SystemExit("TTS sidecar metadata probe returned a malformed HF_HUB_CACHE value.")
    if transformers_cache_obj is not None and not isinstance(transformers_cache_obj, str):
        raise SystemExit(
            "TTS sidecar metadata probe returned a malformed TRANSFORMERS_CACHE value."
        )
    if triton_flash_attn_obj is not None and not isinstance(triton_flash_attn_obj, str):
        raise SystemExit(
            "TTS sidecar metadata probe returned a malformed Triton flash-attention value."
        )
    package_versions: dict[str, str | None] = {}
    for key, value in package_versions_obj.items():
        if isinstance(key, str) and (isinstance(value, str) or value is None):
            package_versions[key] = value
    if triton_flash_attn_obj is None:
        triton_flash_attn_enabled: bool | None = None
    elif triton_flash_attn_obj == "1":
        triton_flash_attn_enabled = True
    elif triton_flash_attn_obj == "0":
        triton_flash_attn_enabled = False
    else:
        raise SystemExit(
            "TTS sidecar metadata probe returned an unexpected Triton flash-attention value."
        )
    return SidecarRuntime(
        image=settings.image,
        image_id=image_id,
        container_name=settings.container_name,
        python_version=python_version_obj,
        package_versions=package_versions,
        stage_config_path="/workspace/tts-sidecar-stage-config.yaml",
        hf_home=hf_home_obj,
        hf_hub_cache=hf_hub_cache_obj,
        transformers_cache=transformers_cache_obj,
        triton_flash_attn_enabled=triton_flash_attn_enabled,
    )


def probe_from_service_container(settings: BenchmarkSettings) -> tuple[bool, int]:
    """Verify the sidecar is reachable from the canonical service container."""
    internal_url = f"http://{settings.network_alias}:{settings.container_port}"
    probe_output = docker_checked(
        [
            "exec",
            settings.service_container,
            "python",
            "-c",
            _build_service_probe_python(internal_url),
        ],
        label="docker exec service-container voices probe",
    )
    payload_obj = json.loads(probe_output)
    if not isinstance(payload_obj, dict):
        raise SystemExit("Service-container probe payload is malformed.")
    count_obj = payload_obj.get("count")
    if not isinstance(count_obj, int):
        raise SystemExit("Service-container probe did not return a voice count.")
    return True, count_obj
