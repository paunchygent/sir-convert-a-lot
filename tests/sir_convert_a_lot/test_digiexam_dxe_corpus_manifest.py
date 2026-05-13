"""Tests for the Task 281 DigiExam `.dxe` validation corpus manifest.

Purpose:
    Prove that local raw DigiExam `.dxe` validation packages can be converted
    into metadata-only parser regression evidence without committing exam
    prompt text, user metadata, or embedded asset payloads.

Relationships:
    - Exercises `domain.digiexam_dxe_corpus_manifest` as the Task 281 corpus
      manifest boundary.
    - Keeps raw OneDrive `.dxe` exports local while preserving parser/IR
      regression counts for EPIC-10.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.sir_convert_a_lot.domain.digiexam_dxe_corpus_manifest import (
    DEFAULT_DIGIEXAM_DXE_CORPUS_ID,
    DIGIEXAM_DXE_CORPUS_MANIFEST_SCHEMA_VERSION,
    LOCAL_RAW_ONLY_POLICY,
    build_digiexam_dxe_corpus_manifest,
)

_CORPUS_ROOT = Path("inputs/examples/digiexam-evidence/OneDrive_1_5-12-2026")
_SOURCE_ROOT_HINT = "inputs/examples/digiexam-evidence/OneDrive_1_5-12-2026"
_MANIFEST = Path(
    "inputs/examples/digiexam-evidence/digiexam-dxe-validation-corpus-2026-05-12.manifest.json"
)
_FORBIDDEN_MARKERS = (
    "bodyHTML",
    "prompt_html",
    "prompt_lines",
    "content_base64",
    "alternatives",
    "options",
    "organization",
    "encryption",
    "user",
)
_ENTRY_KEYS = {
    "filename",
    "source_sha256",
    "byte_size",
    "parse_status",
    "renderer_ready",
    "item_count",
    "item_type_counts",
    "warning_code_counts",
    "embedded_asset_count",
    "embedded_asset_sha256",
    "answer_key_provenance_counts",
}


def _load_manifest_payload() -> dict[str, object]:
    payload = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _objects(value: object) -> list[dict[str, object]]:
    assert isinstance(value, list)
    result: list[dict[str, object]] = []
    for item in value:
        result.append(_object(item))
    return result


def _count_map(value: object) -> dict[str, int]:
    result: dict[str, int] = {}
    for count in _objects(value):
        key = count.get("key")
        amount = count.get("count")
        assert isinstance(key, str)
        assert isinstance(amount, int)
        result[key] = amount
    return result


def test_committed_digiexam_dxe_corpus_manifest_records_task281_baseline() -> None:
    payload = _load_manifest_payload()
    summary = _object(payload["summary"])
    entries = _objects(payload["entries"])

    assert payload["schema_version"] == DIGIEXAM_DXE_CORPUS_MANIFEST_SCHEMA_VERSION
    assert payload["corpus_id"] == DEFAULT_DIGIEXAM_DXE_CORPUS_ID
    assert payload["source_root_hint"] == _SOURCE_ROOT_HINT
    assert payload["raw_source_policy"] == LOCAL_RAW_ONLY_POLICY
    assert len(entries) == 23
    assert summary["file_count"] == 23
    assert summary["item_count"] == 317
    assert summary["embedded_asset_count"] == 8
    assert _count_map(summary["parse_status_counts"]) == {"success": 23}
    assert _count_map(summary["item_type_counts"]) == {
        "gap_fill": 13,
        "multiple_response": 4,
        "open_ended": 273,
        "single_choice": 27,
    }
    assert _count_map(summary["warning_code_counts"]) == {"missing_answer_key_provenance": 44}
    assert _count_map(summary["answer_key_provenance_counts"]) == {
        "absent": 44,
        "not_applicable": 273,
    }
    assert all(set(entry.keys()) == _ENTRY_KEYS for entry in entries)


def test_committed_digiexam_dxe_corpus_manifest_is_metadata_only() -> None:
    manifest_text = _MANIFEST.read_text(encoding="utf-8")

    for marker in _FORBIDDEN_MARKERS:
        assert marker not in manifest_text
    assert Path.cwd().as_posix() not in manifest_text


def test_local_onedrive_dxe_corpus_matches_committed_metadata_manifest() -> None:
    if not _CORPUS_ROOT.exists():
        pytest.skip("local raw OneDrive `.dxe` validation corpus is not present")

    actual = build_digiexam_dxe_corpus_manifest(
        _CORPUS_ROOT,
        source_root_hint=_SOURCE_ROOT_HINT,
    ).to_payload()

    assert actual == _load_manifest_payload()
