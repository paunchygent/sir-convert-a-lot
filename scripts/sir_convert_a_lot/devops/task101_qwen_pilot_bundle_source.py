"""Source and materialization helpers for Task 101 pilot-bundle builds.

Purpose:
    Centralize frozen-root ledger resolution, output-capacity checks, artifact
    copying, and reproducibility metadata helpers so the Task 101 orchestrator
    stays focused on the bundle stage flow.

Relationships:
    - Consumed by `task101_qwen_pilot_bundle.py` during copy-stage setup and
      bundle summary generation.
    - Reuses Task 103 spool, row-key, and JSON storage contracts.
    - Delegates JSON payload validation to
      `task101_qwen_pilot_bundle_validation.py`.
"""

from __future__ import annotations

import errno
import json
import os
import shutil
import subprocess
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from scripts.sir_convert_a_lot.devops import (
    task101_qwen_pilot_bundle_validation as bundle_validation,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    ManifestFamily,
    SpoolRow,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    iter_spool_rows,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_row_keys import (
    RowKey,
    load_row_key_records,
)

DEFAULT_BUNDLE_FREE_SPACE_HEADROOM_BYTES = 1 * 1024 * 1024 * 1024
DEFAULT_BUNDLE_FREE_SPACE_HEADROOM_RATIO = 0.10


def ensure_bundle_output_capacity(
    *,
    source_root: Path,
    output_root: Path,
    owned_row_keys: set[RowKey],
    selected_families: tuple[ManifestFamily, ManifestFamily],
) -> None:
    """Fail closed when the output filesystem cannot hold one full pilot bundle."""
    required_bytes = estimated_bundle_bytes(
        source_root=source_root,
        owned_row_keys=owned_row_keys,
        selected_families=selected_families,
    )
    filesystem_path = existing_output_parent(output_root)
    available_bytes = filesystem_free_bytes(filesystem_path)
    required_with_headroom = required_bytes + bundle_free_space_headroom(required_bytes)
    if available_bytes >= required_with_headroom:
        return
    raise OSError(
        errno.ENOSPC,
        "Task 101 pilot bundle requires approximately "
        f"{render_gib(required_with_headroom)} free under "
        f"`{filesystem_path.as_posix()}` but only "
        f"{render_gib(available_bytes)} is available. "
        "Free space on the target filesystem or choose a different "
        "`--output-root` before retrying.",
        output_root.as_posix(),
    )


def estimated_bundle_bytes(
    *,
    source_root: Path,
    owned_row_keys: set[RowKey],
    selected_families: tuple[ManifestFamily, ManifestFamily],
) -> int:
    """Estimate retained audio plus reference-copy bytes for one pilot bundle."""
    required_bytes = 0
    retained_reference_keys: set[tuple[ManifestFamily, str]] = set()
    for spool_row in iter_spool_rows(source_root):
        row_key = row_key_from_spool_row(spool_row)
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
        audio_path = _resolve_existing_artifact_path(source_root / spool_row.audio_24k_path)
        audio_bytes = audio_path.stat().st_size
        required_bytes += audio_bytes
        for family in selected_targets:
            speaker_key = (family, spool_row.speaker_id)
            if speaker_key in retained_reference_keys:
                continue
            retained_reference_keys.add(speaker_key)
            required_bytes += audio_bytes
    return required_bytes


def existing_output_parent(output_root: Path) -> Path:
    """Return the nearest existing parent path for one not-yet-created output root."""
    current_path = output_root.parent
    while not current_path.exists():
        parent_path = current_path.parent
        if parent_path == current_path:
            raise FileNotFoundError(
                "Task 101 pilot bundle could not resolve an existing parent for "
                f"`{output_root.as_posix()}`."
            )
        current_path = parent_path
    return current_path


def filesystem_free_bytes(path: Path) -> int:
    """Return the free-byte capacity for the filesystem containing one path."""
    return shutil.disk_usage(path).free


def bundle_free_space_headroom(required_bytes: int) -> int:
    """Return the minimum extra free-space margin required for bundle materialization."""
    ratio_headroom = int(required_bytes * DEFAULT_BUNDLE_FREE_SPACE_HEADROOM_RATIO)
    return max(DEFAULT_BUNDLE_FREE_SPACE_HEADROOM_BYTES, ratio_headroom)


def render_gib(byte_count: int) -> str:
    """Render one byte count as a concise gibibyte string for operator errors."""
    gibibyte = 1024 * 1024 * 1024
    return f"{byte_count / gibibyte:.1f} GiB"


def freeze_artifact_paths(source_root: Path) -> tuple[Path, Path, int]:
    """Resolve the owned/conflict freeze artifacts for one frozen pilot root."""
    freeze_summary_path = source_root / "reports" / "canonical_processed_root_freeze.json"
    try:
        freeze_payload = json.loads(freeze_summary_path.read_text(encoding="utf-8"))
    except PermissionError:
        return _freeze_artifact_paths_without_summary(source_root)
    if not isinstance(freeze_payload, dict):
        raise ValueError("Frozen pilot freeze summary must be one JSON object.")
    owned_row_keys_path = _resolve_freeze_report_artifact_path(
        source_root,
        reported_path=Path(
            bundle_validation.required_string(freeze_payload, "owned_row_keys_path")
        ),
    )
    conflict_row_keys_path = _resolve_freeze_report_artifact_path(
        source_root,
        reported_path=Path(
            bundle_validation.required_string(freeze_payload, "conflict_row_keys_path")
        ),
    )
    return (
        owned_row_keys_path,
        conflict_row_keys_path,
        bundle_validation.required_int(freeze_payload, "conflict_row_count"),
    )


def _freeze_artifact_paths_without_summary(source_root: Path) -> tuple[Path, Path, int]:
    """Fall back to canonical ledger artifacts when the freeze summary is unreadable."""
    owned_row_keys_path = _resolve_freeze_report_artifact_path(
        source_root,
        reported_path=Path("canonical_processed_root_owned_row_keys.jsonl"),
    )
    conflict_row_keys_path = _resolve_freeze_report_artifact_path(
        source_root,
        reported_path=Path("canonical_processed_root_conflict_row_keys.jsonl"),
    )
    return (
        owned_row_keys_path,
        conflict_row_keys_path,
        len(load_row_key_records(conflict_row_keys_path)),
    )


def row_key_from_spool_row(spool_row: SpoolRow) -> RowKey:
    """Return the canonical row key for one spool row."""
    return (spool_row.dataset, spool_row.source_split, spool_row.dataset_row_id)


def git_head(repo_root: Path) -> str:
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


def utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def copy_artifact_with_fallback(
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


def _resolve_freeze_report_artifact_path(source_root: Path, reported_path: Path) -> Path:
    """Resolve one freeze-ledger artifact from the current frozen source root."""
    preferred_path = source_root / "reports" / reported_path.name
    if preferred_path.exists():
        return preferred_path
    if reported_path.exists():
        return reported_path
    raise FileNotFoundError(
        "Task 101 pilot bundle could not resolve the frozen-root ledger artifact "
        f"`{reported_path.as_posix()}` from source root `{source_root.as_posix()}`."
    )


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
