"""Public CLI entrypoint for the Qwen backward-lineage and fresh-start proof lane fresh-start proof
surface.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain Qwen backward-lineage and fresh-start proof lane fresh-start proof
    module.

Relationships:
    - Wraps `ml.qwen.training.qwen_freshstart_proof`.
    - Exposed as the public `pdm run qwen-freshstart-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_freshstart_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
