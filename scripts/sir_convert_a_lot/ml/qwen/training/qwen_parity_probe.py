"""CLI implementation for the Qwen stability lab deterministic parity probe.

Purpose:
    Expose one narrow local mechanism surface that compares the recreated
    `the diagnostic lane` failure-family window across the current train-step runtime and a
    reconstructed shared-forward window before any further stabilizer work.

Relationships:
    - Used by the public `qwen-parity-probe` CLI entrypoint.
    - Delegates execution and artifact persistence to
      `qwen_parity_probe_runner.py`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.gradient_accumulation import (
    DEFAULT_GRADIENT_ACCUMULATION_STEPS,
    resolve_gradient_accumulation_steps,
)
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_parity_probe_contracts import (
    DEFAULT_MANIFEST_LINES,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_QWEN_PARITY_PROBE_SETTINGS,
    QwenParityProbeSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_assembly_mode import (
    DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
    resolve_text_embedding_assembly_mode,
)
from scripts.sir_convert_a_lot.ml.qwen.training.text_embedding_mask_policy import (
    LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
    resolve_text_embedding_mask_policy,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser for the Qwen stability lab parity probe."""
    parser = argparse.ArgumentParser(
        description="Run the deterministic Qwen stability lab upstream-vs-current parity probe."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    default_settings = DEFAULT_QWEN_PARITY_PROBE_SETTINGS

    run = subparsers.add_parser("run", help="Run one local Qwen stability lab parity comparison.")
    run.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run.add_argument("--source-bundle-root", type=Path, default=default_settings.source_bundle_root)
    run.add_argument("--image", default=default_settings.image)
    run.add_argument("--model-id", default=default_settings.model_id)
    run.add_argument(
        "--train-manifest-family",
        default=default_settings.train_manifest_family,
    )
    run.add_argument(
        "--eval-manifest-family",
        default=default_settings.eval_manifest_family,
    )
    run.add_argument(
        "--manifest-lines",
        default=",".join(str(value) for value in DEFAULT_MANIFEST_LINES),
    )
    run.add_argument("--batch-size", type=int, default=default_settings.batch_size)
    run.add_argument(
        "--gradient-accumulation-steps",
        type=int,
        default=default_settings.gradient_accumulation_steps,
    )
    run.add_argument(
        "--text-embedding-assembly-mode",
        default=default_settings.text_embedding_assembly_mode,
    )
    run.add_argument(
        "--text-embedding-mask-policy",
        default=default_settings.text_embedding_mask_policy,
    )
    run.add_argument("--max-steps", type=int, default=default_settings.max_steps)
    run.add_argument("--deterministic-seed", type=int, default=default_settings.deterministic_seed)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Qwen stability lab parity probe and persist its artifact set."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command != "run":
        raise SystemExit(f"Unsupported Qwen stability lab parity-probe command: {args.command}")
    from scripts.sir_convert_a_lot.ml.qwen.training.qwen_parity_probe_runner import (
        persist_report,
        run_qwen_parity_probe,
    )

    settings = QwenParityProbeSettings(
        output_root=Path(args.output_root),
        source_bundle_root=Path(args.source_bundle_root),
        image=str(args.image),
        model_id=str(args.model_id),
        train_manifest_family=str(args.train_manifest_family),
        eval_manifest_family=str(args.eval_manifest_family),
        manifest_lines=_parse_manifest_lines(str(args.manifest_lines)),
        batch_size=int(args.batch_size),
        gradient_accumulation_steps=resolve_gradient_accumulation_steps(
            int(args.gradient_accumulation_steps),
            default=DEFAULT_GRADIENT_ACCUMULATION_STEPS,
        ),
        text_embedding_assembly_mode=resolve_text_embedding_assembly_mode(
            str(args.text_embedding_assembly_mode),
            default=DEFAULT_TEXT_EMBEDDING_ASSEMBLY_MODE,
        ),
        text_embedding_mask_policy=resolve_text_embedding_mask_policy(
            str(args.text_embedding_mask_policy),
            default=LEGACY_TEXT_EMBEDDING_MASK_POLICY_DEFAULT,
        ),
        max_steps=int(args.max_steps),
        deterministic_seed=int(args.deterministic_seed),
    )
    report = run_qwen_parity_probe(settings)
    persist_report(settings.output_root, report)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


def _parse_manifest_lines(raw_value: str) -> tuple[int, ...]:
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 4:
        raise SystemExit("Qwen stability lab parity probe requires exactly four manifest lines.")
    return tuple(int(piece) for piece in pieces)


if __name__ == "__main__":
    raise SystemExit(main())
