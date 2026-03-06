"""Run the Task 81 Hemma OpenVoice sidecar benchmark on the live R9700 host.

Purpose:
    Prove that the first normalized OpenVoice V2 sidecar adapter can boot on
    Hemma, remain internal-network only, reuse persistent model caches, and
    synthesize Swedish probe audio from an approved teacher reference clip.

Relationships:
    - Intended to run on Hemma via `pdm run run-hemma -- pdm run benchmark:task-81 ...`.
    - Uses the normalized ADR-0007 sidecar endpoints:
      `/health`, `/capabilities`, `/voices`, and `/synthesize`.
    - Writes deterministic evidence under `build/verification/task-81-openvoice-v2-hemma/`.
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
from scripts.sir_convert_a_lot.devops.task81_openvoice_reporting import (
    BenchmarkReport,
    CacheEvidence,
    GpuIdentity,
    build_report_markdown,
    write_json,
)
from scripts.sir_convert_a_lot.devops.task81_openvoice_runtime import (
    BenchmarkSettings,
    MountResolution,
    capture_docker_logs,
    ensure_image_present,
    ensure_sidecar_preconditions,
    extract_gpu_identity,
    inspect_runtime,
    prefetch_hf_assets,
    prefetch_openvoice_assets,
    probe_from_service_container,
    reference_audio_evidence,
    remove_existing_benchmark_container,
    resolve_effective_cache_dir,
    run_checked,
    start_sidecar,
    synthesize_probe,
    wait_for_sidecar,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/task-81-openvoice-v2-hemma")
DEFAULT_DOCKERFILE = Path("containers/tts-sidecar-openvoice/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot/openvoice-sidecar-task81:local"
DEFAULT_NETWORK = "hule-network"
DEFAULT_NETWORK_ALIAS = "sir-convert-a-lot-openvoice-task81"
DEFAULT_CONTAINER_NAME = "sir_convert_a_lot_openvoice_task81"
DEFAULT_SERVICE_CONTAINER = "sir_convert_a_lot_prod"
DEFAULT_CONTAINER_PORT = 8092
DEFAULT_HOST_PORT = 38092
DEFAULT_TIMEOUT_SECONDS = 1800.0
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_OPENVOICE_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/openvoice")
DEFAULT_OPENVOICE_CACHE_HOME_MOUNT = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/cache/openvoice"
)
DEFAULT_OPENVOICE_CHECKPOINT_URL = (
    "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip"
)
DEFAULT_BASE_MODEL_ID = "facebook/mms-tts-swe"
DEFAULT_SWEDISH_TEXT = (
    "Hej. Det här är ett benchmarkprov för Sir Convert a Lot på Hemma. "
    "Vi testar om OpenVoice V2 kan klona en lärarröst och läsa svensk text på ett tydligt sätt."
)
DEFAULT_LISTENING_NOTES = (
    "Pending manual listening review. Use the generated Swedish sample artifact to judge "
    "naturalness, "
    "pronunciation, and whether the cloned timbre remains recognizably teacher-like."
)
DEFAULT_HF_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_PATH"
DEFAULT_HF_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_HF_CACHE_HOME_MOUNT"
DEFAULT_OPENVOICE_CACHE_ENV = "SIR_CONVERT_A_LOT_HEMMA_OPENVOICE_CACHE_PATH"
DEFAULT_OPENVOICE_CACHE_HOME_MOUNT_ENV = "SIR_CONVERT_A_LOT_HEMMA_OPENVOICE_CACHE_HOME_MOUNT"


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _env_path(name: str, *, default: Path) -> Path:
    """Resolve one optional environment override into a filesystem path."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return Path(value.strip())


def _parse_args(argv: list[str]) -> BenchmarkSettings:
    """Parse CLI arguments into normalized Task 81 benchmark settings."""
    parser = argparse.ArgumentParser(description="Run the Task 81 Hemma OpenVoice benchmark.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--dockerfile", type=Path, default=DEFAULT_DOCKERFILE)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--openvoice-checkpoint-url", default=DEFAULT_OPENVOICE_CHECKPOINT_URL)
    parser.add_argument("--base-model-id", default=DEFAULT_BASE_MODEL_ID)
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
        default=_env_path(DEFAULT_HF_CACHE_ENV, default=DEFAULT_HF_CACHE),
    )
    parser.add_argument(
        "--hf-cache-home-mount",
        type=Path,
        default=_env_path(DEFAULT_HF_CACHE_HOME_MOUNT_ENV, default=DEFAULT_HF_CACHE_HOME_MOUNT),
    )
    parser.add_argument(
        "--openvoice-cache-dir",
        type=Path,
        default=_env_path(DEFAULT_OPENVOICE_CACHE_ENV, default=DEFAULT_OPENVOICE_CACHE),
    )
    parser.add_argument(
        "--openvoice-cache-home-mount",
        type=Path,
        default=_env_path(
            DEFAULT_OPENVOICE_CACHE_HOME_MOUNT_ENV,
            default=DEFAULT_OPENVOICE_CACHE_HOME_MOUNT,
        ),
    )
    parser.add_argument("--reference-audio", type=Path, required=True)
    parser.add_argument("--probe-text", default=DEFAULT_SWEDISH_TEXT)
    parser.add_argument("--skip-build", action="store_true", help="Reuse an already-built image.")
    parser.add_argument(
        "--retain-container",
        action="store_true",
        help="Keep the benchmark container running after evidence capture.",
    )
    args = parser.parse_args(argv)
    return BenchmarkSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile),
        image=str(args.image),
        openvoice_checkpoint_url=str(args.openvoice_checkpoint_url),
        base_model_id=str(args.base_model_id),
        network=str(args.network),
        network_alias=str(args.network_alias),
        container_name=str(args.container_name),
        service_container=str(args.service_container),
        container_port=int(args.container_port),
        host_port=int(args.host_port),
        startup_timeout_seconds=float(args.startup_timeout_seconds),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        openvoice_cache_dir=Path(args.openvoice_cache_dir),
        openvoice_cache_home_mount=Path(args.openvoice_cache_home_mount),
        reference_audio_path=Path(args.reference_audio),
        probe_text=str(args.probe_text),
        build_image=not bool(args.skip_build),
        retain_container=bool(args.retain_container),
    )


def _prepare_output_root(output_root: Path) -> tuple[Path, Path, Path, Path, Path]:
    """Create a clean deterministic output tree for the current benchmark run."""
    output_root.mkdir(parents=True, exist_ok=True)
    artifacts_dir = output_root / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for artifact_path in artifacts_dir.iterdir():
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
    return artifacts_dir, logs_path, report_json_path, report_md_path, failure_path


def _official_support_summary() -> list[str]:
    """Return the official upstream support statements that frame Task 81 evidence."""
    return [
        "OpenVoice V2 inherits V1 features, including zero-shot cross-lingual voice cloning.",
        "OpenVoice V2 natively supports English, Spanish, French, Chinese, Japanese, and Korean.",
        "OpenVoice upstream states it can support any language when paired with a base "
        "speaker in that language.",
        "This Task 81 adapter uses facebook/mms-tts-swe as the Swedish base speaker to "
        "test that claim on Hemma.",
    ]


def _cache_evidence(hf_mount: MountResolution, openvoice_mount: MountResolution) -> CacheEvidence:
    """Build the persistent-cache evidence payload for the benchmark report."""
    return CacheEvidence(
        openvoice_host_root=openvoice_mount.canonical_root.as_posix(),
        openvoice_container_root="/cache/openvoice",
        hf_host_root=hf_mount.canonical_root.as_posix(),
        hf_container_root="/cache/huggingface",
        openvoice_home_mount_used=openvoice_mount.used_home_mount,
        hf_home_mount_used=hf_mount.used_home_mount,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the Task 81 benchmark and write deterministic evidence artifacts."""
    settings = _parse_args(sys.argv[1:] if argv is None else argv)
    enforce_generated_output_path(settings.output_root, label="output_root")
    artifacts_dir, logs_path, report_json_path, report_md_path, failure_path = _prepare_output_root(
        settings.output_root
    )

    ensure_sidecar_preconditions(settings)
    smi_identity_output = run_checked(
        ["rocm-smi", "--showproductname", "--showmeminfo", "vram", "--showuse"],
        label="rocm-smi identity",
    )
    rocminfo_output = run_checked(["rocminfo"], label="rocminfo")
    parsed_gpu_identity = extract_gpu_identity(smi_identity_output, rocminfo_output)
    gpu_identity = GpuIdentity(
        product_name=parsed_gpu_identity.product_name,
        gfx_architecture=parsed_gpu_identity.gfx_architecture,
        vram_total_bytes=parsed_gpu_identity.vram_total_bytes,
        peak_gpu_busy_percent=parsed_gpu_identity.peak_gpu_busy_percent,
        peak_vram_used_bytes=parsed_gpu_identity.peak_vram_used_bytes,
    )
    reference_audio = reference_audio_evidence(settings.reference_audio_path)

    build_performed = False
    cleanup_performed = False
    report: BenchmarkReport | None = None
    try:
        remove_existing_benchmark_container(settings.container_name)
        build_performed, image_id = ensure_image_present(settings)
        hf_mount = resolve_effective_cache_dir(
            cache_dir=settings.hf_cache_dir,
            home_mount=settings.hf_cache_home_mount,
            image=settings.image,
        )
        openvoice_mount = resolve_effective_cache_dir(
            cache_dir=settings.openvoice_cache_dir,
            home_mount=settings.openvoice_cache_home_mount,
            image=settings.image,
        )
        prefetch_openvoice_assets(settings, openvoice_mount)
        prefetch_hf_assets(settings, hf_mount)
        start_sidecar(settings, hf_mount=hf_mount, openvoice_mount=openvoice_mount)
        readiness_seconds, _health_payload, capabilities = wait_for_sidecar(settings)
        internal_probe = probe_from_service_container(settings)
        sidecar_runtime = inspect_runtime(settings, image_id=image_id)

        host_base_url = f"http://127.0.0.1:{settings.host_port}"
        internal_base_url = f"http://{settings.network_alias}:{settings.container_port}"
        synthesis_result, peak_busy, peak_vram = synthesize_probe(
            settings=settings,
            base_url=host_base_url,
            artifacts_dir=artifacts_dir,
        )
        gpu_identity = GpuIdentity(
            product_name=gpu_identity.product_name,
            gfx_architecture=gpu_identity.gfx_architecture,
            vram_total_bytes=gpu_identity.vram_total_bytes,
            peak_gpu_busy_percent=max(gpu_identity.peak_gpu_busy_percent, peak_busy),
            peak_vram_used_bytes=max(gpu_identity.peak_vram_used_bytes, peak_vram),
        )
        if synthesis_result.ok is not True:
            raise SystemExit(
                "Task 81 acceptance failed: normalized `/synthesize` did not return wav audio."
            )
        report = BenchmarkReport(
            benchmark_id="task-81-openvoice-v2-hemma",
            generated_at=_utc_now_iso(),
            repo_head=run_checked(["git", "rev-parse", "HEAD"], label="git rev-parse HEAD"),
            host_base_url=host_base_url,
            internal_base_url=internal_base_url,
            gpu_identity=gpu_identity,
            cache_evidence=_cache_evidence(hf_mount, openvoice_mount),
            sidecar_runtime=sidecar_runtime,
            internal_probe=internal_probe,
            capabilities=capabilities,
            reference_audio=reference_audio,
            synthesis_result=synthesis_result,
            official_support_summary=_official_support_summary(),
            listening_notes=DEFAULT_LISTENING_NOTES,
            pull_performed=False,
            build_performed=build_performed,
            readiness_seconds=readiness_seconds,
            cleanup_performed=not settings.retain_container,
            docker_logs_path=logs_path.as_posix(),
        )
        write_json(report_json_path, report)
        report_md_path.write_text(build_report_markdown(report), encoding="utf-8")
        return 0
    except SystemExit as exc:
        failure_path.write_text(str(exc) + "\n", encoding="utf-8")
        return 1
    finally:
        capture_docker_logs(settings.container_name, output_path=logs_path)
        if not settings.retain_container:
            with suppress(SystemExit):
                run_checked(
                    ["sudo", "-n", "docker", "rm", "-f", settings.container_name],
                    label="docker rm task81",
                )
            cleanup_performed = True
        if report is not None:
            if report.cleanup_performed != cleanup_performed:
                report = replace(report, cleanup_performed=cleanup_performed)
                write_json(report_json_path, report)
                report_md_path.write_text(build_report_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
