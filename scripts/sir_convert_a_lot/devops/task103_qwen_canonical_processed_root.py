"""Canonical processed-root dedupe for Task 103 run roots.

Purpose:
    Materialize one immutable deduplicated processed root from multiple Task
    103 run roots so future allocation can exclude already owned rows through
    one canonical root instead of reasoning across overlapping worker roots.

Relationships:
    - Consumes durable spool rows and completed-row indexes from
      `task103_qwen_preprocessing_storage.py`.
    - Produces one processed-root artifact tree that still conforms to the
      Task 103 completed-row contract and can therefore be reused as an
      exclusion source by Task 121 allocation logic.
    - Does not finalize manifests or mutate any original run root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Sequence

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    AdmissionDecision,
    QualityTier,
    SpeakerQualityGate,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    rebuild_completed_row_keys_index,
    spool_rows_dir,
    write_json,
    write_jsonl,
    write_spool_row,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_row_keys import (
    RowKey,
    write_row_key_records,
)

ConflictReason = Literal["payload_mismatch", "audio_hash_mismatch"]


@dataclass(frozen=True)
class RowCandidate:
    """Describe one candidate row coming from one source run root."""

    run_root: str
    row_key: RowKey
    spool_row: SpoolRow
    spool_path: str
    audio_24k_hash: str
    reference_audio_hashes: dict[str, str]
    payload_signature: str


@dataclass(frozen=True)
class DuplicateDecision:
    """Describe one dropped duplicate that matched the winning candidate exactly."""

    row_key: RowKey
    winning_run_root: str
    dropped_run_root: str


@dataclass(frozen=True)
class ConflictRecord:
    """Describe one quarantined same-row conflict across multiple run roots."""

    row_key: RowKey
    reason: ConflictReason
    candidate_run_roots: list[str]


@dataclass(frozen=True)
class CanonicalProcessedRootSummary:
    """Stable summary for one canonical processed-root build."""

    output_root: str
    input_run_roots: list[str]
    retained_row_count: int
    dropped_duplicate_row_count: int
    conflict_row_count: int
    retained_audio_file_count: int


@dataclass(frozen=True)
class CanonicalProcessedRootFreezeSummary:
    """Stable freeze summary for one canonical processed root."""

    output_root: str
    retained_row_count: int
    conflict_row_count: int
    owned_row_keys_path: str
    conflict_row_keys_path: str


def canonical_processed_root_report_path(output_root: Path) -> Path:
    """Return the summary report path for one canonical processed root."""
    return output_root / "reports" / "canonical_processed_root_report.json"


def canonical_processed_root_duplicates_path(output_root: Path) -> Path:
    """Return the duplicates report path for one canonical processed root."""
    return output_root / "reports" / "canonical_processed_root_duplicates.jsonl"


def canonical_processed_root_conflicts_path(output_root: Path) -> Path:
    """Return the conflicts report path for one canonical processed root."""
    return output_root / "reports" / "canonical_processed_root_conflicts.jsonl"


def canonical_processed_root_owned_row_keys_path(output_root: Path) -> Path:
    """Return the owned-row-key artifact path for one canonical processed root."""
    return output_root / "reports" / "canonical_processed_root_owned_row_keys.jsonl"


def canonical_processed_root_conflict_row_keys_path(output_root: Path) -> Path:
    """Return the conflict-row-key artifact path for one canonical processed root."""
    return output_root / "reports" / "canonical_processed_root_conflict_row_keys.jsonl"


def canonical_processed_root_freeze_path(output_root: Path) -> Path:
    """Return the freeze summary path for one canonical processed root."""
    return output_root / "reports" / "canonical_processed_root_freeze.json"


def build_canonical_processed_root(
    *,
    output_root: Path,
    run_roots: Sequence[Path],
) -> CanonicalProcessedRootSummary:
    """Build one immutable deduplicated processed root from ordered run roots."""
    if not run_roots:
        raise ValueError("At least one input run root is required.")
    if output_root.exists():
        raise ValueError(
            "Canonical processed-root output must be a new path so original "
            "artifacts stay immutable."
        )

    winners: dict[RowKey, RowCandidate] = {}
    duplicates: list[DuplicateDecision] = []
    conflicts: dict[RowKey, ConflictRecord] = {}

    for run_root in run_roots:
        for candidate in _iter_row_candidates(run_root):
            existing = winners.get(candidate.row_key)
            if existing is None and candidate.row_key not in conflicts:
                winners[candidate.row_key] = candidate
                continue
            if existing is None:
                conflict = conflicts[candidate.row_key]
                conflict_roots = sorted({*conflict.candidate_run_roots, candidate.run_root})
                conflicts[candidate.row_key] = ConflictRecord(
                    row_key=candidate.row_key,
                    reason=conflict.reason,
                    candidate_run_roots=conflict_roots,
                )
                continue
            if _candidates_match(existing, candidate):
                duplicates.append(
                    DuplicateDecision(
                        row_key=candidate.row_key,
                        winning_run_root=existing.run_root,
                        dropped_run_root=candidate.run_root,
                    )
                )
                continue
            conflict_reason: ConflictReason = (
                "payload_mismatch"
                if existing.payload_signature != candidate.payload_signature
                else "audio_hash_mismatch"
            )
            conflicts[candidate.row_key] = ConflictRecord(
                row_key=candidate.row_key,
                reason=conflict_reason,
                candidate_run_roots=sorted({existing.run_root, candidate.run_root}),
            )
            del winners[candidate.row_key]

    retained_audio_paths: set[Path] = set()
    for row_key in sorted(winners):
        winner = winners[row_key]
        write_spool_row(output_root, winner.spool_row)
        retained_audio_paths.add(
            _copy_artifact_with_fallback(
                source_path=Path(winner.run_root) / winner.spool_row.audio_24k_path,
                output_root=output_root,
                relative_path=Path(winner.spool_row.audio_24k_path),
            )
        )
        for reference_audio_path in winner.spool_row.reference_audio_24k_paths.values():
            retained_audio_paths.add(
                _copy_artifact_with_fallback(
                    source_path=Path(winner.run_root) / reference_audio_path,
                    output_root=output_root,
                    relative_path=Path(reference_audio_path),
                )
            )

    rebuild_completed_row_keys_index(output_root)
    write_row_key_records(
        canonical_processed_root_owned_row_keys_path(output_root),
        sorted(winners),
    )
    write_row_key_records(
        canonical_processed_root_conflict_row_keys_path(output_root),
        sorted(conflicts),
    )
    write_json(
        canonical_processed_root_report_path(output_root),
        CanonicalProcessedRootSummary(
            output_root=output_root.as_posix(),
            input_run_roots=[run_root.as_posix() for run_root in run_roots],
            retained_row_count=len(winners),
            dropped_duplicate_row_count=len(duplicates),
            conflict_row_count=len(conflicts),
            retained_audio_file_count=len(retained_audio_paths),
        ),
    )
    write_json(
        canonical_processed_root_freeze_path(output_root),
        CanonicalProcessedRootFreezeSummary(
            output_root=output_root.as_posix(),
            retained_row_count=len(winners),
            conflict_row_count=len(conflicts),
            owned_row_keys_path=canonical_processed_root_owned_row_keys_path(
                output_root
            ).as_posix(),
            conflict_row_keys_path=canonical_processed_root_conflict_row_keys_path(
                output_root
            ).as_posix(),
        ),
    )
    write_jsonl(
        canonical_processed_root_duplicates_path(output_root),
        [asdict(record) for record in duplicates],
    )
    write_jsonl(
        canonical_processed_root_conflicts_path(output_root),
        [asdict(conflicts[row_key]) for row_key in sorted(conflicts)],
    )
    return CanonicalProcessedRootSummary(
        output_root=output_root.as_posix(),
        input_run_roots=[run_root.as_posix() for run_root in run_roots],
        retained_row_count=len(winners),
        dropped_duplicate_row_count=len(duplicates),
        conflict_row_count=len(conflicts),
        retained_audio_file_count=len(retained_audio_paths),
    )


def _iter_row_candidates(run_root: Path) -> list[RowCandidate]:
    """Load row candidates from one completed Task 103 run root."""
    rows_root = spool_rows_dir(run_root)
    candidates: list[RowCandidate] = []
    for spool_path in sorted(rows_root.rglob("*.json")):
        payload = json.loads(spool_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Malformed spool row payload: {spool_path}")
        spool_row = _spool_row_from_payload(payload)
        row_key = (spool_row.dataset, spool_row.source_split, spool_row.dataset_row_id)
        candidates.append(
            RowCandidate(
                run_root=run_root.as_posix(),
                row_key=row_key,
                spool_row=spool_row,
                spool_path=spool_path.as_posix(),
                audio_24k_hash=_hash_file(run_root / spool_row.audio_24k_path),
                reference_audio_hashes={
                    family: _hash_file(run_root / relative_path)
                    for family, relative_path in spool_row.reference_audio_24k_paths.items()
                },
                payload_signature=_payload_signature(spool_row),
            )
        )
    return candidates


def _spool_row_from_payload(payload: dict[str, object]) -> SpoolRow:
    """Hydrate one typed spool row from one stored payload."""
    reference_audio_24k_paths_raw = payload.get("reference_audio_24k_paths")
    if not isinstance(reference_audio_24k_paths_raw, dict):
        raise ValueError("Malformed `reference_audio_24k_paths` in spool payload.")
    manifest_targets_raw = payload.get("manifest_targets")
    if not isinstance(manifest_targets_raw, list):
        raise ValueError("Malformed `manifest_targets` in spool payload.")
    if not all(isinstance(value, str) for value in manifest_targets_raw):
        raise ValueError("Malformed `manifest_targets` values in spool payload.")
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in reference_audio_24k_paths_raw.items()
    ):
        raise ValueError("Malformed reference-audio mapping in spool payload.")
    return SpoolRow(
        dataset=_required_str(payload, "dataset"),
        source_split=_required_str(payload, "source_split"),
        dataset_row_id=_required_str(payload, "dataset_row_id"),
        speaker_id=_required_str(payload, "speaker_id"),
        speaker_name=_required_str(payload, "speaker_name"),
        speaker_from_id=_required_bool(payload, "speaker_from_id"),
        source_audio_path=_required_str(payload, "source_audio_path"),
        audio_24k_path=_required_str(payload, "audio_24k_path"),
        duration_seconds=_required_float(payload, "duration_seconds"),
        text_normalized=_required_str(payload, "text_normalized"),
        reference_audio_24k_paths={
            key: value for key, value in reference_audio_24k_paths_raw.items()
        },
        asr_model=_required_str(payload, "asr_model"),
        asr_revision=_required_str(payload, "asr_revision"),
        asr_transcript=_required_str(payload, "asr_transcript"),
        asr_wer=_required_float(payload, "asr_wer"),
        quality_tier=_required_quality_tier(payload),
        speaker_quality_gate=_required_speaker_quality_gate(payload),
        dedup_applied=_required_bool(payload, "dedup_applied"),
        admission_decision=_required_admission_decision(payload),
        manifest_targets=tuple(manifest_targets_raw),
    )


def _required_str(payload: dict[str, object], key: str) -> str:
    """Return one required string field from a spool payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in spool payload.")
    return value


def _required_bool(payload: dict[str, object], key: str) -> bool:
    """Return one required boolean field from a spool payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Malformed `{key}` in spool payload.")
    return value


def _required_float(payload: dict[str, object], key: str) -> float:
    """Return one required float-like field from a spool payload."""
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"Malformed `{key}` in spool payload.")
    return round(float(value), 6)


def _required_quality_tier(payload: dict[str, object]) -> QualityTier:
    """Return one required typed quality tier from a spool payload."""
    value = _required_str(payload, "quality_tier")
    if value == "high_trust":
        return "high_trust"
    if value == "medium_trust":
        return "medium_trust"
    if value == "rejected":
        return "rejected"
    raise ValueError("Malformed `quality_tier` in spool payload.")


def _required_speaker_quality_gate(payload: dict[str, object]) -> SpeakerQualityGate:
    """Return one required typed speaker-quality gate from a spool payload."""
    value = _required_str(payload, "speaker_quality_gate")
    if value == "speaker_from_id":
        return "speaker_from_id"
    if value == "manual_review":
        return "manual_review"
    if value == "rejected_multi_speaker":
        return "rejected_multi_speaker"
    raise ValueError("Malformed `speaker_quality_gate` in spool payload.")


def _required_admission_decision(payload: dict[str, object]) -> AdmissionDecision:
    """Return one required typed admission decision from a spool payload."""
    value = _required_str(payload, "admission_decision")
    if value == "admit":
        return "admit"
    if value == "reject":
        return "reject"
    raise ValueError("Malformed `admission_decision` in spool payload.")


def _payload_signature(spool_row: SpoolRow) -> str:
    """Render one deterministic semantic signature for one spool row."""
    rendered = json.dumps(
        {
            "dataset": spool_row.dataset,
            "source_split": spool_row.source_split,
            "dataset_row_id": spool_row.dataset_row_id,
            "speaker_id": spool_row.speaker_id,
            "speaker_name": spool_row.speaker_name,
            "speaker_from_id": spool_row.speaker_from_id,
            "source_audio_path": spool_row.source_audio_path,
            "duration_seconds": spool_row.duration_seconds,
            "text_normalized": spool_row.text_normalized,
            "asr_model": spool_row.asr_model,
            "asr_revision": spool_row.asr_revision,
            "asr_transcript": spool_row.asr_transcript,
            "asr_wer": spool_row.asr_wer,
            "quality_tier": spool_row.quality_tier,
            "speaker_quality_gate": spool_row.speaker_quality_gate,
            "dedup_applied": spool_row.dedup_applied,
            "admission_decision": spool_row.admission_decision,
            "manifest_targets": list(spool_row.manifest_targets),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _candidates_match(first: RowCandidate, second: RowCandidate) -> bool:
    """Return whether two row candidates are semantically identical duplicates."""
    return (
        first.payload_signature == second.payload_signature
        and first.audio_24k_hash == second.audio_24k_hash
        and first.reference_audio_hashes == second.reference_audio_hashes
    )


def _hash_file(path: Path) -> str:
    """Hash one file with SHA256."""
    resolved_path = _resolve_existing_artifact_path(path)
    digest = hashlib.sha256()
    with resolved_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_artifact_with_fallback(
    *,
    source_path: Path,
    output_root: Path,
    relative_path: Path,
) -> Path:
    """Materialize one retained artifact by hardlink with copy fallback."""
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
    """Resolve a path across Unicode-normalized filesystem variants."""
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
    """Parse CLI arguments for canonical processed-root materialization."""
    parser = argparse.ArgumentParser(
        description="Build one canonical deduplicated processed root from Task 103 run roots."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--output-root", type=Path, required=True)
    build_parser.add_argument(
        "--run-root",
        dest="run_roots",
        action="append",
        type=Path,
        required=True,
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the canonical processed-root CLI."""
    args = _parse_args(argv)
    if args.command != "build":
        raise ValueError(f"Unsupported command: {args.command}")
    summary = build_canonical_processed_root(
        output_root=Path(args.output_root),
        run_roots=[Path(path) for path in args.run_roots],
    )
    print(json.dumps(asdict(summary), indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
