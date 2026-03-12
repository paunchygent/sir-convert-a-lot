"""Validation and parsing helpers for Task 101 pilot-bundle artifacts.

Purpose:
    Centralize Task 101 bundle JSON parsing, prepared-manifest validation, and
    post-assembly counting helpers so the orchestrator stays focused on stage
    flow rather than payload validation details.

Relationships:
    - Consumed by `task101_qwen_pilot_bundle.py` for summary loading and final
      bundle validation.
    - Reuses Task 103 prepared-manifest contracts and JSONL storage helpers.
"""

from __future__ import annotations

from pathlib import Path

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    Task101PilotBundleRuntimeFingerprint,
    load_task101_pilot_bundle_runtime_fingerprint,
    task101_pilot_bundle_runtime_fingerprint_path,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
    PreparedManifestRow,
    QualityTier,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_jsonl_objects,
)


def manifest_row_counts(
    output_root: Path,
    families: tuple[ManifestFamily, ManifestFamily],
) -> dict[ManifestFamily, int]:
    """Count prepared-manifest rows per selected family."""
    counts: dict[ManifestFamily, int] = {}
    for family in families:
        prepared_path = output_root / "manifests" / f"{family}.prepared.jsonl"
        counts[family] = sum(1 for _ in iter_jsonl_objects(prepared_path))
    return counts


def speaker_counts(
    output_root: Path,
    families: tuple[ManifestFamily, ManifestFamily],
) -> dict[ManifestFamily, int]:
    """Count unique speakers per selected prepared manifest family."""
    counts: dict[ManifestFamily, int] = {}
    for family in families:
        prepared_path = output_root / "manifests" / f"{family}.prepared.jsonl"
        speaker_ids = {
            prepared_manifest_row(payload, prepared_path).speaker_id
            for payload in iter_jsonl_objects(prepared_path)
        }
        counts[family] = len(speaker_ids)
    return counts


def prepared_manifest_row(payload: object, path: Path) -> PreparedManifestRow:
    """Parse one prepared manifest row from JSON."""
    if not isinstance(payload, dict):
        raise ValueError(f"Prepared manifest rows must be JSON objects: {path}")
    audio_codes = payload.get("audio_codes")
    if not isinstance(audio_codes, list):
        raise ValueError(f"Malformed `audio_codes` in {path}.")
    rendered_audio_codes: list[list[int]] = []
    for row in audio_codes:
        if not isinstance(row, list):
            raise ValueError(f"Malformed `audio_codes` row in {path}.")
        rendered_audio_codes.append([int(value) for value in row])
    return PreparedManifestRow(
        audio=required_string(payload, "audio"),
        text=required_string(payload, "text"),
        ref_audio=required_string(payload, "ref_audio"),
        speaker_id=required_string(payload, "speaker_id"),
        dataset=required_string(payload, "dataset"),
        source_split=required_string(payload, "source_split"),
        quality_tier=required_quality_tier(payload, "quality_tier"),
        audio_codes=rendered_audio_codes,
    )


def validate_task101_pilot_bundle_paths(
    output_root: Path,
    families: tuple[str, ...],
) -> None:
    """Fail closed if any prepared row points outside the materialized bundle."""
    for family in families:
        prepared_path = output_root / "manifests" / f"{family}.prepared.jsonl"
        for payload in iter_jsonl_objects(prepared_path):
            prepared_row = prepared_manifest_row(payload, prepared_path)
            audio_path = bundle_local_artifact_path(output_root, prepared_row.audio)
            ref_audio_path = bundle_local_artifact_path(output_root, prepared_row.ref_audio)
            if not audio_path.exists():
                raise ValueError(
                    "Task 101 pilot bundle missing prepared-row audio artifact: "
                    f"{audio_path.as_posix()}"
                )
            if not ref_audio_path.exists():
                raise ValueError(
                    "Task 101 pilot bundle missing prepared-row ref audio artifact: "
                    f"{ref_audio_path.as_posix()}"
                )


def bundle_local_artifact_path(output_root: Path, relative_path_text: str) -> Path:
    """Resolve one bundle-local artifact path and reject path escape."""
    relative_path = Path(relative_path_text)
    if relative_path.is_absolute():
        raise ValueError(
            "Task 101 pilot bundle prepared rows must use bundle-local relative paths."
        )
    candidate_path = output_root / relative_path
    try:
        candidate_path.resolve(strict=False).relative_to(output_root.resolve())
    except ValueError as exc:
        raise ValueError(
            "Task 101 pilot bundle prepared rows must not escape the bundle root."
        ) from exc
    return candidate_path


def load_bundle_runtime_fingerprint(output_root: Path) -> Task101PilotBundleRuntimeFingerprint:
    """Load the bundle-level governed runtime fingerprint from disk."""
    return load_task101_pilot_bundle_runtime_fingerprint(
        task101_pilot_bundle_runtime_fingerprint_path(output_root)
    )


def required_quality_tier(payload: dict[str, object], key: str) -> QualityTier:
    """Return one required quality-tier string from a JSON payload."""
    value = required_string(payload, key)
    if value == "high_trust":
        return "high_trust"
    if value == "medium_trust":
        return "medium_trust"
    if value == "rejected":
        return "rejected"
    raise ValueError(f"Malformed `{key}` in prepared manifest payload.")


def required_manifest_family(payload: dict[str, object], key: str) -> ManifestFamily:
    """Return one validated manifest-family string from a JSON payload."""
    value = required_string(payload, key)
    if value == "swedish_smoke_train":
        return "swedish_smoke_train"
    if value == "swedish_pilot_train":
        return "swedish_pilot_train"
    if value == "swedish_scaleup_train":
        return "swedish_scaleup_train"
    if value == "swedish_checkpoint_dev":
        return "swedish_checkpoint_dev"
    if value == "swedish_final_test":
        return "swedish_final_test"
    if value == "swedish_waxholm_control":
        return "swedish_waxholm_control"
    raise ValueError(f"Malformed `{key}` manifest-family value: {value!r}.")


def required_manifest_count_map(
    payload: dict[str, object],
    key: str,
) -> dict[ManifestFamily, int]:
    """Return one manifest-family keyed integer map from a JSON payload."""
    rendered_value = payload.get(key)
    if not isinstance(rendered_value, dict):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    rendered_counts: dict[ManifestFamily, int] = {}
    for family_name, count in rendered_value.items():
        if not isinstance(family_name, str) or not isinstance(count, int):
            raise ValueError(f"Malformed `{key}` entry in JSON payload.")
        rendered_counts[required_manifest_family({key: family_name}, key)] = count
    return rendered_counts


def required_string(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value


def required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value
