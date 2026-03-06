"""Runtime helpers for the Task 79 Hemma TTS sidecar benchmark.

Purpose:
    Keep the benchmark entrypoint small by isolating Docker, ROCm, readiness,
    and audio-probe operations needed to validate the sidecar on Hemma.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.run_task79_hemma_tts_sidecar_benchmark`.
    - Emits typed evidence objects from
      `scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_reporting`.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import subprocess
import textwrap
import threading
import time
import wave
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_reporting import (
    AudioProbeResult,
    GpuIdentity,
    PythonRecommendation,
    SidecarRuntime,
)

GPU_PRODUCT_RE = re.compile(r"Card\s+Series:\s*(.+)", re.IGNORECASE)
GPU_VRAM_TOTAL_RE = re.compile(r"VRAM Total Memory \(B\):\s*([0-9]+)")
GPU_VRAM_USED_RE = re.compile(r"VRAM Total Used Memory \(B\):\s*([0-9]+)")
GPU_BUSY_RE = re.compile(r"GPU use \(%\):\s*([0-9]+)")
GFX_ARCH_RE = re.compile(r"gfx[0-9]+")
CONTAINER_HF_HOME = "/cache/huggingface"
CONTAINER_HF_HUB_CACHE = f"{CONTAINER_HF_HOME}/hub"


@dataclass(frozen=True)
class BenchmarkSettings:
    """Normalized CLI settings for the Task 79 benchmark run."""

    output_root: Path
    image: str
    model: str
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
    hf_token: str | None
    pull_image: bool
    retain_container: bool
    stage_config_path: Path


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


def docker_checked(args: list[str], *, label: str) -> str:
    """Run one Docker command through `sudo -n docker`."""
    return run_checked(["sudo", "-n", "docker", *args], label=label)


def _probe_docker_bind_mount(cache_dir: Path, *, image: str) -> bool:
    """Return whether Docker can bind-mount the requested host cache path."""
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
                    "probe = Path('/cache-probe/.task79_probe'); "
                    "probe.write_text('ok', encoding='utf-8'); "
                    "print(probe.read_text(encoding='utf-8')); "
                    "probe.unlink()"
                ),
            ],
            label="docker run task79 hf cache probe",
        )
    except SystemExit:
        return False
    return True


def _best_effort_unmount(path: Path) -> None:
    """Unmount one path when a previous bind mount exists."""
    subprocess.run(
        ["sudo", "-n", "umount", path.as_posix()],
        check=False,
        capture_output=True,
        text=True,
    )


def _is_srv_cache_path(cache_dir: Path) -> bool:
    """Return whether one cache path is expected to live on Hemma's data disk."""
    return str(cache_dir).startswith("/srv/")


def _sync_home_cache_into_data_disk(canonical_dir: Path, home_mount: Path) -> None:
    """Migrate any existing home-backed cache files into the canonical data-disk path."""
    if not home_mount.exists():
        return
    for source in sorted(home_mount.iterdir()):
        target = canonical_dir / source.name
        if target.exists():
            continue
        if source.is_dir():
            subprocess.run(
                [
                    "cp",
                    "-a",
                    source.as_posix(),
                    target.as_posix(),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            target.write_bytes(source.read_bytes())


def _ensure_home_bind_mount(canonical_dir: Path, home_mount: Path) -> None:
    """Expose the canonical `/srv` cache through a `$HOME` path for Docker-restricted hosts."""
    run_checked(
        ["sudo", "-n", "mkdir", "-p", canonical_dir.as_posix()],
        label="sudo mkdir canonical hf cache",
    )
    run_checked(["mkdir", "-p", home_mount.as_posix()], label="mkdir hf cache home mount")
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
        label="sudo mount --bind hf cache",
    )


def resolve_effective_hf_cache_dir(settings: BenchmarkSettings) -> Path:
    """Return the host cache path Docker can mount without redownloading model weights."""
    settings.hf_cache_dir.mkdir(parents=True, exist_ok=True)
    if _probe_docker_bind_mount(settings.hf_cache_dir, image=settings.image):
        return settings.hf_cache_dir
    if _is_srv_cache_path(settings.hf_cache_dir):
        _ensure_home_bind_mount(settings.hf_cache_dir, settings.hf_cache_home_mount)
        if _probe_docker_bind_mount(settings.hf_cache_home_mount, image=settings.image):
            return settings.hf_cache_home_mount
    raise SystemExit(
        "Task 79 could not establish a Docker-mountable Hugging Face cache path on Hemma."
    )


def extract_gpu_identity(smi_output: str, rocminfo_output: str) -> GpuIdentity:
    """Parse product, architecture, and current GPU counters from ROCm tools."""
    product_match = GPU_PRODUCT_RE.search(smi_output)
    vram_total_match = GPU_VRAM_TOTAL_RE.search(smi_output)
    busy_values = [int(match.group(1)) for match in GPU_BUSY_RE.finditer(smi_output)]
    used_values = [int(match.group(1)) for match in GPU_VRAM_USED_RE.finditer(smi_output)]
    arch_match = GFX_ARCH_RE.search(rocminfo_output) or GFX_ARCH_RE.search(smi_output)
    if product_match is None or vram_total_match is None or arch_match is None:
        raise SystemExit("Unable to parse Hemma GPU identity from rocm-smi/rocminfo output.")
    return GpuIdentity(
        product_name=product_match.group(1).strip(),
        gfx_architecture=arch_match.group(0),
        vram_total_bytes=int(vram_total_match.group(1)),
        peak_gpu_busy_percent=max(busy_values, default=0),
        peak_vram_used_bytes=max(used_values, default=0),
    )


def voice_names_from_payload(payload: object) -> list[str]:
    """Normalize a voices endpoint payload into a stable list of voice names."""
    candidates: object = payload
    if isinstance(payload, dict):
        if isinstance(payload.get("voices"), list):
            candidates = payload["voices"]
        elif isinstance(payload.get("data"), list):
            candidates = payload["data"]
    if not isinstance(candidates, list):
        raise SystemExit("Unexpected `/v1/audio/voices` payload shape.")
    names: list[str] = []
    for entry in candidates:
        if isinstance(entry, str):
            names.append(entry)
        elif isinstance(entry, dict):
            name_obj = entry.get("name") or entry.get("voice")
            if isinstance(name_obj, str) and name_obj.strip() != "":
                names.append(name_obj)
    if not names:
        raise SystemExit("No voice names were parsed from `/v1/audio/voices`.")
    return sorted(dict.fromkeys(names))


def python_recommendation(python_version: str) -> PythonRecommendation:
    """Translate the observed Python runtime into a Task 79 recommendation."""
    minor = ".".join(python_version.split(".")[:2])
    return PythonRecommendation(
        highest_proven_version=python_version,
        recommended_minor=minor,
        python_3_14_supported=minor == "3.14",
        rationale=(
            f"Live sidecar startup and audio synthesis succeeded on Python {python_version}. "
            "Until the same benchmark succeeds on a newer minor, standardize on the highest "
            "live-proven Python version rather than assuming 3.14 support."
        ),
    )


class _GpuSampler:
    """Collect peak GPU busy and VRAM-used counters during one audio request."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self.peak_gpu_busy_percent = 0
        self.peak_vram_used_bytes = 0

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> tuple[int, int]:
        self._stop.set()
        self._thread.join(timeout=5.0)
        return self.peak_gpu_busy_percent, self.peak_vram_used_bytes

    def _run(self) -> None:
        while not self._stop.is_set():
            with suppress(SystemExit):
                smi_output = run_checked(
                    ["rocm-smi", "--showuse", "--showmeminfo", "vram"],
                    label="rocm-smi sample",
                )
                self.peak_gpu_busy_percent = max(
                    self.peak_gpu_busy_percent,
                    max(
                        (int(match.group(1)) for match in GPU_BUSY_RE.finditer(smi_output)),
                        default=0,
                    ),
                )
                self.peak_vram_used_bytes = max(
                    self.peak_vram_used_bytes,
                    max(
                        (int(match.group(1)) for match in GPU_VRAM_USED_RE.finditer(smi_output)),
                        default=0,
                    ),
                )
            self._stop.wait(0.5)


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


def _wav_metadata(audio_bytes: bytes) -> tuple[int, float]:
    """Extract WAV sample-rate and duration from response bytes."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
    duration_seconds = frame_count / float(frame_rate)
    return frame_rate, round(duration_seconds, 6)


def ensure_sidecar_preconditions(settings: BenchmarkSettings) -> None:
    """Fail early if the expected Docker network and service container are missing."""
    if not settings.stage_config_path.resolve().exists():
        raise SystemExit(f"Task 79 stage config is missing: {settings.stage_config_path}")
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
        docker_checked(["pull", settings.image], label="docker pull task79 image")
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
            "VLLM_USE_TRITON_FLASH_ATTN=0",
            "-v",
            f"{settings.hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}",
            "--entrypoint",
            "python",
            settings.image,
            "-c",
            prefetch_script,
        ],
        label="docker run task79 tokenizer prefetch",
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
        "VLLM_USE_TRITON_FLASH_ATTN=0",
        "-v",
        f"{settings.hf_cache_dir.as_posix()}:{CONTAINER_HF_HOME}",
        "-v",
        f"{settings.stage_config_path.resolve().as_posix()}:/workspace/task79_stage_config.yaml:ro",
    ]
    if settings.hf_token:
        run_args.extend(["-e", f"HF_TOKEN={settings.hf_token}"])
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
            "/workspace/task79_stage_config.yaml",
        ]
    )
    docker_checked(run_args, label="docker run task79 sidecar")


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
        f"Timed out waiting for Task 79 sidecar readiness after "
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
            (
                "import importlib.metadata as md, json, os, sys; "
                "versions = {}; "
                "targets = ('vllm', 'vllm-omni', 'vllm_omni'); "
                "for name in targets:\n"
                "    try:\n"
                "        versions[name] = md.version(name)\n"
                "    except md.PackageNotFoundError:\n"
                "        versions[name] = None\n"
                "print(json.dumps({"
                "'python_version': sys.version.split()[0], "
                "'package_versions': versions, "
                "'hf_home': os.environ.get('HF_HOME'), "
                "'hf_hub_cache': os.environ.get('HF_HUB_CACHE'), "
                "'transformers_cache': os.environ.get('TRANSFORMERS_CACHE')"
                "}, sort_keys=True))"
            ),
        ],
        label="docker exec metadata probe",
    )
    payload_obj = json.loads(metadata_output)
    if not isinstance(payload_obj, dict):
        raise SystemExit("Task 79 sidecar metadata probe returned an unexpected payload.")
    python_version_obj = payload_obj.get("python_version")
    package_versions_obj = payload_obj.get("package_versions")
    hf_home_obj = payload_obj.get("hf_home")
    hf_hub_cache_obj = payload_obj.get("hf_hub_cache")
    transformers_cache_obj = payload_obj.get("transformers_cache")
    if not isinstance(python_version_obj, str) or not isinstance(package_versions_obj, dict):
        raise SystemExit("Task 79 sidecar metadata probe payload is malformed.")
    if hf_home_obj is not None and not isinstance(hf_home_obj, str):
        raise SystemExit("Task 79 sidecar metadata probe returned a malformed HF_HOME value.")
    if hf_hub_cache_obj is not None and not isinstance(hf_hub_cache_obj, str):
        raise SystemExit("Task 79 sidecar metadata probe returned a malformed HF_HUB_CACHE value.")
    if transformers_cache_obj is not None and not isinstance(transformers_cache_obj, str):
        raise SystemExit(
            "Task 79 sidecar metadata probe returned a malformed TRANSFORMERS_CACHE value."
        )
    package_versions: dict[str, str | None] = {}
    for key, value in package_versions_obj.items():
        if isinstance(key, str) and (isinstance(value, str) or value is None):
            package_versions[key] = value
    return SidecarRuntime(
        image=settings.image,
        image_id=image_id,
        container_name=settings.container_name,
        python_version=python_version_obj,
        package_versions=package_versions,
        stage_config_path="/workspace/task79_stage_config.yaml",
        hf_home=hf_home_obj,
        hf_hub_cache=hf_hub_cache_obj,
        transformers_cache=transformers_cache_obj,
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


def audio_probe(
    *,
    settings: BenchmarkSettings,
    base_url: str,
    response_format: str,
    artifacts_dir: Path,
) -> tuple[AudioProbeResult, int, int]:
    """Call `/v1/audio/speech` for one response format and persist the artifact."""
    payload = {
        "model": settings.model,
        "input": settings.probe_text,
        "voice": settings.voice,
        "response_format": response_format,
    }
    output_path = artifacts_dir / f"sample.{response_format}"
    sampler = _GpuSampler()
    sampler.start()
    started = time.monotonic()
    with httpx.Client(timeout=600.0) as client:
        response = client.post(f"{base_url}/v1/audio/speech", json=payload)
    elapsed_seconds = round(time.monotonic() - started, 3)
    peak_gpu_busy_percent, peak_vram_used_bytes = sampler.stop()

    content_type = response.headers.get("content-type")
    if response.is_success:
        audio_bytes = response.content
        output_path.write_bytes(audio_bytes)
        sha256_value = hashlib.sha256(audio_bytes).hexdigest()
        sample_rate_hz: int | None = None
        duration_seconds: float | None = None
        if response_format == "wav":
            sample_rate_hz, duration_seconds = _wav_metadata(audio_bytes)
        return (
            AudioProbeResult(
                response_format=response_format,
                ok=True,
                status_code=response.status_code,
                content_type=content_type,
                byte_count=len(audio_bytes),
                sha256=sha256_value,
                output_path=output_path.as_posix(),
                elapsed_seconds=elapsed_seconds,
                sample_rate_hz=sample_rate_hz,
                duration_seconds=duration_seconds,
                error_message=None,
            ),
            peak_gpu_busy_percent,
            peak_vram_used_bytes,
        )

    error_path = artifacts_dir / f"sample.{response_format}.error.txt"
    error_text = response.text.strip()
    error_path.write_text(error_text + "\n", encoding="utf-8")
    return (
        AudioProbeResult(
            response_format=response_format,
            ok=False,
            status_code=response.status_code,
            content_type=content_type,
            byte_count=0,
            sha256=None,
            output_path=None,
            elapsed_seconds=elapsed_seconds,
            sample_rate_hz=None,
            duration_seconds=None,
            error_message=error_text,
        ),
        peak_gpu_busy_percent,
        peak_vram_used_bytes,
    )
