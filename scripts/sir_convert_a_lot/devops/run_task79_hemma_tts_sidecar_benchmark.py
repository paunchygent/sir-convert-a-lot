"""Run the Task 79 Hemma TTS sidecar benchmark on the live R9700 host.

Purpose:
    Prove that the chosen sidecar stack can boot on Hemma as an isolated ROCm
    container, is reachable from the existing Sir Convert-a-Lot service
    container, and can synthesize `wav` plus probe compressed-format support.

Relationships:
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run benchmark:task-79`.
    - Uses the committed Task 79 stage-config asset shipped in this repo.
    - Writes deterministic evidence under `build/verification/task-79-hemma-tts-sidecar/`.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from contextlib import suppress
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_reporting import (
    BenchmarkReport,
    SpeechRequestEvidence,
    VoicesEvidence,
    build_report_markdown,
    write_json,
)
from scripts.sir_convert_a_lot.devops.task79_hemma_tts_sidecar_runtime import (
    BenchmarkSettings,
    audio_probe,
    docker_checked,
    ensure_image_present,
    ensure_sidecar_preconditions,
    extract_gpu_identity,
    inspect_runtime,
    prefetch_qwen3_tts_assets,
    probe_from_service_container,
    python_recommendation,
    remove_existing_benchmark_container,
    resolve_effective_hf_cache_dir,
    run_checked,
    start_sidecar,
    voice_names_from_payload,
    wait_for_voices,
)
from scripts.sir_convert_a_lot.devops.task79_qwen3_tts_request_payload import (
    prepare_request_inputs,
    resolve_text_input,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-79-hemma-tts-sidecar")
DEFAULT_IMAGE = "vllm/vllm-omni-rocm:v0.16.0"
DEFAULT_CUSTOM_VOICE_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
DEFAULT_BASE_MODEL = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_NETWORK = "hule-network"
DEFAULT_NETWORK_ALIAS = "sir-convert-a-lot-tts-task79"
DEFAULT_CONTAINER_NAME = "sir_convert_a_lot_tts_task79"
DEFAULT_SERVICE_CONTAINER = "sir_convert_a_lot_prod"
DEFAULT_CONTAINER_PORT = 8091
DEFAULT_HOST_PORT = 38091
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_VOICE = "ryan"
DEFAULT_HEMMA_HF_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT"
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_TEXT = (
    "Hello from Sir Convert a Lot. This benchmark proves a sidecar backed text to speech "
    "stack on the Hemma Radeon AI PRO R9700. The voice should sound clear, steady, and ready "
    "for audiobook style delivery."
)
STAGE_CONFIG_PATH = Path("scripts/sir_convert_a_lot/devops/task79_qwen3_tts_stage_config.yaml")


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_hf_cache_dir() -> Path:
    """Resolve the canonical Hemma Hugging Face cache path for Task 79."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE
    return Path(configured_path.strip())


def _default_hf_cache_home_mount() -> Path:
    """Resolve the home-backed mount path used when Docker cannot bind `/srv/*` directly."""
    configured_path = os.environ.get(DEFAULT_HEMMA_HF_CACHE_HOME_MOUNT_ENV)
    if configured_path is None or configured_path.strip() == "":
        return DEFAULT_HF_CACHE_HOME_MOUNT
    return Path(configured_path.strip())


def _parse_args(argv: list[str]) -> BenchmarkSettings:
    """Parse CLI arguments into normalized benchmark settings."""
    parser = argparse.ArgumentParser(description="Run the Task 79 Hemma TTS benchmark.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--model", default=None)
    parser.add_argument(
        "--task-type",
        choices=("CustomVoice", "Base"),
        default="CustomVoice",
    )
    parser.add_argument("--language", default="Auto")
    parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
    parser.add_argument("--network", default=DEFAULT_NETWORK)
    parser.add_argument("--network-alias", default=DEFAULT_NETWORK_ALIAS)
    parser.add_argument("--container-name", default=DEFAULT_CONTAINER_NAME)
    parser.add_argument("--service-container", default=DEFAULT_SERVICE_CONTAINER)
    parser.add_argument("--container-port", type=int, default=DEFAULT_CONTAINER_PORT)
    parser.add_argument("--host-port", type=int, default=DEFAULT_HOST_PORT)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--startup-timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--hf-cache-dir",
        type=Path,
        default=_default_hf_cache_dir(),
        help=(
            "Host path for the persistent Hugging Face cache. Defaults to "
            "`SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH` when set, otherwise "
            "`/srv/scratch/sir-convert-a-lot/cache/huggingface`."
        ),
    )
    parser.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=_default_hf_cache_home_mount(),
        help=(
            "Home-backed mount path used when Docker cannot bind the canonical `/srv/*` cache "
            "path directly."
        ),
    )
    parser.add_argument("--probe-text", default=None)
    parser.add_argument("--probe-text-file", type=Path, default=None)
    parser.add_argument("--instructions", default=None)
    parser.add_argument("--instructions-file", type=Path, default=None)
    parser.add_argument("--reference-audio", type=Path, default=None)
    parser.add_argument("--reference-transcript", default=None)
    parser.add_argument("--reference-transcript-file", type=Path, default=None)
    parser.add_argument("--hf-token", default=None)
    parser.add_argument(
        "--response-formats",
        default="wav,mp3",
        help="Comma-separated response formats to probe in order.",
    )
    parser.add_argument(
        "--skip-pull-image",
        action="store_true",
        help="Skip `docker pull` when the image is already present locally.",
    )
    parser.add_argument(
        "--retain-container",
        action="store_true",
        help="Keep the benchmark container running after evidence capture.",
    )
    args = parser.parse_args(argv)
    model = (
        str(args.model).strip()
        if args.model is not None
        else (DEFAULT_BASE_MODEL if str(args.task_type) == "Base" else DEFAULT_CUSTOM_VOICE_MODEL)
    )
    probe_text = resolve_text_input(
        direct_value=None if args.probe_text is None else str(args.probe_text),
        file_path=args.probe_text_file,
        label="probe text",
    )
    instructions = resolve_text_input(
        direct_value=None if args.instructions is None else str(args.instructions),
        file_path=args.instructions_file,
        label="instructions",
    )
    reference_transcript = resolve_text_input(
        direct_value=(
            None if args.reference_transcript is None else str(args.reference_transcript)
        ),
        file_path=args.reference_transcript_file,
        label="reference transcript",
    )
    response_formats = tuple(
        candidate.strip().lower()
        for candidate in str(args.response_formats).split(",")
        if candidate.strip() != ""
    )
    if not response_formats:
        raise SystemExit("At least one response format must be provided.")
    return BenchmarkSettings(
        output_root=Path(args.output_root),
        image=str(args.image),
        model=model,
        task_type=str(args.task_type),
        language=str(args.language).strip(),
        tokenizer_model=str(args.tokenizer_model),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        network=str(args.network),
        network_alias=str(args.network_alias),
        container_name=str(args.container_name),
        service_container=str(args.service_container),
        container_port=int(args.container_port),
        host_port=int(args.host_port),
        voice=str(args.voice),
        response_formats=response_formats,
        startup_timeout_seconds=float(args.startup_timeout_seconds),
        hf_cache_dir=Path(args.hf_cache_dir),
        probe_text=probe_text if probe_text is not None else DEFAULT_TEXT,
        instructions=instructions,
        reference_audio=Path(args.reference_audio) if args.reference_audio is not None else None,
        reference_transcript=reference_transcript,
        hf_token=str(args.hf_token).strip() if args.hf_token else None,
        pull_image=not bool(args.skip_pull_image),
        retain_container=bool(args.retain_container),
        stage_config_path=STAGE_CONFIG_PATH,
    )


def _prepare_output_root(output_root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    """Create a clean deterministic output tree for the current benchmark run."""
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir = output_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = output_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    for managed_dir in (artifacts_dir, inputs_dir):
        for artifact_path in managed_dir.iterdir():
            if artifact_path.is_dir():
                shutil.rmtree(artifact_path)
                continue
            artifact_path.unlink()

    logs_path = output_root / "docker_logs.txt"
    report_json_path = output_root / "report.json"
    report_md_path = output_root / "report.md"
    failure_path = output_root / "failure.txt"
    for generated_path in (logs_path, report_json_path, report_md_path, failure_path):
        with suppress(FileNotFoundError):
            generated_path.unlink()
    return artifacts_dir, inputs_dir, logs_path, report_json_path, report_md_path, failure_path


def main(argv: list[str] | None = None) -> int:
    """Run the Task 79 sidecar benchmark and write report artifacts."""
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(settings.output_root, label="output_root")
    (
        artifacts_dir,
        inputs_dir,
        logs_path,
        report_json_path,
        report_md_path,
        failure_path,
    ) = _prepare_output_root(settings.output_root)
    prepared_inputs = prepare_request_inputs(
        inputs_dir=inputs_dir,
        probe_text=settings.probe_text,
        instructions=settings.instructions,
        reference_audio=settings.reference_audio,
        reference_transcript=settings.reference_transcript,
    )

    ensure_sidecar_preconditions(settings)
    smi_identity_output = run_checked(
        ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showuse"],
        label="rocm-smi identity",
    )
    rocminfo_output = run_checked(["rocminfo"], label="rocminfo")
    gpu_identity = extract_gpu_identity(smi_identity_output, rocminfo_output)

    pull_performed = False
    cleanup_performed = False
    report: BenchmarkReport | None = None
    failure_message: str | None = None
    try:
        remove_existing_benchmark_container(settings.container_name)
        pull_performed, image_id = ensure_image_present(settings)
        settings = replace(settings, hf_cache_dir=resolve_effective_hf_cache_dir(settings))
        prefetch_qwen3_tts_assets(settings)
        start_sidecar(settings)
        readiness_seconds, host_payload = wait_for_voices(settings)
        voice_names = voice_names_from_payload(host_payload)
        if settings.task_type != "Base" and settings.voice not in voice_names:
            supported = ", ".join(voice_names)
            raise SystemExit(
                "Configured Task 79 voice "
                f"`{settings.voice}` is unavailable. Supported: {supported}"
            )
        service_probe_ok, service_voice_count = probe_from_service_container(settings)
        sidecar_runtime = inspect_runtime(settings, image_id=image_id)

        host_base_url = f"http://127.0.0.1:{settings.host_port}"
        internal_base_url = f"http://{settings.network_alias}:{settings.container_port}"
        audio_results = []
        peak_gpu_busy_percent = gpu_identity.peak_gpu_busy_percent
        peak_vram_used_bytes = gpu_identity.peak_vram_used_bytes
        for response_format in settings.response_formats:
            result, busy_peak, vram_peak = audio_probe(
                settings=settings,
                base_url=host_base_url,
                response_format=response_format,
                artifacts_dir=artifacts_dir,
            )
            audio_results.append(result)
            peak_gpu_busy_percent = max(peak_gpu_busy_percent, busy_peak)
            peak_vram_used_bytes = max(peak_vram_used_bytes, vram_peak)
        if not any(result.ok and result.response_format == "wav" for result in audio_results):
            raise SystemExit(
                "Task 79 acceptance failed: `/v1/audio/speech` did not succeed for wav."
            )

        gpu_identity = type(gpu_identity)(
            product_name=gpu_identity.product_name,
            gfx_architecture=gpu_identity.gfx_architecture,
            vram_total_bytes=gpu_identity.vram_total_bytes,
            peak_gpu_busy_percent=peak_gpu_busy_percent,
            peak_vram_used_bytes=peak_vram_used_bytes,
        )
        report = BenchmarkReport(
            benchmark_id="task-79-hemma-tts-sidecar",
            generated_at=_utc_now_iso(),
            repo_head=run_checked(["git", "rev-parse", "HEAD"], label="git rev-parse HEAD"),
            host_base_url=host_base_url,
            internal_base_url=internal_base_url,
            host_hf_cache_dir=settings.hf_cache_dir.as_posix(),
            speech_request=SpeechRequestEvidence(
                task_type=settings.task_type,
                model=settings.model,
                language=settings.language,
                voice=None if settings.task_type == "Base" else settings.voice,
                probe_text_path=prepared_inputs.probe_text_path,
                instructions_path=prepared_inputs.instructions_path,
                reference_audio_path=prepared_inputs.reference_audio_path,
                reference_audio_sha256=prepared_inputs.reference_audio_sha256,
                reference_audio_duration_seconds=prepared_inputs.reference_audio_duration_seconds,
                reference_transcript_path=prepared_inputs.reference_transcript_path,
            ),
            gpu_identity=gpu_identity,
            sidecar_runtime=sidecar_runtime,
            voices_evidence=VoicesEvidence(
                host_probe_ok=True,
                service_probe_ok=service_probe_ok,
                host_voice_count=len(voice_names),
                service_voice_count=service_voice_count,
                voice_names=voice_names,
            ),
            audio_results=audio_results,
            python_recommendation=python_recommendation(sidecar_runtime.python_version),
            pull_performed=pull_performed,
            readiness_seconds=readiness_seconds,
            cleanup_performed=not settings.retain_container,
            docker_logs_path=logs_path.as_posix(),
        )
        write_json(report_json_path, report)
        report_md_path.write_text(build_report_markdown(report) + "\n", encoding="utf-8")
    except SystemExit as exc:
        failure_message = str(exc)
        raise
    finally:
        with suppress(SystemExit):
            logs_output = docker_checked(
                ["logs", settings.container_name],
                label="docker logs task79 container",
            )
            logs_path.write_text(
                logs_output + "\n",
                encoding="utf-8",
            )
        if not settings.retain_container:
            with suppress(SystemExit):
                docker_checked(["rm", "-f", settings.container_name], label="docker rm -f task79")
                cleanup_performed = True
        if failure_message is not None:
            failure_path.write_text(failure_message + "\n", encoding="utf-8")
        if cleanup_performed and report is not None:
            report = BenchmarkReport(
                benchmark_id=report.benchmark_id,
                generated_at=report.generated_at,
                repo_head=report.repo_head,
                host_base_url=report.host_base_url,
                internal_base_url=report.internal_base_url,
                host_hf_cache_dir=report.host_hf_cache_dir,
                speech_request=report.speech_request,
                gpu_identity=report.gpu_identity,
                sidecar_runtime=report.sidecar_runtime,
                voices_evidence=report.voices_evidence,
                audio_results=report.audio_results,
                python_recommendation=report.python_recommendation,
                pull_performed=report.pull_performed,
                readiness_seconds=report.readiness_seconds,
                cleanup_performed=True,
                docker_logs_path=report.docker_logs_path,
            )
            write_json(report_json_path, report)
            report_md_path.write_text(build_report_markdown(report) + "\n", encoding="utf-8")

    print(report_json_path.as_posix())
    print(report_md_path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
