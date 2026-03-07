"""Runtime helpers for the Task 86 Hemma Chatterbox benchmark.

Purpose:
    Keep Docker, cache, readiness, GPU sampling, and synthesis-probe logic
    separate from the Task 86 orchestration script.

Relationships:
    - Consumed by `run_task86_hemma_chatterbox_benchmark`.
    - Uses the normalized ADR-0007 sidecar contract models.
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import re
import textwrap
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.task81_openvoice_runtime import (
    MountResolution,
    docker_checked,
    run_checked,
)
from scripts.sir_convert_a_lot.devops.task86_chatterbox_reporting import ProbeResult
from scripts.sir_convert_a_lot.tts_sidecar.contracts import CapabilityResponse, VoicesResponse

LOGGER = logging.getLogger(__name__)
_MODEL_CACHE_PATTERNS = (
    "models--ResembleAI--chatterbox/snapshots/*",
    "hub/models--ResembleAI--chatterbox/snapshots/*",
)
_GPU_BUSY_RE = re.compile(r"GPU use \(%\):\s*([0-9]+)")
_GPU_VRAM_USED_RE = re.compile(r"VRAM Total Used Memory \(B\):\s*([0-9]+)")


@dataclass(frozen=True)
class BenchmarkSettings:
    """Normalized CLI settings for the Task 86 benchmark run."""

    output_root: Path
    dockerfile_path: Path
    image: str
    network: str
    network_alias: str
    container_name: str
    service_container: str
    container_port: int
    host_port: int
    startup_timeout_seconds: float
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    reference_audio_path: Path
    english_reference_audio_path: Path | None
    smoke_text: str
    probe_text: str
    exaggeration: float
    cfg_weight: float
    build_image: bool
    retain_container: bool


class _GpuSampler:
    """Collect peak GPU busy and VRAM-used counters during one synthesis request."""

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
            try:
                smi_output = run_checked(
                    ["rocm-smi", "--showuse", "--showmeminfo", "vram"],
                    label="rocm-smi sample",
                )
                self.peak_gpu_busy_percent = max(
                    self.peak_gpu_busy_percent,
                    max(
                        (int(match.group(1)) for match in _GPU_BUSY_RE.finditer(smi_output)),
                        default=0,
                    ),
                )
                self.peak_vram_used_bytes = max(
                    self.peak_vram_used_bytes,
                    max(
                        (int(match.group(1)) for match in _GPU_VRAM_USED_RE.finditer(smi_output)),
                        default=0,
                    ),
                )
            except SystemExit:
                pass
            time.sleep(0.5)


def ensure_image_present(settings: BenchmarkSettings) -> tuple[bool, str]:
    """Build the Task 86 sidecar image with BuildKit and return the image id."""
    image_present = True
    try:
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect",
        )
    except SystemExit:
        image_present = False
        image_id = ""
    build_performed = settings.build_image or not image_present
    if build_performed:
        docker_checked(["buildx", "version"], label="docker buildx version")
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
            label="docker buildx build task86 image",
        )
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect after build",
        )
    return build_performed, image_id.strip()


def discover_model_snapshot_path(cache_root: Path) -> Path | None:
    """Return the first discovered Chatterbox model snapshot under the host cache root."""
    for pattern in _MODEL_CACHE_PATTERNS:
        matches = sorted(cache_root.glob(pattern))
        if matches:
            return matches[0]
    return None


def start_sidecar(settings: BenchmarkSettings, *, hf_mount: MountResolution) -> None:
    """Launch the Task 86 sidecar container on the internal Hemma Docker network."""
    docker_checked(
        [
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
            "--ipc=host",
            "--cap-add=SYS_PTRACE",
            "--security-opt",
            "seccomp=unconfined",
            "-p",
            f"127.0.0.1:{settings.host_port}:{settings.container_port}",
            "-e",
            "HF_HUB_DISABLE_XET=1",
            "-e",
            "HF_HOME=/cache/huggingface",
            "-e",
            "HUGGINGFACE_HUB_CACHE=/cache/huggingface",
            "-e",
            "TRANSFORMERS_CACHE=/cache/huggingface",
            "-e",
            "TORCH_HOME=/cache/huggingface/torch",
            "-e",
            "SIR_TTS_SIDECAR_BACKEND_ID=chatterbox_multilingual",
            "-e",
            "SIR_TTS_SIDECAR_BACKEND_VERSION=0.1.6",
            "-e",
            "SIR_TTS_SIDECAR_BACKEND_PROFILE=official_multilingual_0p5b",
            "-e",
            "SIR_TTS_SIDECAR_GPU_REQUIRED=1",
            "-e",
            "SIR_TTS_SIDECAR_MODEL_REPO_ID=ResembleAI/chatterbox",
            "-e",
            f"SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT={hf_mount.canonical_root.as_posix()}",
            "-e",
            "SIR_TTS_SIDECAR_HF_CACHE_CONTAINER_ROOT=/cache/huggingface",
            "-e",
            f"SIR_TTS_SIDECAR_CHATTERBOX_EXAGGERATION={settings.exaggeration}",
            "-e",
            f"SIR_TTS_SIDECAR_CHATTERBOX_CFG_WEIGHT={settings.cfg_weight}",
            "-v",
            f"{hf_mount.effective_root.as_posix()}:/cache/huggingface",
            settings.image,
        ],
        label="docker run task86 sidecar",
    )


def wait_for_sidecar(
    settings: BenchmarkSettings,
) -> tuple[float, CapabilityResponse, VoicesResponse]:
    """Poll health, capabilities, and voices until the sidecar is ready."""
    base_url = f"http://127.0.0.1:{settings.host_port}"
    deadline = time.monotonic() + settings.startup_timeout_seconds
    last_error = "sidecar not yet ready"
    with httpx.Client(timeout=30.0) as client:
        while time.monotonic() < deadline:
            try:
                health_response = client.get(f"{base_url}/health")
                health_response.raise_for_status()
                health_payload = health_response.json()
                if health_payload.get("ready") is not True:
                    last_error = json.dumps(health_payload, sort_keys=True)
                    time.sleep(3.0)
                    continue
                capabilities_response = client.get(f"{base_url}/capabilities")
                capabilities_response.raise_for_status()
                voices_response = client.get(f"{base_url}/voices")
                voices_response.raise_for_status()
                readiness_seconds = round(
                    settings.startup_timeout_seconds - (deadline - time.monotonic()),
                    3,
                )
                return (
                    readiness_seconds,
                    CapabilityResponse.model_validate(capabilities_response.json()),
                    VoicesResponse.model_validate(voices_response.json()),
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)
                time.sleep(3.0)
    raise SystemExit(
        f"Timed out waiting for Task 86 sidecar readiness after "
        f"{settings.startup_timeout_seconds} seconds: {last_error}"
    )


def probe_from_service_container(settings: BenchmarkSettings) -> tuple[bool, str, bool]:
    """Verify that the sidecar remains reachable from the Sir service container."""
    internal_url = f"http://{settings.network_alias}:{settings.container_port}"
    probe_output = docker_checked(
        [
            "exec",
            settings.service_container,
            "python",
            "-c",
            textwrap.dedent(
                f"""
                import json
                import urllib.request

                with urllib.request.urlopen("{internal_url}/health", timeout=30) as response:
                    payload = json.load(response)
                print(json.dumps(payload))
                """
            ).strip(),
        ],
        label="docker exec service-container task86 health probe",
    )
    payload = json.loads(probe_output)
    return True, str(payload["backend_id"]), bool(payload["ready"])


def write_runtime_versions(settings: BenchmarkSettings, *, output_path: Path) -> None:
    """Persist installed package versions from inside the running sidecar."""
    output = docker_checked(
        [
            "exec",
            settings.container_name,
            "python",
            "-c",
            (
                "import json; "
                "from importlib import metadata; "
                "packages=('chatterbox-tts','torch','torchaudio','transformers','diffusers'); "
                "payload={name: metadata.version(name) for name in packages}; "
                "print(json.dumps(payload, sort_keys=True))"
            ),
        ],
        label="docker exec task86 package versions",
    )
    payload = json.loads(output)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def capture_gpu_snapshot(output_path: Path) -> None:
    """Persist one ROCm GPU snapshot to disk."""
    output = run_checked(
        ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showuse"],
        label="rocm-smi snapshot",
    )
    output_path.write_text(output + "\n", encoding="utf-8")


def synthesize_probe(
    *,
    base_url: str,
    artifacts_dir: Path,
    filename: str,
    text: str,
    language: str,
    voice_mode: str,
    preset_voice_id: str | None,
    reference_audio_path: Path | None,
) -> ProbeResult:
    """Call the normalized `/synthesize` endpoint and persist one artifact."""
    output_path = artifacts_dir / filename
    data: dict[str, str] = {
        "text": text,
        "language": language,
        "voice_mode": voice_mode,
        "output_format": "wav",
        "normalization_profile": "auto",
    }
    if preset_voice_id is not None:
        data["preset_voice_id"] = preset_voice_id
    files: dict[str, tuple[str, bytes, str]] = {}
    if reference_audio_path is not None:
        mime_type = mimetypes.guess_type(reference_audio_path.name)[0] or "application/octet-stream"
        files["reference_audio"] = (
            reference_audio_path.name,
            reference_audio_path.read_bytes(),
            mime_type,
        )
    sampler = _GpuSampler()
    started = time.monotonic()
    sampler.start()
    try:
        with httpx.Client(timeout=900.0) as client:
            response = client.post(f"{base_url}/synthesize", data=data, files=files or None)
    finally:
        peak_gpu_busy_percent, peak_vram_used_bytes = sampler.stop()
    if not response.is_success:
        raise SystemExit(
            "Task 86 synthesis failed.\n"
            f"status={response.status_code}\n"
            f"content-type={response.headers.get('content-type')}\n"
            f"body={response.text.strip()}"
        )
    output_path.write_bytes(response.content)
    return ProbeResult(
        ok=True,
        output_path=output_path.as_posix(),
        sha256=hashlib.sha256(response.content).hexdigest(),
        content_type=response.headers.get("content-type"),
        duration_seconds=round(time.monotonic() - started, 3),
        peak_gpu_busy_percent=peak_gpu_busy_percent,
        peak_vram_used_bytes=peak_vram_used_bytes,
    )


def restart_sidecar_and_measure(settings: BenchmarkSettings) -> float:
    """Restart the existing sidecar container and return the warm readiness time."""
    docker_checked(["stop", settings.container_name], label="docker stop task86")
    docker_checked(["start", settings.container_name], label="docker start task86")
    readiness_seconds, _, _ = wait_for_sidecar(settings)
    return readiness_seconds
