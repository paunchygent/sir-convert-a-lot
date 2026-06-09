"""Public CLI entrypoint for the historical Qwen pilot training control lane.

Purpose:
    Keep the public command surface small while delegating historical-control
    execution to the training-domain module.

Relationships:
    - Wraps `ml.qwen.training.qwen_historical_pilot_control`.
    - Exposed as `pdm run qwen-historical-pilot-control`.
"""

from __future__ import annotations

from scripts.sir_convert_a_lot.ml.qwen.training.qwen_historical_pilot_control import main

if __name__ == "__main__":
    raise SystemExit(main())
