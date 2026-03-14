"""Runtime helpers for containerized Qwen preprocessing on Hemma.

Purpose:
    Run the staged public-corpus Qwen preprocessing lane inside the shared
    Qwen runtime image so preprocessing and fine-tuning share the same
    canonical execution unit.

Relationships:
    - Used by `cli.ml.qwen_containerized_preprocessing`.
    - Reuses image-build and bind-mount helpers from `ml.qwen.common.runtime`.
    - Executes `cli.ml.qwen_preprocess` inside the Qwen
      runtime image rather than on the Hemma host virtualenv.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import ManifestFamily, MountResolution
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    docker_checked,
    parse_json_object_from_mixed_stdout,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.models import (
    PreprocessingReport,
    PreprocessingStage,
)


@dataclass(frozen=True)
class ContainerizedPreprocessingSettings:
    """Normalized settings for the containerized preprocessing runner."""

    output_root: Path
    runs_root: Path
    run_id: str | None
    run_root: Path | None
    promote_on_success: bool
    stage: PreprocessingStage
    finalization_families: tuple[ManifestFamily, ...]
    dockerfile_path: Path
    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    scratch_build_root: Path
    scratch_build_home_mount: Path
    data_root: Path
    data_root_home_mount: Path
    build_image: bool
    fleurs_max_rows_per_split: int
    rixvox_splits: tuple[str, ...]
    rixvox_max_rows_per_split: int | None
    audio_codes_chunk_size: int
    row_worker_count: int
    gpu_asr_worker_count: int
    resume_row_processing: bool


@dataclass(frozen=True)
class ContainerizedPreprocessingRun:
    """Parsed results from one in-container preprocessing run."""

    preprocessing_report: PreprocessingReport
    command: list[str]


CONTAINER_BUILD_ROOT = Path("/app/build")
DEFAULT_GOVERNED_DEVICE_MAP = "cuda:0"
DEFAULT_GOVERNED_DTYPE = "bfloat16"
DEFAULT_GOVERNED_ATTN_IMPLEMENTATION = "flash_attention_2"


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from the preprocessing JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Containerized preprocessing payload returned malformed `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from the preprocessing JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Containerized preprocessing payload returned malformed `{key}`.")
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from the preprocessing JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Containerized preprocessing payload returned malformed `{key}`.")
    return list(value)


def _required_manifest_counts(payload: dict[str, object]) -> dict[ManifestFamily, int]:
    """Return typed manifest counts from the preprocessing JSON payload."""
    value = payload.get("manifest_counts")
    if not isinstance(value, dict):
        raise SystemExit(
            "Containerized preprocessing payload returned malformed `manifest_counts`."
        )
    manifest_counts: dict[ManifestFamily, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not isinstance(count, int):
            raise SystemExit(
                "Containerized preprocessing payload returned malformed `manifest_counts`."
            )
        manifest_counts[_manifest_family_from_key(key)] = count
    return manifest_counts


def _manifest_family_from_key(key: str) -> ManifestFamily:
    """Convert one manifest-count JSON key into the typed manifest-family literal."""
    if key == "swedish_smoke_train":
        return "swedish_smoke_train"
    if key == "swedish_pilot_train":
        return "swedish_pilot_train"
    if key == "swedish_scaleup_train":
        return "swedish_scaleup_train"
    if key == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    if key == "swedish_final_test":
        return "swedish_final_test"
    if key == "swedish_waxholm_control":
        return "swedish_waxholm_control"
    raise SystemExit("Containerized preprocessing payload returned an unknown manifest family.")


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    try:
        relative_path = host_path.relative_to(scratch_root)
    except ValueError as exc:
        raise SystemExit(
            "Scratch-backed preprocessing paths must live under the configured "
            f"scratch_build_root `{scratch_root.as_posix()}`, got `{host_path.as_posix()}`."
        ) from exc
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def build_containerized_preprocessing_command(
    settings: ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
    scratch_mount: MountResolution,
) -> list[str]:
    """Build the Docker command that runs preprocessing inside the Qwen runtime image."""
    container_hf_home = hf_mount.canonical_root.as_posix()
    container_hf_hub_cache = CONTAINER_HF_HUB_CACHE.replace(
        "/cache/huggingface",
        container_hf_home,
    )
    container_torch_home = CONTAINER_TORCH_HOME.replace("/cache/huggingface", container_hf_home)
    container_runs_root = _containerize_scratch_path(
        settings.runs_root,
        scratch_root=settings.scratch_build_root,
    )
    command = [
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
        f"HF_HOME={container_hf_home}",
        "-e",
        f"HUGGINGFACE_HUB_CACHE={container_hf_hub_cache}",
        "-e",
        f"TORCH_HOME={container_torch_home}",
        "-v",
        f"{repo_root.as_posix()}:/app",
        "-v",
        f"{scratch_mount.effective_root.as_posix()}:{CONTAINER_BUILD_ROOT.as_posix()}",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{hf_mount.canonical_root.as_posix()}",
        "-v",
        f"{data_mount.effective_root.as_posix()}:{data_mount.canonical_root.as_posix()}:ro",
        "--workdir",
        "/app",
        "--entrypoint",
        "python",
        settings.image,
        "-m",
        "scripts.sir_convert_a_lot.cli.ml.qwen_preprocess",
        "--source-mode",
        "staged-public-corpus",
        "--stage",
        settings.stage,
        "--runs-root",
        container_runs_root,
        "--data-root",
        data_mount.canonical_root.as_posix(),
        "--fleurs-max-rows-per-split",
        str(settings.fleurs_max_rows_per_split),
        "--rixvox-splits",
        ",".join(settings.rixvox_splits),
        "--audio-codes-chunk-size",
        str(settings.audio_codes_chunk_size),
        "--audio-codes-device-map",
        DEFAULT_GOVERNED_DEVICE_MAP,
        "--audio-codes-dtype",
        DEFAULT_GOVERNED_DTYPE,
        "--audio-codes-attn-implementation",
        DEFAULT_GOVERNED_ATTN_IMPLEMENTATION,
        "--require-audio-codes-gpu",
        "--row-worker-count",
        str(settings.row_worker_count),
        "--gpu-asr-worker-count",
        str(settings.gpu_asr_worker_count),
        "--finalization-families",
        ",".join(settings.finalization_families),
    ]
    if settings.run_id is not None:
        command.extend(["--run-id", settings.run_id])
    if settings.run_root is not None:
        command.extend(
            [
                "--run-root",
                _containerize_scratch_path(
                    settings.run_root,
                    scratch_root=settings.scratch_build_root,
                ),
            ]
        )
    if settings.promote_on_success:
        command.append("--promote-on-success")
    if settings.resume_row_processing:
        command.append("--resume-row-processing")
    if settings.rixvox_max_rows_per_split is not None:
        command.extend(
            [
                "--rixvox-max-rows-per-split",
                str(settings.rixvox_max_rows_per_split),
            ]
        )
    return command


def run_containerized_preprocessing(
    settings: ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
    scratch_mount: MountResolution,
) -> ContainerizedPreprocessingRun:
    """Run the public-corpus preprocessing lane inside the Qwen runtime image."""
    command = build_containerized_preprocessing_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
        scratch_mount=scratch_mount,
    )
    raw_output = docker_checked(command, label="docker run qwen containerized preprocessing")
    payload = parse_json_object_from_mixed_stdout(raw_output)
    preprocessing_report = PreprocessingReport(
        output_root=_required_str(payload, "output_root"),
        datasets=_required_str_list(payload, "datasets"),
        asr_model=_required_str(payload, "asr_model"),
        asr_revision=_required_str(payload, "asr_revision"),
        tokenizer_model=_required_str(payload, "tokenizer_model"),
        inventory_rows=_required_int(payload, "inventory_rows"),
        curated_rows=_required_int(payload, "curated_rows"),
        admitted_rows=_required_int(payload, "admitted_rows"),
        prepared_rows=_required_int(payload, "prepared_rows"),
        speaker_ids=_required_str_list(payload, "speaker_ids"),
        manifest_counts=_required_manifest_counts(payload),
    )
    return ContainerizedPreprocessingRun(
        preprocessing_report=preprocessing_report,
        command=["sudo", "-n", "docker", *command],
    )
