"""Detached in-container probe for the Task 101 Qwen pilot fine-tune lane.

Purpose:
    Execute one bounded Swedish Qwen3-TTS pilot fine-tuning run inside the
    Task 100 training image, persist machine-readable status/report artifacts,
    and keep the detached outer Hemma runner independent from the inner
    training loop.

Relationships:
    - Executed inside the shared Qwen runtime image by the detached Task 101
      Hemma runner.
    - Reuses the patched `sft_12hz.py` training entrypoint from
      `scripts/devops/qwen_finetuning_patches/`.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import traceback
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import sft_12hz
import torch


@dataclass(frozen=True)
class Task101PilotProbeReport:
    """Machine-readable report emitted by the detached Task 101 probe."""

    generated_at: str
    model_id: str
    train_jsonl: str
    output_dir: str
    torch_version: str
    torchaudio_version: str | None
    torch_cuda_available: bool
    torch_cuda_device_count: int
    torch_hip_version: str | None
    flash_attn_importable: bool
    flash_attn_version: str | None
    training_summary: dict[str, object]


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in RFC3339 format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _package_version(distribution_name: str) -> str | None:
    """Return one installed package version, or `None` when it is absent."""
    try:
        return importlib.metadata.version(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the detached Task 101 training probe."""
    parser = argparse.ArgumentParser(description="Run the detached Task 101 Qwen pilot probe.")
    parser.add_argument("--model-id", default="Qwen/Qwen3-TTS-12Hz-1.7B-Base")
    parser.add_argument("--train-jsonl", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--num-epochs", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=8)
    return parser.parse_args()


def _write_json(path: Path, payload: object) -> None:
    """Write one deterministic JSON artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    """Run the detached Task 101 pilot probe and persist report artifacts."""
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "status.json"
    report_path = output_dir / "report.json"
    failure_path = output_dir / "failure.txt"
    training_summary_path = output_dir / "training_summary.json"
    _write_json(
        status_path,
        {
            "status": "running",
            "stage": "training",
            "updated_at": _utc_now_iso(),
            "train_jsonl": args.train_jsonl.as_posix(),
            "output_dir": output_dir.as_posix(),
        },
    )
    try:
        if not torch.cuda.is_available():
            raise SystemExit(
                "Task 101 pilot probe expected GPU-visible torch inside the container."
            )
        if torch.version.hip is None:
            raise SystemExit(
                "Task 101 pilot probe expected ROCm-enabled torch inside the container."
            )
        training_args = argparse.Namespace(
            init_model_path=str(args.model_id),
            output_model_path=(output_dir / "checkpoints").as_posix(),
            train_jsonl=args.train_jsonl.as_posix(),
            batch_size=int(args.batch_size),
            lr=float(args.lr),
            num_epochs=int(args.num_epochs),
            max_steps=int(args.max_steps),
            metrics_output_json=training_summary_path.as_posix(),
            speaker_name="pilot_multi_speaker",
        )
        training_summary = sft_12hz.train_with_args(training_args)
        report = Task101PilotProbeReport(
            generated_at=_utc_now_iso(),
            model_id=str(args.model_id),
            train_jsonl=args.train_jsonl.as_posix(),
            output_dir=output_dir.as_posix(),
            torch_version=str(torch.__version__),
            torchaudio_version=_package_version("torchaudio"),
            torch_cuda_available=True,
            torch_cuda_device_count=int(torch.cuda.device_count()),
            torch_hip_version=str(torch.version.hip),
            flash_attn_importable=importlib.util.find_spec("flash_attn") is not None,
            flash_attn_version=_package_version("flash-attn"),
            training_summary=asdict(training_summary),
        )
        _write_json(report_path, asdict(report))
        _write_json(
            status_path,
            {
                "status": "completed",
                "stage": "training",
                "updated_at": _utc_now_iso(),
                "train_jsonl": args.train_jsonl.as_posix(),
                "output_dir": output_dir.as_posix(),
                "optimizer_steps_completed": training_summary.optimizer_steps_completed,
            },
        )
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        failure_path.write_text(traceback.format_exc(), encoding="utf-8")
        _write_json(
            status_path,
            {
                "status": "failed",
                "stage": "training",
                "updated_at": _utc_now_iso(),
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
