"""Run PaddleOCR formula recognition for Task 346 replay.

Purpose:
    Provide a Hemma runtime command adapter for UniMERNet and PP-FormulaNet
    candidate execution when the installed PaddleOCR CLI lacks formula commands.

Relationships:
    - Invoked by `task346_formula_candidate_eval` through its Paddle command
      template.
    - Uses the official PaddleOCR formula-recognition Python API.
    - Writes PaddleOCR JSON/image artifacts into the Task 346 evidence bundle.
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Run one PaddleOCR formula-recognition candidate."""
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    runtime = run_paddle_formula(args=args, output_dir=output_dir)
    elapsed_ms = max(0, int((time.monotonic() - started) * 1000))
    metadata = {
        "schema_version": "task347_paddle_formula_command_v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_ms": elapsed_ms,
        "hostname": platform.node(),
        "input": Path(args.input).as_posix(),
        "output_dir": output_dir.as_posix(),
        "model_name": str(args.model_name),
        "device": str(args.device),
        "runtime": runtime,
    }
    (output_dir / "task347-paddle-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the PaddleOCR formula command parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--device", default="gpu")
    return parser


def run_paddle_formula(*, args: argparse.Namespace, output_dir: Path) -> dict[str, object]:
    """Execute PaddleOCR formula recognition through the official Python API."""
    import paddle
    from paddleocr import FormulaRecognitionPipeline

    runtime = {
        "paddle_version": getattr(paddle, "__version__", None),
        "compiled_with_cuda": bool(paddle.device.is_compiled_with_cuda()),
        "device": str(args.device),
    }
    pipeline = FormulaRecognitionPipeline(
        formula_recognition_model_name=str(args.model_name),
        device=str(args.device),
    )
    output = pipeline.predict(Path(args.input).as_posix())
    for index, result in enumerate(output):
        result.save_to_json(save_path=(output_dir / f"result-{index}.json").as_posix())
        result.save_to_img(save_path=output_dir.as_posix())
    return runtime


if __name__ == "__main__":
    raise SystemExit(main())
