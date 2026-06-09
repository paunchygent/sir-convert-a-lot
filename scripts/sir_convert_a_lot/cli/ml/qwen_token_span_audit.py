"""Public CLI entrypoint for the Qwen fallback proof lane token-span audit.

Purpose:
    Keep the public command surface small while delegating implementation to
    the training-domain token-span audit runner.

Relationships:
    - Wraps `ml.qwen.training.token_span_audit`.
    - Exposed as the public `pdm run qwen-token-span-audit` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.token_span_audit import main

if __name__ == "__main__":
    raise SystemExit(main())
