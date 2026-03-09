"""Storage and atomic-write helpers for the staged Qwen preprocessing lane.

Purpose:
    Provide deterministic output-root preparation, JSON/JSONL atomic writes,
    and durable spool read/write helpers for the Task 103/T110 preprocessing
    pipeline.

Relationships:
    - Shared by row-processing, finalization, and reporting modules.
    - Owns the durable spool path contract used to decouple row-processing from
      later manifest finalization.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterator, Protocol

from scripts.sir_convert_a_lot.benchmarking.output_policy import enforce_generated_output_path
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    AdmissionDecision,
    ManifestFamily,
    QualityTier,
    SpeakerQualityGate,
    SpoolRow,
    Task103Stage,
)


def json_default(value: object) -> object:
    """Serialize supported objects into stable JSON payloads."""
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable.")


class JsonlAtomicWriter:
    """Write one JSONL artifact through a temp file and atomic rename."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: _TextWriteCloser | None = None
        self._temp_path: Path | None = None

    def __enter__(self) -> "JsonlAtomicWriter":
        enforce_generated_output_path(self._path, label=self._path.name)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self._path.parent,
            delete=False,
            suffix=".tmp",
        )
        self._handle = temp_handle
        self._temp_path = Path(temp_handle.name)
        return self

    def write_row(self, row: object) -> None:
        """Write one JSONL row to the temp artifact."""
        if self._handle is None:
            raise RuntimeError("JSONL writer must be opened before writing rows.")
        rendered_row = json.dumps(row, sort_keys=True, ensure_ascii=False, default=json_default)
        self._handle.write(rendered_row)
        self._handle.write("\n")

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self._handle is not None:
            self._handle.close()
        if self._temp_path is None:
            return
        if exc_type is None:
            self._temp_path.replace(self._path)
        elif self._temp_path.exists():
            self._temp_path.unlink()


def _atomic_write_text(path: Path, rendered_text: str) -> None:
    """Write one text artifact through a temp file and atomic rename."""
    enforce_generated_output_path(path, label=path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(rendered_text)
    temp_path.replace(path)


def write_json(path: Path, payload: object) -> None:
    """Write deterministic JSON output."""
    _atomic_write_text(
        path,
        json.dumps(payload, indent=2, sort_keys=True, default=json_default) + "\n",
    )


def write_jsonl(path: Path, rows: list[object]) -> None:
    """Write deterministic JSONL output from one bounded row list."""
    with JsonlAtomicWriter(path) as writer:
        for row in rows:
            writer.write_row(row)


def prepare_output_root(output_root: Path, *, stage: Task103Stage) -> None:
    """Prepare the generated output root for the requested stage."""
    output_root.mkdir(parents=True, exist_ok=True)
    if stage in {"all", "row-processing"}:
        for subdir_name in (
            "inventory",
            "curated",
            "refs",
            "audio_24k",
            "manifests",
            "reports",
            "spool",
        ):
            subdir = output_root / subdir_name
            if subdir.exists():
                shutil.rmtree(subdir)
    elif stage in {"finalization", "reports"}:
        reports_dir = output_root / "reports"
        if reports_dir.exists():
            shutil.rmtree(reports_dir)
    for generated_name in ("report.json", "report.md", "failure.txt"):
        generated_path = output_root / generated_name
        if generated_path.exists():
            generated_path.unlink()


def iter_jsonl_objects(path: Path) -> Iterator[dict[str, object]]:
    """Yield parsed JSONL rows from one file if it exists."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if raw_line.strip() == "":
            continue
        payload = json.loads(raw_line)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object rows in {path}.")
        yield payload


def _safe_path_component(raw_value: str) -> str:
    """Render one stable path component for spool storage."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", raw_value)


def _manifest_family_from_value(value: object) -> ManifestFamily:
    """Validate one manifest-family string from one stored JSON payload."""
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
    raise ValueError("Spool row contained an unknown manifest family.")


def spool_rows_dir(output_root: Path) -> Path:
    """Return the canonical spool row root."""
    return output_root / "spool" / "rows"


def spool_row_path(output_root: Path, row: SpoolRow) -> Path:
    """Return the canonical on-disk path for one spool row."""
    return (
        spool_rows_dir(output_root)
        / _safe_path_component(row.dataset)
        / _safe_path_component(row.source_split)
        / _safe_path_component(row.speaker_id)
        / f"{_safe_path_component(row.dataset_row_id)}.json"
    )


def write_spool_row(output_root: Path, row: SpoolRow) -> None:
    """Persist one completed row-processing result atomically."""
    write_json(spool_row_path(output_root, row), row)


def iter_spool_rows(output_root: Path) -> Iterator[SpoolRow]:
    """Yield typed spool rows from the durable row-processing subtree."""
    rows_root = spool_rows_dir(output_root)
    if not rows_root.exists():
        return
    for path in sorted(rows_root.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected one JSON object in spool row {path}.")
        reference_audio_24k_paths_raw = payload.get("reference_audio_24k_paths")
        if not isinstance(reference_audio_24k_paths_raw, dict):
            raise ValueError(f"Malformed `reference_audio_24k_paths` in {path}.")
        reference_audio_24k_paths: dict[ManifestFamily, str] = {}
        for key, value in reference_audio_24k_paths_raw.items():
            manifest_family = _manifest_family_from_value(key)
            if not isinstance(value, str):
                raise ValueError(f"Malformed reference path mapping in {path}.")
            reference_audio_24k_paths[manifest_family] = value
        manifest_targets_raw = payload.get("manifest_targets")
        if not isinstance(manifest_targets_raw, list):
            raise ValueError(f"Malformed `manifest_targets` in {path}.")
        manifest_targets = tuple(
            _manifest_family_from_value(value) for value in manifest_targets_raw
        )
        yield SpoolRow(
            dataset=_required_str(payload, "dataset", path),
            source_split=_required_str(payload, "source_split", path),
            dataset_row_id=_required_str(payload, "dataset_row_id", path),
            speaker_id=_required_str(payload, "speaker_id", path),
            speaker_name=_required_str(payload, "speaker_name", path),
            speaker_from_id=_required_bool(payload, "speaker_from_id", path),
            source_audio_path=_required_str(payload, "source_audio_path", path),
            audio_24k_path=_required_str(payload, "audio_24k_path", path),
            duration_seconds=_required_float(payload, "duration_seconds", path),
            text_normalized=_required_str(payload, "text_normalized", path),
            reference_audio_24k_paths=reference_audio_24k_paths,
            asr_model=_required_str(payload, "asr_model", path),
            asr_revision=_required_str(payload, "asr_revision", path),
            asr_transcript=_required_str(payload, "asr_transcript", path),
            asr_wer=_required_float(payload, "asr_wer", path),
            quality_tier=_required_quality_tier(payload, path),
            speaker_quality_gate=_required_speaker_quality_gate(payload, path),
            dedup_applied=_required_bool(payload, "dedup_applied", path),
            admission_decision=_required_admission_decision(payload, path),
            manifest_targets=manifest_targets,
        )


def _required_str(payload: dict[str, object], key: str, path: Path) -> str:
    """Return one required string field from one stored JSON payload."""
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"Malformed `{key}` in {path}.")
    return value


class _TextWriteCloser(Protocol):
    """Minimal text-writer surface used by the JSONL atomic writer."""

    def write(self, text: str) -> object:
        """Write text to one underlying temp file."""

    def close(self) -> object:
        """Close one underlying temp file."""


def _required_bool(payload: dict[str, object], key: str, path: Path) -> bool:
    """Return one required boolean field from one stored JSON payload."""
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"Malformed `{key}` in {path}.")
    return value


def _required_float(payload: dict[str, object], key: str, path: Path) -> float:
    """Return one required float-like field from one stored JSON payload."""
    value = payload.get(key)
    if not isinstance(value, (float, int)):
        raise ValueError(f"Malformed `{key}` in {path}.")
    return round(float(value), 6)


def _required_quality_tier(payload: dict[str, object], path: Path) -> QualityTier:
    """Return one required typed quality tier from one stored spool payload."""
    value = _required_str(payload, "quality_tier", path)
    if value == "high_trust":
        return "high_trust"
    if value == "medium_trust":
        return "medium_trust"
    if value == "rejected":
        return "rejected"
    raise ValueError(f"Malformed `quality_tier` in {path}.")


def _required_speaker_quality_gate(
    payload: dict[str, object],
    path: Path,
) -> SpeakerQualityGate:
    """Return one required typed speaker gate from one stored spool payload."""
    value = _required_str(payload, "speaker_quality_gate", path)
    if value == "speaker_from_id":
        return "speaker_from_id"
    if value == "manual_review":
        return "manual_review"
    if value == "rejected_multi_speaker":
        return "rejected_multi_speaker"
    raise ValueError(f"Malformed `speaker_quality_gate` in {path}.")


def _required_admission_decision(
    payload: dict[str, object],
    path: Path,
) -> AdmissionDecision:
    """Return one required typed admission decision from one stored spool payload."""
    value = _required_str(payload, "admission_decision", path)
    if value == "admit":
        return "admit"
    if value == "reject":
        return "reject"
    raise ValueError(f"Malformed `admission_decision` in {path}.")
