"""Public CLI entrypoint for the Story 30 fresh-start proof surface.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain Story 30 fresh-start proof module.

Relationships:
    - Wraps `ml.qwen.training.story30_freshstart_proof`.
    - Exposed as the public `pdm run qwen-story30-freshstart-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.story30_freshstart_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
