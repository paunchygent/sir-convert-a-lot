"""Run the Hemma STT sidecar benchmark preflight.

Purpose:
    Record content-safe readiness evidence for the current Hemma speech-to-text
    benchmark environment.

Relationships:
    - Wraps `devops.audio_transcription_sidecar_benchmark` for CLI use.
    - Uses the `pdm run run-hemma -- pdm run benchmark:stt-sidecar-preflight`
      operator lane.
    - Writes preflight reports under `build/verification/` for sidecar
      readiness evidence; transcript execution is governed by the runtime
      audio route.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_benchmark import (
    DEFAULT_HF_HOME,
    DEFAULT_HF_HUB_CACHE,
    DEFAULT_OUTPUT_ROOT,
    REQUIRED_SECRET_ENV_VARS,
    BenchmarkPreflightSettings,
    build_preflight_report,
    write_preflight_report,
)


def main(argv: list[str] | None = None) -> int:
    """Run the STT benchmark preflight and write report artifacts."""

    args = _build_parser().parse_args(argv)
    settings = BenchmarkPreflightSettings(
        output_root=Path(args.output_root),
        hf_home=Path(args.hf_home),
        hf_hub_cache=Path(args.hf_hub_cache),
        secret_env_var_names=tuple(args.secret_env_var),
        environment=dict(os.environ),
    )
    report = build_preflight_report(settings=settings)
    report_json_path, report_markdown_path = write_preflight_report(
        report,
        output_root=settings.output_root,
    )
    print(report_json_path.as_posix())
    print(report_markdown_path.as_posix())
    if bool(args.fail_on_blocked) and not report["preflight_ready"]:
        return 2
    return 0


def _build_parser() -> argparse.ArgumentParser:
    """Build the STT sidecar benchmark preflight command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--hf-home", type=Path, default=DEFAULT_HF_HOME)
    parser.add_argument("--hf-hub-cache", type=Path, default=DEFAULT_HF_HUB_CACHE)
    parser.add_argument(
        "--secret-env-var",
        action="append",
        default=list(REQUIRED_SECRET_ENV_VARS),
        help=(
            "Required secret environment variable name. Values are never written "
            "to reports. May be repeated."
        ),
    )
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="Return exit code 2 when preflight blockers remain.",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
