"""Public CLI entrypoint for the Story 30 backward-lineage proof surface.

Purpose:
    Keep the public command surface small while delegating implementation to
    the training-domain T212 backward-lineage proof module.

Relationships:
    - Wraps `ml.qwen.training.story30_backward_lineage_proof`.
    - Exposed as the public `pdm run qwen-story30-backward-lineage` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.story30_backward_lineage_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
