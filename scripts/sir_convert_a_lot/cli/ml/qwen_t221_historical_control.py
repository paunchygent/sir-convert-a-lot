"""Public CLI entrypoint for the T221 historical Task 101 control lane.

Purpose:
    Keep the public command surface small while delegating the T221 historical
    control implementation to the training-domain module.

Relationships:
    - Wraps `ml.qwen.training.t221_historical_control`.
    - Exposed as `pdm run qwen-t221-historical-control`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.t221_historical_control import main

if __name__ == "__main__":
    raise SystemExit(main())
