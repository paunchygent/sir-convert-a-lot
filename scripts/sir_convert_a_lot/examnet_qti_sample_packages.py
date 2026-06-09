"""Exam.net QTI sample package generator.

Purpose:
    Materialize governed deterministic QTI 2.1 sample packages and validation
    reports for Exam.net QTI proof gates.

Relationships:
    - Uses `domain.examnet_qti_samples` as the sample source.
    - Uses package planning and infrastructure writers without touching service
      routes, Skriptoteket UI, or Exam.net upload automation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.sir_convert_a_lot.domain.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from scripts.sir_convert_a_lot.domain.examnet_qti_samples import (
    ExamNetQtiSamplePackage,
    examnet_qti_keyed_samples,
    examnet_qti_manual_unkeyed_samples,
)
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    write_examnet_qti_artifacts,
)

DEFAULT_KEYED_OUTPUT_DIR = Path("inputs/examples/examnet-qti-samples/keyed")
DEFAULT_MANUAL_UNKEYED_OUTPUT_DIR = Path("inputs/examples/examnet-qti-samples/manual-unkeyed")


def main() -> int:
    """CLI entrypoint for deterministic keyed QTI sample generation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("keyed", "manual-unkeyed"),
        default="keyed",
        help="Governed QTI sample set to materialize.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory where sample package subdirectories should be written.",
    )
    args = parser.parse_args()

    output_dir = args.output_dir or _default_profile_output_dir(args.profile)
    summary = []
    for sample in _samples_for_profile(args.profile):
        sample_dir = output_dir / sample.name
        plan = build_examnet_qti_package_plan(package_name=sample.name, items=sample.items)
        artifacts = write_examnet_qti_artifacts(
            plan=plan,
            output_dir=sample_dir,
            package_filename=sample.package_filename,
            report_filename=sample.report_filename,
        )
        summary.append(
            {
                "name": sample.name,
                "package": str(artifacts.package_path) if artifacts.package_path else None,
                "report": str(artifacts.report_path),
                "status": str(artifacts.report.package_status),
                "examnet_proof_status": str(artifacts.report.examnet_proof_status),
            }
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _samples_for_profile(task: str) -> tuple[ExamNetQtiSamplePackage, ...]:
    if task == "manual-unkeyed":
        return examnet_qti_manual_unkeyed_samples()
    return examnet_qti_keyed_samples()


def _default_profile_output_dir(task: str) -> Path:
    if task == "manual-unkeyed":
        return DEFAULT_MANUAL_UNKEYED_OUTPUT_DIR
    return DEFAULT_KEYED_OUTPUT_DIR


if __name__ == "__main__":
    raise SystemExit(main())
