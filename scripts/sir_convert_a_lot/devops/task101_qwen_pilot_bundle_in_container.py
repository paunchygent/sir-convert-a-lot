"""In-container Task 101 pilot-bundle batch finalization entrypoint.

Purpose:
    Finalize one or more contiguous Task 101 bundle batches inside the governed
    Qwen runtime image so the host only orchestrates Docker launches and
    progress remains bundle-rooted.

Relationships:
    - Invoked by `task101_qwen_pilot_bundle_runtime.py`.
    - Calls the local batch finalizer in
      `task101_qwen_pilot_bundle_batch_execution.py`.
    - Reuses the bundle runtime fingerprint persisted by the host runtime
      helper.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_contracts import (
    load_task101_pilot_bundle_batch_plan,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_batch_execution import (
    finalize_task101_pilot_bundle_batch,
)
from scripts.sir_convert_a_lot.devops.task101_qwen_pilot_bundle_runtime import (
    load_task101_pilot_bundle_runtime_fingerprint,
    task101_pilot_bundle_runtime_fingerprint_path,
    write_task101_pilot_bundle_audio_codes_runtime_report,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_finalization import (
    describe_governed_audio_codes_runtime,
    encode_audio_codes_with_governed_gpu_runtime,
)
from scripts.sir_convert_a_lot.devops.task103_qwen_preprocessing_models import (
    CANONICAL_MANIFEST_FAMILIES,
)


def _build_parser() -> argparse.ArgumentParser:
    """Build the narrow in-container parser for one contiguous batch launch."""
    parser = argparse.ArgumentParser(
        description="Finalize one Task 101 pilot-bundle batch inside the governed Qwen image."
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest-family", required=True, choices=CANONICAL_MANIFEST_FAMILIES)
    parser.add_argument("--batch-index", type=int, required=True)
    parser.add_argument("--batch-count", type=int, default=1)
    parser.add_argument("--audio-codes-chunk-size", type=int, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one containerized Task 101 finalization launch."""
    args = _build_parser().parse_args(argv)
    output_root = Path(args.output_root)
    if int(args.batch_count) <= 0:
        raise ValueError("`batch_count` must be positive.")
    fingerprint = load_task101_pilot_bundle_runtime_fingerprint(
        task101_pilot_bundle_runtime_fingerprint_path(output_root)
    )
    plan = load_task101_pilot_bundle_batch_plan(output_root)
    runtime_report = describe_governed_audio_codes_runtime(plan.tokenizer_model)
    write_task101_pilot_bundle_audio_codes_runtime_report(output_root, runtime_report)
    rendered_batches: list[dict[str, object]] = []
    for batch_index in range(
        int(args.batch_index),
        int(args.batch_index) + int(args.batch_count),
    ):
        batch = finalize_task101_pilot_bundle_batch(
            output_root=output_root,
            plan=plan,
            manifest_family=args.manifest_family,
            batch_index=batch_index,
            audio_codes_chunk_size=int(args.audio_codes_chunk_size),
            encode_audio_codes_fn=encode_audio_codes_with_governed_gpu_runtime,
            runtime_fingerprint=fingerprint,
        )
        rendered_batches.append(asdict(batch))
    print(json.dumps({"batches": rendered_batches}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
