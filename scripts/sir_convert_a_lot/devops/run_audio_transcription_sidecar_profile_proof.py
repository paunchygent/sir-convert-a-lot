"""Run the audio transcription sidecar profile-proof command.

Purpose:
    Produce content-safe speech-to-text sidecar profile-proof artifacts from
    deterministic projection evidence or sanitized live Hemma observations.

Relationships:
    - Orchestrates the STT profile-proof contracts and report builder.
    - Provides the PDM command surface for local projection checks and Hemma
      live-proof observation ingestion.
    - Does not import STT, diarization, Hugging Face, FFmpeg, or sidecar
      runtime libraries into the main service path.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_live_observations import (
    LIVE_OBSERVATION_SCHEMA_VERSION,
    build_blocked_live_profile_proof_evidence,
    build_live_profile_proof_evidence_from_observation,
    build_projection_profile_proof_evidence,
    read_live_observation_mapping,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_contracts import (
    AudioTranscriptionSidecarProfileProofEvidence,
)
from scripts.sir_convert_a_lot.devops.audio_transcription_sidecar_profile_proof import (
    build_live_profile_proof_report,
    write_live_profile_proof_report,
)

DEFAULT_OUTPUT_ROOT = Path("build/verification/stt-sidecar-profile-proof")


def main(argv: list[str] | None = None) -> int:
    """Run profile-proof reporting and return an operator-facing exit code."""

    args = _build_parser().parse_args(argv)
    if args.mode == "projection":
        evidence = build_projection_profile_proof_evidence()
        blocked_exit_code = 2 if bool(args.fail_on_blocked) else 0
    else:
        evidence = _live_evidence_from_args(args)
        blocked_exit_code = 2

    report = build_live_profile_proof_report(evidence)
    json_path, markdown_path = write_live_profile_proof_report(
        report,
        output_root=Path(args.output_root),
    )
    print(json_path.as_posix())
    print(markdown_path.as_posix())
    if report["proof_ready"]:
        return 0
    return blocked_exit_code


def _build_parser() -> argparse.ArgumentParser:
    """Build the STT sidecar profile-proof command-line parser."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("projection", "live"),
        default="projection",
        help="Use deterministic local projection evidence or sanitized live Hemma observations.",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--live-observation-json",
        type=Path,
        help="Sanitized observation JSON produced by the benchmark-only STT sidecar.",
    )
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="Return exit code 2 for blocked projection reports.",
    )
    return parser


def _live_evidence_from_args(
    args: argparse.Namespace,
) -> AudioTranscriptionSidecarProfileProofEvidence:
    """Return live evidence from a sanitized observation JSON path."""

    observation_path = args.live_observation_json
    if observation_path is None:
        return build_blocked_live_profile_proof_evidence("live_observation_missing")
    path = Path(observation_path)
    if not path.is_file():
        return build_blocked_live_profile_proof_evidence("live_observation_missing")
    try:
        payload = read_live_observation_mapping(path)
    except ValueError:
        return build_blocked_live_profile_proof_evidence("live_observation_invalid")
    schema_version = payload.get("schema_version")
    if schema_version != LIVE_OBSERVATION_SCHEMA_VERSION:
        return build_blocked_live_profile_proof_evidence("live_observation_schema_invalid")
    return build_live_profile_proof_evidence_from_observation(payload)


if __name__ == "__main__":
    raise SystemExit(main())
