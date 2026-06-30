"""CLI entrypoint for Story 58 live replay proof.

Purpose:
    Expose the governed Story 58 Service API replay proof runner as a PDM
    command for Dev/Prod closeout evidence collection.

Relationships:
    - Parses operator inputs and delegates execution to
      `story58_live_replay_proof`.
    - Reads the Service API key from the same environment pattern used by
      other Sir Convert live proof tools.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from scripts.sir_convert_a_lot.devops.story58_live_replay_proof import (
    run_story58_live_replay_proof,
)
from scripts.sir_convert_a_lot.devops.story58_live_replay_proof_models import (
    Story58LiveReplayProofSettings,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/story-58-live-replay-proof")
DEFAULT_API_KEY_ENV = "SIR_CONVERT_A_LOT_V2_API_KEY"


def main(argv: list[str] | None = None) -> int:
    """Run the Story 58 live replay proof CLI."""

    args = _parse_args(sys.argv[1:] if argv is None else argv)
    summary_path = run_story58_live_replay_proof(
        Story58LiveReplayProofSettings(
            service_url=str(args.service_url),
            api_key=_api_key_from_args(args),
            case_manifest=Path(args.case_manifest),
            output_root=Path(args.output_root),
            timeout_seconds=float(args.timeout_seconds),
            monitoring_pointers=tuple(args.monitoring_pointer),
            log_capture_paths=tuple(Path(path) for path in args.log_capture),
        )
    )
    print(summary_path.as_posix())
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Story 58 live replay proof.")
    parser.add_argument("--service-url", default="http://127.0.0.1:28085")
    parser.add_argument("--case-manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--api-key-env", default=DEFAULT_API_KEY_ENV)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument(
        "--monitoring-pointer",
        action="append",
        default=[],
        help="Redacted service log or monitoring pointer to retain in the summary.",
    )
    parser.add_argument(
        "--log-capture",
        action="append",
        default=[],
        help="Path to an already relevant service log capture; output is metadata-redacted.",
    )
    return parser.parse_args(argv)


def _api_key_from_args(args: argparse.Namespace) -> str:
    api_key_arg = args.api_key
    if isinstance(api_key_arg, str) and api_key_arg.strip() != "":
        return api_key_arg.strip()
    api_key_env = str(args.api_key_env)
    value = os.environ.get(api_key_env, "").strip()
    if value == "":
        raise SystemExit(f"Missing API key. Provide --api-key or set {api_key_env}.")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
