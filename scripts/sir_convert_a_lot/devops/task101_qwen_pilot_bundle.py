"""Task 101 pilot-bundle materialization for frozen Qwen pilot ownership.

Purpose:
    Project the frozen canonical Qwen pilot root into one deterministic Task
    101 training bundle so the bounded Hemma fine-tune consumes immutable
    prepared manifests, stable speaker references, and machine-readable bundle
    metadata instead of a generic promoted preprocessing root.

Relationships:
    - Consumes the frozen canonical processed root emitted by
      `task103_qwen_canonical_processed_root.py`.
    - Reuses Task 103 finalization helpers from
      `task103_qwen_preprocessing_finalization.py` to build bundle-local
      `raw`/`prepared` manifests and stable `refs/`.
    - Supplies the canonical input root consumed by
      `run_task101_hemma_qwen_pilot.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import unicodedata
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    AudioCodesEncoderProtocol,
    encode_audio_codes,
    finalize_from_spool,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
    PreparedManifestRow,
    QualityTier,
    SpoolRow,
    Task103PreprocessingSettings,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_jsonl_objects,
    iter_spool_rows,
    rebuild_completed_row_keys_index,
    write_json,
    write_spool_row,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_row_keys import RowKey, load_row_key_records
from scripts.sir_convert_a_lot.devops.task112_hemma_storage_runtime import (
    DEFAULT_SCRATCH_BUILD_ROOT,
)

DEFAULT_FROZEN_PILOT_ROOT = Path(
    "/srv/storage/sir-convert-a-lot/backups/qwen-preprocessing-canonical/"
    "task140-qwen-pilot-frozen-20260311a"
)
DEFAULT_PILOT_BUNDLE_ROOT = (
    DEFAULT_SCRATCH_BUILD_ROOT / "reference/qwen3-tts-swedish-task101-pilot-bundle"
)
DEFAULT_TRAIN_MANIFEST_FAMILY: ManifestFamily = "swedish_pilot_train"
DEFAULT_EVAL_MANIFEST_FAMILY: ManifestFamily = "swedish_checkpoint_dev"
DEFAULT_TOKENIZER_MODEL = "Qwen/Qwen3-TTS-Tokenizer-12Hz"
DEFAULT_AUDIO_CODES_CHUNK_SIZE = 8


@dataclass(frozen=True)
class Task101PilotBundleSummary:
    """Machine-readable summary for one deterministic Task 101 pilot bundle."""

    source_root: str
    output_root: str
    train_manifest_family: ManifestFamily
    eval_manifest_family: ManifestFamily
    tokenizer_model: str
    retained_row_count: int
    conflict_row_count: int
    manifest_row_counts: dict[ManifestFamily, int]
    speaker_counts: dict[ManifestFamily, int]
    owned_row_keys_path: str
    conflict_row_keys_path: str
    repo_head: str
    generated_at: str


def task101_pilot_bundle_report_path(output_root: Path) -> Path:
    """Return the machine-readable report path for one pilot bundle."""
    return output_root / "reports" / "task101_pilot_bundle_report.json"


def build_task101_pilot_bundle(
    *,
    source_root: Path,
    output_root: Path,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
    tokenizer_model: str,
    encode_audio_codes_fn: AudioCodesEncoderProtocol,
    repo_root: Path,
) -> Task101PilotBundleSummary:
    """Materialize one deterministic Task 101 pilot bundle from a frozen root."""
    if output_root.exists():
        raise ValueError(
            "Task 101 pilot-bundle output must be a new path so the bundle stays immutable."
        )
    selected_families = _selected_manifest_families(
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
    )
    owned_row_keys_path, conflict_row_keys_path, conflict_row_count = _freeze_artifact_paths(
        source_root
    )
    owned_row_keys = load_row_key_records(owned_row_keys_path)
    copied_row_count = 0

    for spool_row in iter_spool_rows(source_root):
        row_key = _row_key_from_spool_row(spool_row)
        if row_key not in owned_row_keys:
            raise ValueError(
                "Frozen pilot bundle encountered a spool row not present in the owned-row ledger: "
                f"{row_key!r}"
            )
        selected_targets = tuple(
            family for family in spool_row.manifest_targets if family in selected_families
        )
        if spool_row.admission_decision != "admit" or not selected_targets:
            continue
        bundle_row = replace(
            spool_row,
            manifest_targets=selected_targets,
            reference_audio_24k_paths={
                family: relative_path
                for family, relative_path in spool_row.reference_audio_24k_paths.items()
                if family in selected_families
            },
        )
        write_spool_row(output_root, bundle_row)
        _copy_artifact_with_fallback(
            source_path=source_root / bundle_row.audio_24k_path,
            output_root=output_root,
            relative_path=Path(bundle_row.audio_24k_path),
        )
        copied_row_count += 1

    if copied_row_count == 0:
        raise ValueError("Task 101 pilot bundle cannot be empty.")

    rebuild_completed_row_keys_index(output_root)
    settings = Task103PreprocessingSettings(
        output_root=output_root,
        asr_model=_single_spool_value(source_root, "asr_model"),
        asr_revision=_single_spool_value(source_root, "asr_revision"),
        tokenizer_model=tokenizer_model,
        stage="finalization",
        finalization_families=selected_families,
        audio_codes_chunk_size=DEFAULT_AUDIO_CODES_CHUNK_SIZE,
    )
    finalize_from_spool(
        settings,
        output_root=output_root,
        encode_audio_codes_fn=encode_audio_codes_fn,
    )

    _validate_bundle_paths(output_root, selected_families)
    manifest_row_counts = _manifest_row_counts(output_root, selected_families)
    for family in selected_families:
        if manifest_row_counts[family] <= 0:
            raise ValueError(
                f"Task 101 pilot bundle is missing retained rows for `{family}`."
            )
    speaker_counts = _speaker_counts(output_root, selected_families)
    summary = Task101PilotBundleSummary(
        source_root=source_root.as_posix(),
        output_root=output_root.as_posix(),
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
        tokenizer_model=tokenizer_model,
        retained_row_count=copied_row_count,
        conflict_row_count=conflict_row_count,
        manifest_row_counts=manifest_row_counts,
        speaker_counts=speaker_counts,
        owned_row_keys_path=owned_row_keys_path.as_posix(),
        conflict_row_keys_path=conflict_row_keys_path.as_posix(),
        repo_head=_git_head(repo_root),
        generated_at=_utc_now_iso(),
    )
    write_json(task101_pilot_bundle_report_path(output_root), summary)
    return summary


def _selected_manifest_families(
    *,
    train_manifest_family: ManifestFamily,
    eval_manifest_family: ManifestFamily,
) -> tuple[ManifestFamily, ...]:
    """Return the canonical ordered manifest families for one pilot bundle."""
    if train_manifest_family == eval_manifest_family:
        raise ValueError("Train and eval manifest families must be distinct.")
    return (train_manifest_family, eval_manifest_family)


def _freeze_artifact_paths(source_root: Path) -> tuple[Path, Path, int]:
    """Resolve the owned/conflict freeze artifacts for one frozen pilot root."""
    freeze_payload = json.loads(
        (source_root / "reports" / "canonical_processed_root_freeze.json").read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(freeze_payload, dict):
        raise ValueError("Frozen pilot freeze summary must be one JSON object.")
    owned_row_keys_path = Path(_required_string(freeze_payload, "owned_row_keys_path"))
    conflict_row_keys_path = Path(_required_string(freeze_payload, "conflict_row_keys_path"))
    return (
        owned_row_keys_path,
        conflict_row_keys_path,
        _required_int(freeze_payload, "conflict_row_count"),
    )


def _row_key_from_spool_row(spool_row: SpoolRow) -> RowKey:
    """Return the canonical row key for one spool row."""
    return (spool_row.dataset, spool_row.source_split, spool_row.dataset_row_id)


def _single_spool_value(source_root: Path, field_name: str) -> str:
    """Return one single-valued string field shared by all spool rows."""
    values = {
        _required_string(spool_row.__dict__, field_name)
        for spool_row in iter_spool_rows(source_root)
    }
    if len(values) != 1:
        raise ValueError(
            f"Expected one shared `{field_name}` across the frozen pilot root, got {values!r}."
        )
    return next(iter(values))


def _manifest_row_counts(
    output_root: Path,
    families: tuple[ManifestFamily, ...],
) -> dict[ManifestFamily, int]:
    """Count prepared-manifest rows per selected family."""
    counts: dict[ManifestFamily, int] = {}
    for family in families:
        prepared_path = output_root / "manifests" / f"{family}.prepared.jsonl"
        counts[family] = sum(1 for _ in iter_jsonl_objects(prepared_path))
    return counts


def _speaker_counts(
    output_root: Path,
    families: tuple[ManifestFamily, ...],
) -> dict[ManifestFamily, int]:
    """Count unique speakers per selected prepared manifest family."""
    counts: dict[ManifestFamily, int] = {}
    for family in families:
        prepared_path = output_root / "manifests" / f"{family}.prepared.jsonl"
        speaker_ids = {
            _prepared_manifest_row(payload, prepared_path).speaker_id
            for payload in iter_jsonl_objects(prepared_path)
        }
        counts[family] = len(speaker_ids)
    return counts


def _prepared_manifest_row(payload: object, path: Path) -> PreparedManifestRow:
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
        audio=_required_string(payload, "audio"),
        text=_required_string(payload, "text"),
        ref_audio=_required_string(payload, "ref_audio"),
        speaker_id=_required_string(payload, "speaker_id"),
        dataset=_required_string(payload, "dataset"),
        source_split=_required_string(payload, "source_split"),
        quality_tier=_required_quality_tier(payload, "quality_tier"),
        audio_codes=rendered_audio_codes,
    )


def _required_quality_tier(payload: dict[str, object], key: str) -> QualityTier:
    """Return one required quality-tier string from a JSON payload."""
    value = _required_string(payload, key)
    if value == "high_trust":
        return "high_trust"
    if value == "medium_trust":
        return "medium_trust"
    if value == "rejected":
        return "rejected"
    raise ValueError(f"Malformed `{key}` in prepared manifest payload.")


def _required_string(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value


def _required_int(payload: dict[str, object], key: str) -> int:
    """Return one required integer field from a JSON payload."""
    value = payload.get(key)
    if not isinstance(value, int):
        raise ValueError(f"Malformed `{key}` in JSON payload.")
    return value


def _git_head(repo_root: Path) -> str:
    """Return the current repository HEAD for bundle reproducibility metadata."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Task 101 pilot bundle could not resolve repo HEAD.\n"
            f"stdout:\n{result.stdout.strip()}\n"
            f"stderr:\n{result.stderr.strip()}"
        )
    return result.stdout.strip()


def _validate_bundle_paths(output_root: Path, families: tuple[ManifestFamily, ...]) -> None:
    """Fail closed if any prepared row points outside the materialized bundle."""
    for family in families:
        prepared_path = output_root / "manifests" / f"{family}.prepared.jsonl"
        for payload in iter_jsonl_objects(prepared_path):
            prepared_row = _prepared_manifest_row(payload, prepared_path)
            audio_path = output_root / prepared_row.audio
            ref_audio_path = output_root / prepared_row.ref_audio
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


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _copy_artifact_with_fallback(
    *,
    source_path: Path,
    output_root: Path,
    relative_path: Path,
) -> Path:
    """Materialize one bundle artifact by hardlink with copy fallback."""
    resolved_source_path = _resolve_existing_artifact_path(source_path)
    target_path = output_root / relative_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        return target_path
    try:
        os.link(resolved_source_path, target_path)
    except OSError:
        shutil.copy2(resolved_source_path, target_path)
    return target_path


def _resolve_existing_artifact_path(path: Path) -> Path:
    """Resolve one path across Unicode-normalized filesystem variants."""
    if path.exists():
        return path
    if not path.is_absolute():
        raise FileNotFoundError(path)
    parts = path.parts
    if not parts:
        raise FileNotFoundError(path)
    current_path = Path(parts[0])
    if not current_path.exists():
        raise FileNotFoundError(path)
    for part in parts[1:]:
        candidate_path = current_path / part
        if candidate_path.exists():
            current_path = candidate_path
            continue
        normalized_part = unicodedata.normalize("NFC", part)
        matching_paths = [
            child_path
            for child_path in current_path.iterdir()
            if unicodedata.normalize("NFC", child_path.name) == normalized_part
        ]
        if len(matching_paths) != 1:
            raise FileNotFoundError(path)
        current_path = matching_paths[0]
    return current_path


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    """Parse CLI arguments for deterministic Task 101 pilot-bundle creation."""
    parser = argparse.ArgumentParser(
        description="Materialize one deterministic Task 101 pilot bundle from a frozen root."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--source-root", type=Path, default=DEFAULT_FROZEN_PILOT_ROOT)
    build_parser.add_argument("--output-root", type=Path, default=DEFAULT_PILOT_BUNDLE_ROOT)
    build_parser.add_argument(
        "--train-manifest-family",
        default=DEFAULT_TRAIN_MANIFEST_FAMILY,
    )
    build_parser.add_argument(
        "--eval-manifest-family",
        default=DEFAULT_EVAL_MANIFEST_FAMILY,
    )
    build_parser.add_argument("--tokenizer-model", default=DEFAULT_TOKENIZER_MODEL)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the committed CLI surface for Task 101 pilot-bundle materialization."""
    args = _parse_args(argv)
    if args.command == "build":
        summary = build_task101_pilot_bundle(
            source_root=Path(args.source_root),
            output_root=Path(args.output_root),
            train_manifest_family=args.train_manifest_family,
            eval_manifest_family=args.eval_manifest_family,
            tokenizer_model=str(args.tokenizer_model),
            encode_audio_codes_fn=encode_audio_codes,
            repo_root=Path.cwd(),
        )
        print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
        return 0
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
