"""Task 198 detached proof command surface for Qwen training on Hemma.

Purpose:
    Expose the committed Task 198 accumulation-ablation prepare/launch/status
    CLI while reusing the shared Story 29 proof core.

Relationships:
    - Uses the shared implementation in `t197_proof.py`.
    - Applies the `T198` profile from `t197_proof_artifacts.py`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof import run_main
from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof_artifacts import (
    T198_PROOF_PROFILE,
)


def main(argv: list[str] | None = None) -> int:
    """Prepare or operate the detached Hemma Task 198 proof surface."""
    return run_main(T198_PROOF_PROFILE, argv)


if __name__ == "__main__":
    raise SystemExit(main())
