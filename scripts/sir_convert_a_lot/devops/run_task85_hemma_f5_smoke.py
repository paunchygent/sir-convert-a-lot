"""Run the Task 85 Hemma F5-TTS sidecar benchmark.

Purpose:
    Prove the minimum Task 85 setup on Hemma through the canonical service
    path: the F5-TTS sidecar image builds, the Swedish model is present on
    persistent storage, the normalized sidecar boots, the existing Sir service
    container can reach it internally, and one Swedish cloning synthesis
    succeeds from the approved teacher reference clip.

Relationships:
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run benchmark:task-85`.
    - Reuses the ADR-0007 `/health`, `/capabilities`, and service-container
      probe pattern established by Tasks 79 and 81.
    - Builds the current Task 85 runtime from `ChiliOlavi/F5-TTS@swedish-tts`.
    - Writes deterministic evidence under
      `build/verification/task-85-f5-tts-hemma/`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import mimetypes
import os
import sys
import textwrap
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task81_openvoice_runtime import (
    MountResolution,
    capture_docker_logs,
    docker_checked,
    extract_gpu_identity,
    reference_audio_evidence,
    remove_existing_benchmark_container,
    resolve_effective_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.tts_sidecar.contracts import CapabilityResponse

LOGGER = logging.getLogger(__name__)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-85-f5-tts-hemma")
DEFAULT_DOCKERFILE = Path("containers/tts-sidecar-f5/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot/f5-sidecar-task85:local"
DEFAULT_NETWORK = "hule-network"
DEFAULT_NETWORK_ALIAS = "sir-convert-a-lot-f5-task85"
DEFAULT_CONTAINER_NAME = "sir_convert_a_lot_f5_task85"
DEFAULT_SERVICE_CONTAINER = "sir_convert_a_lot_prod"
DEFAULT_CONTAINER_PORT = 8093
DEFAULT_HOST_PORT = 38093
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_MODEL_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/f5-tts-swedish")
DEFAULT_MODEL_CACHE_HOME_MOUNT = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/cache/f5-tts-swedish"
)
DEFAULT_MODEL_REPO_ID = "EkhoCollective/f5-tts-swedish"
DEFAULT_REFERENCE_AUDIO = Path(
    "build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
)
DEFAULT_WHISPER_MODEL = "turbo"
DEFAULT_SWEDISH_TEXT = (
    "Hej. Det här är ett benchmarkprov för Sir Convert a Lot på Hemma. "
    "Vi testar om F5-TTS kan klona en lärarröst och läsa svensk text på ett tydligt sätt."
)
DEFAULT_F5_NFE_STEP = 64
DEFAULT_F5_CFG_STRENGTH = 2.0
DEFAULT_F5_SWAY_SAMPLING_COEF = -1.0
DEFAULT_F5_SPEED = 1.0
DEFAULT_F5_CROSS_FADE_DURATION = 0.15
DEFAULT_F5_TARGET_RMS = 0.1


@dataclass(frozen=True)
class BenchmarkSettings:
    """Normalized CLI settings for the Task 85 benchmark run."""

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
    model_cache_dir: Path
    model_cache_home_mount: Path
    model_repo_id: str
    reference_audio_path: Path
    reference_transcript: str | None
    reference_transcript_path: Path | None
    whisper_model: str
    probe_text: str
    probe_text_path: Path | None
    remove_silence: bool
    nfe_step: int
    cfg_strength: float
    sway_sampling_coef: float
    speed: float
    fix_duration: float | None
    cross_fade_duration: float
    target_rms: float
    vocoder_name: str
    load_vocoder_from_local: bool
    build_image: bool
    retain_container: bool


@dataclass(frozen=True)
class BenchmarkReport:
    """Top-level JSON payload for Task 85 Hemma evidence."""

    benchmark_id: str
    run_id: str
    generated_at: str
    repo_head: str
    host_base_url: str
    internal_base_url: str
    image: str
    image_id: str
    build_performed: bool
    readiness_seconds: float
    help_command_ok: bool
    help_output_path: str
    synthesized_ok: bool
    synthesized_output_path: str | None
    synthesized_sha256: str | None
    synthesized_content_type: str | None
    service_probe_ok: bool
    service_backend_id: str
    service_ready: bool
    capability_backend_id: str
    capability_language_support: str
    capability_reference_transcript_required: bool
    reference_audio_path: str
    reference_audio_duration_seconds: float
    reference_audio_sample_rate_hz: int
    reference_transcript: str
    reference_transcript_path: str
    probe_text: str
    probe_text_path: str | None
    remove_silence: bool
    nfe_step: int
    cfg_strength: float
    sway_sampling_coef: float
    speed: float
    fix_duration: float | None
    cross_fade_duration: float
    target_rms: float
    vocoder_name: str
    load_vocoder_from_local: bool
    hf_cache_host_root: str
    model_cache_host_root: str
    model_files: list[str]
    gpu_product_name: str
    gpu_gfx_architecture: str
    docker_logs_path: str


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_path(name: str, *, default: Path) -> Path:
    """Resolve one optional environment override into a filesystem path."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return Path(value.strip())


def _resolve_text_argument(
    *,
    text: str | None,
    text_file: Path | None,
    label: str,
) -> tuple[str, Path | None]:
    """Return text from one direct value or one file-backed value."""
    if text_file is None:
        if text is None:
            raise SystemExit(f"Task 85 {label} text is missing.")
        return text, None
    if not text_file.exists():
        raise SystemExit(f"Task 85 {label} text file is missing: {text_file}")
    file_text = text_file.read_text(encoding="utf-8").strip()
    if file_text == "":
        raise SystemExit(f"Task 85 {label} text file is empty: {text_file}")
    return file_text, text_file


def _parse_args(argv: list[str]) -> BenchmarkSettings:
    """Parse CLI arguments into normalized Task 85 benchmark settings."""
    parser = argparse.ArgumentParser(description="Run the Task 85 Hemma F5-TTS benchmark.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dockerfile", type=Path, default=DEFAULT_DOCKERFILE)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--network", default=DEFAULT_NETWORK)
    parser.add_argument("--network-alias", default=DEFAULT_NETWORK_ALIAS)
    parser.add_argument("--container-name", default=DEFAULT_CONTAINER_NAME)
    parser.add_argument("--service-container", default=DEFAULT_SERVICE_CONTAINER)
    parser.add_argument("--container-port", type=int, default=DEFAULT_CONTAINER_PORT)
    parser.add_argument("--host-port", type=int, default=DEFAULT_HOST_PORT)
    parser.add_argument("--startup-timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--hf-cache-dir",
        type=Path,
        default=_env_path("SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH", default=DEFAULT_HF_CACHE),
    )
    parser.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=_env_path(
            "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT",
            default=DEFAULT_HF_CACHE_HOME_MOUNT,
        ),
    )
    parser.add_argument(
        "--model-cache-dir",
        type=Path,
        default=_env_path(
            "SIR_CONVERT_A_LOT_HEMMA_F5_MODEL_CACHE_PATH", default=DEFAULT_MODEL_CACHE
        ),
    )
    parser.add_argument(
        "--model-cache-home-mount",
        type=Path,
        default=_env_path(
            "SIR_CONVERT_A_LOT_HEMMA_F5_MODEL_CACHE_HOME_MOUNT",
            default=DEFAULT_MODEL_CACHE_HOME_MOUNT,
        ),
    )
    parser.add_argument("--model-repo-id", default=DEFAULT_MODEL_REPO_ID)
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--reference-transcript", default=None)
    parser.add_argument("--reference-transcript-file", type=Path, default=None)
    parser.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL)
    parser.add_argument("--probe-text", default=DEFAULT_SWEDISH_TEXT)
    parser.add_argument("--probe-text-file", type=Path, default=None)
    parser.add_argument(
        "--remove-silence",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--nfe-step", type=int, default=DEFAULT_F5_NFE_STEP)
    parser.add_argument("--cfg-strength", type=float, default=DEFAULT_F5_CFG_STRENGTH)
    parser.add_argument(
        "--sway-sampling-coef",
        type=float,
        default=DEFAULT_F5_SWAY_SAMPLING_COEF,
    )
    parser.add_argument("--speed", type=float, default=DEFAULT_F5_SPEED)
    parser.add_argument("--fix-duration", type=float, default=None)
    parser.add_argument(
        "--cross-fade-duration",
        type=float,
        default=DEFAULT_F5_CROSS_FADE_DURATION,
    )
    parser.add_argument("--target-rms", type=float, default=DEFAULT_F5_TARGET_RMS)
    parser.add_argument("--vocoder-name", default="vocos")
    parser.add_argument(
        "--load-vocoder-from-local",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--skip-build", action="store_true", help="Reuse an already-built image.")
    parser.add_argument(
        "--retain-container",
        action="store_true",
        help="Keep the sidecar running after evidence capture.",
    )
    args = parser.parse_args(argv)
    probe_text, probe_text_path = _resolve_text_argument(
        text=str(args.probe_text) if args.probe_text is not None else None,
        text_file=Path(args.probe_text_file) if args.probe_text_file is not None else None,
        label="probe",
    )
    return BenchmarkSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile),
        image=str(args.image),
        network=str(args.network),
        network_alias=str(args.network_alias),
        container_name=str(args.container_name),
        service_container=str(args.service_container),
        container_port=int(args.container_port),
        host_port=int(args.host_port),
        startup_timeout_seconds=float(args.startup_timeout_seconds),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        model_cache_dir=Path(args.model_cache_dir),
        model_cache_home_mount=Path(args.model_cache_home_mount),
        model_repo_id=str(args.model_repo_id),
        reference_audio_path=Path(args.reference_audio),
        reference_transcript=str(args.reference_transcript).strip()
        if args.reference_transcript
        else None,
        reference_transcript_path=Path(args.reference_transcript_file)
        if args.reference_transcript_file is not None
        else None,
        whisper_model=str(args.whisper_model),
        probe_text=probe_text,
        probe_text_path=probe_text_path,
        remove_silence=bool(args.remove_silence),
        nfe_step=int(args.nfe_step),
        cfg_strength=float(args.cfg_strength),
        sway_sampling_coef=float(args.sway_sampling_coef),
        speed=float(args.speed),
        fix_duration=float(args.fix_duration) if args.fix_duration is not None else None,
        cross_fade_duration=float(args.cross_fade_duration),
        target_rms=float(args.target_rms),
        vocoder_name=str(args.vocoder_name),
        load_vocoder_from_local=bool(args.load_vocoder_from_local),
        build_image=not bool(args.skip_build),
        retain_container=bool(args.retain_container),
    )


def _ensure_preconditions(settings: BenchmarkSettings) -> None:
    """Fail early if Docker, the network, or the service container is missing."""
    if not settings.dockerfile_path.resolve().exists():
        raise SystemExit(f"Task 85 Dockerfile is missing: {settings.dockerfile_path}")
    if not settings.reference_audio_path.exists():
        raise SystemExit(f"Task 85 reference audio is missing: {settings.reference_audio_path}")
    if (
        settings.reference_transcript_path is not None
        and not settings.reference_transcript_path.exists()
    ):
        raise SystemExit(
            f"Task 85 reference transcript file is missing: {settings.reference_transcript_path}"
        )
    docker_checked(["network", "inspect", settings.network], label="docker network inspect")
    running = docker_checked(["ps", "--format", "{{.Names}}"], label="docker ps").splitlines()
    if settings.service_container not in running:
        raise SystemExit(
            f"Expected service container `{settings.service_container}` to be running on Hemma."
        )


def _prepare_output_root(output_root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    """Create a clean deterministic output tree for the current benchmark run."""
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir = output_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(artifacts_dir.iterdir()):
        if child.is_file():
            child.unlink()
    help_path = output_root / "f5_help.txt"
    transcript_path = output_root / "reference_transcript.txt"
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    logs_path = output_root / "docker_logs.txt"
    for path in (help_path, transcript_path, report_json_path, report_md_path, logs_path):
        with suppress(FileNotFoundError):
            path.unlink()
    return artifacts_dir, help_path, transcript_path, report_json_path, report_md_path, logs_path


def _ensure_image_present(settings: BenchmarkSettings) -> tuple[bool, str]:
    """Build the Task 85 sidecar image with BuildKit and return the image id."""
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
            label="docker buildx build task85 image",
        )
        image_id = docker_checked(
            ["image", "inspect", settings.image, "--format", "{{.Id}}"],
            label="docker image inspect after build",
        )
    return build_performed, image_id.strip()


def _prefetch_model_snapshot(
    settings: BenchmarkSettings,
    *,
    hf_mount: MountResolution,
    model_mount: MountResolution,
) -> None:
    """Download the Swedish F5 model into the persistent mounted model root."""
    docker_checked(
        [
            "run",
            "--rm",
            "-e",
            "HF_HUB_DISABLE_XET=1",
            "-e",
            "HF_HOME=/cache/huggingface",
            "-e",
            "HUGGINGFACE_HUB_CACHE=/cache/huggingface",
            "-e",
            "TRANSFORMERS_CACHE=/cache/huggingface",
            "-v",
            f"{hf_mount.effective_root.as_posix()}:/cache/huggingface",
            "-v",
            f"{model_mount.effective_root.as_posix()}:/models/swedish",
            "--entrypoint",
            "python",
            settings.image,
            "-c",
            (
                "from huggingface_hub import snapshot_download; "
                f"snapshot_download('{settings.model_repo_id}', local_dir='/models/swedish', "
                "local_dir_use_symlinks=False)"
            ),
        ],
        label="docker run task85 model prefetch",
    )


def _transcribe_reference_audio(
    settings: BenchmarkSettings,
    *,
    transcript_path: Path,
) -> str:
    """Use Whisper inside the F5 image to transcribe the approved reference clip."""
    output = docker_checked(
        [
            "run",
            "--rm",
            "-v",
            f"{settings.reference_audio_path.resolve().parent.as_posix()}:/input:ro",
            "--entrypoint",
            "bash",
            settings.image,
            "-lc",
            (
                "python -m whisper "
                f"/input/{settings.reference_audio_path.name} "
                f"--model {settings.whisper_model} "
                "--language Swedish "
                "--task transcribe "
                "--device cpu "
                "--output_dir /tmp/task85-whisper "
                "--output_format txt >/tmp/task85-whisper.log 2>&1 && "
                f"cat /tmp/task85-whisper/{settings.reference_audio_path.stem}.txt"
            ),
        ],
        label="docker run task85 whisper transcription",
    )
    transcript = output.strip()
    if transcript == "":
        raise SystemExit("Whisper returned an empty transcript for the Task 85 reference audio.")
    transcript_path.write_text(transcript + "\n", encoding="utf-8")
    return transcript


def _resolve_reference_transcript(
    settings: BenchmarkSettings,
    *,
    transcript_path: Path,
) -> str:
    """Resolve the reference transcript from CLI text, file, or Whisper fallback."""
    if settings.reference_transcript is not None:
        transcript_path.write_text(settings.reference_transcript + "\n", encoding="utf-8")
        return settings.reference_transcript
    if settings.reference_transcript_path is not None:
        transcript = settings.reference_transcript_path.read_text(encoding="utf-8").strip()
        if transcript == "":
            raise SystemExit("Task 85 reference transcript file is empty.")
        transcript_path.write_text(transcript + "\n", encoding="utf-8")
        return transcript
    return _transcribe_reference_audio(settings, transcript_path=transcript_path)


def _start_sidecar(
    settings: BenchmarkSettings,
    *,
    hf_mount: MountResolution,
    model_mount: MountResolution,
) -> None:
    """Launch the Task 85 sidecar container on the internal Hemma Docker network."""
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
        "SIR_TTS_SIDECAR_BACKEND_ID=f5_tts_swedish",
        "-e",
        "SIR_TTS_SIDECAR_BACKEND_VERSION=swedish-tts",
        "-e",
        "SIR_TTS_SIDECAR_BACKEND_PROFILE=f5tts_v1_base_swedish_finetune",
        "-e",
        "SIR_TTS_SIDECAR_GPU_REQUIRED=1",
        "-e",
        "SIR_TTS_SIDECAR_MODEL_NAME=F5TTS_v1_Base",
        "-e",
        f"SIR_TTS_SIDECAR_MODEL_REPO_ID={settings.model_repo_id}",
        "-e",
        "SIR_TTS_SIDECAR_MODEL_ROOT=/models/swedish",
        "-e",
        f"SIR_TTS_SIDECAR_HF_CACHE_HOST_ROOT={hf_mount.canonical_root.as_posix()}",
        "-e",
        "SIR_TTS_SIDECAR_HF_CACHE_CONTAINER_ROOT=/cache/huggingface",
        "-e",
        f"SIR_TTS_SIDECAR_MODEL_CACHE_HOST_ROOT={model_mount.canonical_root.as_posix()}",
        "-e",
        "SIR_TTS_SIDECAR_MODEL_CACHE_CONTAINER_ROOT=/models",
        "-e",
        "SIR_TTS_SIDECAR_ALLOWED_LANGUAGE_CODES=sv",
        "-e",
        f"SIR_TTS_SIDECAR_F5_REMOVE_SILENCE={'1' if settings.remove_silence else '0'}",
        "-e",
        f"SIR_TTS_SIDECAR_F5_NFE_STEP={settings.nfe_step}",
        "-e",
        f"SIR_TTS_SIDECAR_F5_CFG_STRENGTH={settings.cfg_strength}",
        "-e",
        f"SIR_TTS_SIDECAR_F5_SWAY_SAMPLING_COEF={settings.sway_sampling_coef}",
        "-e",
        f"SIR_TTS_SIDECAR_F5_SPEED={settings.speed}",
        "-e",
        (
            "SIR_TTS_SIDECAR_F5_FIX_DURATION="
            if settings.fix_duration is None
            else f"SIR_TTS_SIDECAR_F5_FIX_DURATION={settings.fix_duration}"
        ),
        "-e",
        f"SIR_TTS_SIDECAR_F5_CROSS_FADE_DURATION={settings.cross_fade_duration}",
        "-e",
        f"SIR_TTS_SIDECAR_F5_TARGET_RMS={settings.target_rms}",
        "-e",
        f"SIR_TTS_SIDECAR_F5_VOCODER_NAME={settings.vocoder_name}",
        "-e",
        (
            "SIR_TTS_SIDECAR_F5_LOAD_VOCODER_FROM_LOCAL=1"
            if settings.load_vocoder_from_local
            else "SIR_TTS_SIDECAR_F5_LOAD_VOCODER_FROM_LOCAL=0"
        ),
        "-v",
        f"{hf_mount.effective_root.as_posix()}:/cache/huggingface",
        "-v",
        f"{model_mount.effective_root.as_posix()}:/models/swedish",
        settings.image,
    ]
    docker_checked(run_args, label="docker run task85 sidecar")


def _wait_for_sidecar(settings: BenchmarkSettings) -> tuple[float, CapabilityResponse]:
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
                if health_payload.get("ready") is not True:
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
                    CapabilityResponse.model_validate(capabilities_response.json()),
                )
            except (httpx.HTTPError, ValueError) as exc:
                last_error = str(exc)
                time.sleep(3.0)
    raise SystemExit(
        f"Timed out waiting for Task 85 sidecar readiness after "
        f"{settings.startup_timeout_seconds} seconds: {last_error}"
    )


def _probe_from_service_container(settings: BenchmarkSettings) -> tuple[bool, str, bool]:
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
        label="docker exec service-container task85 health probe",
    )
    payload = json.loads(probe_output)
    return True, str(payload["backend_id"]), bool(payload["ready"])


def _collect_model_files(model_mount: MountResolution) -> list[str]:
    """Return the current Swedish model file inventory under the mounted model root."""
    root = model_mount.canonical_root
    return [
        path.relative_to(root).as_posix()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".cache/" not in path.relative_to(root).as_posix()
    ]


def _write_help_output(settings: BenchmarkSettings, *, help_path: Path) -> bool:
    """Run `f5-tts_infer-cli --help` inside the sidecar and persist its output."""
    output = docker_checked(
        ["exec", settings.container_name, "bash", "-lc", "timeout 120 f5-tts_infer-cli --help"],
        label="docker exec task85 f5 help",
    )
    help_path.write_text(output + "\n", encoding="utf-8")
    return "Commandline interface for E2/F5 TTS" in output


def _synthesize_probe(
    *,
    settings: BenchmarkSettings,
    base_url: str,
    artifacts_dir: Path,
    reference_transcript: str,
) -> tuple[bool, str | None, str | None, str | None]:
    """Call the normalized `/synthesize` endpoint and persist the Swedish sample."""
    output_path = artifacts_dir / "sample_sv.wav"
    mime_type = (
        mimetypes.guess_type(settings.reference_audio_path.name)[0] or "application/octet-stream"
    )
    with httpx.Client(timeout=900.0) as client:
        response = client.post(
            f"{base_url}/synthesize",
            data={
                "text": settings.probe_text,
                "language": "sv",
                "voice_mode": "reference_clone",
                "output_format": "wav",
                "normalization_profile": "auto",
                "reference_transcript": reference_transcript,
            },
            files={
                "reference_audio": (
                    settings.reference_audio_path.name,
                    settings.reference_audio_path.read_bytes(),
                    mime_type,
                )
            },
        )
    if not response.is_success:
        raise SystemExit(
            "Task 85 synthesis failed.\n"
            f"status={response.status_code}\n"
            f"content-type={response.headers.get('content-type')}\n"
            f"body={response.text.strip()}"
        )
    output_path.write_bytes(response.content)
    return (
        True,
        output_path.as_posix(),
        hashlib.sha256(response.content).hexdigest(),
        response.headers.get("content-type"),
    )


def _build_report_markdown(report: BenchmarkReport) -> str:
    """Render one operator-friendly markdown summary for Task 85 evidence."""
    lines = [
        "# Task 85 Hemma F5-TTS Benchmark",
        "",
        f"- run_id: `{report.run_id}`",
        f"- repo_head: `{report.repo_head}`",
        f"- host_base_url: `{report.host_base_url}`",
        f"- internal_base_url: `{report.internal_base_url}`",
        f"- image: `{report.image}`",
        f"- image_id: `{report.image_id}`",
        f"- build_performed: `{report.build_performed}`",
        f"- readiness_seconds: `{report.readiness_seconds}`",
        f"- help_command_ok: `{report.help_command_ok}`",
        f"- synthesized_ok: `{report.synthesized_ok}`",
        f"- synthesized_output_path: `{report.synthesized_output_path}`",
        f"- service_probe_ok: `{report.service_probe_ok}`",
        f"- service_backend_id: `{report.service_backend_id}`",
        f"- service_ready: `{report.service_ready}`",
        f"- capability_backend_id: `{report.capability_backend_id}`",
        f"- capability_language_support: `{report.capability_language_support}`",
        (
            "- capability_reference_transcript_required: "
            f"`{report.capability_reference_transcript_required}`"
        ),
        f"- reference_audio_path: `{report.reference_audio_path}`",
        f"- reference_audio_duration_seconds: `{report.reference_audio_duration_seconds}`",
        f"- reference_audio_sample_rate_hz: `{report.reference_audio_sample_rate_hz}`",
        f"- reference_transcript: `{report.reference_transcript}`",
        f"- probe_text: `{report.probe_text}`",
        f"- probe_text_path: `{report.probe_text_path}`",
        f"- remove_silence: `{report.remove_silence}`",
        f"- nfe_step: `{report.nfe_step}`",
        f"- cfg_strength: `{report.cfg_strength}`",
        f"- sway_sampling_coef: `{report.sway_sampling_coef}`",
        f"- speed: `{report.speed}`",
        f"- fix_duration: `{report.fix_duration}`",
        f"- cross_fade_duration: `{report.cross_fade_duration}`",
        f"- target_rms: `{report.target_rms}`",
        f"- vocoder_name: `{report.vocoder_name}`",
        f"- load_vocoder_from_local: `{report.load_vocoder_from_local}`",
        f"- hf_cache_host_root: `{report.hf_cache_host_root}`",
        f"- model_cache_host_root: `{report.model_cache_host_root}`",
        f"- gpu_product_name: `{report.gpu_product_name}`",
        f"- gpu_gfx_architecture: `{report.gpu_gfx_architecture}`",
        "",
        "## Model Files",
    ]
    lines.extend(f"- `{entry}`" for entry in report.model_files)
    lines.extend(
        [
            "",
            "## Evidence",
            f"- help_output_path: `{report.help_output_path}`",
            f"- reference_transcript_path: `{report.reference_transcript_path}`",
            f"- docker_logs_path: `{report.docker_logs_path}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Run the Task 85 benchmark and write deterministic evidence artifacts."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    LOGGER.info(
        (
            "Task 85 starting: output_root=%s skip_build=%s remove_silence=%s "
            "nfe_step=%s cfg_strength=%s sway_sampling_coef=%s speed=%s "
            "fix_duration=%s cross_fade_duration=%s target_rms=%s "
            "load_vocoder_from_local=%s vocoder=%s"
        ),
        settings.output_root,
        not settings.build_image,
        settings.remove_silence,
        settings.nfe_step,
        settings.cfg_strength,
        settings.sway_sampling_coef,
        settings.speed,
        settings.fix_duration,
        settings.cross_fade_duration,
        settings.target_rms,
        settings.load_vocoder_from_local,
        settings.vocoder_name,
    )
    enforce_generated_output_path(settings.output_root, label="output_root")
    (
        artifacts_dir,
        help_path,
        transcript_path,
        report_json_path,
        report_md_path,
        logs_path,
    ) = _prepare_output_root(settings.output_root)
    generated_at = _utc_now_iso()
    run_id = generated_at.replace("-", "").replace(":", "")
    repo_head = run_checked(["git", "rev-parse", "HEAD"], label="git rev-parse HEAD")
    host_base_url = f"http://127.0.0.1:{settings.host_port}"
    internal_base_url = f"http://{settings.network_alias}:{settings.container_port}"
    build_performed = False
    cleanup_performed = False
    try:
        LOGGER.info("Checking Docker/service/reference preconditions")
        _ensure_preconditions(settings)
        LOGGER.info("Inspecting GPU runtime")
        smi_identity_output = run_checked(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showuse"],
            label="rocm-smi identity",
        )
        rocminfo_output = run_checked(["rocminfo"], label="rocminfo")
        gpu_identity = extract_gpu_identity(smi_identity_output, rocminfo_output)
        LOGGER.info(
            "GPU detected: product=%s gfx=%s",
            gpu_identity.product_name,
            gpu_identity.gfx_architecture,
        )
        remove_existing_benchmark_container(settings.container_name)
        LOGGER.info("Ensuring F5 sidecar image is present")
        build_performed, image_id = _ensure_image_present(settings)
        LOGGER.info("Image ready: build_performed=%s image_id=%s", build_performed, image_id)
        hf_mount = resolve_effective_cache_dir(
            cache_dir=settings.hf_cache_dir,
            home_mount=settings.hf_cache_home_mount,
            image=settings.image,
        )
        model_mount = resolve_effective_cache_dir(
            cache_dir=settings.model_cache_dir,
            home_mount=settings.model_cache_home_mount,
            image=settings.image,
        )
        LOGGER.info(
            "Resolved cache mounts: hf=%s model=%s",
            hf_mount.canonical_root,
            model_mount.canonical_root,
        )
        LOGGER.info("Prefetching Swedish model snapshot if needed")
        _prefetch_model_snapshot(settings, hf_mount=hf_mount, model_mount=model_mount)
        LOGGER.info("Collecting reference audio evidence")
        reference_evidence = reference_audio_evidence(
            settings.reference_audio_path,
            image=settings.image,
        )
        LOGGER.info("Resolving reference transcript input")
        reference_transcript = _resolve_reference_transcript(
            settings,
            transcript_path=transcript_path,
        )
        LOGGER.info("Starting F5 sidecar container")
        _start_sidecar(settings, hf_mount=hf_mount, model_mount=model_mount)
        LOGGER.info("Waiting for sidecar readiness")
        readiness_seconds, capabilities = _wait_for_sidecar(settings)
        LOGGER.info("Probing sidecar from service container")
        service_probe_ok, service_backend_id, service_ready = _probe_from_service_container(
            settings
        )
        LOGGER.info("Capturing f5-tts_infer-cli --help evidence")
        help_command_ok = _write_help_output(settings, help_path=help_path)
        LOGGER.info("Running synthesis probe")
        (
            synthesized_ok,
            synthesized_output_path,
            synthesized_sha256,
            synthesized_content_type,
        ) = _synthesize_probe(
            settings=settings,
            base_url=host_base_url,
            artifacts_dir=artifacts_dir,
            reference_transcript=reference_transcript,
        )
        report = BenchmarkReport(
            benchmark_id="task-85-f5-tts-hemma",
            run_id=run_id,
            generated_at=generated_at,
            repo_head=repo_head,
            host_base_url=host_base_url,
            internal_base_url=internal_base_url,
            image=settings.image,
            image_id=image_id,
            build_performed=build_performed,
            readiness_seconds=readiness_seconds,
            help_command_ok=help_command_ok,
            help_output_path=help_path.as_posix(),
            synthesized_ok=synthesized_ok,
            synthesized_output_path=synthesized_output_path,
            synthesized_sha256=synthesized_sha256,
            synthesized_content_type=synthesized_content_type,
            service_probe_ok=service_probe_ok,
            service_backend_id=service_backend_id,
            service_ready=service_ready,
            capability_backend_id=capabilities.backend_id,
            capability_language_support=capabilities.languages[0].support_level.value,
            capability_reference_transcript_required=capabilities.voice.reference_transcript_required,
            reference_audio_path=reference_evidence.input_path,
            reference_audio_duration_seconds=reference_evidence.duration_seconds,
            reference_audio_sample_rate_hz=reference_evidence.sample_rate_hz,
            reference_transcript=reference_transcript,
            reference_transcript_path=transcript_path.as_posix(),
            probe_text=settings.probe_text,
            probe_text_path=settings.probe_text_path.as_posix()
            if settings.probe_text_path is not None
            else None,
            remove_silence=settings.remove_silence,
            nfe_step=settings.nfe_step,
            cfg_strength=settings.cfg_strength,
            sway_sampling_coef=settings.sway_sampling_coef,
            speed=settings.speed,
            fix_duration=settings.fix_duration,
            cross_fade_duration=settings.cross_fade_duration,
            target_rms=settings.target_rms,
            vocoder_name=settings.vocoder_name,
            load_vocoder_from_local=settings.load_vocoder_from_local,
            hf_cache_host_root=hf_mount.canonical_root.as_posix(),
            model_cache_host_root=model_mount.canonical_root.as_posix(),
            model_files=_collect_model_files(model_mount),
            gpu_product_name=gpu_identity.product_name,
            gpu_gfx_architecture=gpu_identity.gfx_architecture,
            docker_logs_path=logs_path.as_posix(),
        )
        LOGGER.info("Writing benchmark report and evidence bundle")
        report_json_path.write_text(
            json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        report_md_path.write_text(_build_report_markdown(report), encoding="utf-8")
        LOGGER.info("Task 85 completed successfully: sample=%s", synthesized_output_path)
        return 0
    finally:
        LOGGER.info("Capturing docker logs for %s", settings.container_name)
        capture_docker_logs(settings.container_name, output_path=logs_path)
        if not settings.retain_container:
            with suppress(SystemExit):
                run_checked(
                    ["sudo", "-n", "docker", "rm", "-f", settings.container_name],
                    label="docker rm task85",
                )
            cleanup_performed = True
            LOGGER.info("Removed benchmark container %s", settings.container_name)
        _ = cleanup_performed


if __name__ == "__main__":
    raise SystemExit(main())
