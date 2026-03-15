"""Shared host-runtime helpers for Qwen training control-plane use cases.

Purpose:
    Prepare the training image, Hugging Face cache mount, and scratch mount for
    detached control-plane commands without owning command-specific behavior.

Relationships:
    - Used by launch, resume, eval, diagnose, and schedule use cases.
    - Consumes canonical Qwen runtime and mount-resolution helpers.
"""

from __future__ import annotations

import argparse

from scripts.sir_convert_a_lot.ml.qwen.common.runtime import (
    MountResolution,
    prepare_qwen_image,
    resolve_effective_bind_root,
    resolve_effective_hf_cache_dir,
)
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings


def prepare_runtime_dependencies(
    *,
    settings: TrainingSettings,
    dockerfile_path,
    skip_build: bool,
) -> tuple[bool, str, MountResolution, MountResolution]:
    """Prepare the image and resolve canonical cache/scratch mounts."""
    build_performed, image_id = prepare_qwen_image(
        argparse.Namespace(
            dockerfile_path=dockerfile_path,
            image=settings.image,
            build_image=not skip_build,
        )
    )
    hf_mount = resolve_effective_hf_cache_dir(
        argparse.Namespace(
            image=settings.image,
            hf_cache_dir=settings.hf_cache_dir,
            hf_cache_home_mount=settings.hf_cache_home_mount,
        )
    )
    scratch_mount = resolve_effective_bind_root(
        settings.scratch_build_root,
        settings.scratch_build_home_mount,
        image=settings.image,
        sync_home_into_canonical=False,
    )
    return build_performed, image_id, hf_mount, scratch_mount
