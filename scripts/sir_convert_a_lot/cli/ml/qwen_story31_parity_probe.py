"""Public CLI entrypoint for the Story 31 deterministic parity probe.

Purpose:
    Keep the public command surface small while delegating the mechanism-lane
    parity implementation to the training-domain module.

Relationships:
    - Wraps `ml.qwen.training.story31_parity_probe`.
    - Exposed as the public `pdm run qwen-story31-parity-probe` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.story31_parity_probe import main

if __name__ == "__main__":
    raise SystemExit(main())
