"""Formula candidate evaluation external command execution.

Purpose:
    Run configured specialist formula/OCR candidate commands and normalize
    their artifacts into Task 346/350 evidence records.

Relationships:
    - Consumes `formula_candidate_eval_candidate_specs` declarations.
    - Uses source inputs from `formula_candidate_eval_inputs`.
    - Delegates marker and text extraction to candidate output helpers.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Mapping, Sequence

from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_commands import (
    build_candidate_command,
    command_blocker,
    deepseek_batch_command,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_outputs import (
    baseline_elapsed_ms,
    candidate_output_text,
    collect_marker_counts,
    sum_marker_counts,
    tail_text,
    timeout_text,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_specs import (
    CandidateSpec,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_inputs import (
    SourceInput,
    source_text_for_input,
)


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
