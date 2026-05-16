"""DigiExam answer-key live-validation golden verification.

Purpose:
    Validate Task 309 expected-answer manifests against the versioned DigiExam
    DXE fixture corpus before any live provider output is scored.

Relationships:
    - Uses `digiexam_answer_key_live_validation_manifest` for eligible item
      binding, source hashes, fingerprints, and output-mode metadata.
    - Uses `digiexam_answer_key_payloads` to prove each teacher-verified
      answer payload is accepted by the same reviewed-overlay contract used by
      apply mode.
    - Feeds the Task 309 runner and later report evaluators without involving
      the model under validation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pydantic import JsonValue

from scripts.sir_convert_a_lot.domain.digiexam_answer_key_live_validation_manifest import (
    TASK309_CORPUS_ID,
    Task309AssetEvalPolicy,
    Task309LiveValidationFile,
    Task309LiveValidationItem,
    build_task309_live_validation_manifest,
)
from scripts.sir_convert_a_lot.domain.digiexam_answer_key_payloads import (
    validated_reviewed_answer_payload,
)
from scripts.sir_convert_a_lot.domain.digiexam_dxe_parser import DigiExamDxeParser
from scripts.sir_convert_a_lot.domain.digiexam_ir_contracts import (
    DigiExamIrItem,
    build_digiexam_intermediate_exam,
)

TASK309_EXPECTED_ANSWER_MANIFEST_SCHEMA_VERSION = (
    "digiexam_answer_key_live_validation_expected_answers_v1"
)
TASK309_TEACHER_VERIFIED_STATE = "teacher_verified"


@dataclass(frozen=True)
class Task309GoldenValidationIssue:
    """One deterministic expected-answer manifest validation issue."""

    code: str
    source_filename: str | None
    item_id: str | None
    detail: str


@dataclass(frozen=True)
class Task309GoldenValidationSummary:
    """Aggregate expected-answer manifest validation result."""

    entry_count: int
    eligible_item_count: int
    validated_item_count: int
    missing_item_count: int
    unknown_item_count: int
    duplicate_item_count: int
    adjudication_required_count: int
    issue_count: int
    valid: bool


@dataclass(frozen=True)
class Task309GoldenValidationReport:
    """Task 309 expected-answer validation report safe to retain."""

    schema_version: str
    corpus_id: str
    expected_answer_manifest_path: str
    source_root_hint: str
    source_manifest_sha256: str
    expected_answer_manifest_sha256: str
    summary: Task309GoldenValidationSummary
    issues: tuple[Task309GoldenValidationIssue, ...]

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON payload for the validation report."""

        return {
            "schema_version": self.schema_version,
            "corpus_id": self.corpus_id,
            "expected_answer_manifest_path": self.expected_answer_manifest_path,
            "source_root_hint": self.source_root_hint,
            "source_manifest_sha256": self.source_manifest_sha256,
            "expected_answer_manifest_sha256": self.expected_answer_manifest_sha256,
            "summary": asdict(self.summary),
            "issues": [asdict(issue) for issue in self.issues],
        }


def validate_task309_expected_answer_manifest(
    *,
    corpus_root: Path,
    expected_answer_manifest_path: Path,
) -> Task309GoldenValidationReport:
    """Validate the committed expected-answer manifest for one Task 309 corpus."""

    corpus_manifest = build_task309_live_validation_manifest(
        corpus_root,
        asset_eval_policy=Task309AssetEvalPolicy(allow_supported_embedded_assets=True),
    )
    eligible_items = _eligible_items(corpus_manifest.files)
    ir_items = _ir_items(corpus_root)
    payload = _load_object(expected_answer_manifest_path)
    entries = _entries(payload)
    issues: list[Task309GoldenValidationIssue] = []

    if payload.get("schema_version") != TASK309_EXPECTED_ANSWER_MANIFEST_SCHEMA_VERSION:
        issues.append(
            _issue(
                "unexpected_schema_version",
                None,
                None,
                f"Expected {TASK309_EXPECTED_ANSWER_MANIFEST_SCHEMA_VERSION}.",
            )
        )
    if payload.get("corpus_id") != TASK309_CORPUS_ID:
        issues.append(_issue("unexpected_corpus_id", None, None, f"Expected {TASK309_CORPUS_ID}."))

    seen_keys: set[tuple[str, str]] = set()
    unknown_keys: set[tuple[str, str]] = set()
    duplicate_count = 0
    validated_count = 0
    adjudication_required_count = 0

    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            issues.append(_issue("malformed_entry", None, None, f"Entry {index} is not an object."))
            continue
        entry = _entry(raw_entry, index=index, issues=issues)
        if entry is None:
            continue
        key = (entry.source_filename, entry.item_id)
        if key in seen_keys:
            duplicate_count += 1
            issues.append(
                _issue(
                    "duplicate_item",
                    entry.source_filename,
                    entry.item_id,
                    "Expected-answer manifest contains the same item more than once.",
                )
            )
            continue
        seen_keys.add(key)
        manifest_item = eligible_items.get(key)
        ir_item = ir_items.get(key)
        if manifest_item is None or ir_item is None:
            unknown_keys.add(key)
            issues.append(
                _issue(
                    "unknown_item",
                    entry.source_filename,
                    entry.item_id,
                    "Expected-answer entry does not match an eligible corpus item.",
                )
            )
            continue
        _validate_entry_binding(entry=entry, manifest_item=manifest_item, issues=issues)
        if entry.adjudication_required:
            adjudication_required_count += 1
            issues.append(
                _issue(
                    "adjudication_required",
                    entry.source_filename,
                    entry.item_id,
                    "Scored Task 309 items must be teacher verified before correctness scoring.",
                )
            )
        if entry.expected_answer_state != TASK309_TEACHER_VERIFIED_STATE:
            issues.append(
                _issue(
                    "expected_answer_not_teacher_verified",
                    entry.source_filename,
                    entry.item_id,
                    "Expected-answer state must be teacher_verified.",
                )
            )
        if entry.verification_state != TASK309_TEACHER_VERIFIED_STATE:
            issues.append(
                _issue(
                    "verification_not_teacher_verified",
                    entry.source_filename,
                    entry.item_id,
                    "Verification state must be teacher_verified.",
                )
            )
        if validated_reviewed_answer_payload(item=ir_item, payload=entry.expected_answer_payload):
            validated_count += 1
        else:
            issues.append(
                _issue(
                    "invalid_expected_answer_payload",
                    entry.source_filename,
                    entry.item_id,
                    "Expected-answer payload is not valid for the bound DigiExam IR item.",
                )
            )

    missing_keys = set(eligible_items) - seen_keys
    for source_filename, item_id in sorted(missing_keys):
        issues.append(
            _issue(
                "missing_item",
                source_filename,
                item_id,
                "Eligible corpus item is missing a teacher-verified expected answer.",
            )
        )
    _validate_summary(payload, entries=entries, issues=issues)

    issue_tuple = tuple(issues)
    summary = Task309GoldenValidationSummary(
        entry_count=len(entries),
        eligible_item_count=len(eligible_items),
        validated_item_count=validated_count,
        missing_item_count=len(missing_keys),
        unknown_item_count=len(unknown_keys),
        duplicate_item_count=duplicate_count,
        adjudication_required_count=adjudication_required_count,
        issue_count=len(issue_tuple),
        valid=len(issue_tuple) == 0,
    )
    return Task309GoldenValidationReport(
        schema_version="digiexam_answer_key_live_validation_expected_answer_validation_v1",
        corpus_id=TASK309_CORPUS_ID,
        expected_answer_manifest_path=expected_answer_manifest_path.as_posix(),
        source_root_hint=corpus_root.as_posix(),
        source_manifest_sha256=_sha256(corpus_root / "validation-corpus-manifest.json"),
        expected_answer_manifest_sha256=_sha256(expected_answer_manifest_path),
        summary=summary,
        issues=issue_tuple,
    )


@dataclass(frozen=True)
class _ExpectedAnswerEntry:
    source_filename: str
    source_sha256: str
    item_id: str
    sequence: int
    source_item_fingerprint: str
    item_type: str
    output_mode: str
    expected_answer_state: str
    verification_state: str
    adjudication_required: bool
    expected_answer_payload: dict[str, JsonValue]


def _eligible_items(
    files: tuple[Task309LiveValidationFile, ...],
) -> dict[tuple[str, str], Task309LiveValidationItem]:
    items: dict[tuple[str, str], Task309LiveValidationItem] = {}
    for file_entry in files:
        for item in file_entry.items:
            if item.eligible:
                items[(item.source_filename, item.item_id)] = item
    return items


def _ir_items(corpus_root: Path) -> dict[tuple[str, str], DigiExamIrItem]:
    parser = DigiExamDxeParser()
    items: dict[tuple[str, str], DigiExamIrItem] = {}
    for path in sorted(corpus_root.glob("*.dxe")):
        exam = build_digiexam_intermediate_exam(parser.parse_file(path))
        for item in exam.items:
            items[(path.name, item.item_id)] = item
    return items


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Task 309 expected-answer manifest must be an object: {path}")
    return {str(key): value for key, value in payload.items()}


def _entries(payload: dict[str, object]) -> list[object]:
    value = payload.get("entries")
    if not isinstance(value, list):
        return []
    return value


def _entry(
    raw_entry: dict[object, object],
    *,
    index: int,
    issues: list[Task309GoldenValidationIssue],
) -> _ExpectedAnswerEntry | None:
    source_filename = _required_str(raw_entry, "source_filename", index, issues)
    source_sha256 = _required_str(raw_entry, "source_sha256", index, issues)
    item_id = _required_str(raw_entry, "item_id", index, issues)
    sequence = _required_int(raw_entry, "sequence", index, issues)
    source_item_hash = _required_str(raw_entry, "source_item_fingerprint", index, issues)
    item_type = _required_str(raw_entry, "item_type", index, issues)
    output_mode = _required_str(raw_entry, "output_mode", index, issues)
    expected_answer_state = _required_str(raw_entry, "expected_answer_state", index, issues)
    verification_state = _required_str(raw_entry, "verification_state", index, issues)
    adjudication_required = _required_bool(raw_entry, "adjudication_required", index, issues)
    expected_answer_payload = _required_json_object(
        raw_entry, "expected_answer_payload", index, issues
    )
    if (
        source_filename is None
        or source_sha256 is None
        or item_id is None
        or sequence is None
        or source_item_hash is None
        or item_type is None
        or output_mode is None
        or expected_answer_state is None
        or verification_state is None
        or adjudication_required is None
        or expected_answer_payload is None
    ):
        return None
    return _ExpectedAnswerEntry(
        source_filename=source_filename,
        source_sha256=source_sha256,
        item_id=item_id,
        sequence=sequence,
        source_item_fingerprint=source_item_hash,
        item_type=item_type,
        output_mode=output_mode,
        expected_answer_state=expected_answer_state,
        verification_state=verification_state,
        adjudication_required=adjudication_required,
        expected_answer_payload=expected_answer_payload,
    )


def _validate_entry_binding(
    *,
    entry: _ExpectedAnswerEntry,
    manifest_item: Task309LiveValidationItem,
    issues: list[Task309GoldenValidationIssue],
) -> None:
    checks = (
        ("source_sha256_mismatch", entry.source_sha256, manifest_item.source_sha256),
        ("sequence_mismatch", str(entry.sequence), str(manifest_item.sequence)),
        (
            "source_item_fingerprint_mismatch",
            entry.source_item_fingerprint,
            manifest_item.source_item_fingerprint,
        ),
        ("item_type_mismatch", entry.item_type, manifest_item.item_type),
        ("output_mode_mismatch", entry.output_mode, manifest_item.output_mode),
    )
    for code, actual, expected in checks:
        if actual != expected:
            issues.append(
                _issue(
                    code,
                    entry.source_filename,
                    entry.item_id,
                    f"Expected {expected}, found {actual}.",
                )
            )


def _validate_summary(
    payload: dict[str, object],
    *,
    entries: list[object],
    issues: list[Task309GoldenValidationIssue],
) -> None:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        issues.append(_issue("missing_summary", None, None, "Manifest summary is missing."))
        return
    entry_count = summary.get("entry_count")
    if entry_count != len(entries):
        issues.append(
            _issue("summary_entry_count_mismatch", None, None, f"Expected {len(entries)}.")
        )


def _required_str(
    payload: dict[object, object],
    key: str,
    index: int,
    issues: list[Task309GoldenValidationIssue],
) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value
    issues.append(_issue("missing_string_field", None, None, f"Entry {index} missing `{key}`."))
    return None


def _required_int(
    payload: dict[object, object],
    key: str,
    index: int,
    issues: list[Task309GoldenValidationIssue],
) -> int | None:
    value = payload.get(key)
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    issues.append(_issue("missing_integer_field", None, None, f"Entry {index} missing `{key}`."))
    return None


def _required_bool(
    payload: dict[object, object],
    key: str,
    index: int,
    issues: list[Task309GoldenValidationIssue],
) -> bool | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    issues.append(_issue("missing_boolean_field", None, None, f"Entry {index} missing `{key}`."))
    return None


def _required_json_object(
    payload: dict[object, object],
    key: str,
    index: int,
    issues: list[Task309GoldenValidationIssue],
) -> dict[str, JsonValue] | None:
    value = payload.get(key)
    try:
        json_value = _json_value(value)
    except ValueError:
        issues.append(_issue("missing_json_object", None, None, f"Entry {index} missing `{key}`."))
        return None
    if isinstance(json_value, dict):
        return json_value
    issues.append(_issue("missing_json_object", None, None, f"Entry {index} missing `{key}`."))
    return None


def _json_value(value: object) -> JsonValue:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, list):
        return [_json_value(child) for child in value]
    if isinstance(value, dict):
        result: dict[str, JsonValue] = {}
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings.")
            result[key] = _json_value(child)
        return result
    raise ValueError(f"Unsupported JSON value: {type(value).__name__}")


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _issue(
    code: str,
    source_filename: str | None,
    item_id: str | None,
    detail: str,
) -> Task309GoldenValidationIssue:
    return Task309GoldenValidationIssue(
        code=code,
        source_filename=source_filename,
        item_id=item_id,
        detail=detail,
    )
