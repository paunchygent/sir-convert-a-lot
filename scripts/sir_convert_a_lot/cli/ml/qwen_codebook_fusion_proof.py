"""Public CLI entrypoint for the canonical Qwen codebook-fusion proof codebook-fusion proof.

Purpose:
    Keep the public command surface small while delegating implementation to
    the training-domain proof runner.

Relationships:
    - Wraps `ml.qwen.training.codebook_fusion_proof`.
    - Exposed as the public `pdm run qwen-codebook-fusion-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.codebook_fusion_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
