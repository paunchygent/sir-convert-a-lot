"""Public CLI entrypoint for the canonical Qwen training smoke lane.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain smoke module.

Relationships:
    - Wraps `ml.qwen.training.smoke`.
    - Exposed as the public `pdm run qwen-smoke` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.smoke import main

if __name__ == "__main__":
    raise SystemExit(main())
