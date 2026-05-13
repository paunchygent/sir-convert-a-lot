"""Task 280 Exam.net QTI sample package generator.

Purpose:
    Materialize the governed deterministic QTI 2.1 sample packages and
    validation reports used as the first Exam.net QTI proof gate.

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
    examnet_qti_task_280_samples,
)
from scripts.sir_convert_a_lot.infrastructure.examnet_qti_package_writer import (
    write_examnet_qti_artifacts,
)

DEFAULT_OUTPUT_DIR = Path("inputs/examples/examnet-qti-samples/task-280")


def main() -> int:
    """CLI entrypoint for deterministic Task 280 sample generation."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where sample package subdirectories should be written.",
    )
    args = parser.parse_args()

    summary = []
    for sample in examnet_qti_task_280_samples():
        sample_dir = args.output_dir / sample.name
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


if __name__ == "__main__":
    raise SystemExit(main())
