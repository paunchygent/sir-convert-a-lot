"""Runtime helpers for the Task 81 Hemma OpenVoice sidecar benchmark.

Purpose:
    Keep the Task 81 benchmark runner small by isolating Docker, cache,
    readiness, runtime-inspection, and synthesis-probe behavior needed to
    evaluate the OpenVoice V2 adapter on Hemma.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.run_task81_hemma_openvoice_benchmark`.
    - Targets the normalized sidecar contract implemented by
      `scripts.sir_convert_a_lot.tts_sidecar.openvoice_app`.
"""

from __future__ import annotations

import hashlib
import io
import json
import mimetypes
import re
import shutil
import subprocess
import textwrap
import threading
import time
import urllib.request
import wave
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import httpx
from huggingface_hub import snapshot_download

from scripts.sir_convert_a_lot.devops.task81_openvoice_reporting import (
    InternalProbeEvidence,
    ReferenceAudioEvidence,
    SidecarRuntime,
    SynthesisProbeResult,
)
from scripts.sir_convert_a_lot.tts_sidecar.contracts import CapabilityResponse

GPU_PRODUCT_RE = re.compile(r"Card\s+Series:\s*(.+)", re.IGNORECASE)
GPU_VRAM_TOTAL_RE = re.compile(r"VRAM Total Memory \(B\):\s*([0-9]+)")
GPU_VRAM_USED_RE = re.compile(r"VRAM Total Used Memory \(B\):\s*([0-9]+)")
GPU_BUSY_RE = re.compile(r"GPU use \(%\):\s*([0-9]+)")
GFX_ARCH_RE = re.compile(r"gfx[0-9]+")
CONTAINER_HF_HOME = "/cache/huggingface"
CONTAINER_HF_HUB_CACHE = f"{CONTAINER_HF_HOME}/hub"
CONTAINER_OPENVOICE_HOME = "/cache/openvoice"


@dataclass(frozen=True)
class BenchmarkSettings:
    """Normalized CLI settings for the Task 81 benchmark run."""

    output_root: Path
    dockerfile_path: Path
    image: str
    openvoice_checkpoint_url: str
    base_model_id: str
    network: str
    network_alias: str
    container_name: str
    service_container: str
    container_port: int
    host_port: int
    startup_timeout_seconds: float
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    openvoice_cache_dir: Path
    openvoice_cache_home_mount: Path
    reference_audio_path: Path
    probe_text: str
    build_image: bool
    retain_container: bool


@dataclass(frozen=True)
class MountResolution:
    """Resolved host path used for one Docker-visible persistent cache."""

    canonical_root: Path
    effective_root: Path
    used_home_mount: bool


@dataclass(frozen=True)
class GpuIdentity:
    """Parsed GPU identity and current peak counters."""

    product_name: str
    gfx_architecture: str
    vram_total_bytes: int
    peak_gpu_busy_percent: int
    peak_vram_used_bytes: int


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
                    "probe = Path('/cache-probe/.task81_probe'); "
                    "probe.write_text('ok', encoding='utf-8'); "
                    "print(probe.read_text(encoding='utf-8')); "
                    "probe.unlink()"
                ),
            ],
            label="docker run task81 cache probe",
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
            shutil.copytree(source, target)
            continue
        target.write_bytes(source.read_bytes())


def _ensure_home_bind_mount(canonical_dir: Path, home_mount: Path) -> None:
    """Expose one canonical `/srv` cache root through a Docker-visible home path."""
    run_checked(["sudo", "-n", "mkdir", "-p", canonical_dir.as_posix()], label="sudo mkdir cache")
    run_checked(["mkdir", "-p", home_mount.as_posix()], label="mkdir home cache")
    _sync_home_cache_into_data_disk(canonical_dir, home_mount)
    _best_effort_unmount(home_mount)
    run_checked(
        ["sudo", "-n", "mount", "--bind", canonical_dir.as_posix(), home_mount.as_posix()],
        label="sudo mount --bind cache",
    )


def resolve_effective_cache_dir(
    *, cache_dir: Path, home_mount: Path, image: str
) -> MountResolution:
    """Return the Docker-mountable host path that still preserves canonical storage."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    if _probe_docker_bind_mount(cache_dir, image=image):
        return MountResolution(
            canonical_root=cache_dir, effective_root=cache_dir, used_home_mount=False
        )
    if _is_srv_cache_path(cache_dir):
        _ensure_home_bind_mount(cache_dir, home_mount)
        if _probe_docker_bind_mount(home_mount, image=image):
            return MountResolution(
                canonical_root=cache_dir, effective_root=home_mount, used_home_mount=True
            )
    raise SystemExit(f"Task 81 could not establish a Docker-mountable cache path for {cache_dir}.")


def extract_gpu_identity(smi_output: str, rocminfo_output: str) -> GpuIdentity:
    """Parse GPU identity and current counters from ROCm tooling output."""
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


def ensure_sidecar_preconditions(settings: BenchmarkSettings) -> None:
    """Fail early if Docker, the network, or the service container is missing."""
    if not settings.dockerfile_path.resolve().exists():
        raise SystemExit(f"Task 81 Dockerfile is missing: {settings.dockerfile_path}")
    if not settings.reference_audio_path.exists():
        raise SystemExit(f"Task 81 reference audio is missing: {settings.reference_audio_path}")
    docker_checked(["network", "inspect", settings.network], label="docker network inspect")
    running = docker_checked(["ps", "--format", "{{.Names}}"], label="docker ps").splitlines()
    if settings.service_container not in running:
        raise SystemExit(
            f"Expected service container `{settings.service_container}` to be running on Hemma."
        )


def remove_existing_benchmark_container(container_name: str) -> None:
    """Remove a stale benchmark container before a fresh Task 81 run."""
    existing = docker_checked(
        ["ps", "-a", "--filter", f"name=^{container_name}$", "--format", "{{.Names}}"],
        label="docker ps -a",
    )
    if existing.strip() == container_name:
        docker_checked(["rm", "-f", container_name], label="docker rm -f stale benchmark")


def ensure_image_present(settings: BenchmarkSettings) -> tuple[bool, str]:
    """Build the Task 81 sidecar image when requested and return the image id."""
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
        docker_checked(
            [
                "build",
                "-t",
                settings.image,
                "-f",
                settings.dockerfile_path.resolve().as_posix(),
                ".",
            ],
            label="docker build task81 image",
        )
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect after build",
        )
    return build_performed, image_id.strip()


def prefetch_openvoice_assets(settings: BenchmarkSettings, mount: MountResolution) -> None:
    """Download and extract OpenVoice V2 checkpoints into the persistent cache root."""
    checkpoints_root = mount.canonical_root / "checkpoints_v2"
    converter_checkpoint = checkpoints_root / "converter" / "checkpoint.pth"
    converter_config = checkpoints_root / "converter" / "config.json"
    if converter_checkpoint.exists() and converter_config.exists():
        return
    download_dir = mount.canonical_root / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    archive_path = download_dir / "checkpoints_v2_0417.zip"
    if not archive_path.exists():
        request = urllib.request.Request(
            settings.openvoice_checkpoint_url, headers={"User-Agent": "sir-convert-a-lot-task81"}
        )
        with (
            urllib.request.urlopen(request, timeout=600) as response,
            archive_path.open("wb") as output_file,
        ):
            shutil.copyfileobj(response, output_file)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(mount.canonical_root)
    if not converter_checkpoint.exists() or not converter_config.exists():
        raise SystemExit(
            "Task 81 OpenVoice checkpoint extraction did not materialize converter assets."
        )


def prefetch_hf_assets(settings: BenchmarkSettings, mount: MountResolution) -> None:
    """Prime the shared Hugging Face cache with the Swedish base model."""
    snapshot_download(settings.base_model_id, cache_dir=str(mount.canonical_root))


def start_sidecar(
    settings: BenchmarkSettings,
    *,
    hf_mount: MountResolution,
    openvoice_mount: MountResolution,
) -> None:
    """Launch the Task 81 sidecar container on the internal Hemma Docker network."""
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
        "SIR_TTS_SIDECAR_BIND_HOST=0.0.0.0",
        "-e",
        f"SIR_TTS_SIDECAR_PORT={settings.container_port}",
        "-e",
        "SIR_TTS_SIDECAR_BACKEND_ID=openvoice_v2",
        "-e",
        "SIR_TTS_SIDECAR_BACKEND_VERSION=74a1d147",
        "-e",
        "SIR_TTS_SIDECAR_BACKEND_PROFILE=mms_tts_swe_base",
        "-e",
        "SIR_TTS_SIDECAR_GPU_REQUIRED=1",
        "-e",
        f"SIR_TTS_SIDECAR_BASE_MODEL_ID={settings.base_model_id}",
        "-e",
        "SIR_TTS_SIDECAR_ALLOWED_LANGUAGE_CODES=sv",
        "-e",
        "SIR_TTS_SIDECAR_OPENVOICE_ENABLE_WATERMARK=0",
        "-e",
        f"SIR_TTS_SIDECAR_OPENVOICE_CHECKPOINTS_ROOT={CONTAINER_OPENVOICE_HOME}/checkpoints_v2",
        "-e",
        f"SIR_TTS_SIDECAR_OPENVOICE_CACHE_HOST_ROOT={openvoice_mount.canonical_root.as_posix()}",
        "-e",
        f"SIR_TTS_SIDECAR_OPENVOICE_CACHE_CONTAINER_ROOT={CONTAINER_OPENVOICE_HOME}",
        "-e",
        f"SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT={hf_mount.canonical_root.as_posix()}",
        "-e",
        f"SIR_TTS_SIDECAR_HF_CACHE_CONTAINER_ROOT={CONTAINER_HF_HOME}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "-v",
        f"{openvoice_mount.effective_root.as_posix()}:{CONTAINER_OPENVOICE_HOME}",
        settings.image,
    ]
    docker_checked(run_args, label="docker run task81 sidecar")


def wait_for_sidecar(
    settings: BenchmarkSettings,
) -> tuple[float, dict[str, object], CapabilityResponse]:
    """Poll the normalized health and capability endpoints until the sidecar is ready."""
    base_url = f"http://127.0.0.1:{settings.host_port}"
    deadline = time.monotonic() + settings.startup_timeout_seconds
    last_error = "sidecar not yet ready"
    with httpx.Client(timeout=30.0) as client:
        while time.monotonic() < deadline:
            try:
                health_response = client.get(f"{base_url}/health")
                health_response.raise_for_status()
                health_payload = health_response.json()
                ready_obj = health_payload.get("ready")
                if ready_obj is not True:
                    last_error = json.dumps(health_payload, sort_keys=True)
                    time.sleep(3.0)
                    continue
                capabilities_response = client.get(f"{base_url}/capabilities")
                capabilities_response.raise_for_status()
                readiness_seconds = round(
                    settings.startup_timeout_seconds - (deadline - time.monotonic()),
                    3,
                )
                return (
                    readiness_seconds,
                    health_payload,
                    CapabilityResponse.model_validate(capabilities_response.json()),
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)
                time.sleep(3.0)
    raise SystemExit(
        f"Timed out waiting for Task 81 sidecar readiness after "
        f"{settings.startup_timeout_seconds} seconds: {last_error}"
    )


def inspect_runtime(settings: BenchmarkSettings, *, image_id: str) -> SidecarRuntime:
    """Read Python, package versions, and cache env vars from inside the container."""
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
        raise SystemExit("Task 81 sidecar metadata probe returned an unexpected payload.")
    python_version_obj = payload_obj.get("python_version")
    package_versions_obj = payload_obj.get("package_versions")
    if not isinstance(python_version_obj, str) or not isinstance(package_versions_obj, dict):
        raise SystemExit("Task 81 sidecar metadata probe payload is malformed.")
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
        hf_home=_string_or_none(payload_obj.get("hf_home")),
        hf_hub_cache=_string_or_none(payload_obj.get("hf_hub_cache")),
        transformers_cache=_string_or_none(payload_obj.get("transformers_cache")),
        openvoice_checkpoints_root=_string_or_none(payload_obj.get("openvoice_checkpoints_root")),
    )


def probe_from_service_container(settings: BenchmarkSettings) -> InternalProbeEvidence:
    """Verify that the sidecar remains reachable from the Sir service container."""
    internal_url = f"http://{settings.network_alias}:{settings.container_port}"
    probe_output = docker_checked(
        [
            "exec",
            settings.service_container,
            "python",
            "-c",
            _build_service_probe_python(internal_url),
        ],
        label="docker exec service-container task81 health probe",
    )
    payload_obj = json.loads(probe_output)
    if not isinstance(payload_obj, dict):
        raise SystemExit("Task 81 service-container probe payload is malformed.")
    backend_id_obj = payload_obj.get("backend_id")
    ready_obj = payload_obj.get("ready")
    if not isinstance(backend_id_obj, str) or not isinstance(ready_obj, bool):
        raise SystemExit("Task 81 service-container probe did not return normalized health fields.")
    return InternalProbeEvidence(
        host_probe_ok=True,
        service_probe_ok=True,
        service_backend_id=backend_id_obj,
        service_ready=ready_obj,
    )


def reference_audio_evidence(reference_audio_path: Path) -> ReferenceAudioEvidence:
    """Collect deterministic metadata for the approved reference-audio input."""
    output = run_checked(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=sample_rate,codec_type",
            "-of",
            "json",
            reference_audio_path.as_posix(),
        ],
        label="ffprobe reference audio",
    )
    payload_obj = json.loads(output)
    if not isinstance(payload_obj, dict):
        raise SystemExit("Reference audio probe returned an unexpected payload.")
    streams_obj = payload_obj.get("streams")
    format_obj = payload_obj.get("format")
    if not isinstance(streams_obj, list) or not isinstance(format_obj, dict):
        raise SystemExit("Reference audio probe payload is malformed.")
    sample_rate_hz = 0
    for stream in streams_obj:
        if not isinstance(stream, dict):
            continue
        if stream.get("codec_type") != "audio":
            continue
        sample_rate_obj = stream.get("sample_rate")
        if isinstance(sample_rate_obj, str) and sample_rate_obj.isdigit():
            sample_rate_hz = int(sample_rate_obj)
            break
    duration_obj = format_obj.get("duration")
    if sample_rate_hz <= 0 or not isinstance(duration_obj, str):
        raise SystemExit("Reference audio probe did not return audio sample-rate and duration.")
    return ReferenceAudioEvidence(
        input_path=reference_audio_path.as_posix(),
        filename=reference_audio_path.name,
        reference_role="teacher_voice_cloning_reference",
        duration_seconds=round(float(duration_obj), 6),
        sample_rate_hz=sample_rate_hz,
    )


def synthesize_probe(
    *,
    settings: BenchmarkSettings,
    base_url: str,
    artifacts_dir: Path,
) -> tuple[SynthesisProbeResult, int, int]:
    """Call the normalized `/synthesize` endpoint and persist the Swedish sample."""
    output_path = artifacts_dir / "sample_sv.wav"
    error_path = artifacts_dir / "sample_sv.error.txt"
    with suppress(FileNotFoundError):
        output_path.unlink()
    with suppress(FileNotFoundError):
        error_path.unlink()
    sampler = _GpuSampler()
    sampler.start()
    started = time.monotonic()
    mime_type = (
        mimetypes.guess_type(settings.reference_audio_path.name)[0] or "application/octet-stream"
    )
    with httpx.Client(timeout=600.0) as client:
        response = client.post(
            f"{base_url}/synthesize",
            data={
                "text": settings.probe_text,
                "language": "sv",
                "voice_mode": "reference_clone",
                "output_format": "wav",
                "normalization_profile": "auto",
            },
            files={
                "reference_audio": (
                    settings.reference_audio_path.name,
                    settings.reference_audio_path.read_bytes(),
                    mime_type,
                )
            },
        )
    elapsed_seconds = round(time.monotonic() - started, 3)
    peak_gpu_busy_percent, peak_vram_used_bytes = sampler.stop()
    content_type = response.headers.get("content-type")
    if response.is_success:
        audio_bytes = response.content
        if "json" in (content_type or "").lower() or audio_bytes.lstrip().startswith(b"{"):
            error_text = response.text.strip()
            error_path.write_text(error_text + "\n", encoding="utf-8")
            return (
                SynthesisProbeResult(
                    ok=False,
                    status_code=response.status_code,
                    content_type=content_type,
                    byte_count=len(audio_bytes),
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
        output_path.write_bytes(audio_bytes)
        sha256_value = hashlib.sha256(audio_bytes).hexdigest()
        sample_rate_hz, duration_seconds = _wav_metadata(audio_bytes)
        return (
            SynthesisProbeResult(
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
    error_text = response.text.strip()
    error_path.write_text(error_text + "\n", encoding="utf-8")
    return (
        SynthesisProbeResult(
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


def capture_docker_logs(container_name: str, *, output_path: Path) -> None:
    """Write best-effort Docker logs for the benchmark container."""
    result = subprocess.run(
        ["sudo", "-n", "docker", "logs", "--timestamps", container_name],
        check=False,
        capture_output=True,
        text=True,
    )
    output_path.write_text((result.stdout + result.stderr).strip() + "\n", encoding="utf-8")


def _build_runtime_metadata_probe_python() -> str:
    """Return the Python snippet used to inspect versions inside the sidecar container."""
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

        targets = ("openvoice", "transformers", "torch", "fastapi")
        payload = {
            "python_version": sys.version.split()[0],
            "package_versions": {name: version_or_none(name) for name in targets},
            "hf_home": os.environ.get("HF_HOME"),
            "hf_hub_cache": os.environ.get("HF_HUB_CACHE"),
            "transformers_cache": os.environ.get("TRANSFORMERS_CACHE"),
            "openvoice_checkpoints_root": os.environ.get(
                "SIR_TTS_SIDECAR_OPENVOICE_CHECKPOINTS_ROOT"
            ),
        }
        print(json.dumps(payload, sort_keys=True))
        """
    ).strip()


def _build_service_probe_python(base_url: str) -> str:
    """Return the Python snippet used inside the service container for health probes."""
    return (
        "import json, urllib.request; "
        f"response = urllib.request.urlopen('{base_url}/health', timeout=30); "
        "payload=json.loads(response.read().decode('utf-8')); "
        "print(json.dumps("
        "{'backend_id': payload.get('backend_id'), 'ready': payload.get('ready')}, "
        "sort_keys=True))"
    )


def _wav_metadata(audio_bytes: bytes) -> tuple[int, float]:
    """Extract WAV sample-rate and duration from response bytes."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
    duration_seconds = frame_count / float(frame_rate)
    return frame_rate, round(duration_seconds, 6)


def _string_or_none(value: object) -> str | None:
    """Return one string value or `None`, failing on malformed metadata."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise SystemExit(f"Expected a string-or-null metadata value, got {value!r}.")
    return value
