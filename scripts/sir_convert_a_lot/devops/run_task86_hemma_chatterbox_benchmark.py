"""Run the Task 86 Hemma Chatterbox Multilingual sidecar benchmark.

Purpose:
    Prove that the official Chatterbox Multilingual model can boot on Hemma,
    expose the normalized ADR-0007 sidecar contract, synthesize an English
    smoke sample, and perform Swedish cloning from the approved teacher
    reference clip.

Relationships:
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run benchmark:task-86`.
    - Reuses the ADR-0007 `/health`, `/capabilities`, `/voices`, and
      `/synthesize` contract already used by the earlier TTS sidecars.
    - Writes deterministic evidence under
      `build/verification/task-86-chatterbox-hemma/`.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from contextlib import suppress
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task81_openvoice_runtime import (
    capture_docker_logs,
    extract_gpu_identity,
    reference_audio_evidence,
    remove_existing_benchmark_container,
    resolve_effective_cache_dir,
    run_checked,
)
from scripts.sir_convert_a_lot.devops.task86_chatterbox_reporting import (
    BenchmarkReport,
    build_report_markdown,
)
from scripts.sir_convert_a_lot.devops.task86_chatterbox_runtime import (
    BenchmarkSettings,
    capture_gpu_snapshot,
    discover_model_snapshot_path,
    ensure_image_present,
    probe_from_service_container,
    restart_sidecar_and_measure,
    start_sidecar,
    synthesize_probe,
    wait_for_sidecar,
    write_runtime_versions,
)

LOGGER = logging.getLogger(__name__)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-86-chatterbox-hemma")
DEFAULT_DOCKERFILE = Path("containers/tts-sidecar-chatterbox/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot/chatterbox-sidecar-task86:local"
DEFAULT_NETWORK = "hule-network"
DEFAULT_NETWORK_ALIAS = "sir-convert-a-lot-chatterbox-task86"
DEFAULT_CONTAINER_NAME = "sir_convert_a_lot_chatterbox_task86"
DEFAULT_SERVICE_CONTAINER = "sir_convert_a_lot_prod"
DEFAULT_CONTAINER_PORT = 8094
DEFAULT_HOST_PORT = 38094
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_REFERENCE_AUDIO = Path(
    "build/verification/task-81-openvoice-v2-hemma/inputs/teacher_reference_voice.m4a"
)
DEFAULT_PROBE_LANGUAGE = "sv"
DEFAULT_SWEDISH_TEXT = (
    "Hej. Det här är ett benchmarkprov för Sir Convert a Lot på Hemma. "
    "Vi testar om Chatterbox kan klona en lärarröst och läsa svensk text på ett tydligt sätt."
)
DEFAULT_ENGLISH_SMOKE_TEXT = "This is a smoke test."


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_path(name: str, *, default: Path) -> Path:
    """Resolve one optional environment override into a filesystem path."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return Path(value.strip())


def _resolve_text_argument(*, text: str | None, text_file: Path | None, label: str) -> str:
    """Return text from one direct value or one file-backed value."""
    if text_file is None:
        if text is None:
            raise SystemExit(f"Task 86 {label} text is missing.")
        return text
    if not text_file.exists():
        raise SystemExit(f"Task 86 {label} text file is missing: {text_file}")
    file_text = text_file.read_text(encoding="utf-8").strip()
    if file_text == "":
        raise SystemExit(f"Task 86 {label} text file is empty: {text_file}")
    return file_text


def _parse_args(argv: list[str]) -> BenchmarkSettings:
    """Parse CLI arguments into normalized Task 86 benchmark settings."""
    parser = argparse.ArgumentParser(description="Run the Task 86 Hemma Chatterbox benchmark.")
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
    parser.add_argument("--reference-audio", type=Path, default=DEFAULT_REFERENCE_AUDIO)
    parser.add_argument("--english-reference-audio", type=Path, default=None)
    parser.add_argument("--smoke-text", default=DEFAULT_ENGLISH_SMOKE_TEXT)
    parser.add_argument("--smoke-text-file", type=Path, default=None)
    parser.add_argument("--probe-text", default=DEFAULT_SWEDISH_TEXT)
    parser.add_argument("--probe-text-file", type=Path, default=None)
    parser.add_argument("--probe-language", choices=("sv", "en"), default=DEFAULT_PROBE_LANGUAGE)
    parser.add_argument("--exaggeration", type=float, default=0.5)
    parser.add_argument("--cfg-weight", type=float, default=0.5)
    parser.add_argument("--segment-text", action="store_true")
    parser.add_argument("--segment-max-chars", type=int, default=220)
    parser.add_argument("--segment-cross-fade-ms", type=int, default=80)
    parser.add_argument(
        "--segment-stitch-mode",
        choices=("simple", "speech_aware"),
        default="simple",
    )
    parser.add_argument("--segment-debug-dir", type=Path, default=None)
    parser.add_argument("--skip-build", action="store_true", help="Reuse an already-built image.")
    parser.add_argument(
        "--retain-container",
        action="store_true",
        help="Keep the sidecar running after evidence capture.",
    )
    args = parser.parse_args(argv)
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
        reference_audio_path=Path(args.reference_audio),
        english_reference_audio_path=Path(args.english_reference_audio)
        if args.english_reference_audio is not None
        else None,
        smoke_text=_resolve_text_argument(
            text=str(args.smoke_text) if args.smoke_text is not None else None,
            text_file=Path(args.smoke_text_file) if args.smoke_text_file is not None else None,
            label="smoke",
        ),
        probe_text=_resolve_text_argument(
            text=str(args.probe_text) if args.probe_text is not None else None,
            text_file=Path(args.probe_text_file) if args.probe_text_file is not None else None,
            label="probe",
        ),
        probe_language=str(args.probe_language),
        exaggeration=float(args.exaggeration),
        cfg_weight=float(args.cfg_weight),
        segment_text=bool(args.segment_text),
        segment_max_chars=int(args.segment_max_chars),
        segment_cross_fade_ms=int(args.segment_cross_fade_ms),
        segment_stitch_mode=str(args.segment_stitch_mode),
        segment_debug_dir=Path(args.segment_debug_dir) if args.segment_debug_dir else None,
        build_image=not bool(args.skip_build),
        retain_container=bool(args.retain_container),
    )


def _ensure_preconditions(settings: BenchmarkSettings) -> None:
    """Fail early if Docker, the network, or required inputs are missing."""
    if not settings.dockerfile_path.resolve().exists():
        raise SystemExit(f"Task 86 Dockerfile is missing: {settings.dockerfile_path}")
    if not settings.reference_audio_path.exists():
        raise SystemExit(f"Task 86 reference audio is missing: {settings.reference_audio_path}")
    if (
        settings.english_reference_audio_path is not None
        and not settings.english_reference_audio_path.exists()
    ):
        raise SystemExit(
            f"Task 86 English reference audio is missing: {settings.english_reference_audio_path}"
        )
    running = run_checked(
        ["sudo", "-n", "docker", "ps", "--format", "{{.Names}}"],
        label="docker ps",
    ).splitlines()
    if settings.service_container not in running:
        raise SystemExit(
            f"Expected service container `{settings.service_container}` to be running on Hemma."
        )
    run_checked(
        ["sudo", "-n", "docker", "network", "inspect", settings.network],
        label="docker network inspect",
    )


def _prepare_output_root(output_root: Path) -> dict[str, Path]:
    """Create a clean deterministic output tree for the current benchmark run."""
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir = output_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(artifacts_dir.iterdir()):
        if child.is_file():
            child.unlink()
    paths = {
        "artifacts_dir": artifacts_dir,
        "report_json": output_root / "report.json",
        "report_md": output_root / "report.md",
        "docker_logs": output_root / "docker_logs.txt",
        "gpu_before": output_root / "gpu-before.txt",
        "gpu_after": output_root / "gpu-after.txt",
        "package_versions": output_root / "package_versions.json",
        "capabilities": output_root / "capabilities.json",
        "voices": output_root / "voices.json",
    }
    segment_debug_dir = output_root / "segment-debug"
    shutil.rmtree(segment_debug_dir, ignore_errors=True)
    paths["segment_debug_dir"] = segment_debug_dir
    for path in paths.values():
        if path in {artifacts_dir, segment_debug_dir}:
            continue
        with suppress(FileNotFoundError):
            path.unlink()
    return paths


def main(argv: list[str] | None = None) -> int:
    """Run the Task 86 benchmark and write deterministic evidence artifacts."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    LOGGER.info(
        (
            "Task 86 starting: output_root=%s skip_build=%s exaggeration=%s "
            "cfg_weight=%s segment_text=%s segment_stitch_mode=%s"
        ),
        settings.output_root,
        not settings.build_image,
        settings.exaggeration,
        settings.cfg_weight,
        settings.segment_text,
        settings.segment_stitch_mode,
    )
    enforce_generated_output_path(settings.output_root, label="output_root")
    paths = _prepare_output_root(settings.output_root)
    effective_settings = replace(
        settings,
        segment_debug_dir=settings.segment_debug_dir
        if settings.segment_debug_dir is not None
        else (paths["segment_debug_dir"] if settings.segment_text else None),
    )
    generated_at = _utc_now_iso()
    run_id = generated_at.replace("-", "").replace(":", "")
    repo_head = run_checked(["git", "rev-parse", "HEAD"], label="git rev-parse HEAD")
    host_base_url = f"http://127.0.0.1:{settings.host_port}"
    internal_base_url = f"http://{settings.network_alias}:{settings.container_port}"
    try:
        LOGGER.info("Checking Docker/service/reference preconditions")
        _ensure_preconditions(effective_settings)
        LOGGER.info("Inspecting GPU identity")
        smi_identity_output = run_checked(
            ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showuse"],
            label="rocm-smi identity",
        )
        rocminfo_output = run_checked(["rocminfo"], label="rocminfo")
        gpu_identity = extract_gpu_identity(smi_identity_output, rocminfo_output)
        capture_gpu_snapshot(paths["gpu_before"])
        remove_existing_benchmark_container(effective_settings.container_name)
        LOGGER.info("Ensuring Chatterbox sidecar image is present")
        build_performed, image_id = ensure_image_present(effective_settings)
        hf_mount = resolve_effective_cache_dir(
            cache_dir=effective_settings.hf_cache_dir,
            home_mount=effective_settings.hf_cache_home_mount,
            image=effective_settings.image,
        )
        model_snapshot_before = discover_model_snapshot_path(hf_mount.canonical_root)
        LOGGER.info("Starting Chatterbox sidecar container")
        start_sidecar(effective_settings, hf_mount=hf_mount)
        first_startup_seconds, capabilities, voices = wait_for_sidecar(effective_settings)
        paths["capabilities"].write_text(
            json.dumps(capabilities.model_dump(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        paths["voices"].write_text(
            json.dumps(voices.model_dump(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_runtime_versions(effective_settings, output_path=paths["package_versions"])
        service_probe_ok, service_backend_id, service_ready = probe_from_service_container(
            effective_settings
        )
        LOGGER.info("Running official English smoke synthesis")
        smoke_probe = synthesize_probe(
            base_url=host_base_url,
            artifacts_dir=paths["artifacts_dir"],
            filename="smoke-test-en.wav",
            text=effective_settings.smoke_text,
            language="en",
            voice_mode="preset",
            preset_voice_id="builtin_default",
            reference_audio_path=None,
        )
        LOGGER.info("Running primary cloning synthesis")
        primary_clone_probe = synthesize_probe(
            base_url=host_base_url,
            artifacts_dir=paths["artifacts_dir"],
            filename=(
                f"scenario-a-{effective_settings.probe_language}-ref-"
                f"{effective_settings.probe_language}-out.wav"
            ),
            text=effective_settings.probe_text,
            language=effective_settings.probe_language,
            voice_mode="reference_clone",
            preset_voice_id=None,
            reference_audio_path=effective_settings.reference_audio_path,
        )
        cross_language_probe = None
        english_reference_evidence = None
        if effective_settings.english_reference_audio_path is not None:
            LOGGER.info("Running optional cross-language cloning synthesis")
            english_reference_evidence = reference_audio_evidence(
                effective_settings.english_reference_audio_path,
                image=effective_settings.image,
            )
            cross_language_probe = synthesize_probe(
                base_url=host_base_url,
                artifacts_dir=paths["artifacts_dir"],
                filename="scenario-b-en-ref-sv-out.wav",
                text=effective_settings.probe_text,
                language="sv",
                voice_mode="reference_clone",
                preset_voice_id=None,
                reference_audio_path=effective_settings.english_reference_audio_path,
            )
        LOGGER.info("Measuring warm restart")
        warm_restart_seconds = restart_sidecar_and_measure(effective_settings)
        capture_gpu_snapshot(paths["gpu_after"])
        reference_evidence = reference_audio_evidence(
            effective_settings.reference_audio_path,
            image=effective_settings.image,
        )
        model_snapshot_after = discover_model_snapshot_path(hf_mount.canonical_root)
        downloaded_during_first_start = (
            model_snapshot_before is None and model_snapshot_after is not None
        )
        report = BenchmarkReport(
            benchmark_id="task-86-chatterbox-hemma",
            run_id=run_id,
            generated_at=generated_at,
            repo_head=repo_head,
            host_base_url=host_base_url,
            internal_base_url=internal_base_url,
            image=effective_settings.image,
            image_id=image_id,
            build_performed=build_performed,
            package_versions_path=paths["package_versions"].as_posix(),
            model_snapshot_path=model_snapshot_after.as_posix() if model_snapshot_after else None,
            model_snapshot_present_before_start=model_snapshot_before is not None,
            model_snapshot_downloaded_during_first_start=downloaded_during_first_start,
            first_startup_seconds=first_startup_seconds,
            cold_start_seconds=first_startup_seconds if downloaded_during_first_start else None,
            warm_restart_seconds=warm_restart_seconds,
            service_probe_ok=service_probe_ok,
            service_backend_id=service_backend_id,
            service_ready=service_ready,
            capability_backend_id=capabilities.backend_id,
            capability_reference_transcript_required=capabilities.voice.reference_transcript_required,
            capability_language_support_sv=next(
                language.support_level.value
                for language in capabilities.languages
                if language.code == "sv"
            ),
            voices_count=len(voices.voices),
            smoke_text=effective_settings.smoke_text,
            smoke_probe=smoke_probe,
            probe_text=effective_settings.probe_text,
            probe_language=effective_settings.probe_language,
            primary_clone_probe=primary_clone_probe,
            cross_language_probe=cross_language_probe,
            reference_audio_path=reference_evidence.input_path,
            reference_audio_duration_seconds=reference_evidence.duration_seconds,
            reference_audio_sample_rate_hz=reference_evidence.sample_rate_hz,
            english_reference_audio_path=english_reference_evidence.input_path
            if english_reference_evidence
            else None,
            english_reference_audio_duration_seconds=english_reference_evidence.duration_seconds
            if english_reference_evidence
            else None,
            english_reference_audio_sample_rate_hz=english_reference_evidence.sample_rate_hz
            if english_reference_evidence
            else None,
            exaggeration=effective_settings.exaggeration,
            cfg_weight=effective_settings.cfg_weight,
            segment_text=effective_settings.segment_text,
            segment_max_chars=effective_settings.segment_max_chars,
            segment_cross_fade_ms=effective_settings.segment_cross_fade_ms,
            segment_stitch_mode=effective_settings.segment_stitch_mode,
            segment_debug_dir=(
                effective_settings.segment_debug_dir.as_posix()
                if (
                    effective_settings.segment_text
                    and effective_settings.segment_debug_dir is not None
                )
                else None
            ),
            hf_cache_host_root=hf_mount.canonical_root.as_posix(),
            gpu_product_name=gpu_identity.product_name,
            gpu_gfx_architecture=gpu_identity.gfx_architecture,
            gpu_before_path=paths["gpu_before"].as_posix(),
            gpu_after_path=paths["gpu_after"].as_posix(),
            docker_logs_path=paths["docker_logs"].as_posix(),
        )
        paths["report_json"].write_text(
            json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        paths["report_md"].write_text(build_report_markdown(report), encoding="utf-8")
        LOGGER.info(
            "Task 86 completed successfully: smoke=%s clone=%s",
            smoke_probe.output_path,
            primary_clone_probe.output_path,
        )
        return 0
    finally:
        LOGGER.info("Capturing docker logs for %s", effective_settings.container_name)
        capture_docker_logs(effective_settings.container_name, output_path=paths["docker_logs"])
        if not effective_settings.retain_container:
            with suppress(SystemExit):
                run_checked(
                    ["sudo", "-n", "docker", "rm", "-f", effective_settings.container_name],
                    label="docker rm task86",
                )


if __name__ == "__main__":
    raise SystemExit(main())
