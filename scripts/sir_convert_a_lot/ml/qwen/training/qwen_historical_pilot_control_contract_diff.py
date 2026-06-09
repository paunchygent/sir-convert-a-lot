"""Contract-diff helpers for the historical Qwen pilot training control lane.

Purpose:
    Keep the written evidence comparing the documented historical Qwen pilot training
    contract, the invalid scratch-only approximation, and the recreated control
    launch in one focused module so the public surface stays small and readable.

Relationships:
    - Used by `qwen_historical_pilot_control.py`.
    - Reused by tests that verify the launcher writes historical-control
      evidence before launch.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import MountResolution
from scripts.sir_convert_a_lot.ml.qwen.training.models import TrainingSettings

DOCUMENTED_HISTORICAL_BUNDLE_ROOT = Path(
    "/srv/scratch/sir-convert-a-lot/build/reference/qwen3-tts-swedish-pilot-bundle-20260312h"
)
DOCUMENTED_HISTORICAL_MAX_STEPS = 1_000_000
DOCUMENTED_HISTORICAL_TRAIN_ROWS = 8445
DOCUMENTED_HISTORICAL_EVAL_ROWS = 8
INVALID_HISTORICAL_APPROXIMATION: dict[str, object] = {
    "launch_id": "qwen-historical-approximation-20260317t183856z-a1",
    "pilot_bundle_root": (
        "/srv/scratch/sir-convert-a-lot/build/verification/"
        "historical-finalization-benchmark-20260312j/"
        "direct-encode-chunk64-span1"
    ),
    "batch_size": 8,
    "max_steps": 8,
    "launch_surface": "qwen-train launch",
}


def build_contract_diff_payload(
    *,
    launch_id: str,
    settings: TrainingSettings,
    build_performed: bool,
    image_id: str,
    historical_bundle_root: Path,
    historical_bundle_home_mount: Path,
    bundle_mount: MountResolution,
    train_rows: int,
    eval_rows: int,
    model_id: str,
    documented_batch_size: int,
    documented_lr: float,
    documented_num_epochs: int,
    documented_checkpoint_interval_steps: int,
    documented_durable_checkpoint_retention: int,
    documented_durable_checkpoint_min_free_bytes: int,
    image: str,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> dict[str, object]:
    """Return the written contract diff for the historical control lane."""
    return {
        "lane": "qwen_historical_pilot_control",
        "launch_id": launch_id,
        "historical_contract": {
            "launch_id": "qwen-historical-pilot-20260313t102144z",
            "pilot_bundle_root": DOCUMENTED_HISTORICAL_BUNDLE_ROOT.as_posix(),
            "train_manifest_family": train_manifest_family,
            "eval_manifest_family": eval_manifest_family,
            "model_id": model_id,
            "batch_size": documented_batch_size,
            "lr": documented_lr,
            "num_epochs": documented_num_epochs,
            "max_steps": DOCUMENTED_HISTORICAL_MAX_STEPS,
            "checkpoint_interval_steps": documented_checkpoint_interval_steps,
            "durable_checkpoint_retention": documented_durable_checkpoint_retention,
            "durable_checkpoint_min_free_bytes": documented_durable_checkpoint_min_free_bytes,
            "train_rows": DOCUMENTED_HISTORICAL_TRAIN_ROWS,
            "eval_rows": DOCUMENTED_HISTORICAL_EVAL_ROWS,
            "image": image,
            "in_training_eval": False,
        },
        "invalid_historical_approximation": INVALID_HISTORICAL_APPROXIMATION,
        "historical_control_recreation": {
            "pilot_bundle_root": historical_bundle_root.as_posix(),
            "historical_bundle_home_mount": historical_bundle_home_mount.as_posix(),
            "effective_bundle_mount_root": bundle_mount.effective_root.as_posix(),
            "batch_size": settings.batch_size,
            "lr": settings.lr,
            "num_epochs": settings.num_epochs,
            "max_steps": settings.max_steps,
            "checkpoint_interval_steps": settings.checkpoint_interval_steps,
            "eval_interval_steps": settings.eval_interval_steps,
            "gradient_accumulation_steps": settings.gradient_accumulation_steps,
            "throughput_profile_label": settings.throughput_profile_label,
            "text_embedding_assembly_mode": settings.text_embedding_assembly_mode,
            "text_embedding_mask_policy": settings.text_embedding_mask_policy,
            "train_rows": train_rows,
            "eval_rows": eval_rows,
            "image": settings.image,
            "image_id": image_id,
            "build_performed": build_performed,
        },
        "remaining_known_diffs": [
            (
                "The surviving historical bundle now lives under /srv/storage backups rather than "
                "the original /srv/scratch reference root recorded on 2026-03-13."
            ),
            (
                "The recreated control uses the current trainer module with "
                "full_channel_masked + text_span_only, not the older Qwen pilot "
                "training probe implementation."
            ),
            (
                "The recreated control bounds max_steps to the requested probe window "
                "and sets eval_interval_steps to suppress in-training eval, which is "
                "the closest current replacement for the historical no-in-training-eval lane."
            ),
        ],
    }


def render_contract_diff_markdown(payload: dict[str, object]) -> str:
    """Render the written historical-control contract diff as concise markdown evidence."""
    historical = _required_object(payload, "historical_contract")
    invalid_historical_approximation = _required_object(
        payload,
        "invalid_historical_approximation",
    )
    historical_control_recreation = _required_object(
        payload,
        "historical_control_recreation",
    )
    remaining_diffs = _required_str_list(payload, "remaining_known_diffs")
    return "\n".join(
        [
            "# Historical Pilot Control Contract Diff",
            "",
            "## Historical Contract",
            f"- launch_id: `{historical['launch_id']}`",
            f"- pilot_bundle_root: `{historical['pilot_bundle_root']}`",
            f"- batch_size: `{historical['batch_size']}`",
            f"- max_steps: `{historical['max_steps']}`",
            f"- checkpoint_interval_steps: `{historical['checkpoint_interval_steps']}`",
            f"- train_rows: `{historical['train_rows']}`",
            f"- eval_rows: `{historical['eval_rows']}`",
            "",
            "## Invalid Historical Approximation",
            f"- launch_id: `{invalid_historical_approximation['launch_id']}`",
            f"- pilot_bundle_root: `{invalid_historical_approximation['pilot_bundle_root']}`",
            f"- batch_size: `{invalid_historical_approximation['batch_size']}`",
            f"- max_steps: `{invalid_historical_approximation['max_steps']}`",
            f"- launch_surface: `{invalid_historical_approximation['launch_surface']}`",
            "",
            "## Historical Control Recreation",
            f"- pilot_bundle_root: `{historical_control_recreation['pilot_bundle_root']}`",
            "- effective_bundle_mount_root: "
            f"`{historical_control_recreation['effective_bundle_mount_root']}`",
            f"- batch_size: `{historical_control_recreation['batch_size']}`",
            f"- max_steps: `{historical_control_recreation['max_steps']}`",
            "- checkpoint_interval_steps: "
            f"`{historical_control_recreation['checkpoint_interval_steps']}`",
            f"- eval_interval_steps: `{historical_control_recreation['eval_interval_steps']}`",
            "- gradient_accumulation_steps: "
            f"`{historical_control_recreation['gradient_accumulation_steps']}`",
            "- text_embedding_assembly_mode: "
            f"`{historical_control_recreation['text_embedding_assembly_mode']}`",
            "- text_embedding_mask_policy: "
            f"`{historical_control_recreation['text_embedding_mask_policy']}`",
            f"- train_rows: `{historical_control_recreation['train_rows']}`",
            f"- eval_rows: `{historical_control_recreation['eval_rows']}`",
            f"- image: `{historical_control_recreation['image']}`",
            f"- image_id: `{historical_control_recreation['image_id']}`",
            "",
            "## Remaining Known Diffs",
            *(f"- {item}" for item in remaining_diffs),
        ]
    )


def _required_object(payload: dict[str, object], key: str) -> dict[str, object]:
    """Return one required object from a contract-diff payload."""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise SystemExit(f"Historical-control contract payload lacked a valid `{key}` object.")
    return value


def _required_str_list(payload: dict[str, object], key: str) -> list[str]:
    """Return one required string list from a contract-diff payload."""
    value = payload.get(key)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise SystemExit(f"Historical-control contract payload lacked a valid `{key}` string list.")
    return list(value)
