"""Formula candidate evaluation command construction.

Purpose:
    Build and validate external candidate command argv for the Task 346/350
    formula/OCR evidence harness.

Relationships:
    - Used by candidate execution helpers before invoking PaddleOCR or
      DeepSeek-OCR-2 command surfaces.
    - Keeps command-template expansion separate from process execution and
      report shaping.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_outputs import (
    executable_exists,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_candidate_specs import (
    CandidateSpec,
)
from scripts.sir_convert_a_lot.devops.formula_candidate_eval_inputs import SourceInput


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
