"""Selected-row mini-bundle helpers for the Qwen backward-lineage and fresh-start proof lane
backward-lineage probe.

Purpose:
    Materialize one tiny truthful bundle containing the exact fresh-start rows
    under investigation so the backward-lineage probe can run against stable
    bundle-local assets on Hemma.

Relationships:
    - Used by `qwen_backward_lineage_runner.py` before the container probe
      launches.
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
    validate_bundle_row_path,
    validate_precomputed_ref_input_contract,
)

_SOURCE_LINE_FIELD = "qwen_lineage_source_manifest_line_number"
_SOURCE_FAMILY_FIELD = "qwen_lineage_source_manifest_family"


@dataclass(frozen=True)
class SelectedRowLineage:
    """Source identity for one selected train row in the mini-bundle."""

    source_line_number: int
    speaker_id: str | None
    text_preview: str


@dataclass(frozen=True)
class BackwardLineageMiniBundle:
    """Deterministic summary of one backward-lineage mini-bundle."""

    source_bundle_root: str
    bundle_root: str
    manifest_path: str
    manifest_family: str
    selected_source_lines: tuple[int, ...]
    selected_rows: tuple[SelectedRowLineage, ...]


def materialize_backward_lineage_bundle(
    *,
    source_bundle_root: Path,
    target_bundle_root: Path,
    manifest_family: str,
    selected_source_lines: tuple[int, ...],
) -> BackwardLineageMiniBundle:
    """Copy the exact selected prepared rows plus bundle-local assets."""
    resolved_source_bundle_root = _resolve_source_bundle_root(
        source_bundle_root=source_bundle_root,
        manifest_family=manifest_family,
    )
    source_manifest_path = _manifest_path(resolved_source_bundle_root, manifest_family)
    selected_rows = _selected_rows(source_manifest_path, selected_source_lines, manifest_family)
    if len(selected_rows) == 0:
        raise SystemExit("Backward-lineage mini-bundle selection was empty.")
    if target_bundle_root.exists():
        raise SystemExit(
            "Backward-lineage mini-bundle target already exists: "
            f"`{target_bundle_root.as_posix()}`."
        )
    (target_bundle_root / "manifests").mkdir(parents=True, exist_ok=False)
    _copy_rows_assets(
        source_bundle_root=resolved_source_bundle_root,
        target_bundle_root=target_bundle_root,
        rows=(row for _, row in selected_rows),
    )
    target_manifest_path = _manifest_path(target_bundle_root, manifest_family)
    _write_manifest(target_manifest_path, (row for _, row in selected_rows))
    _validate_single_manifest_bundle(
        bundle_root=target_bundle_root,
        manifest_family=manifest_family,
    )
    lineage_rows = tuple(
        SelectedRowLineage(
            source_line_number=source_line_number,
            speaker_id=_optional_string(row, "speaker_id"),
            text_preview=_text_preview(row),
        )
        for source_line_number, row in selected_rows
    )
    return BackwardLineageMiniBundle(
        source_bundle_root=resolved_source_bundle_root.as_posix(),
        bundle_root=target_bundle_root.as_posix(),
        manifest_path=target_manifest_path.as_posix(),
        manifest_family=manifest_family,
        selected_source_lines=tuple(source_line_number for source_line_number, _ in selected_rows),
        selected_rows=lineage_rows,
    )


def _resolve_source_bundle_root(*, source_bundle_root: Path, manifest_family: str) -> Path:
    """Resolve the canonical dated Qwen pilot training bundle root when needed."""
    if _has_required_manifest(bundle_root=source_bundle_root, manifest_family=manifest_family):
        return source_bundle_root
    parent = source_bundle_root.parent
    prefix = f"{source_bundle_root.name}-"
    dated_candidates = sorted(
        candidate
        for candidate in parent.glob(f"{prefix}*")
        if candidate.is_dir()
        and _has_required_manifest(bundle_root=candidate, manifest_family=manifest_family)
    )
    if dated_candidates:
        return dated_candidates[-1]
    raise SystemExit(
        "Backward-lineage mini-bundle source bundle root did not exist and no canonical "
        f"bundle matched manifest `{manifest_family}`. Tried `{source_bundle_root.as_posix()}`."
    )


def _manifest_path(bundle_root: Path, manifest_family: str) -> Path:
    return bundle_root / "manifests" / f"{manifest_family}.prepared.jsonl"


def _has_required_manifest(*, bundle_root: Path, manifest_family: str) -> bool:
    return _manifest_path(bundle_root, manifest_family).exists()


def _selected_rows(
    manifest_path: Path,
    selected_source_lines: tuple[int, ...],
    manifest_family: str,
) -> list[tuple[int, dict[str, object]]]:
    """Return selected manifest rows in the requested source-line order."""
    if len(selected_source_lines) == 0:
        raise SystemExit("Backward-lineage probe requires at least one selected source line.")
    unresolved = list(selected_source_lines)
    selected_rows_by_line: dict[int, dict[str, object]] = {}
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if line_number not in unresolved:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise SystemExit(
                    "Prepared manifest row in "
                    f"`{manifest_path.as_posix()}` line {line_number} was not an object."
                )
            annotated_payload = dict(payload)
            annotated_payload[_SOURCE_LINE_FIELD] = line_number
            annotated_payload[_SOURCE_FAMILY_FIELD] = manifest_family
            selected_rows_by_line[line_number] = annotated_payload
            if len(selected_rows_by_line) == len(set(selected_source_lines)):
                break
    missing_lines = [
        line_number
        for line_number in selected_source_lines
        if line_number not in selected_rows_by_line
    ]
    if missing_lines:
        raise SystemExit(
            "Backward-lineage mini-bundle could not resolve source lines "
            f"{missing_lines} from `{manifest_path.as_posix()}`."
        )
    return [
        (line_number, selected_rows_by_line[line_number]) for line_number in selected_source_lines
    ]


def _copy_rows_assets(
    *,
    source_bundle_root: Path,
    target_bundle_root: Path,
    rows: Iterable[dict[str, object]],
) -> None:
    """Copy bundle-local assets for the selected prepared rows."""
    for row in rows:
        for key in ("audio", "ref_audio", "precomputed_ref_input_path"):
            raw_value = row.get(key)
            if raw_value is None:
                if key == "ref_audio":
                    raise SystemExit(
                        "Backward-lineage mini-bundle row lacked required `ref_audio`."
                    )
                continue
            for relative_path in row_path_values(
                raw_value, key=key, manifest_path=target_bundle_root
            ):
                source_path = source_bundle_root / relative_path
                target_path = target_bundle_root / relative_path
                if not source_path.exists():
                    raise SystemExit(
                        "Backward-lineage mini-bundle source asset did not exist: "
                        f"`{source_path.as_posix()}`."
                    )
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if not target_path.exists():
                    shutil.copy2(source_path, target_path)


def _write_manifest(path: Path, rows: Iterable[dict[str, object]]) -> None:
    """Write the selected prepared rows into the target mini-bundle manifest."""
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _validate_single_manifest_bundle(*, bundle_root: Path, manifest_family: str) -> None:
    """Validate the single-manifest mini-bundle contract for backward-lineage."""
    manifest_path = _manifest_path(bundle_root, manifest_family)
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise SystemExit(
                    f"Prepared manifest row in `{manifest_path.as_posix()}` was not an object."
                )
            for key in ("audio", "ref_audio"):
                validate_bundle_row_path(
                    bundle_root,
                    manifest_path,
                    payload,
                    key,
                    required=True,
                )
            validate_bundle_row_path(
                bundle_root,
                manifest_path,
                payload,
                "precomputed_ref_input_path",
                required=True,
            )
            validate_precomputed_ref_input_contract(manifest_path, payload)


def _optional_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) else None


def _text_preview(payload: dict[str, object]) -> str:
    """Return one short text preview for a selected manifest row."""
    text = payload.get("text")
    if not isinstance(text, str):
        raise SystemExit("Backward-lineage selected row lacked required `text`.")
    return text[:120]
