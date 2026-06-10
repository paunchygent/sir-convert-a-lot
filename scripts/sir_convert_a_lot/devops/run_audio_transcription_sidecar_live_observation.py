"""Run the audio transcription sidecar live-observation producer.

Purpose:
    Generate the sanitized Hemma live-observation JSON consumed by the STT
    profile-proof ingestion runner.

Relationships:
    - Provides the `benchmark:stt-sidecar-live-observation` PDM command.
    - Uses the benchmark-only STT sidecar runtime for Docker mode.
    - Does not register `audio -> transcript_bundle` or persist transcript
      artifacts.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_cache import (
    DEFAULT_HF_CACHE_HOME_MOUNT,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_commands import (
    CommandRunner,
    SubprocessCommandRunner,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observation_runtime import (
    DEFAULT_DOCKERFILE_PATH,
    DEFAULT_HF_HOME,
    DEFAULT_IMAGE_TAG,
    DEFAULT_OUTPUT_ROOT,
    LiveObservationSettings,
    build_live_observation,
    write_live_observation,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_operator_environment import (
    merged_operator_environment,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_proof import (
    REQUIRED_SIDECAR_IMAGE_NAME,
)


def main(
    argv: list[str] | None = None,
    *,
    command_runner: CommandRunner | None = None,
    environment: Mapping[str, str] | None = None,
) -> int:
    """Run live observation production and return an operator exit code."""

    args = _build_parser().parse_args(argv)
    env = (
        merged_operator_environment(os.environ, env_file=Path(args.env_file))
        if environment is None
        else dict(environment)
    )
    hf_home = Path(args.hf_home) if args.hf_home is not None else _default_hf_home(env)
    hf_hub_cache = (
        Path(args.hf_hub_cache)
        if args.hf_hub_cache is not None
        else _default_hf_hub_cache(env, hf_home)
    )
    settings = LiveObservationSettings(
        output_root=Path(args.output_root),
        runtime_mode=args.runtime_mode,
        english_fixture=Path(args.english_fixture),
        swedish_fixture=Path(args.swedish_fixture),
        sidecar_launch_observed=bool(args.sidecar_launch_observed),
        dockerfile_path=Path(args.dockerfile_path),
        image_name=str(args.image_name),
        image_tag=str(args.image_tag),
        hf_home=hf_home,
        hf_hub_cache=hf_hub_cache,
        hf_cache_home_mount=Path(args.hf_cache_home_mount),
        english_speakers=int(args.english_speakers),
        swedish_speakers=int(args.swedish_speakers),
        min_speakers=int(args.min_speakers),
        max_speakers=int(args.max_speakers),
        runtime_timeout_seconds=float(args.runtime_timeout_seconds),
        ffprobe_timeout_seconds=float(args.ffprobe_timeout_seconds),
    )
    runner = command_runner or SubprocessCommandRunner()
    observation = build_live_observation(
        settings=settings,
        command_runner=runner,
        environment=env,
    )
    output_path = write_live_observation(observation, output_root=settings.output_root)
    print(output_path.as_posix())
    return _observation_exit_code(observation)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-mode", choices=("host", "docker"), default="docker")
    parser.add_argument("--english-fixture", type=Path, required=True)
    parser.add_argument("--swedish-fixture", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--sidecar-launch-observed", action="store_true")
    parser.add_argument("--dockerfile-path", type=Path, default=DEFAULT_DOCKERFILE_PATH)
    parser.add_argument("--image-name", default=REQUIRED_SIDECAR_IMAGE_NAME)
    parser.add_argument("--image-tag", default=DEFAULT_IMAGE_TAG)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--hf-home", type=Path, default=None)
    parser.add_argument("--hf-hub-cache", type=Path, default=None)
    parser.add_argument("--hf-cache-home-mount", type=Path, default=DEFAULT_HF_CACHE_HOME_MOUNT)
    parser.add_argument("--english-speakers", type=int, default=2)
    parser.add_argument("--swedish-speakers", type=int, default=1)
    parser.add_argument("--min-speakers", type=int, default=1)
    parser.add_argument("--max-speakers", type=int, default=3)
    parser.add_argument("--runtime-timeout-seconds", type=float, default=3600.0)
    parser.add_argument("--ffprobe-timeout-seconds", type=float, default=30.0)
    return parser


def _default_hf_home(environment: Mapping[str, str]) -> Path:
    value = environment.get("HF_HOME", "").strip()
    return Path(value) if value else DEFAULT_HF_HOME


def _default_hf_hub_cache(environment: Mapping[str, str], hf_home: Path) -> Path:
    value = environment.get("HF_HUB_CACHE", "").strip()
    return Path(value) if value else hf_home / "hub"


def _observation_exit_code(observation: Mapping[str, object]) -> int:
    reasons = observation.get("observation_failure_reasons")
    if isinstance(reasons, list) and len(reasons) == 0:
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
