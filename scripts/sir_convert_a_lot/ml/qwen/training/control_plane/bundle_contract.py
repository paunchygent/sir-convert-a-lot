"""Bundle validation helpers for Qwen training control-plane commands.

Purpose:
    Enforce deterministic training-bundle integrity before detached training,
    resume, eval, and diagnostic launches proceed.

Relationships:
    - Used by host-side launch, resume, and diagnose use cases.
    - Consumes bundle summaries and prepared-manifest row iteration helpers.
"""

from __future__ import annotations

from pathlib import Path

from scripts.devops.qwen_finetuning_patches.sft_12hz_ref_input_contract import (
    PRECOMPUTED_REF_INPUT_KIND,
    PRECOMPUTED_REF_INPUT_VERSION,
)
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.storage import iter_jsonl_objects
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    bundle_manifest_path,
    bundle_report_path,
    load_training_bundle_summary,
)


def ensure_training_bundle_exists(
    bundle_root: Path,
    *,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> None:
    """Fail fast when the deterministic training bundle is incomplete."""
    missing_paths = [
        path
        for path in (
            bundle_manifest_path(bundle_root, train_manifest_family),
            bundle_manifest_path(bundle_root, eval_manifest_family),
        )
        if not path.exists()
    ]
    if missing_paths:
        rendered_paths = ", ".join(path.as_posix() for path in missing_paths)
        available_manifest_families = available_bundle_manifest_families(bundle_root)
        rendered_available_families = (
            "none"
            if len(available_manifest_families) == 0
            else ", ".join(available_manifest_families)
        )
        raise SystemExit(
            "Qwen training could not find the required training-bundle artifacts: "
            f"{rendered_paths}.\n"
            "Available manifest families under the bundle root: "
            f"{rendered_available_families}."
        )
    try:
        validate_training_bundle_paths(
            bundle_root,
            (train_manifest_family, eval_manifest_family),
        )
    except ValueError as exc:
        raise SystemExit(
            f"Qwen training bundle integrity check failed before launch.\n{exc}"
        ) from exc
    bundle_report = bundle_report_path(bundle_root)
    if not bundle_report.exists():
        return
    try:
        bundle_summary = load_training_bundle_summary(bundle_root)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(
            f"Qwen training bundle integrity check failed before launch.\n{exc}"
        ) from exc
    if bundle_summary.precomputed_reference_input.kind != "ref_mel":
        raise SystemExit(
            "Qwen training bundle integrity check failed before launch.\n"
            "Unsupported bundle precomputed reference-input kind; expected `ref_mel`."
        )
    if bundle_summary.precomputed_reference_input.artifact_count <= 0:
        raise SystemExit(
            "Qwen training bundle integrity check failed before launch.\n"
            "Training bundle did not report any persisted precomputed reference inputs."
        )
    try:
        validate_training_bundle_paths(
            bundle_root,
            (train_manifest_family, eval_manifest_family),
            require_precomputed_ref_inputs=True,
        )
    except ValueError as exc:
        raise SystemExit(
            f"Qwen training bundle integrity check failed before launch.\n{exc}"
        ) from exc


def validate_training_bundle_paths(
    bundle_root: Path,
    families: tuple[str, str],
    *,
    require_precomputed_ref_inputs: bool = False,
) -> None:
    """Validate that prepared manifests reference existing local bundle assets."""
    for manifest_family in families:
        manifest_path = bundle_manifest_path(bundle_root, manifest_family)
        for row in iter_jsonl_objects(manifest_path):
            if not isinstance(row, dict):
                raise ValueError(
                    f"Prepared manifest row in `{manifest_path}` was not a JSON object."
                )
            for key in ("audio", "ref_audio"):
                validate_bundle_row_path(bundle_root, manifest_path, row, key, required=True)
            validate_bundle_row_path(
                bundle_root,
                manifest_path,
                row,
                "precomputed_ref_input_path",
                required=require_precomputed_ref_inputs,
            )
            if require_precomputed_ref_inputs:
                validate_precomputed_ref_input_contract(manifest_path, row)


def available_bundle_manifest_families(bundle_root: Path) -> list[str]:
    """Return the prepared manifest families present under one bundle root."""
    manifests_dir = bundle_root / "manifests"
    if not manifests_dir.is_dir():
        return []
    families: list[str] = []
    for manifest_path in sorted(manifests_dir.glob("*.prepared.jsonl")):
        manifest_name = manifest_path.name
        if not manifest_name.endswith(".prepared.jsonl"):
            continue
        families.append(manifest_name[: -len(".prepared.jsonl")])
    return families


def validate_bundle_row_path(
    bundle_root: Path,
    manifest_path: Path,
    row: dict[str, object],
    key: str,
    *,
    required: bool,
) -> None:
    """Validate one required or optional manifest-relative bundle path field."""
    raw_value = row.get(key)
    if raw_value is None:
        if required:
            raise ValueError(f"Prepared manifest row in `{manifest_path}` lacked `{key}`.")
        return
    for raw_path in row_path_values(raw_value, key=key, manifest_path=manifest_path):
        resolved_path = (bundle_root / raw_path).resolve()
        try:
            resolved_path.relative_to(bundle_root.resolve())
        except ValueError as exc:
            raise ValueError(
                f"Prepared manifest `{key}` escaped the bundle root: {raw_path}"
            ) from exc
        if not resolved_path.exists():
            raise ValueError(
                f"Prepared manifest `{key}` path did not exist: {resolved_path.as_posix()}"
            )


def row_path_values(
    raw_value: object,
    *,
    key: str,
    manifest_path: Path,
) -> list[str]:
    """Normalize one manifest row path field into concrete string paths."""
    if isinstance(raw_value, str):
        return [raw_value]
    if isinstance(raw_value, list):
        values: list[str] = []
        for item in raw_value:
            if not isinstance(item, str):
                raise ValueError(
                    f"Prepared manifest row in `{manifest_path}` had non-string `{key}` entries."
                )
            values.append(item)
        if len(values) == 0:
            raise ValueError(f"Prepared manifest row in `{manifest_path}` had empty `{key}`.")
        return values
    raise ValueError(
        f"Prepared manifest row in `{manifest_path}` had unsupported `{key}` value type."
    )


def validate_precomputed_ref_input_contract(
    manifest_path: Path,
    row: dict[str, object],
) -> None:
    """Validate the canonical persisted ref-input metadata on one prepared row."""
    kind = row.get("precomputed_ref_input_kind")
    version = row.get("precomputed_ref_input_version")
    source_audio = row.get("precomputed_ref_input_source_audio")
    if kind != PRECOMPUTED_REF_INPUT_KIND:
        raise ValueError(
            f"Prepared manifest row in `{manifest_path}` lacked required "
            f"`precomputed_ref_input_kind={PRECOMPUTED_REF_INPUT_KIND}`."
        )
    if version != PRECOMPUTED_REF_INPUT_VERSION:
        raise ValueError(
            "Prepared manifest row in "
            f"`{manifest_path}` lacked required "
            f"`precomputed_ref_input_version={PRECOMPUTED_REF_INPUT_VERSION}`."
        )
    if not isinstance(source_audio, str) or source_audio.strip() == "":
        raise ValueError(
            "Prepared manifest row in "
            f"`{manifest_path}` lacked `precomputed_ref_input_source_audio`."
        )
