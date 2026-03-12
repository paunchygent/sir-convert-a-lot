"""Portable-slice staging and localization operations for Task 121.

Purpose:
    Own the runtime mechanics that materialize one portable Qwen preprocessing
    bundle on a worker: stage the required dataset archives locally, then
    extract only the referenced audio members into a plain-file localized
    manifest.

Relationships:
    - Consumes portable bundle artifacts defined in
      `task121_qwen_portable_slice_models.py`.
    - Uses selected-source loading from
      `task121_qwen_portable_slice_planning.py`.
    - Feeds localized manifests into Task 103 row-processing.
"""

from __future__ import annotations

import json
import shutil
import tarfile
import time
from dataclasses import replace
from pathlib import Path
from typing import IO

from huggingface_hub import hf_hub_download

from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_storage import (
    write_json,
    write_jsonl,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_source_models import (
    AudioLocator,
    SourceRecord,
    source_record_to_payload,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_staged_public_corpus import (
    RAW_CORPUS_SUBDIR,
    resolve_selected_source_records_for_local_data,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_models import (
    LocalizedSliceSummary,
    PortableSliceRequiredFile,
    localized_audio_root,
    localized_selected_source_records_path,
    localized_slice_summary_path,
    portable_required_files_path,
)
from scripts.sir_convert_a_lot.devops.task121_qwen_portable_slice_planning import (
    load_portable_selected_source_records,
)


def stage_required_files_for_portable_slice(
    *,
    slice_root: Path,
    data_root: Path,
    cache_dir: Path | None = None,
) -> list[Path]:
    """Stage the exact Hub files required by one portable slice into local raw storage."""
    stage_started_at = time.perf_counter()
    required_files_payload = json.loads(
        portable_required_files_path(slice_root).read_text(encoding="utf-8")
    )
    if not isinstance(required_files_payload, list):
        raise ValueError("Portable slice required-files payload must be a list.")
    _emit_progress(
        "[task121] staging required archives "
        f"count={len(required_files_payload)} slice_root={slice_root.as_posix()}"
    )
    staged_paths: list[Path] = []
    for file_index, payload in enumerate(required_files_payload, start=1):
        required_file = _required_file_from_payload(payload)
        file_started_at = time.perf_counter()
        _emit_progress(
            "[task121] staging archive start "
            f"index={file_index}/{len(required_files_payload)} "
            f"filename={required_file.filename}"
        )
        cached_path = Path(
            hf_hub_download(
                repo_id=required_file.repo_id,
                repo_type=required_file.repo_type,
                filename=required_file.filename,
                revision=required_file.revision,
                cache_dir=None if cache_dir is None else cache_dir.as_posix(),
            )
        )
        target_path = data_root / RAW_CORPUS_SUBDIR / required_file.local_relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_preexisted = target_path.exists()
        shutil.copy2(cached_path, target_path)
        staged_paths.append(target_path)
        _emit_progress(
            "[task121] staging archive done "
            f"index={file_index}/{len(required_files_payload)} "
            f"filename={required_file.filename} "
            f"target={target_path.as_posix()} "
            f"target_preexisted={str(target_preexisted).lower()} "
            f"elapsed_seconds={time.perf_counter() - file_started_at:.2f}"
        )
    _emit_progress(
        "[task121] staging required archives done "
        f"count={len(staged_paths)} elapsed_seconds={time.perf_counter() - stage_started_at:.2f}"
    )
    return staged_paths


def localize_portable_slice(
    *,
    slice_root: Path,
    data_root: Path,
) -> LocalizedSliceSummary:
    """Materialize one portable slice into plain local files plus a localized manifest."""
    localize_started_at = time.perf_counter()
    portable_source_records = load_portable_selected_source_records(slice_root)
    _emit_progress(
        "[task121] localize slice start "
        f"slice_root={slice_root.as_posix()} row_count={len(portable_source_records)}"
    )
    resolved_source_records = resolve_selected_source_records_for_local_data(
        data_root=data_root,
        source_records=portable_source_records,
    )
    localized_root = localized_audio_root(slice_root)
    localized_source_records = _localize_source_records(
        resolved_source_records,
        localized_root=localized_root,
    )
    write_jsonl(
        localized_selected_source_records_path(slice_root),
        [source_record_to_payload(source_record) for source_record in localized_source_records],
    )
    summary = LocalizedSliceSummary(
        slice_root=slice_root.as_posix(),
        localized_row_count=len(localized_source_records),
        localized_audio_file_count=len(
            {
                row.source_audio_locator.path
                for row in localized_source_records
                if row.source_audio_locator is not None
            }
        ),
        localized_manifest_path=localized_selected_source_records_path(slice_root).as_posix(),
        localized_audio_root=localized_root.as_posix(),
    )
    write_json(localized_slice_summary_path(slice_root), summary)
    _emit_progress(
        "[task121] localize slice done "
        f"row_count={summary.localized_row_count} "
        f"localized_audio_file_count={summary.localized_audio_file_count} "
        f"elapsed_seconds={time.perf_counter() - localize_started_at:.2f}"
    )
    return summary


def _emit_progress(message: str) -> None:
    """Print one operator-facing progress line for notebook-backed runs."""
    print(message, flush=True)


def _localize_source_records(
    source_records: list[SourceRecord],
    *,
    localized_root: Path,
) -> list[SourceRecord]:
    """Extract archive-backed source rows into deterministic plain local files."""
    localized_root.mkdir(parents=True, exist_ok=True)
    localized_source_records: list[SourceRecord] = []
    records_by_archive_path: dict[Path, list[SourceRecord]] = {}
    for source_record in source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None:
            raise ValueError("Resolved portable source records must include source_audio_locator.")
        if source_audio_locator.archive_member is not None:
            records_by_archive_path.setdefault(source_audio_locator.path, []).append(source_record)

    localized_paths_by_key: dict[tuple[Path, str], Path] = {}
    for archive_path in sorted(records_by_archive_path):
        records_for_archive = records_by_archive_path[archive_path]
        required_members = {
            source_record.source_audio_locator.archive_member
            for source_record in records_for_archive
            if source_record.source_audio_locator is not None
            and source_record.source_audio_locator.archive_member is not None
        }
        archive_started_at = time.perf_counter()
        _emit_progress(
            "[task121] localize archive start "
            f"archive_path={archive_path.as_posix()} "
            f"required_member_count={len(required_members)}"
        )
        extracted_member_count = 0
        reused_member_count = 0
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                member_name = member.name.strip()
                if member_name not in required_members:
                    continue
                target_path = localized_root / member_name
                target_path.parent.mkdir(parents=True, exist_ok=True)
                if not target_path.exists():
                    extracted_file = archive.extractfile(member)
                    if extracted_file is None:
                        raise FileNotFoundError(
                            "Could not extract archive member "
                            f"`{member_name}` from `{archive_path}`."
                        )
                    _write_extracted_file(target_path, extracted_file)
                    extracted_member_count += 1
                else:
                    reused_member_count += 1
                localized_paths_by_key[(archive_path, member_name)] = target_path
                if extracted_member_count + reused_member_count >= len(required_members):
                    break
        _emit_progress(
            "[task121] localize archive done "
            f"archive_path={archive_path.as_posix()} "
            f"extracted_file_count={extracted_member_count} "
            f"reused_file_count={reused_member_count} "
            f"elapsed_seconds={time.perf_counter() - archive_started_at:.2f}"
        )

    for source_record in source_records:
        source_audio_locator = source_record.source_audio_locator
        if source_audio_locator is None:
            raise ValueError("Resolved portable source records must include source_audio_locator.")
        if source_audio_locator.archive_member is None:
            localized_source_records.append(source_record)
            continue
        localized_path = localized_paths_by_key.get(
            (source_audio_locator.path, source_audio_locator.archive_member)
        )
        if localized_path is None:
            raise FileNotFoundError(
                "Localized portable slice is missing extracted file for "
                f"{source_audio_locator.path.as_posix()}::{source_audio_locator.archive_member}"
            )
        localized_source_records.append(
            replace(source_record, source_audio_locator=AudioLocator(path=localized_path))
        )
    return localized_source_records


def _write_extracted_file(target_path: Path, extracted_file: IO[bytes]) -> None:
    """Persist one extracted tar member to a deterministic target path."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("wb") as handle:
        shutil.copyfileobj(extracted_file, handle)


def _required_file_from_payload(payload: object) -> PortableSliceRequiredFile:
    """Parse one required-file payload from JSON."""
    if not isinstance(payload, dict):
        raise ValueError("Portable slice required-file payload must be a mapping.")
    repo_id = payload.get("repo_id")
    repo_type = payload.get("repo_type")
    filename = payload.get("filename")
    local_relative_path = payload.get("local_relative_path")
    revision = payload.get("revision")
    if not isinstance(repo_id, str):
        raise ValueError("Portable slice required-file payload is missing `repo_id`.")
    if not isinstance(repo_type, str):
        raise ValueError("Portable slice required-file payload is missing `repo_type`.")
    if not isinstance(filename, str):
        raise ValueError("Portable slice required-file payload is missing `filename`.")
    if not isinstance(local_relative_path, str):
        raise ValueError("Portable slice required-file payload is missing `local_relative_path`.")
    if revision is not None and not isinstance(revision, str):
        raise ValueError("Portable slice required-file `revision` must be a string or null.")
    return PortableSliceRequiredFile(
        repo_id=repo_id,
        repo_type=repo_type,
        filename=filename,
        local_relative_path=local_relative_path,
        revision=revision,
    )
