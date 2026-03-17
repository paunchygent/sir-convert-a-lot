"""CLI implementation for the Story 31 talker-core stability lab.

Purpose:
    Expose one lightweight attached exploration surface for running compact
    stabilization matrices against the exact fresh-start failing family,
    without creating proof packages for each hypothesis.

Relationships:
    - Uses `story31_stability_lab_runner.py` for execution and artifact
      persistence.
    - Reuses Story 30 selected-row lineage mechanics through the runner.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.training.smoke import (
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_IMAGE,
    DEFAULT_MODEL_ID,
    default_hf_cache_dir,
    default_hf_cache_home_mount,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_contracts import (
    Story31StabilityLabSettings,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_gate import (
    DEFAULT_BASELINE_VARIANT,
    DEFAULT_CANDIDATE_VARIANT,
    evaluate_promotion_gate,
    load_results_payload,
    persist_promotion_gate,
)
from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab_runner import (
    DEFAULT_HOOK_PROFILE,
    DEFAULT_MANIFEST_FAMILY,
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
    DEFAULT_SOURCE_BUNDLE_ROOT,
    DEFAULT_SOURCE_LINES,
    DEFAULT_STABILIZATION_VARIANTS,
    DEFAULT_TEXT_EMBEDDING_MASK_POLICY,
    parse_stabilization_variants,
    persist_report,
    run_stability_lab,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the public CLI parser for the Story 31 stability lab."""
    parser = argparse.ArgumentParser(
        description="Run the Story 31 talker-core stability-lab exploration surface."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run one compact Story 31 matrix.")
    run.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    run.add_argument("--image", default=DEFAULT_IMAGE)
    run.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    run.add_argument("--hf-cache-dir", type=Path, default=default_hf_cache_dir())
    run.add_argument("--hf-cache-home-mount", type=Path, default=default_hf_cache_home_mount())
    run.add_argument(
        "--output-root-home-mount-base",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT_HOME_MOUNT_BASE,
    )
    run.add_argument("--source-bundle-root", type=Path, default=DEFAULT_SOURCE_BUNDLE_ROOT)
    run.add_argument("--manifest-family", default=DEFAULT_MANIFEST_FAMILY)
    run.add_argument(
        "--source-lines",
        default=",".join(str(value) for value in DEFAULT_SOURCE_LINES),
    )
    run.add_argument("--text-embedding-mask-policy", default=DEFAULT_TEXT_EMBEDDING_MASK_POLICY)
    run.add_argument("--hook-profile", default=DEFAULT_HOOK_PROFILE)
    run.add_argument(
        "--stabilization-variants",
        default=",".join(DEFAULT_STABILIZATION_VARIANTS),
    )
    run.add_argument("--skip-build", action="store_true")

    gate = subparsers.add_parser(
        "gate",
        help="Evaluate whether one Story 31 candidate variant earns promotion.",
    )
    gate.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    gate.add_argument("--results-path", type=Path, default=None)
    gate.add_argument("--baseline-variant", default=DEFAULT_BASELINE_VARIANT)
    gate.add_argument("--candidate-variant", default=DEFAULT_CANDIDATE_VARIANT)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one Story 31 stability-lab matrix and persist compact artifacts."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "gate":
        output_root = Path(args.output_root)
        results_path = (
            output_root / "results.json" if args.results_path is None else Path(args.results_path)
        )
        gate_report = evaluate_promotion_gate(
            results_payload=load_results_payload(results_path),
            results_path=results_path,
            baseline_variant=str(args.baseline_variant),
            candidate_variant=str(args.candidate_variant),
        )
        persist_promotion_gate(output_root, gate_report)
        print(json.dumps(asdict(gate_report), indent=2, ensure_ascii=False))
        return 0
    if args.command != "run":
        raise SystemExit(f"Unsupported Story 31 stability-lab command: {args.command}")
    settings = Story31StabilityLabSettings(
        output_root=Path(args.output_root),
        dockerfile_path=Path(args.dockerfile_path),
        image=str(args.image),
        model_id=str(args.model_id),
        hf_cache_dir=Path(args.hf_cache_dir),
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        output_root_home_mount_base=Path(args.output_root_home_mount_base),
        source_bundle_root=Path(args.source_bundle_root),
        manifest_family=str(args.manifest_family),
        source_lines=_parse_source_lines(str(args.source_lines)),
        text_embedding_mask_policy=str(args.text_embedding_mask_policy),
        hook_profile=str(args.hook_profile),
        stabilization_variants=parse_stabilization_variants(str(args.stabilization_variants)),
        build_image=not bool(args.skip_build),
    )
    report = run_stability_lab(settings)
    persist_report(settings.output_root, report)
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    return 0


def _parse_source_lines(raw_value: str) -> tuple[int, int]:
    pieces = [piece.strip() for piece in raw_value.split(",") if piece.strip() != ""]
    if len(pieces) != 2:
        raise SystemExit("Story 31 stability lab requires exactly two source lines.")
    return int(pieces[0]), int(pieces[1])


if __name__ == "__main__":
    raise SystemExit(main())
