---
id: task-287-split-cli-route-submission-and-manifest-construction-responsibilities
title: Split CLI route submission and manifest construction responsibilities
type: task
status: completed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/tasks/task-285-introduce-service-v2-route-policy-handler-registry-before-exam-net-authoring-runtime.md
  - docs/backlog/tasks/task-35-cli-pivot-remote-only-routes-via-service-api-v2.md
labels:
  - cli
  - manifest
  - source-simplification
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Split CLI route submission, polling, and manifest construction out of
`scripts/sir_convert_a_lot/interfaces/cli_app.py` so the CLI entrypoint remains
a thin interface layer and future route additions do not enlarge the current
entrypoint.

## PR Scope

- Extract service-route submission/building behavior into bounded CLI
  application helpers or use cases.
- Extract deterministic manifest construction and writing behavior out of the
  Typer command definitions.
- Preserve existing command names, arguments, exit codes, manifest fields, and
  failure messages unless a governed docs update explicitly changes them.
- Keep future Exam.net authoring route preparation generic; do not implement
  `examnet_artifact -> teacher_authoring_bundle` CLI submission here.
- Keep local and remote service-route semantics aligned with the route registry
  from Task 285.

## Deliverables

- [x] CLI route submission helper/use case.
- [x] CLI manifest builder/writer helper/use case.
- [x] Focused CLI tests for existing route submission and manifest output.
- [x] Updated CLI documentation only where the source split changes
  discoverability.

## Acceptance Criteria

- [x] `cli_app.py` is reduced to interface wiring and command definitions for
  the touched routes.
- [x] Existing CLI snapshots or focused assertions prove manifest field names
  and values remain deterministic.
- [x] CLI behavior for existing production routes is unchanged.
- [x] New modules carry Google-style domain-purpose docstrings.
- [x] Close-out validation includes focused CLI tests plus the standard Python
  and docs gates required for backend changes.

## Implementation Notes

- Extracted CLI route submission/polling/artifact writing into
  `interfaces/cli_route_submission_v2.py`.
- Extracted deterministic manifest entry construction and persistence into
  `interfaces/cli_manifest_writer_v2.py`.
- Kept `interfaces/cli_app.py` as Typer wiring, route discovery, auth/retry
  option resolution, dry-run output, and final exit-code handling.
- Did not add `examnet_artifact -> teacher_authoring_bundle` CLI submission;
  that remains future runtime work under the Exam.net authoring contract.

## Module-Size Evidence

- `interfaces/cli_app.py`: 308 LoC.
- `interfaces/cli_route_submission_v2.py`: 446 LoC.
- `interfaces/cli_manifest_writer_v2.py`: 116 LoC.

## Validation Evidence

- `pdm run format-all` -> 687 files left unchanged after final fix.
- `pdm run lint-fix` -> All checks passed; docs validated as part of the
  command.
- `pdm run typecheck-all` -> Success: no issues found in 638 source files.
- Focused CLI tests:
  `pdm run pytest-root tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_cli_route_registry_and_dry_run.py tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py -q`
  -> 23 passed.
- Final `pdm run coverage-gate` -> 1152 passed, 5 skipped, total coverage
  96.95%.
- `pdm run docs-sync` -> generated docs indexes refreshed.
- `pdm run docs-validate` -> Validated 363 backlog files; Validated docs=422
  rules=11.
- `pdm run skills-validate` -> ok.
- `pdm run handoff-validate` -> ok.
- `git diff --check` -> clean.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
