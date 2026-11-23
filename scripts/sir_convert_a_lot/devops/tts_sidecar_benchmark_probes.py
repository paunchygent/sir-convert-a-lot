"""Cache, measurement, and report probes for the Hemma TTS sidecar benchmark.

Purpose:
    Hold the host-cache resolution, GPU measurement, and audio-probe
    operations the benchmark uses to gather evidence on Hemma while keeping
    the Docker launch/readiness runtime module focused.

Relationships:
    - Used by `scripts.sir_convert_a_lot.devops.run_tts_sidecar_hemma_benchmark`.
    - Imports the Docker execution helpers from
      `scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime`.
"""

from __future__ import annotations

import hashlib
import io
import re
import subprocess
import threading
import time
import wave
from contextlib import suppress
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.devops.qwen3_tts_request_payload import (
    build_speech_payload,
)
from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_reporting import (
    AudioProbeResult,
    GpuIdentity,
    PythonRecommendation,
)
from scripts.sir_convert_a_lot.devops.tts_sidecar_benchmark_runtime import (
    BenchmarkSettings,
    docker_checked,
    run_checked,
)

GPU_PRODUCT_RE = re.compile(r"Card\s+Series:\s*(.+)", re.IGNORECASE)
GPU_VRAM_TOTAL_RE = re.compile(r"VRAM Total Memory \(B\):\s*([0-9]+)")
GPU_VRAM_USED_RE = re.compile(r"VRAM Total Used Memory \(B\):\s*([0-9]+)")
GPU_BUSY_RE = re.compile(r"GPU use \(%\):\s*([0-9]+)")
GFX_ARCH_RE = re.compile(r"gfx[0-9]+")


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
                    "probe = Path('/cache-probe/.tts-sidecar_probe'); "
                    "probe.write_text('ok', encoding='utf-8'); "
                    "print(probe.read_text(encoding='utf-8')); "
                    "probe.unlink()"
                ),
            ],
            label="docker run tts-sidecar hf cache probe",
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
    raise SystemExit("TTS sidecar could not establish a Docker-mountable Hugging Face cache path.")


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
    return sorted(dict.fromkeys(names))


def python_recommendation(python_version: str) -> PythonRecommendation:
    """Translate the observed Python runtime into a TTS sidecar benchmark recommendation."""
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


def _wav_metadata(audio_bytes: bytes) -> tuple[int, float]:
    """Extract WAV sample-rate and duration from response bytes."""
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
    duration_seconds = frame_count / float(frame_rate)
    return frame_rate, round(duration_seconds, 6)


def audio_probe(
    *,
    settings: BenchmarkSettings,
    base_url: str,
    response_format: str,
    artifacts_dir: Path,
) -> tuple[AudioProbeResult, int, int]:
    """Call `/v1/audio/speech` for one response format and persist the artifact."""
    payload = {
        key: value
        for key, value in build_speech_payload(
            model=settings.model,
            probe_text=settings.probe_text,
            response_format=response_format,
            task_type=settings.task_type,
            language=settings.language,
            voice=settings.voice,
            instructions=settings.instructions,
            reference_audio=settings.reference_audio,
            reference_transcript=settings.reference_transcript,
        ).items()
    }
    output_path = artifacts_dir / f"sample.{response_format}"
    error_path = artifacts_dir / f"sample.{response_format}.error.txt"
    with suppress(FileNotFoundError):
        output_path.unlink()
    with suppress(FileNotFoundError):
        error_path.unlink()
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
        content_type_normalized = (content_type or "").lower()
        if "json" in content_type_normalized or audio_bytes.lstrip().startswith(b"{"):
            error_text = response.text.strip()
            error_path.write_text(error_text + "\n", encoding="utf-8")
            return (
                AudioProbeResult(
                    response_format=response_format,
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
        sample_rate_hz: int | None = None
        duration_seconds: float | None = None
        if response_format == "wav":
            with suppress(wave.Error):
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
