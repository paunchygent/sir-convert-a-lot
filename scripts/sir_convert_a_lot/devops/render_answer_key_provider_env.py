"""Render production answer-key provider environment.

Purpose:
    Emit canonical env-file lines for the governed Qwen3.6 structured
    answer-key provider without requiring operators to hand-write provider JSON.

Relationships:
    - Used by `scripts/devops/sync-prod-env-mirror.sh` for Hemma production.
    - Reuses `infrastructure.answer_key_provider_runtime_config` so service
      startup and operator env rendering share the same URL/profile contract.
"""

from __future__ import annotations

import argparse
import sys

from scripts.sir_convert_a_lot.infrastructure.answer_key_local_model_profiles import (
    AnswerKeyProviderProfileName,
)
from scripts.sir_convert_a_lot.infrastructure.answer_key_provider_runtime_config import (
    AnswerKeyProviderRuntimeLane,
    render_answer_key_provider_environment,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render answer-key provider env lines.")
    parser.add_argument(
        "--lane",
        choices=[lane.value for lane in AnswerKeyProviderRuntimeLane],
        default=AnswerKeyProviderRuntimeLane.HEMMA_PROD_COMPOSE.value,
    )
    parser.add_argument(
        "--profile",
        choices=[
            AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP.value,
            AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP.value,
        ],
        default=AnswerKeyProviderProfileName.QWEN36_LLAMA_CPP_MTP.value,
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    env = render_answer_key_provider_environment(
        lane=AnswerKeyProviderRuntimeLane(args.lane),
        profile_name=AnswerKeyProviderProfileName(args.profile),
    )
    for key in sorted(env):
        print(f"{key}={env[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
