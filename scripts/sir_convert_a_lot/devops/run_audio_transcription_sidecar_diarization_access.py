"""Run the audio transcription sidecar diarization access diagnostic.

Purpose:
    Produce a content-safe JSON report describing whether the operator
    Hugging Face token can access the gated pyannote artifact used by the STT
    sidecar diarization profile.

Relationships:
    - Provides the `diagnose:stt-sidecar-diarization-access` PDM command.
    - Uses the same operator environment loading pattern as the live STT
      observation runner.
    - Does not execute transcription, diarization, route registration, or
      transcript artifact persistence.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Mapping
from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_diarization_access import (
    DEFAULT_OUTPUT_ROOT,
    DEFAULT_PYANNOTE_ARTIFACT_FILENAME,
    DEFAULT_PYANNOTE_DIARIZATION_REPO_ID,
    DEFAULT_TOKEN_ENV_VAR_NAME,
    DiarizationModelAccessSettings,
    HubModelAccessClient,
    HuggingFaceHubModelAccessClient,
    build_diarization_model_access_report,
    write_diarization_model_access_report,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_operator_environment import (
    merged_operator_environment,
)


def main(
    argv: list[str] | None = None,
    *,
    environment: Mapping[str, str] | None = None,
    client: HubModelAccessClient | None = None,
) -> int:
    """Run the diarization access diagnostic and return an operator exit code."""

    args = _build_parser().parse_args(argv)
    env = (
        merged_operator_environment(os.environ, env_file=Path(args.env_file))
        if environment is None
        else dict(environment)
    )
    settings = DiarizationModelAccessSettings(
        output_root=Path(args.output_root),
        repo_id=str(args.repo_id),
        artifact_filename=str(args.artifact_filename),
        token_env_var_name=str(args.token_env_var_name),
    )
    report = build_diarization_model_access_report(
        settings=settings,
        client=client or HuggingFaceHubModelAccessClient(),
        environment=env,
    )
    output_path = write_diarization_model_access_report(
        report,
        output_root=settings.output_root,
    )
    print(output_path.as_posix())
    return 0 if report["status"] == "ready" else 2


def _build_parser() -> argparse.ArgumentParser:
    """Build the diarization access diagnostic parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--repo-id", default=DEFAULT_PYANNOTE_DIARIZATION_REPO_ID)
    parser.add_argument("--artifact-filename", default=DEFAULT_PYANNOTE_ARTIFACT_FILENAME)
    parser.add_argument("--token-env-var-name", default=DEFAULT_TOKEN_ENV_VAR_NAME)
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
