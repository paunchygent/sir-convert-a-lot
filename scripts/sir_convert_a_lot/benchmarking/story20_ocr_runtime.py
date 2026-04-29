"""OCR runtime preflight for Task 74 local smoke execution.

Purpose:
    Fail fast when the local in-process Story 20/Task 74 command-surface smoke
    cannot satisfy the requested OCR engine/model configuration. Acceptance
    benchmark evidence for Task 74/Story 39 remains Hemma-only.

Relationships:
    - Used by `story20_profile_runner` before launching local in-process smoke
      jobs.
    - Keeps dependency/model checks separate from HTTP profile execution.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def assert_in_process_runtime_supports_requested_ocr(
    *,
    ocr_mode: str,
    ocr_engine: str,
    easyocr_model_storage_directory: str | None,
) -> None:
    """Fail fast when the local in-process smoke runtime lacks requested OCR deps."""
    if ocr_mode == "off":
        return
    if ocr_engine != "easyocr":
        return
    if importlib.util.find_spec("easyocr") is None:
        raise RuntimeError(
            "Task 74 local in-process smoke runtime is missing EasyOCR. "
            "Run `pdm sync` in the benchmark environment or use the canonical "
            "`benchmark:task-74-hemma` workflow before benchmarking."
        )
    if easyocr_model_storage_directory is None:
        return
    model_dir = Path(easyocr_model_storage_directory).expanduser()
    if not model_dir.exists():
        raise RuntimeError(
            "Task 74 local in-process smoke runtime is missing the EasyOCR model directory "
            f"`{model_dir}`. Warm the host EasyOCR cache first or pass "
            "`--easyocr-model-storage-dir` to a prepared path."
        )
