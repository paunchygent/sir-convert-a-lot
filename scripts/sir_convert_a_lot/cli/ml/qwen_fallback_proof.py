"""Public CLI entrypoint for the canonical Qwen fallback proof surface.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain Qwen fallback proof module.

Relationships:
    - Wraps `ml.qwen.training.qwen_fallback_proof`.
    - Exposed as the public `pdm run qwen-fallback-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_fallback_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
