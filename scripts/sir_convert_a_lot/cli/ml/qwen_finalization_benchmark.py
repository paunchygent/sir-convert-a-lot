"""Public CLI entrypoint for the canonical Qwen finalization benchmark lane.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain benchmark module.

Relationships:
    - Wraps `ml.qwen.training.finalization_benchmark`.
    - Exposed as the public `pdm run qwen-finalization-benchmark` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.finalization_benchmark import main

if __name__ == "__main__":
    raise SystemExit(main())
