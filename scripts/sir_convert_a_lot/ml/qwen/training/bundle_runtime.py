"""Container runtime helpers for Qwen training-bundle batch finalization.

Purpose:
    Restore the governed Task 101 bundle finalization contract by launching
    bounded batch work inside the shared Qwen Hemma container runtime instead
    of executing tokenizer-dependent audio-code generation in host Python.

Relationships:
    - Used by `cli.ml.qwen_bundle` for the public `task-101-pilot-bundle`
      operator surface.
    - Invokes the narrow in-container batch entrypoint in
      `ml.qwen.training.bundle_in_container`.
    - Reuses shared image-build and bind-mount helpers from
      `ml.qwen.common.runtime`.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Sequence

from scripts.sir_convert_a_lot.ml.qwen.common.models import (
    ManifestFamily,
    MountResolution,
)
from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    docker_checked,
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.audio_codes_runtime import (
    DEFAULT_GOVERNED_ATTN_IMPLEMENTATION,
    DEFAULT_GOVERNED_DEVICE_MAP,
    DEFAULT_GOVERNED_DTYPE,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    AudioCodesRuntimeReport,
)

DEFAULT_DOCKERFILE_PATH = Path("containers/qwen-finetune-hemma/Dockerfile")
DEFAULT_IMAGE = "sir-convert-a-lot-qwen-finetune-hemma:latest"
DEFAULT_HF_CACHE = Path("/srv/scratch/sir-convert-a-lot/cache/huggingface")
DEFAULT_HF_CACHE_HOME_MOUNT = Path("/home/paunchygent/.data/sir-convert-a-lot/cache/huggingface")
DEFAULT_RUNTIME_KIND = "task101_qwen_training_bundle_containerized_batch_v1"
DEFAULT_ENTRY_MODULE = "scripts.sir_convert_a_lot.ml.qwen.training.bundle_in_container"
DEFAULT_AUDIO_CODES_RUNTIME_KIND = "task101_task103_qwen_audio_codes_gpu_v1"
DEFAULT_TRITON_CACHE_DIR = Path("/srv/scratch/sir-convert-a-lot/cache/triton/task101-audio-codes")
DEFAULT_TRITON_CACHE_HOME_MOUNT = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/cache/triton/task101-audio-codes"
)
DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE = Path(
    "/home/paunchygent/.data/sir-convert-a-lot/task101-training-bundle-output-roots"
)
CONTAINER_TRITON_CACHE_DIR = "/cache/triton"


@dataclass(frozen=True)
class TrainingBundleContainerSettings:
    """Normalized settings for the governed Qwen training-bundle runtime."""

    dockerfile_path: Path
    image: str
    hf_cache_dir: Path
    hf_cache_home_mount: Path
    triton_cache_dir: Path
    triton_cache_home_mount: Path
    output_root_home_mount_base: Path
    build_image: bool


@dataclass(frozen=True)
class TrainingBundleRuntimeFingerprint:
    """Machine-readable runtime fingerprint for one governed bundle build."""

    runtime_kind: str
    image: str
    image_id: str
    dockerfile_path: str
    container_entry_module: str
    container_hf_home: str
    container_hf_hub_cache: str
    container_torch_home: str
    audio_codes_runtime_kind: str
    audio_codes_device: str
    audio_codes_dtype: str
    audio_codes_attn_implementation: str
    audio_codes_require_gpu: bool
    audio_codes_require_flash_attn: bool


def default_container_settings() -> TrainingBundleContainerSettings:
    """Return the canonical governed Qwen runtime settings for bundle batches."""
    return TrainingBundleContainerSettings(
        dockerfile_path=DEFAULT_DOCKERFILE_PATH,
        image=DEFAULT_IMAGE,
        hf_cache_dir=DEFAULT_HF_CACHE,
        hf_cache_home_mount=DEFAULT_HF_CACHE_HOME_MOUNT,
        triton_cache_dir=DEFAULT_TRITON_CACHE_DIR,
        triton_cache_home_mount=DEFAULT_TRITON_CACHE_HOME_MOUNT,
        output_root_home_mount_base=DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
        build_image=False,
    )


def training_bundle_runtime_fingerprint_path(output_root: Path) -> Path:
    """Return the bundle-level runtime fingerprint path."""
    return output_root / "reports" / "training_bundle_runtime.json"


def training_bundle_audio_codes_runtime_report_path(output_root: Path) -> Path:
    """Return the bundle-level observed audio-code runtime report path."""
    return output_root / "reports" / "training_bundle_audio_codes_runtime.json"


def training_bundle_batch_runtime_path(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
) -> Path:
    """Return the per-batch runtime fingerprint path."""
    return (
        output_root
        / "reports"
        / "batches"
        / manifest_family
        / f"batch-{batch_index:05d}.runtime.json"
    )


def write_training_bundle_runtime_fingerprint(
    output_root: Path,
    fingerprint: TrainingBundleRuntimeFingerprint,
) -> None:
    """Persist the bundle-level governed runtime fingerprint."""
    path = training_bundle_runtime_fingerprint_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(fingerprint), indent=2, ensure_ascii=False) + "\n")


def write_training_bundle_batch_runtime_fingerprint(
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
    fingerprint: TrainingBundleRuntimeFingerprint,
) -> None:
    """Persist the runtime fingerprint for one completed batch shard."""
    path = training_bundle_batch_runtime_path(output_root, manifest_family, batch_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(fingerprint), indent=2, ensure_ascii=False) + "\n")


def write_training_bundle_audio_codes_runtime_report(
    output_root: Path,
    report: AudioCodesRuntimeReport,
) -> None:
    """Persist the observed governed audio-code runtime report."""
    path = training_bundle_audio_codes_runtime_report_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False) + "\n")


def load_training_bundle_runtime_fingerprint(path: Path) -> TrainingBundleRuntimeFingerprint:
    """Load one governed runtime fingerprint from disk."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Training bundle runtime fingerprint must be one JSON object.")
    return TrainingBundleRuntimeFingerprint(
        runtime_kind=_required_string(payload, "runtime_kind"),
        image=_required_string(payload, "image"),
        image_id=_required_string(payload, "image_id"),
        dockerfile_path=_required_string(payload, "dockerfile_path"),
        container_entry_module=_required_string(payload, "container_entry_module"),
        container_hf_home=_required_string(payload, "container_hf_home"),
        container_hf_hub_cache=_required_string(payload, "container_hf_hub_cache"),
        container_torch_home=_required_string(payload, "container_torch_home"),
        audio_codes_runtime_kind=_required_string(payload, "audio_codes_runtime_kind"),
        audio_codes_device=_required_string(payload, "audio_codes_device"),
        audio_codes_dtype=_required_string(payload, "audio_codes_dtype"),
        audio_codes_attn_implementation=_required_string(
            payload,
            "audio_codes_attn_implementation",
        ),
        audio_codes_require_gpu=_required_bool(payload, "audio_codes_require_gpu"),
        audio_codes_require_flash_attn=_required_bool(payload, "audio_codes_require_flash_attn"),
    )


def validate_runtime_fingerprint_matches(
    observed: TrainingBundleRuntimeFingerprint,
    expected: TrainingBundleRuntimeFingerprint,
) -> None:
    """Fail closed when an observed runtime fingerprint drifts from the request."""
    if observed != expected:
        raise ValueError(
            "Training bundle runtime fingerprint does not match the current governed "
            "container runtime request."
        )


def training_bundle_output_root_home_mount(
    output_root: Path,
    *,
    home_mount_base: Path,
) -> Path:
    """Map one canonical output root onto its deterministic home-backed bind path."""
    if not output_root.is_absolute():
        raise ValueError("Training bundle output roots must be absolute for bind-root resolution.")
    return home_mount_base / output_root.relative_to("/")


def resolve_effective_output_root(
    output_root: Path,
    *,
    settings: TrainingBundleContainerSettings,
) -> MountResolution:
    """Return the Docker-mountable host path for one training-bundle output root."""
    return resolve_effective_bind_root(
        output_root,
        training_bundle_output_root_home_mount(
            output_root,
            home_mount_base=settings.output_root_home_mount_base,
        ),
        image=settings.image,
        sync_home_into_canonical=False,
    )


def resolve_effective_triton_cache_dir(
    settings: TrainingBundleContainerSettings,
) -> MountResolution:
    """Return the Docker-mountable host path for the Task 101 Triton cache."""
    return resolve_effective_bind_root(
        settings.triton_cache_dir,
        settings.triton_cache_home_mount,
        image=settings.image,
        sync_home_into_canonical=True,
    )


def prepare_training_bundle_batch_runtime(
    *,
    settings: TrainingBundleContainerSettings | None = None,
    emit: Callable[[str], None] = print,
) -> tuple[MountResolution, TrainingBundleRuntimeFingerprint]:
    """Prepare the governed Qwen image once and return shared batch runtime state."""
    effective_settings = settings or default_container_settings()
    _, image_id = prepare_qwen_image(effective_settings, emit=emit)
    hf_mount = resolve_effective_hf_cache_dir(effective_settings)
    return hf_mount, TrainingBundleRuntimeFingerprint(
        runtime_kind=DEFAULT_RUNTIME_KIND,
        image=effective_settings.image,
        image_id=image_id,
        dockerfile_path=effective_settings.dockerfile_path.as_posix(),
        container_entry_module=DEFAULT_ENTRY_MODULE,
        container_hf_home=CONTAINER_HF_HOME,
        container_hf_hub_cache=CONTAINER_HF_HUB_CACHE,
        container_torch_home=CONTAINER_TORCH_HOME,
        audio_codes_runtime_kind=DEFAULT_AUDIO_CODES_RUNTIME_KIND,
        audio_codes_device=DEFAULT_GOVERNED_DEVICE_MAP,
        audio_codes_dtype=DEFAULT_GOVERNED_DTYPE,
        audio_codes_attn_implementation=DEFAULT_GOVERNED_ATTN_IMPLEMENTATION,
        audio_codes_require_gpu=True,
        audio_codes_require_flash_attn=True,
    )


def build_containerized_training_bundle_batch_command(
    *,
    repo_root: Path,
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
    batch_count: int,
    audio_codes_chunk_size: int,
    image: str,
    hf_mount: MountResolution,
    triton_mount: MountResolution,
    output_root_mount: MountResolution,
    host_uid: int | None = None,
    host_gid: int | None = None,
    gpu_group_ids: Sequence[str] | None = None,
) -> list[str]:
    """Build the Docker command for one containerized training-bundle batch."""
    effective_host_uid = os.getuid() if host_uid is None else host_uid
    effective_host_gid = os.getgid() if host_gid is None else host_gid
    run_args = [
        "run",
        "--rm",
        "--user",
        f"{effective_host_uid}:{effective_host_gid}",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
    ]
    for group_id in gpu_group_ids or _gpu_device_group_ids():
        run_args.extend(["--group-add", group_id])
    run_args.extend(
        [
            "--ipc=host",
            "--cap-add=SYS_PTRACE",
            "--security-opt",
            "seccomp=unconfined",
            "-e",
            "HF_HUB_DISABLE_XET=1",
            "-e",
            f"HF_HOME={CONTAINER_HF_HOME}",
            "-e",
            f"HUGGINGFACE_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
            "-e",
            f"TORCH_HOME={CONTAINER_TORCH_HOME}",
            "-e",
            f"TRITON_CACHE_DIR={CONTAINER_TRITON_CACHE_DIR}",
            "-v",
            f"{repo_root.as_posix()}:/app",
            "-v",
            f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
            "-v",
            f"{triton_mount.effective_root.as_posix()}:{CONTAINER_TRITON_CACHE_DIR}",
            "-v",
            f"{output_root_mount.effective_root.as_posix()}:{output_root.as_posix()}",
            "--workdir",
            "/app",
            "--entrypoint",
            "python",
            image,
            "-m",
            DEFAULT_ENTRY_MODULE,
            "--output-root",
            output_root.as_posix(),
            "--manifest-family",
            manifest_family,
            "--batch-index",
            str(batch_index),
            "--batch-count",
            str(batch_count),
            "--audio-codes-chunk-size",
            str(audio_codes_chunk_size),
        ]
    )
    return run_args


def run_containerized_training_bundle_batch(
    *,
    repo_root: Path,
    output_root: Path,
    manifest_family: ManifestFamily,
    batch_index: int,
    batch_count: int,
    audio_codes_chunk_size: int,
    settings: TrainingBundleContainerSettings | None = None,
    hf_mount: MountResolution | None = None,
    triton_mount: MountResolution | None = None,
    fingerprint: TrainingBundleRuntimeFingerprint | None = None,
    emit: Callable[[str], None] = print,
) -> TrainingBundleRuntimeFingerprint:
    """Run one bounded training-bundle batch inside the governed Qwen image."""
    effective_settings = settings or default_container_settings()
    effective_hf_mount = hf_mount
    effective_triton_mount = triton_mount
    effective_fingerprint = fingerprint
    if effective_hf_mount is None or effective_fingerprint is None:
        effective_hf_mount, effective_fingerprint = prepare_training_bundle_batch_runtime(
            settings=effective_settings,
            emit=emit,
        )
    if effective_triton_mount is None:
        effective_triton_mount = resolve_effective_triton_cache_dir(effective_settings)
    output_root_mount = resolve_effective_output_root(output_root, settings=effective_settings)
    write_training_bundle_runtime_fingerprint(output_root, effective_fingerprint)
    command = build_containerized_training_bundle_batch_command(
        repo_root=repo_root,
        output_root=output_root,
        manifest_family=manifest_family,
        batch_index=batch_index,
        batch_count=batch_count,
        audio_codes_chunk_size=audio_codes_chunk_size,
        image=effective_settings.image,
        hf_mount=effective_hf_mount,
        triton_mount=effective_triton_mount,
        output_root_mount=output_root_mount,
    )
    emit(
        "[training-bundle] "
        + json.dumps(
            {
                "event": "batch_container_launch",
                "manifest_family": manifest_family,
                "batch_index": batch_index,
                "batch_count": batch_count,
                "audio_codes_chunk_size": audio_codes_chunk_size,
                "image": effective_fingerprint.image,
                "image_id": effective_fingerprint.image_id,
                "effective_output_root": output_root_mount.effective_root.as_posix(),
                "used_output_root_home_mount": output_root_mount.used_home_mount,
                "effective_triton_cache_dir": effective_triton_mount.effective_root.as_posix(),
                "used_triton_cache_home_mount": effective_triton_mount.used_home_mount,
                "command": ["sudo", "-n", "docker", *command],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    docker_checked(command, label="docker run qwen training-bundle batch")
    return effective_fingerprint


def _gpu_device_group_ids() -> list[str]:
    """Return unique numeric group ids required for Hemma GPU device access."""
    candidate_paths = [Path("/dev/kfd")]
    dri_root = Path("/dev/dri")
    if dri_root.exists():
        candidate_paths.extend(sorted(dri_root.glob("card*")))
        candidate_paths.extend(sorted(dri_root.glob("renderD*")))
    group_ids: list[str] = []
    for candidate in candidate_paths:
        if not candidate.exists():
            continue
        group_id = str(os.stat(candidate).st_gid)
        if group_id not in group_ids:
            group_ids.append(group_id)
    return group_ids


def _required_string(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a runtime JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in training-bundle runtime fingerprint.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean field from the runtime fingerprint payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Training-bundle runtime fingerprint is missing `{key}`.")
    return value
