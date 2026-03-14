"""Public CLI entrypoint for the canonical Qwen ref-mel cache comparison lane.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain comparison module.

Relationships:
    - Wraps `ml.qwen.training.ref_mel_cache_comparison`.
    - Exposed as the public `pdm run qwen-ref-mel-cache-comparison` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.ref_mel_cache_comparison import main

if __name__ == "__main__":
    raise SystemExit(main())
