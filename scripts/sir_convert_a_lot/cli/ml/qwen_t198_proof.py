"""Public CLI entrypoint for the canonical Task 198 proof surface.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain Task 198 proof module.

Relationships:
    - Wraps `ml.qwen.training.t198_proof`.
    - Exposed as the public `pdm run qwen-t198-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.t198_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
