"""Run formula candidate evaluation formula/OCR candidate adapters.

Purpose:
    Compare the current Granite/Docling output, source-layer extraction, and
    configured specialist model commands on the same incident inputs.

Relationships:
    - Consumes source inputs from `formula_candidate_eval_inputs`.
    - Feeds candidate summaries to formula candidate evaluation report writers.
    - Does not provide production conversion routing.
"""

from __future__ import annotations

import json
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from scripts.sir_convert_a_lot.devops.formula_candidate_eval_inputs import (
    SourceInput,
    object_mapping,
    source_text_for_input,
)

BAD_MARKERS = ("</formula", "\\mathbmath", "\\mathbf", "l o o l y")
TAIL_CHARS = 6000


@dataclass(frozen=True)
class CandidateSpec:
    """One formula/OCR candidate adapter declaration."""

    candidate_id: str
    label: str
    kind: str
    model_name: str | None
    input_kind: str


def run_granite_baseline(
    *,
    baseline_markdown: Path,
    incident_report: Mapping[str, object],
    output_root: Path,
) -> dict[str, object]:
    """Record current Granite/Docling incident output as the regression baseline."""
    output_root.mkdir(parents=True, exist_ok=True)
    output_path = output_root / "baseline.md"
    text = baseline_markdown.read_text(encoding="utf-8", errors="replace")
    output_path.write_text(text, encoding="utf-8")
    return {
        "candidate_id": "granite_docling_baseline",
        "label": "Current Docling page-window replay Granite/Docling baseline",
        "status": "succeeded",
        "elapsed_ms": baseline_elapsed_ms(incident_report),
        "input_count": 1,
        "output_text_path": output_path.as_posix(),
        "marker_counts": collect_marker_counts(text),
        "output_char_count": len(text),
        "notes": "Persisted Docling page-window replay affected-window Markdown, not rerun.",
    }


def run_source_layer_baseline(
    *,
    source_pdf: Path,
    source_inputs: Sequence[SourceInput],
    output_root: Path,
) -> dict[str, object]:
    """Extract PyMuPDF page/crop text as a non-generative source baseline."""
    started = time.monotonic()
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []
    import pymupdf

    with pymupdf.open(source_pdf.as_posix()) as document:
        for source_input in source_inputs:
            text = source_text_for_input(document=document, source_input=source_input)
            output_path = output_root / f"{source_input.input_id}.txt"
            output_path.write_text(text, encoding="utf-8")
            results.append(
                {
                    "input_id": source_input.input_id,
                    "status": "succeeded",
                    "output_text_path": output_path.as_posix(),
                    "elapsed_ms": 0,
                    "marker_counts": collect_marker_counts(text),
                    "output_char_count": len(text),
                }
            )
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    return {
        "candidate_id": "source_layer_pymupdf",
        "label": "PyMuPDF source-layer baseline",
        "status": "succeeded",
        "elapsed_ms": elapsed_ms,
        "input_count": len(source_inputs),
        "marker_counts": sum_marker_counts(results),
        "input_results": results,
    }


def run_external_candidate(
    *,
    candidate: CandidateSpec,
    source_inputs: Sequence[SourceInput],
    output_root: Path,
    executable: str,
    device: str,
    paddle_template: str | None,
    timeout_seconds: float,
    deepseek_template: str | None,
    deepseek_batch_template: str | None,
) -> dict[str, object]:
    """Run or block one external candidate using configured command surfaces."""
    output_root.mkdir(parents=True, exist_ok=True)
    if candidate.kind == "deepseek_batch_template":
        return run_batch_candidate(
            candidate=candidate,
            source_inputs=source_inputs,
            output_root=output_root,
            timeout_seconds=timeout_seconds,
            deepseek_batch_template=deepseek_batch_template,
        )
    command_error = command_blocker(
        candidate=candidate,
        executable=executable,
        paddle_template=paddle_template,
        deepseek_template=deepseek_template,
        deepseek_batch_template=deepseek_batch_template,
    )
    if command_error is not None:
        return blocked_candidate(candidate, source_inputs, command_error)
    started = time.monotonic()
    input_results = [
        run_candidate_input(
            candidate=candidate,
            source_input=source_input,
            output_root=output_root,
            executable=executable,
            device=device,
            paddle_template=paddle_template,
            timeout_seconds=timeout_seconds,
            deepseek_template=deepseek_template,
        )
        for source_input in source_inputs
    ]
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    succeeded = all(result.get("status") == "succeeded" for result in input_results)
    return {
        "candidate_id": candidate.candidate_id,
        "label": candidate.label,
        "status": "succeeded" if succeeded else "failed",
        "elapsed_ms": elapsed_ms,
        "input_count": len(source_inputs),
        "marker_counts": sum_marker_counts(input_results),
        "input_results": input_results,
    }


def run_candidate_input(
    *,
    candidate: CandidateSpec,
    source_input: SourceInput,
    output_root: Path,
    executable: str,
    device: str,
    paddle_template: str | None,
    timeout_seconds: float,
    deepseek_template: str | None,
) -> dict[str, object]:
    """Run one candidate for one source image."""
    input_dir = output_root / source_input.input_id
    input_dir.mkdir(parents=True, exist_ok=True)
    command = build_candidate_command(
        candidate=candidate,
        source_input=source_input,
        input_dir=input_dir,
        executable=executable,
        device=device,
        paddle_template=paddle_template,
        deepseek_template=deepseek_template,
    )
    return run_one_external_input(
        command=command,
        input_dir=input_dir,
        source_input=source_input,
        timeout_seconds=timeout_seconds,
    )


def run_batch_candidate(
    *,
    candidate: CandidateSpec,
    source_inputs: Sequence[SourceInput],
    output_root: Path,
    timeout_seconds: float,
    deepseek_batch_template: str | None,
) -> dict[str, object]:
    """Run a batch-oriented external candidate once and map outputs per input."""
    command_error = command_blocker(
        candidate=candidate,
        executable="",
        paddle_template=None,
        deepseek_template=None,
        deepseek_batch_template=deepseek_batch_template,
    )
    if command_error is not None:
        return blocked_candidate(candidate, source_inputs, command_error)
    batch_input_dir = output_root / "batch-inputs"
    batch_output_dir = output_root / "batch-output"
    batch_input_dir.mkdir(parents=True, exist_ok=True)
    batch_output_dir.mkdir(parents=True, exist_ok=True)
    for source_input in source_inputs:
        shutil.copyfile(source_input.image_path, batch_input_dir / f"{source_input.input_id}.png")
    command = deepseek_batch_command(
        template=deepseek_batch_template or "",
        input_dir=batch_input_dir,
        output_dir=batch_output_dir,
        model_name=candidate.model_name or "deepseek-ai/DeepSeek-OCR-2",
    )
    started = time.monotonic()
    run_result = run_batch_external_command(
        command=command,
        output_root=output_root,
        timeout_seconds=timeout_seconds,
    )
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    input_results = [
        batch_input_result(
            source_input=source_input,
            output_dir=batch_output_dir,
            status=str(run_result["status"]),
            elapsed_ms=elapsed_ms,
            return_code=run_result["return_code"],
            command=command,
        )
        for source_input in source_inputs
    ]
    succeeded = all(result.get("status") == "succeeded" for result in input_results)
    return {
        "candidate_id": candidate.candidate_id,
        "label": candidate.label,
        "status": "succeeded" if succeeded else "failed",
        "elapsed_ms": elapsed_ms,
        "input_count": len(source_inputs),
        "marker_counts": sum_marker_counts(input_results),
        "input_results": input_results,
        "batch_stdout_path": str(run_result["stdout_path"]),
        "batch_stderr_path": str(run_result["stderr_path"]),
    }


def run_batch_external_command(
    *,
    command: Sequence[str],
    output_root: Path,
    timeout_seconds: float,
) -> dict[str, object]:
    """Run one batch external command and persist bounded stdout/stderr."""
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        return_code: int | None = completed.returncode
        status = "succeeded" if completed.returncode == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        stdout = timeout_text(exc.stdout)
        stderr = timeout_text(exc.stderr)
        return_code = None
        status = "timed_out"
    stdout_path = output_root / "batch-stdout.txt"
    stderr_path = output_root / "batch-stderr.txt"
    stdout_path.write_text(tail_text(stdout), encoding="utf-8")
    stderr_path.write_text(tail_text(stderr), encoding="utf-8")
    return {
        "status": status,
        "return_code": return_code,
        "stdout_path": stdout_path.as_posix(),
        "stderr_path": stderr_path.as_posix(),
    }


def batch_input_result(
    *,
    source_input: SourceInput,
    output_dir: Path,
    status: str,
    elapsed_ms: int,
    return_code: object,
    command: Sequence[str],
) -> dict[str, object]:
    """Return one mapped batch result for a source input."""
    output_path = first_existing_output(output_dir=output_dir, input_id=source_input.input_id)
    text = output_path.read_text(encoding="utf-8", errors="replace") if output_path else ""
    mapped_status = "succeeded" if status == "succeeded" and output_path is not None else status
    if status == "succeeded" and output_path is None:
        mapped_status = "failed"
    output_text_path = (
        output_path if output_path else output_dir / f"{source_input.input_id}.missing"
    )
    if output_path is None:
        output_text_path.write_text("", encoding="utf-8")
    return {
        "input_id": source_input.input_id,
        "status": mapped_status,
        "elapsed_ms": elapsed_ms,
        "return_code": return_code,
        "command": list(command),
        "output_text_path": output_text_path.as_posix(),
        "marker_counts": collect_marker_counts(text),
        "output_char_count": len(text),
    }


def first_existing_output(*, output_dir: Path, input_id: str) -> Path | None:
    """Return the first recognized batch output path for one input id."""
    for suffix in (".md", ".mmd", ".txt", ".tex"):
        candidate_path = output_dir / f"{input_id}{suffix}"
        if candidate_path.exists():
            return candidate_path
    return None


def run_one_external_input(
    *,
    command: Sequence[str],
    input_dir: Path,
    source_input: SourceInput,
    timeout_seconds: float,
) -> dict[str, object]:
    """Run one external candidate command for one source image."""
    started = time.monotonic()
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        return_code: int | None = completed.returncode
        status = "succeeded" if completed.returncode == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        stdout = timeout_text(exc.stdout)
        stderr = timeout_text(exc.stderr)
        return_code = None
        status = "timed_out"
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    (input_dir / "stdout.txt").write_text(tail_text(stdout), encoding="utf-8")
    (input_dir / "stderr.txt").write_text(tail_text(stderr), encoding="utf-8")
    text = candidate_output_text(output_root=input_dir, stdout=stdout)
    output_text_path = input_dir / "candidate-output.txt"
    output_text_path.write_text(text, encoding="utf-8")
    return {
        "input_id": source_input.input_id,
        "status": status,
        "elapsed_ms": elapsed_ms,
        "return_code": return_code,
        "command": list(command),
        "output_text_path": output_text_path.as_posix(),
        "marker_counts": collect_marker_counts(text),
        "output_char_count": len(text),
    }


def build_candidate_command(
    *,
    candidate: CandidateSpec,
    source_input: SourceInput,
    input_dir: Path,
    executable: str,
    device: str,
    paddle_template: str | None,
    deepseek_template: str | None,
) -> list[str]:
    """Build the argv command for one candidate input."""
    if candidate.kind == "paddle_pipeline":
        model_name = candidate.model_name or "PP-FormulaNet_plus-S"
        if paddle_template:
            return paddle_command(
                template=paddle_template,
                source_input=source_input,
                input_dir=input_dir,
                model_name=model_name,
                device=device,
            )
        return [
            executable,
            "formula_recognition_pipeline",
            "-i",
            source_input.image_path.as_posix(),
            "--formula_recognition_model_name",
            model_name,
            "--save_path",
            input_dir.as_posix(),
            "--device",
            device,
        ]
    if candidate.kind == "deepseek_template":
        return deepseek_command(
            template=deepseek_template or "",
            source_input=source_input,
            input_dir=input_dir,
            model_name=candidate.model_name or "deepseek-ai/DeepSeek-OCR-2",
        )
    return []


def paddle_command(
    *,
    template: str,
    source_input: SourceInput,
    input_dir: Path,
    model_name: str,
    device: str,
) -> list[str]:
    """Expand a PaddleOCR formula command template."""
    return [
        part.format(
            input=source_input.image_path.as_posix(),
            output_dir=input_dir.as_posix(),
            model=model_name,
            device=device,
        )
        for part in shlex.split(template)
    ]


def deepseek_command(
    *,
    template: str,
    source_input: SourceInput,
    input_dir: Path,
    model_name: str,
) -> list[str]:
    """Expand the DeepSeek-OCR-2 command template."""
    output_path = input_dir / "deepseek-output.txt"
    return [
        part.format(
            input=source_input.image_path.as_posix(),
            output=output_path.as_posix(),
            output_dir=input_dir.as_posix(),
            model=model_name,
        )
        for part in shlex.split(template)
    ]


def deepseek_batch_command(
    *,
    template: str,
    input_dir: Path,
    output_dir: Path,
    model_name: str,
) -> list[str]:
    """Expand the DeepSeek-OCR-2 batch command template."""
    return [
        part.format(
            input_dir=input_dir.as_posix(),
            output_dir=output_dir.as_posix(),
            model=model_name,
        )
        for part in shlex.split(template)
    ]


def command_blocker(
    *,
    candidate: CandidateSpec,
    executable: str,
    paddle_template: str | None,
    deepseek_template: str | None,
    deepseek_batch_template: str | None,
) -> dict[str, object] | None:
    """Return a blocker payload when the candidate cannot be invoked."""
    if candidate.kind == "deepseek_batch_template":
        if deepseek_batch_template is None or not deepseek_batch_template.strip():
            return {
                "block_reason": "candidate_command_not_configured",
                "detail": (
                    "Set --deepseek-ocr2-batch-command or "
                    "SIR_CONVERT_A_LOT_FORMULA_CANDIDATE_DEEPSEEK_OCR2_BATCH_COMMAND."
                ),
            }
        command = shlex.split(deepseek_batch_template)
        if command and not executable_exists(command[0]):
            return {"block_reason": "candidate_executable_not_found", "executable": command[0]}
        return None
    if candidate.kind == "deepseek_template":
        if deepseek_template is None or not deepseek_template.strip():
            return {
                "block_reason": "candidate_command_not_configured",
                "detail": (
                    "Set --deepseek-ocr2-command or "
                    "SIR_CONVERT_A_LOT_FORMULA_CANDIDATE_DEEPSEEK_OCR2_COMMAND."
                ),
            }
        command = shlex.split(deepseek_template)
        if command and not executable_exists(command[0]):
            return {"block_reason": "candidate_executable_not_found", "executable": command[0]}
        return None
    if candidate.kind == "paddle_pipeline" and paddle_template:
        command = shlex.split(paddle_template)
        if command and not executable_exists(command[0]):
            return {"block_reason": "candidate_executable_not_found", "executable": command[0]}
        return None
    if not executable_exists(executable):
        return {"block_reason": "candidate_executable_not_found", "executable": executable}
    return None


def blocked_candidate(
    candidate: CandidateSpec,
    source_inputs: Sequence[SourceInput],
    blocker: Mapping[str, object],
) -> dict[str, object]:
    """Return a report record for an evidence-backed candidate blocker."""
    return {
        "candidate_id": candidate.candidate_id,
        "label": candidate.label,
        "status": "blocked",
        "input_count": len(source_inputs),
        "block_reason": blocker.get("block_reason"),
        "blocker": dict(blocker),
        "marker_counts": collect_marker_counts(""),
        "input_results": [],
    }


def candidate_output_text(*, output_root: Path, stdout: str) -> str:
    """Extract candidate text from saved JSON outputs or stdout."""
    fragments: list[str] = []
    for path in sorted(output_root.rglob("*.json")):
        loaded = read_json_object(path)
        fragments.extend(json_text_fragments(loaded))
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or not is_candidate_text_artifact(path):
            continue
        fragments.append(path.read_text(encoding="utf-8", errors="replace"))
    if fragments:
        return "\n\n".join(fragments)
    return tail_text(stdout)


def is_candidate_text_artifact(path: Path) -> bool:
    """Return whether a candidate-produced file should count as output text."""
    if path.name in {"candidate-output.txt", "stdout.txt", "stderr.txt"}:
        return False
    return path.suffix.lower() in {".md", ".mmd", ".txt", ".tex"}


def json_text_fragments(value: object) -> list[str]:
    """Collect formula-like text fields from nested JSON structures."""
    fragments: list[str] = []
    if isinstance(value, dict):
        for key_obj, child in value.items():
            key = str(key_obj)
            if key in {"rec_formula", "formula", "latex", "text", "markdown"} and isinstance(
                child, str
            ):
                fragments.append(child)
            else:
                fragments.extend(json_text_fragments(child))
    elif isinstance(value, list):
        for child in value:
            fragments.extend(json_text_fragments(child))
    return fragments


def collect_marker_counts(text: str) -> dict[str, int]:
    """Count Docling page-window replay known bad output markers."""
    return {marker: text.count(marker) for marker in BAD_MARKERS}


def sum_marker_counts(results: Sequence[Mapping[str, object]]) -> dict[str, int]:
    """Sum marker counts across input results."""
    totals = {marker: 0 for marker in BAD_MARKERS}
    for result in results:
        counts = object_mapping(result.get("marker_counts"))
        for marker in BAD_MARKERS:
            value = counts.get(marker)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[marker] += value
    return totals


def default_external_candidates() -> tuple[CandidateSpec, ...]:
    """Return the formula candidate evaluation candidate matrix."""
    return (
        CandidateSpec(
            candidate_id="unimernet_paddleocr",
            label="UniMERNet through PaddleOCR formula pipeline",
            kind="paddle_pipeline",
            model_name="UniMERNet",
            input_kind="formula_crop",
        ),
        CandidateSpec(
            candidate_id="pp_formulanet_plus_s_paddleocr",
            label="PP-FormulaNet_plus-S through PaddleOCR formula pipeline",
            kind="paddle_pipeline",
            model_name="PP-FormulaNet_plus-S",
            input_kind="formula_crop",
        ),
        CandidateSpec(
            candidate_id="deepseek_ocr2_hf_eager",
            label="DeepSeek-OCR-2 HF eager command",
            kind="deepseek_template",
            model_name="deepseek-ai/DeepSeek-OCR-2",
            input_kind="page",
        ),
    )


def candidate_sources() -> dict[str, str]:
    """Return official candidate documentation sources used by the harness."""
    return {
        "paddleocr_formula_pipeline": "https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/formula_recognition.html",
        "paddleocr_formula_module": "https://www.paddleocr.ai/latest/en/version3.x/module_usage/formula_recognition.html",
        "unimernet": "https://huggingface.co/PaddlePaddle/UniMERNet",
        "pp_formulanet_plus_s": "https://huggingface.co/PaddlePaddle/PP-FormulaNet_plus-S",
        "deepseek_ocr2": "https://huggingface.co/deepseek-ai/DeepSeek-OCR-2",
    }


def baseline_elapsed_ms(report: Mapping[str, object]) -> int | None:
    """Extract the Docling page-window replay baseline elapsed time when present."""
    records = report.get("records")
    if not isinstance(records, list) or not records:
        return None
    first = object_mapping(records[0])
    child = object_mapping(first.get("child"))
    elapsed = child.get("elapsed_ms")
    if isinstance(elapsed, int) and not isinstance(elapsed, bool):
        return elapsed
    return None


def executable_exists(executable: str) -> bool:
    """Return whether an executable is available."""
    if "/" in executable:
        return Path(executable).exists()
    return shutil.which(executable) is not None


def timeout_text(value: object) -> str:
    """Normalize TimeoutExpired stdout/stderr values."""
    if isinstance(value, str):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return ""


def tail_text(value: str) -> str:
    """Return a bounded text tail for reports."""
    if len(value) <= TAIL_CHARS:
        return value
    return value[-TAIL_CHARS:]


def read_json_object(path: Path) -> dict[str, object]:
    """Read a JSON object from disk, returning empty mapping for non-objects."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return {str(key): value for key, value in loaded.items()}
    return {}
