"""Public CLI entrypoint for the Qwen backward-lineage and fresh-start proof lane backward-lineage
proof surface.

Purpose:
    Keep the public command surface small while delegating implementation to
    the training-domain backward-lineage backward-lineage proof module.

Relationships:
    - Wraps `ml.qwen.training.qwen_backward_lineage_proof`.
    - Exposed as the public `pdm run qwen-backward-lineage` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_backward_lineage_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
