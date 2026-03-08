"""Runtime helpers for Task 109 containerized Qwen preprocessing on Hemma.

Purpose:
    Run the staged public-corpus Qwen preprocessing lane inside the selected
    Task 100-style Qwen runtime image so preprocessing and fine-tuning share
    the same canonical execution unit.

Relationships:
    - Used by `run_task109_hemma_qwen_containerized_preprocessing.py`.
    - Reuses image-build and bind-mount helpers from
      `task100_qwen_finetune_runtime.py`.
    - Executes `run_task103_qwen_swedish_preprocessing.py` inside the Qwen
      runtime image rather than on the Hemma host virtualenv.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task100_qwen_finetune_runtime import (
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    MountResolution,
    docker_checked,
    parse_json_object_from_mixed_stdout,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_core import (
    ManifestFamily,
    Task103PreprocessingReport,
)


@dataclass(frozen=True)
class Task109ContainerizedPreprocessingSettings:
    """Normalized settings for the Task 109 containerized preprocessing runner."""

    output_root: Path
    dockerfile_path: Path
    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    data_root: Path
    data_root_home_mount: Path
    build_image: bool
    fleurs_max_rows_per_split: int


@dataclass(frozen=True)
class ContainerizedPreprocessingRun:
    """Parsed results from one in-container Task 103 preprocessing run."""

    preprocessing_report: Task103PreprocessingReport
    command: list[str]


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from the Task 103 JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise SystemExit(f"Task 109 preprocessing payload returned malformed `{key}`.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from the Task 103 JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise SystemExit(f"Task 109 preprocessing payload returned malformed `{key}`.")
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from the Task 103 JSON payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Task 109 preprocessing payload returned malformed `{key}`.")
    return list(value)


def _required_manifest_counts(payload: dict[str, object]) -> dict[ManifestFamily, int]:
    """Return typed manifest counts from the Task 103 JSON payload."""
    value = payload.get("manifest_counts")
    if not isinstance(value, dict):
        raise SystemExit("Task 109 preprocessing payload returned malformed `manifest_counts`.")
    manifest_counts: dict[ManifestFamily, int] = {}
    for key, count in value.items():
        if not isinstance(key, str) or not isinstance(count, int):
            raise SystemExit(
                "Task 109 preprocessing payload returned malformed `manifest_counts`."
            )
        manifest_counts[key] = count
    return manifest_counts


def build_containerized_preprocessing_command(
    settings: Task109ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
) -> list[str]:
    """Build the Docker command that runs Task 103 inside the Qwen runtime image."""
    container_hf_home = hf_mount.canonical_root.as_posix()
    container_hf_hub_cache = CONTAINER_HF_HUB_CACHE.replace(
        "/cache/huggingface",
        container_hf_home,
    )
    container_torch_home = CONTAINER_TORCH_HOME.replace("/cache/huggingface", container_hf_home)
    return [
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
        f"{hf_mount.effective_root.as_posix()}:{hf_mount.canonical_root.as_posix()}",
        "-v",
        f"{data_mount.effective_root.as_posix()}:{data_mount.canonical_root.as_posix()}:ro",
        "--workdir",
        "/app",
        "--entrypoint",
        "python",
        settings.image,
        "-m",
        "scripts.sir_convert_a_lot.devops.run_task103_qwen_swedish_preprocessing",
        "--source-mode",
        "staged-public-corpus",
        "--data-root",
        data_mount.canonical_root.as_posix(),
        "--fleurs-max-rows-per-split",
        str(settings.fleurs_max_rows_per_split),
    ]


def run_containerized_preprocessing(
    settings: Task109ContainerizedPreprocessingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    data_mount: MountResolution,
) -> ContainerizedPreprocessingRun:
    """Run the public-corpus preprocessing lane inside the Qwen runtime image."""
    command = build_containerized_preprocessing_command(
        settings,
        repo_root=repo_root,
        hf_mount=hf_mount,
        data_mount=data_mount,
    )
    raw_output = docker_checked(command, label="docker run task109 containerized preprocessing")
    payload = parse_json_object_from_mixed_stdout(raw_output)
    preprocessing_report = Task103PreprocessingReport(
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
