"""Host-side standalone eval orchestration for detached Qwen training.

Purpose:
    Build and execute a governed one-shot container command that restores a
    durable Qwen checkpoint and runs standalone held-out eval inside the
    canonical training image.

Relationships:
    - Consumes mount and Docker helpers from `ml.qwen.common.runtime`.
    - Reuses training settings from `ml.qwen.training.models`.
    - Executes `ml.qwen.training.evaluator` inside the Qwen training image.
"""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    CONTAINER_HF_HOME,
    CONTAINER_HF_HUB_CACHE,
    CONTAINER_TORCH_HOME,
    MountResolution,
    docker_checked,
)
from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import (
    StandaloneEvalReport,
    TrainingSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
    resolve_text_embedding_assembly_mode,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    resolve_text_embedding_mask_policy,
)

CONTAINER_BUILD_ROOT = Path("/app/build")


def _containerize_scratch_path(host_path: Path, *, scratch_root: Path) -> str:
    """Translate one host scratch path into the mounted container build path."""
    relative_path = host_path.resolve().relative_to(scratch_root.resolve())
    return (CONTAINER_BUILD_ROOT / relative_path).as_posix()


def default_eval_id() -> str:
    """Return one deterministic standalone eval identifier."""
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("eval-%Y%m%dT%H%M%SZ")


def default_eval_output_dir(launch_root: Path, *, eval_id: str) -> Path:
    """Return the canonical eval output dir under one verification launch root."""
    return launch_root / "evals" / eval_id


def build_standalone_eval_command(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    output_dir: Path,
    checkpoint_path: Path,
    eval_jsonl: Path,
    pilot_bundle_root: Path | None,
) -> list[str]:
    """Build the governed Docker command for one standalone eval pass."""
    container_output_dir = _containerize_scratch_path(
        output_dir,
        scratch_root=settings.scratch_build_root,
    )
    container_checkpoint_path = _containerize_scratch_path(
        checkpoint_path,
        scratch_root=settings.scratch_build_root,
    )
    container_eval_jsonl = _containerize_scratch_path(
        eval_jsonl,
        scratch_root=settings.scratch_build_root,
    )
    command = [
        "run",
        "--rm",
        "--device",
        "/dev/kfd",
        "--device",
        "/dev/dri",
        "--group-add",
        "video",
        "--group-add",
        "render",
        "--ipc=host",
        "--shm-size",
        "64g",
        "--cap-add",
        "SYS_PTRACE",
        "-e",
        f"HF_HOME={CONTAINER_HF_HOME}",
        "-e",
        f"HUGGINGFACE_HUB_CACHE={CONTAINER_HF_HUB_CACHE}",
        "-e",
        f"TORCH_HOME={CONTAINER_TORCH_HOME}",
        "-v",
        f"{repo_root.resolve().as_posix()}:/app",
        "-v",
        f"{hf_mount.effective_root.as_posix()}:{CONTAINER_HF_HOME}",
        "-v",
        f"{scratch_mount.effective_root.as_posix()}:{CONTAINER_BUILD_ROOT.as_posix()}",
        "-w",
        "/app",
        settings.image,
        "python",
        "-m",
        "scripts.sir_convert_a_lot.ml.qwen.training.evaluator",
        "--model-id",
        settings.model_id,
        "--eval-jsonl",
        container_eval_jsonl,
        "--output-dir",
        container_output_dir,
        "--checkpoint-path",
        container_checkpoint_path,
        "--gradient-accumulation-steps",
        str(settings.gradient_accumulation_steps),
        "--text-embedding-assembly-mode",
        settings.text_embedding_assembly_mode,
        "--text-embedding-mask-policy",
        settings.text_embedding_mask_policy,
        "--batch-size",
        str(settings.batch_size),
        "--throughput-profile-label",
        settings.throughput_profile_label,
        "--dataloader-num-workers",
        str(settings.dataloader_num_workers),
        "--dataloader-pin-memory",
        "true" if settings.dataloader_pin_memory else "false",
        "--dataloader-persistent-workers",
        "true" if settings.dataloader_persistent_workers else "false",
        "--dataloader-prefetch-factor",
        str(settings.dataloader_prefetch_factor),
        "--non-blocking-transfer",
        "true" if settings.non_blocking_transfer else "false",
        "--ref-mel-cache-enabled",
        "true" if settings.ref_mel_cache_enabled else "false",
        "--ref-mel-cache-max-items",
        str(settings.ref_mel_cache_max_items),
        "--torch-profiler-enabled",
        "true" if settings.torch_profiler_enabled else "false",
        "--torch-profiler-wait-steps",
        str(settings.torch_profiler_wait_steps),
        "--torch-profiler-warmup-steps",
        str(settings.torch_profiler_warmup_steps),
        "--torch-profiler-active-steps",
        str(settings.torch_profiler_active_steps),
        "--torch-profiler-repeat",
        str(settings.torch_profiler_repeat),
        "--torch-profiler-record-shapes",
        "true" if settings.torch_profiler_record_shapes else "false",
        "--torch-profiler-profile-memory",
        "true" if settings.torch_profiler_profile_memory else "false",
        "--torch-profiler-with-stack",
        "true" if settings.torch_profiler_with_stack else "false",
    ]
    if pilot_bundle_root is not None:
        command.extend(
            [
                "--pilot-bundle-root",
                _containerize_scratch_path(
                    pilot_bundle_root,
                    scratch_root=settings.scratch_build_root,
                ),
            ]
        )
    return command


def run_standalone_eval(
    settings: TrainingSettings,
    *,
    repo_root: Path,
    hf_mount: MountResolution,
    scratch_mount: MountResolution,
    output_dir: Path,
    checkpoint_path: Path,
    eval_jsonl: Path,
    pilot_bundle_root: Path | None,
) -> StandaloneEvalReport:
    """Run one standalone eval container and return the parsed report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    docker_checked(
        build_standalone_eval_command(
            settings,
            repo_root=repo_root,
            hf_mount=hf_mount,
            scratch_mount=scratch_mount,
            output_dir=output_dir,
            checkpoint_path=checkpoint_path,
            eval_jsonl=eval_jsonl,
            pilot_bundle_root=pilot_bundle_root,
        ),
        label="qwen standalone eval",
    )
    report_path = output_dir / "report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return StandaloneEvalReport(
        generated_at=str(payload["generated_at"]),
        status=str(payload["status"]),
        model_id=str(payload["model_id"]),
        checkpoint_path=str(payload["checkpoint_path"]),
        eval_jsonl=str(payload["eval_jsonl"]),
        output_dir=str(payload["output_dir"]),
        eval_row_count=int(payload["eval_row_count"]),
        gradient_accumulation_steps=resolve_gradient_accumulation_steps(
            (
                None
                if "gradient_accumulation_steps" not in payload
                else int(payload["gradient_accumulation_steps"])
            ),
            default=settings.gradient_accumulation_steps,
        ),
        text_embedding_assembly_mode=resolve_text_embedding_assembly_mode(
            (
                None
                if "text_embedding_assembly_mode" not in payload
                else str(payload["text_embedding_assembly_mode"])
            ),
            default=DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
        ),
        text_embedding_mask_policy=resolve_text_embedding_mask_policy(
            (
                None
                if "text_embedding_mask_policy" not in payload
                else str(payload["text_embedding_mask_policy"])
            ),
            default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
        ),
        bundle_precomputed_reference_input=(
            None
            if payload.get("bundle_precomputed_reference_input") is None
            else dict(payload["bundle_precomputed_reference_input"])
        ),
        throughput_profile=(
            None
            if payload.get("throughput_profile") is None
            else dict(payload["throughput_profile"])
        ),
        eval_summary=(
            None if payload.get("eval_summary") is None else dict(payload["eval_summary"])
        ),
        failure=None if payload.get("failure") is None else dict(payload["failure"]),
    )
