"""DigiExam `.dxe` validation corpus manifests.

Purpose:
    Build metadata-only manifests for local raw DigiExam `.dxe` validation
    corpora without exposing prompt text, user metadata, or embedded asset
    payloads.

Relationships:
    - Consumes `domain.digiexam_dxe_parser` as the canonical `.dxe` parser.
    - Produces safe corpus evidence for EPIC-10 parser and IR regression gates.
    - Keeps raw teacher exports outside tracked fixtures unless a later task
      derives a sanitized minimal fixture.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from scripts.sir_convert_a_lot.domain.digiexam_contracts import DigiExamParseResult
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser

DIGIEXAM_DXE_CORPUS_MANIFEST_SCHEMA_VERSION = "digiexam_dxe_validation_corpus_manifest_v1"
DEFAULT_DIGIEXAM_DXE_CORPUS_ID = "onedrive-2026-05-12-dxe-validation"
LOCAL_RAW_ONLY_POLICY = "local_raw_only"


@dataclass(frozen=True)
class DigiExamDxeCorpusCount:
    """One deterministic count entry in a metadata-only corpus manifest."""

    key: str
    count: int

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable count metadata."""

        return {"key": self.key, "count": self.count}


@dataclass(frozen=True)
class DigiExamDxeCorpusEntry:
    """Metadata-only parse summary for one raw local `.dxe` file."""

    filename: str
    source_sha256: str
    byte_size: int
    parse_status: str
    renderer_ready: bool
    item_count: int
    item_type_counts: tuple[DigiExamDxeCorpusCount, ...]
    warning_code_counts: tuple[DigiExamDxeCorpusCount, ...]
    embedded_asset_count: int
    embedded_asset_sha256: tuple[str, ...]
    answer_key_provenance_counts: tuple[DigiExamDxeCorpusCount, ...]

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable metadata without raw exam content."""

        return {
            "filename": self.filename,
            "source_sha256": self.source_sha256,
            "byte_size": self.byte_size,
            "parse_status": self.parse_status,
            "renderer_ready": self.renderer_ready,
            "item_count": self.item_count,
            "item_type_counts": _counts_payload(self.item_type_counts),
            "warning_code_counts": _counts_payload(self.warning_code_counts),
            "embedded_asset_count": self.embedded_asset_count,
            "embedded_asset_sha256": list(self.embedded_asset_sha256),
            "answer_key_provenance_counts": _counts_payload(self.answer_key_provenance_counts),
        }


@dataclass(frozen=True)
class DigiExamDxeCorpusSummary:
    """Aggregate metadata-only summary for a local `.dxe` corpus."""

    file_count: int
    item_count: int
    parse_status_counts: tuple[DigiExamDxeCorpusCount, ...]
    item_type_counts: tuple[DigiExamDxeCorpusCount, ...]
    warning_code_counts: tuple[DigiExamDxeCorpusCount, ...]
    embedded_asset_count: int
    answer_key_provenance_counts: tuple[DigiExamDxeCorpusCount, ...]

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable aggregate metadata."""

        return {
            "file_count": self.file_count,
            "item_count": self.item_count,
            "parse_status_counts": _counts_payload(self.parse_status_counts),
            "item_type_counts": _counts_payload(self.item_type_counts),
            "warning_code_counts": _counts_payload(self.warning_code_counts),
            "embedded_asset_count": self.embedded_asset_count,
            "answer_key_provenance_counts": _counts_payload(self.answer_key_provenance_counts),
        }


@dataclass(frozen=True)
class DigiExamDxeCorpusManifest:
    """Metadata-only corpus manifest safe to commit."""

    schema_version: str
    corpus_id: str
    source_root_hint: str
    raw_source_policy: str
    entries: tuple[DigiExamDxeCorpusEntry, ...]
    summary: DigiExamDxeCorpusSummary

    def to_payload(self) -> dict[str, object]:
        """Return JSON-serializable corpus metadata."""

        return {
            "schema_version": self.schema_version,
            "corpus_id": self.corpus_id,
            "source_root_hint": self.source_root_hint,
            "raw_source_policy": self.raw_source_policy,
            "entries": [entry.to_payload() for entry in self.entries],
            "summary": self.summary.to_payload(),
        }


def build_digiexam_dxe_corpus_manifest(
    corpus_root: Path,
    *,
    corpus_id: str = DEFAULT_DIGIEXAM_DXE_CORPUS_ID,
    source_root_hint: str | None = None,
) -> DigiExamDxeCorpusManifest:
    """Parse a local raw `.dxe` corpus and return safe metadata only."""

    if not corpus_root.is_dir():
        raise ValueError(f"DigiExam `.dxe` corpus root does not exist: {corpus_root}")

    files = tuple(sorted(corpus_root.glob("*.dxe")))
    if not files:
        raise ValueError(f"DigiExam `.dxe` corpus contains no `.dxe` files: {corpus_root}")

    parser = DigiExamDxeParser()
    entries = tuple(_build_entry(path, parser=parser) for path in files)
    return DigiExamDxeCorpusManifest(
        schema_version=DIGIEXAM_DXE_CORPUS_MANIFEST_SCHEMA_VERSION,
        corpus_id=corpus_id,
        source_root_hint=source_root_hint if source_root_hint is not None else corpus_root.name,
        raw_source_policy=LOCAL_RAW_ONLY_POLICY,
        entries=entries,
        summary=_build_summary(entries),
    )


def write_digiexam_dxe_corpus_manifest(
    manifest: DigiExamDxeCorpusManifest,
    output_path: Path,
) -> None:
    """Write a deterministic metadata-only manifest payload."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        manifest.to_payload(),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    output_path.write_text(f"{payload}\n", encoding="utf-8")


def _build_entry(
    path: Path,
    *,
    parser: DigiExamDxeParser,
) -> DigiExamDxeCorpusEntry:
    result = parser.parse_file(path)
    return DigiExamDxeCorpusEntry(
        filename=path.name,
        source_sha256=_source_sha256(path),
        byte_size=path.stat().st_size,
        parse_status=result.status.value,
        renderer_ready=result.renderer_ready,
        item_count=len(result.items),
        item_type_counts=_count_values(item.item_type.value for item in result.items),
        warning_code_counts=_count_values(warning.code.value for warning in result.warnings),
        embedded_asset_count=_embedded_asset_count(result),
        embedded_asset_sha256=_embedded_asset_hashes(result),
        answer_key_provenance_counts=_count_values(
            item.answer_key_provenance.value for item in result.items
        ),
    )


def _build_summary(
    entries: tuple[DigiExamDxeCorpusEntry, ...],
) -> DigiExamDxeCorpusSummary:
    return DigiExamDxeCorpusSummary(
        file_count=len(entries),
        item_count=sum(entry.item_count for entry in entries),
        parse_status_counts=_count_values(entry.parse_status for entry in entries),
        item_type_counts=_merge_counts(entry.item_type_counts for entry in entries),
        warning_code_counts=_merge_counts(entry.warning_code_counts for entry in entries),
        embedded_asset_count=sum(entry.embedded_asset_count for entry in entries),
        answer_key_provenance_counts=_merge_counts(
            entry.answer_key_provenance_counts for entry in entries
        ),
    )


def _source_sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _embedded_asset_count(result: DigiExamParseResult) -> int:
    return sum(len(item.embedded_assets) for item in result.items)


def _embedded_asset_hashes(result: DigiExamParseResult) -> tuple[str, ...]:
    hashes = (f"sha256:{asset.sha256}" for item in result.items for asset in item.embedded_assets)
    return tuple(sorted(hashes))


def _count_values(values: Iterable[str]) -> tuple[DigiExamDxeCorpusCount, ...]:
    counter = Counter(values)
    return tuple(
        DigiExamDxeCorpusCount(key=key, count=counter[key]) for key in sorted(counter.keys())
    )


def _merge_counts(
    count_groups: Iterable[tuple[DigiExamDxeCorpusCount, ...]],
) -> tuple[DigiExamDxeCorpusCount, ...]:
    counter: Counter[str] = Counter()
    for group in count_groups:
        for count in group:
            counter[count.key] += count.count
    return tuple(
        DigiExamDxeCorpusCount(key=key, count=counter[key]) for key in sorted(counter.keys())
    )


def _counts_payload(counts: tuple[DigiExamDxeCorpusCount, ...]) -> list[dict[str, object]]:
    return [count.to_payload() for count in counts]
