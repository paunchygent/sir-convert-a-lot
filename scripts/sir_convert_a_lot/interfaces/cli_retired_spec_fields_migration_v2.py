"""Run the one-time stored job-spec migration for the Sir exam retirement.

Purpose:
    Provide the operator command that must run against a stopped Sir service
    data root before the post-retirement runtime serves it. The default is a
    dry run; `--execute` rewrites manifests. The JSON report prints to stdout.

    Exit codes: 0 when the data root is current or was rewritten, 1 when a dry
    run found manifests that still need rewriting, 2 when exam jobs, invalid
    manifests, or live idempotency records block the migration.

Relationships:
    - Wraps `infrastructure.retired_spec_fields_migration_v2`.
    - Required pre-start step in the Sir Hemma service operations runbook.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from scripts.sir_convert_a_lot.infrastructure.retired_spec_fields_migration_v2 import (
    migrate_retired_spec_fields,
)
from scripts.sir_convert_a_lot.infrastructure.runtime_models import ServiceConfig

EXIT_CURRENT = 0
EXIT_REWRITE_REQUIRED = 1
EXIT_BLOCKED = 2


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate stored v2 job specs across the Sir exam retirement."
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        required=True,
        help="Service data root that holds jobs_v2/ and idempotency/.",
    )
    parser.add_argument(
        "--idempotency-ttl-seconds",
        type=int,
        default=ServiceConfig.idempotency_ttl_seconds,
        help="Idempotency replay window of the service that wrote the records.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Rewrite manifests. Without it the command only reports.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the migration and print its JSON report."""
    args = _parse_args(argv)
    report = migrate_retired_spec_fields(
        data_root=Path(args.data_root),
        idempotency_ttl_seconds=int(args.idempotency_ttl_seconds),
        execute=bool(args.execute),
    )
    print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    if report.blocked:
        return EXIT_BLOCKED
    if report.outcome == "rewrite_required":
        return EXIT_REWRITE_REQUIRED
    return EXIT_CURRENT


if __name__ == "__main__":
    raise SystemExit(main())
