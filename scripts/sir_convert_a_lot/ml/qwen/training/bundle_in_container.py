"""In-container entrypoint for governed training-bundle batch finalization.

Purpose:
    Finalize one or more contiguous training-bundle batches inside the shared
    governed Qwen runtime image so the host only orchestrates Docker launches
    and bundle artifacts remain rooted on the host-visible output path.

Relationships:
    - Invoked by `ml.qwen.training.bundle_runtime`.
    - Calls the local batch finalizer in `ml.qwen.training.bundles`.
    - Persists governed runtime provenance and observed audio-code runtime
      posture for the current bundle root.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.ml.qwen.common.models import CANONICAL_MANIFEST_FAMILIES
from scripts.sir_convert_a_lot.ml.qwen.preprocessing.finalization import (
    describe_governed_audio_codes_runtime,
    encode_audio_codes_with_governed_gpu_runtime,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundle_runtime import (
    load_training_bundle_runtime_fingerprint,
    training_bundle_runtime_fingerprint_path,
    write_training_bundle_audio_codes_runtime_report,
)
from scripts.sir_convert_a_lot.ml.qwen.training.bundles import (
    finalize_training_bundle_batch,
    load_training_bundle_batch_plan,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the narrow parser for one contiguous in-container batch launch."""
    parser = argparse.ArgumentParser(
        description="Finalize one training-bundle batch inside the governed Qwen image."
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest-family", required=True, choices=CANONICAL_MANIFEST_FAMILIES)
    parser.add_argument("--batch-index", type=int, required=True)
    parser.add_argument("--batch-count", type=int, default=1)
    parser.add_argument("--audio-codes-chunk-size", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one containerized training-bundle finalization launch."""
    args = build_parser().parse_args(argv)
    output_root = Path(args.output_root)
    if int(args.batch_count) <= 0:
        raise ValueError("`batch_count` must be positive.")
    fingerprint = load_training_bundle_runtime_fingerprint(
        training_bundle_runtime_fingerprint_path(output_root)
    )
    plan = load_training_bundle_batch_plan(output_root)
    runtime_report = describe_governed_audio_codes_runtime(plan.tokenizer_model)
    write_training_bundle_audio_codes_runtime_report(output_root, runtime_report)
    rendered_batches: list[dict[str, object]] = []
    for batch_index in range(int(args.batch_index), int(args.batch_index) + int(args.batch_count)):
        finalize_training_bundle_batch(
            output_root=output_root,
            plan=plan,
            manifest_family=args.manifest_family,
            batch_index=batch_index,
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            encode_audio_codes_fn=encode_audio_codes_with_governed_gpu_runtime,
            runtime_fingerprint=fingerprint,
        )
        batch = next(
            candidate
            for candidate in plan.batches
            if candidate.manifest_family == args.manifest_family
            and candidate.batch_index == batch_index
        )
        rendered_batches.append(asdict(batch))
    print(json.dumps({"batches": rendered_batches}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
