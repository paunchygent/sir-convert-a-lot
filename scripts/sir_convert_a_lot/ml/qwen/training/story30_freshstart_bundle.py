"""Mini-bundle materialization for the Story 30 fresh-start proof.

Purpose:
    Build one tiny truthful training bundle from the canonical Task 101 pilot
    bundle so fresh-start Candidate 1 probes can run without touching the full
    bundle contract.

Relationships:
    - Used by `story30_freshstart_proof.py` during remote launch handling.
    - Reuses training-bundle validation from `control_plane.bundle_contract`.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from scripts.sir_convert_a_lot.ml.qwen.training.control_plane.bundle_contract import (
    row_path_values,
    validate_training_bundle_paths,
)


@dataclass(frozen=True)
class MiniBundleMaterialization:
    """Deterministic summary of one mini-bundle materialization."""

    source_bundle_root: str
    bundle_root: str
    train_manifest_path: str
    eval_manifest_path: str
    train_row_count: int
    eval_row_count: int


def materialize_mini_bundle(
    *,
    source_bundle_root: Path,
    target_bundle_root: Path,
    train_manifest_family: str,
    eval_manifest_family: str,
    train_line_start: int,
    train_line_end: int,
    eval_line_start: int,
    eval_line_end: int,
) -> MiniBundleMaterialization:
    """Copy one bounded truthful subset of the canonical pilot bundle."""
    resolved_source_bundle_root = _resolve_source_bundle_root(
        source_bundle_root=source_bundle_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
    )
    train_manifest_path = _manifest_path(resolved_source_bundle_root, train_manifest_family)
    eval_manifest_path = _manifest_path(resolved_source_bundle_root, eval_manifest_family)
    train_rows = _selected_rows(train_manifest_path, train_line_start, train_line_end)
    eval_rows = _selected_rows(eval_manifest_path, eval_line_start, eval_line_end)
    if not train_rows:
        raise SystemExit("Fresh-start mini-bundle train slice was empty.")
    if not eval_rows:
        raise SystemExit("Fresh-start mini-bundle eval slice was empty.")
    if target_bundle_root.exists():
        raise SystemExit(
            f"Fresh-start mini-bundle target already exists: `{target_bundle_root.as_posix()}`."
        )
    (target_bundle_root / "manifests").mkdir(parents=True, exist_ok=False)
    for row in [*train_rows, *eval_rows]:
        _copy_row_assets(
            source_bundle_root=resolved_source_bundle_root,
            target_bundle_root=target_bundle_root,
            row=row,
        )
    target_train_manifest = _manifest_path(target_bundle_root, train_manifest_family)
    target_eval_manifest = _manifest_path(target_bundle_root, eval_manifest_family)
    _write_manifest(target_train_manifest, train_rows)
    _write_manifest(target_eval_manifest, eval_rows)
    validate_training_bundle_paths(
        target_bundle_root,
        (train_manifest_family, eval_manifest_family),
        require_precomputed_ref_inputs=True,
    )
    return MiniBundleMaterialization(
        source_bundle_root=resolved_source_bundle_root.as_posix(),
        bundle_root=target_bundle_root.as_posix(),
        train_manifest_path=target_train_manifest.as_posix(),
        eval_manifest_path=target_eval_manifest.as_posix(),
        train_row_count=len(train_rows),
        eval_row_count=len(eval_rows),
    )


def _resolve_source_bundle_root(
    *,
    source_bundle_root: Path,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> Path:
    """Resolve the canonical source bundle root, including dated Task 101 roots."""
    if _has_required_manifests(
        bundle_root=source_bundle_root,
        train_manifest_family=train_manifest_family,
        eval_manifest_family=eval_manifest_family,
    ):
        return source_bundle_root
    parent = source_bundle_root.parent
    prefix = f"{source_bundle_root.name}-"
    dated_candidates = sorted(
        candidate
        for candidate in parent.glob(f"{prefix}*")
        if candidate.is_dir()
        and _has_required_manifests(
            bundle_root=candidate,
            train_manifest_family=train_manifest_family,
            eval_manifest_family=eval_manifest_family,
        )
    )
    if dated_candidates:
        return dated_candidates[-1]
    raise SystemExit(
        "Fresh-start mini-bundle source bundle root did not exist and no canonical "
        "dated Task 101 bundle matched the required manifests. "
        f"Tried `{source_bundle_root.as_posix()}`."
    )


def _manifest_path(bundle_root: Path, manifest_family: str) -> Path:
    return bundle_root / "manifests" / f"{manifest_family}.prepared.jsonl"


def _has_required_manifests(
    *,
    bundle_root: Path,
    train_manifest_family: str,
    eval_manifest_family: str,
) -> bool:
    return _manifest_path(bundle_root, train_manifest_family).exists() and _manifest_path(
        bundle_root, eval_manifest_family
    ).exists()


def _selected_rows(manifest_path: Path, start_line: int, end_line: int) -> list[dict[str, object]]:
    if start_line <= 0 or end_line < start_line:
        raise SystemExit(
            "Fresh-start mini-bundle line bounds must be positive and inclusive. "
            f"Got start={start_line} end={end_line}."
        )
    rows: list[dict[str, object]] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line_number < start_line:
                continue
            if line_number > end_line:
                break
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise SystemExit(
                    "Prepared manifest row in "
                    f"`{manifest_path.as_posix()}` line {line_number} "
                    "was not an object."
                )
            rows.append(payload)
    return rows


def _copy_row_assets(
    *,
    source_bundle_root: Path,
    target_bundle_root: Path,
    row: dict[str, object],
) -> None:
    for key in ("audio", "ref_audio", "precomputed_ref_input_path"):
        raw_value = row.get(key)
        if raw_value is None:
            if key == "ref_audio":
                raise SystemExit("Fresh-start mini-bundle row lacked required `ref_audio`.")
            continue
        for relative_path in row_path_values(raw_value, key=key, manifest_path=target_bundle_root):
            source_path = source_bundle_root / relative_path
            target_path = target_bundle_root / relative_path
            if not source_path.exists():
                raise SystemExit(
                    "Fresh-start mini-bundle source asset did not exist: "
                    f"`{source_path.as_posix()}`."
                )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if target_path.exists():
                continue
            shutil.copy2(source_path, target_path)


def _write_manifest(path: Path, rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
