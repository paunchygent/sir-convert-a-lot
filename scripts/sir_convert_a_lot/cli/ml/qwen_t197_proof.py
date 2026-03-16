"""Public CLI entrypoint for the canonical Task 197 proof surface.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain Task 197 proof module.

Relationships:
    - Wraps `ml.qwen.training.t197_proof`.
    - Exposed as the public `pdm run qwen-t197-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.t197_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
