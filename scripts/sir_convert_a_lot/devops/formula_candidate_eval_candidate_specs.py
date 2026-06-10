"""Formula candidate evaluation candidate declarations.

Purpose:
    Declare the specialist formula/OCR candidate matrix used for Task 346 and
    Task 350 evidence replay without owning runtime execution.

Relationships:
    - Consumed by `formula_candidate_eval_candidates` and its execution helpers.
    - Names evaluated candidate lanes while keeping production conversion
      routing out of the evaluation harness.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateSpec:
    """One formula/OCR candidate adapter declaration."""

    candidate_id: str
    label: str
    kind: str
    model_name: str | None
    input_kind: str


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
        "paddleocr_formula_pipeline": (
            "https://www.paddleocr.ai/latest/en/version3.x/pipeline_usage/formula_recognition.html"
        ),
        "paddleocr_formula_module": (
            "https://www.paddleocr.ai/latest/en/version3.x/module_usage/formula_recognition.html"
        ),
        "unimernet": "https://huggingface.co/PaddlePaddle/UniMERNet",
        "pp_formulanet_plus_s": "https://huggingface.co/PaddlePaddle/PP-FormulaNet_plus-S",
        "deepseek_ocr2": "https://huggingface.co/deepseek-ai/DeepSeek-OCR-2",
    }
