"""Public CLI entrypoint for the Story 31 talker-core stability lab.

Purpose:
    Keep the public command surface small while delegating implementation to
    the training-domain Story 31 exploration module.

Relationships:
    - Wraps `ml.qwen.training.story31_stability_lab`.
    - Exposed as the public `pdm run qwen-story31-stability-lab` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.story31_stability_lab import main

if __name__ == "__main__":
    raise SystemExit(main())
