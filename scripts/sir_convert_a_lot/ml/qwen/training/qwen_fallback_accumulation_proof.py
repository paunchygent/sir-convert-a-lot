"""Qwen fallback accumulation proof command surface for Qwen training on Hemma.

Purpose:
    Expose the committed Qwen fallback accumulation-ablation prepare/launch/status
    CLI while reusing the shared Qwen fallback proof core.

Relationships:
    - Uses the shared implementation in `qwen_fallback_proof.py`.
    - Applies the fallback accumulation profile from `qwen_fallback_proof_artifacts.py`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_fallback_proof import run_main
from scripts.sir_convert_a_lot.ml.qwen.training.qwen_fallback_proof_artifacts import (
    FALLBACK_ACCUMULATION_PROOF_PROFILE,
)


def main(argv: list[str] | None = None) -> int:
    """Prepare or operate the detached Hemma Qwen fallback accumulation proof surface."""
    return run_main(FALLBACK_ACCUMULATION_PROOF_PROFILE, argv)


if __name__ == "__main__":
    raise SystemExit(main())
