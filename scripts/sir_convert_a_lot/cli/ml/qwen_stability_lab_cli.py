"""Public CLI entrypoint for the Qwen stability lab talker-core stability lab.

Purpose:
    Keep the public command surface small while delegating implementation to
    the training-domain Qwen stability lab exploration module.

Relationships:
    - Wraps `ml.qwen.training.qwen_stability_lab`.
    - Exposed as the public `pdm run qwen-stability-lab` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_stability_lab import main

if __name__ == "__main__":
    raise SystemExit(main())
