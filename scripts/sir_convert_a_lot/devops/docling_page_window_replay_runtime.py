"""Reusable runtime helpers for Docling page-window replay page-window replay diagnostics.

Purpose:
    Keep page-window planning, child-process timeout handling, OCR default
    resolution, and sanitized report writing separate from the CLI conversion
    child so the diagnostic command remains small and auditable.

Relationships:
    - Imported by `devops.docling_page_window_replay`.
    - Exercises canonical OCR language normalization from infrastructure.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from scripts.sir_convert_a_lot.domain.specs import (
    AccelerationPolicy,
    BackendStrategy,
    NormalizeMode,
    OcrMode,
    Priority,
    TableMode,
)
from scripts.sir_convert_a_lot.domain.specs_v2 import OcrEngineV2
from scripts.sir_convert_a_lot.infrastructure.ocr_language_mapping_v2 import (
    normalize_bcp47_language_tags,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/docling-page-window-replay")
MODULE_NAME = "scripts.sir_convert_a_lot.devops.docling_page_window_replay"
DEFAULT_INCIDENT_WINDOW = "13-16"
DEFAULT_ATTEMPT_TIMEOUT_SECONDS = 120.0
DEFAULT_TERMINATE_GRACE_SECONDS = 5.0
DEFAULT_TOTAL_TIMEOUT_SECONDS = 900.0
TAIL_CHARS = 6000


@dataclass(frozen=True)
class ReplayWindow:
    """One inclusive 1-based PDF page window to replay."""

    start_page: int
    end_page: int

    @property
    def label(self) -> str:
        """Return a stable filename-safe page-window label."""
        if self.start_page == self.end_page:
            return f"p{self.start_page:06d}"
        return f"p{self.start_page:06d}-{self.end_page:06d}"

    def to_payload(self) -> dict[str, int | str]:
        """Return sanitized JSON payload fields."""
        return {
            "label": self.label,
            "start_page": self.start_page,
            "end_page": self.end_page,
        }


@dataclass(frozen=True)
class ChildProcessOutcome:
    """Parent-observed subprocess result for one replay attempt."""

    elapsed_ms: int
    return_code: int | None
    timed_out: bool
    stdout_tail: str
    stderr_tail: str

    def to_payload(self) -> dict[str, int | bool | str | None]:
        """Return sanitized JSON payload fields."""
        return {
            "elapsed_ms": self.elapsed_ms,
            "return_code": self.return_code,
            "timed_out": self.timed_out,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }


@dataclass(frozen=True)
class RunSettings:
    """Typed parent-run settings parsed from CLI arguments."""

    source_pdf: Path
    output_root: Path
    windows: tuple[ReplayWindow, ...]
    attempt_timeout_seconds: float
    docling_document_timeout_seconds: int
    stack_dump_after_seconds: float
    terminate_grace_seconds: float
    max_total_seconds: float
    backend_strategy: BackendStrategy
    ocr_mode: OcrMode
    table_mode: TableMode
    normalize_mode: NormalizeMode
    acceleration_policy: AccelerationPolicy
    priority: Priority
    ocr_engine: OcrEngineV2 | None
    ocr_languages: tuple[str, ...]
    easyocr_model_storage_directory: str | None
    fail_on_timeout: bool
    formula_preset_only: str | None = None
    single_formula_items: bool = False


def parse_page_window(raw_value: str) -> ReplayWindow:
    """Parse `13` or `13-16` into a replay window."""
    value = raw_value.strip()
    if not value:
        raise ValueError("page window must not be empty")
    if "-" in value:
        start_raw, end_raw = value.split("-", maxsplit=1)
        start_page = int(start_raw)
        end_page = int(end_raw)
    else:
        start_page = int(value)
        end_page = start_page
    if start_page < 1 or end_page < start_page:
        raise ValueError(f"invalid page window: {raw_value}")
    return ReplayWindow(start_page=start_page, end_page=end_page)


def build_locator_windows(incident_window: ReplayWindow) -> tuple[ReplayWindow, ...]:
    """Return full, single-page, and adjacent-pair windows for localization."""
    windows: list[ReplayWindow] = [incident_window]
    for page_number in range(incident_window.start_page, incident_window.end_page + 1):
        windows.append(ReplayWindow(start_page=page_number, end_page=page_number))
    for page_number in range(incident_window.start_page, incident_window.end_page):
        windows.append(ReplayWindow(start_page=page_number, end_page=page_number + 1))
    seen: set[tuple[int, int]] = set()
    unique_windows: list[ReplayWindow] = []
    for window in windows:
        identity = (window.start_page, window.end_page)
        if identity not in seen:
            unique_windows.append(window)
            seen.add(identity)
    return tuple(unique_windows)


def run_child_process(
    command: Sequence[str],
    *,
    timeout_seconds: float,
    terminate_grace_seconds: float,
) -> ChildProcessOutcome:
    """Run a child command with terminate/kill cleanup when the budget expires."""
    started = time.monotonic()
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=terminate_grace_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    return ChildProcessOutcome(
        elapsed_ms=elapsed_ms,
        return_code=process.returncode,
        timed_out=timed_out,
        stdout_tail=tail_text(stdout, TAIL_CHARS),
        stderr_tail=tail_text(stderr, TAIL_CHARS),
    )


def tail_text(value: str, max_chars: int) -> str:
    """Return a bounded tail for logs and stack dumps."""
    if len(value) <= max_chars:
        return value
    return value[-max_chars:]


def read_text_tail(path: Path, max_chars: int) -> str:
    """Read a bounded text tail from a file when it exists."""
    if not path.exists():
        return ""
    return tail_text(path.read_text(encoding="utf-8", errors="replace"), max_chars)


def load_json_object(path: Path) -> dict[str, object]:
    """Load a JSON object or return an explanatory fallback."""
    if not path.exists():
        return {}
    loaded: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return {"diagnostic_error": "child_result_was_not_json_object"}
    return {str(key): value for key, value in loaded.items()}


def load_jsonl_objects(path: Path) -> list[dict[str, object]]:
    """Load bounded JSONL diagnostic objects from a replay sidecar."""
    if not path.exists():
        return []
    records: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            loaded: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            records.append({str(key): value for key, value in loaded.items()})
    return records[-48:]


def write_json(path: Path, payload: dict[str, object]) -> None:
    """Write deterministic UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def utc_run_id() -> str:
    """Return a stable timestamped run id."""
    return datetime.now(UTC).strftime("docling-page-window-replay-%Y%m%dT%H%M%SZ")


def build_child_command(
    *,
    settings: RunSettings,
    window: ReplayWindow,
    result_path: Path,
    stack_path: Path,
    formula_events_path: Path,
) -> list[str]:
    """Build the child-process command for one replay window."""
    command = [
        sys.executable,
        "-m",
        MODULE_NAME,
        "child",
        settings.source_pdf.as_posix(),
        "--start-page",
        str(window.start_page),
        "--end-page",
        str(window.end_page),
        "--output-json",
        result_path.as_posix(),
        "--stack-dump-path",
        stack_path.as_posix(),
        "--formula-diagnostics-jsonl",
        formula_events_path.as_posix(),
        "--stack-dump-after-seconds",
        str(settings.stack_dump_after_seconds),
        "--docling-document-timeout-seconds",
        str(settings.docling_document_timeout_seconds),
        "--backend-strategy",
        settings.backend_strategy.value,
        "--ocr-mode",
        settings.ocr_mode.value,
        "--table-mode",
        settings.table_mode.value,
        "--normalize",
        settings.normalize_mode.value,
        "--acceleration-policy",
        settings.acceleration_policy.value,
        "--priority",
        settings.priority.value,
    ]
    if settings.ocr_engine is not None:
        command.extend(["--ocr-engine", settings.ocr_engine.value])
    for language in settings.ocr_languages:
        command.extend(["--ocr-language", language])
    if settings.easyocr_model_storage_directory is not None:
        command.extend(
            [
                "--easyocr-model-storage-directory",
                settings.easyocr_model_storage_directory,
            ]
        )
    if settings.formula_preset_only is not None:
        command.extend(["--formula-preset-only", settings.formula_preset_only])
    if settings.single_formula_items:
        command.append("--single-formula-items")
    return command


def run_replay(settings: RunSettings) -> int:
    """Run the bounded parent replay and write JSON/Markdown evidence."""
    run_dir = settings.output_root / utc_run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    records: list[dict[str, object]] = []

    for window in settings.windows:
        elapsed_total = time.monotonic() - started
        if elapsed_total >= settings.max_total_seconds:
            records.append(
                {
                    **window.to_payload(),
                    "status": "skipped_total_budget_exhausted",
                    "elapsed_ms": 0,
                }
            )
            continue

        result_path = run_dir / f"{window.label}.child.json"
        stack_path = run_dir / f"{window.label}.stack.txt"
        formula_events_path = run_dir / f"{window.label}.formula.jsonl"
        command = build_child_command(
            settings=settings,
            window=window,
            result_path=result_path,
            stack_path=stack_path,
            formula_events_path=formula_events_path,
        )
        remaining_budget = max(1.0, settings.max_total_seconds - elapsed_total)
        attempt_budget = min(settings.attempt_timeout_seconds, remaining_budget)
        outcome = run_child_process(
            command,
            timeout_seconds=attempt_budget,
            terminate_grace_seconds=settings.terminate_grace_seconds,
        )
        child_payload = load_json_object(result_path)
        child_status_obj = child_payload.get("status")
        child_status = child_status_obj if isinstance(child_status_obj, str) else "missing"
        status = "timed_out" if outcome.timed_out else child_status
        records.append(
            {
                **window.to_payload(),
                "status": status,
                "attempt_timeout_seconds": attempt_budget,
                "docling_document_timeout_seconds": settings.docling_document_timeout_seconds,
                "stack_dump_after_seconds": settings.stack_dump_after_seconds,
                "child": outcome.to_payload(),
                "child_payload": child_payload,
                "formula_diagnostics_events": load_jsonl_objects(formula_events_path),
                "stack_dump_tail": read_text_tail(stack_path, TAIL_CHARS),
            }
        )

    report_payload: dict[str, object] = {
        "schema_version": "docling_page_window_replay_v1",
        "source_pdf": settings.source_pdf.as_posix(),
        "source_sha256": hashlib.sha256(settings.source_pdf.read_bytes()).hexdigest(),
        "settings": {
            "attempt_timeout_seconds": settings.attempt_timeout_seconds,
            "docling_document_timeout_seconds": settings.docling_document_timeout_seconds,
            "stack_dump_after_seconds": settings.stack_dump_after_seconds,
            "terminate_grace_seconds": settings.terminate_grace_seconds,
            "max_total_seconds": settings.max_total_seconds,
            "backend_strategy": settings.backend_strategy.value,
            "ocr_mode": settings.ocr_mode.value,
            "table_mode": settings.table_mode.value,
            "normalize": settings.normalize_mode.value,
            "acceleration_policy": settings.acceleration_policy.value,
            "ocr_engine": settings.ocr_engine.value if settings.ocr_engine is not None else None,
            "ocr_languages": list(settings.ocr_languages),
            "formula_preset_only": settings.formula_preset_only,
            "single_formula_items": settings.single_formula_items,
        },
        "records": records,
    }
    write_json(run_dir / "report.json", report_payload)
    write_markdown_report(path=run_dir / "report.md", payload=report_payload)
    print((run_dir / "report.json").as_posix())
    timed_out = [record for record in records if record.get("status") == "timed_out"]
    failed = [record for record in records if record.get("status") == "failed"]
    if settings.fail_on_timeout and timed_out:
        return 2
    return 1 if failed else 0


def write_markdown_report(*, path: Path, payload: dict[str, object]) -> None:
    """Write a compact human-readable replay report."""
    records_obj = payload.get("records")
    records = records_obj if isinstance(records_obj, list) else []
    lines = [
        "# Docling page-window replay page-window replay",
        "",
        f"- Source SHA256: `{payload.get('source_sha256')}`",
        f"- Source path: `{payload.get('source_pdf')}`",
        "",
        "| Window | Status | Elapsed ms | Return | Markdown chars | Formula ms "
        "| VLM items | Transformers | Tokens | Stack dump |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record_obj in records:
        if not isinstance(record_obj, dict):
            continue
        child_obj = record_obj.get("child")
        child = child_obj if isinstance(child_obj, dict) else {}
        child_payload_obj = record_obj.get("child_payload")
        child_payload = child_payload_obj if isinstance(child_payload_obj, dict) else {}
        formula_obj = child_payload.get("docling_formula_diagnostics")
        formula = formula_obj if isinstance(formula_obj, dict) else {}
        events_obj = record_obj.get("formula_diagnostics_events")
        events = events_obj if isinstance(events_obj, list) else []
        transformer_count = formula.get("transformers_call_count", "")
        token_total = formula.get("transformers_generated_token_total", "")
        started_count = formula_started_event_count(events)
        if transformer_count == "" and started_count > 0:
            transformer_count = f"started:{started_count}"
        if token_total == "":
            token_total = formula_started_max_new_tokens(events)
        stack_tail = record_obj.get("stack_dump_tail")
        has_stack = "yes" if isinstance(stack_tail, str) and stack_tail.strip() else "no"
        lines.append(
            "| "
            + str(record_obj.get("label"))
            + " | "
            + str(record_obj.get("status"))
            + " | "
            + str(child.get("elapsed_ms", record_obj.get("elapsed_ms", "")))
            + " | "
            + str(child.get("return_code", ""))
            + " | "
            + str(child_payload.get("markdown_char_count", ""))
            + " | "
            + str(formula.get("formula_vlm_total_ms", ""))
            + " | "
            + str(formula.get("formula_vlm_item_count", ""))
            + " | "
            + str(transformer_count)
            + " | "
            + str(token_total)
            + " | "
            + has_stack
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def formula_started_event_count(events: list[object]) -> int:
    """Count sidecar events proving Transformers generation was entered."""
    return sum(
        1
        for event_obj in events
        if isinstance(event_obj, dict)
        and event_obj.get("event") == "transformers_predict_batch_started"
    )


def formula_started_max_new_tokens(events: list[object]) -> int | str:
    """Return max sidecar token budget for started Transformers calls."""
    values: list[int] = []
    for event_obj in events:
        if not isinstance(event_obj, dict):
            continue
        if event_obj.get("event") != "transformers_predict_batch_started":
            continue
        value = event_obj.get("max_new_tokens_max")
        if isinstance(value, int) and not isinstance(value, bool):
            values.append(max(0, value))
    return max(values) if values else ""


def resolve_ocr_engine(raw_value: str) -> OcrEngineV2:
    """Resolve `auto` through service-default environment semantics."""
    if raw_value == OcrEngineV2.AUTO.value:
        raw_value = os.environ.get(
            "SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_ENGINE",
            OcrEngineV2.EASYOCR.value,
        )
    return OcrEngineV2(raw_value)


def resolve_ocr_languages(raw_values: Sequence[str]) -> tuple[str, ...]:
    """Resolve CLI or environment OCR languages using the canonical normalizer."""
    values = list(raw_values)
    if not values:
        env_value = os.environ.get("SIR_CONVERT_A_LOT_DEFAULT_PDF_OCR_LANGUAGES", "sv,en")
        values = [part.strip() for part in env_value.split(",") if part.strip()]
    return normalize_bcp47_language_tags(values)
