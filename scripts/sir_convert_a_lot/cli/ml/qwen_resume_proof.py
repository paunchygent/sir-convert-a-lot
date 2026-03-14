"""Public CLI entrypoint for the canonical Qwen resume proof lane.

Purpose:
    Keep the public command surface small while delegating the implementation
    to the training-domain resume-proof module.

Relationships:
    - Wraps `ml.qwen.training.resume_proof`.
    - Exposed as the public `pdm run qwen-resume-proof` command.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.resume_proof import main

if __name__ == "__main__":
    raise SystemExit(main())
