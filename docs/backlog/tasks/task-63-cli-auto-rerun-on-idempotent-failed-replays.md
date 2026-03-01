---
id: task-63-cli-auto-rerun-on-idempotent-failed-replays
title: CLI auto-rerun on idempotent failed replays
type: task
status: completed
priority: high
created: '2026-03-01'
last_updated: '2026-03-01'
related:
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - cli
  - v2
  - ux
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make reruns after fixes feel obvious and safe:

- Default `convert-a-lot convert` should not require filename hacks to rerun after a previously failed
  idempotent replay.
- Preserve strict service idempotency semantics (no server behavior changes).

## PR Scope

- Extend v2 client submit surface to expose `X-Idempotent-Replay` state.
- Add a v2 client retry mode that:
  - defaults to auto-rerun only when the server indicates an idempotent replay and the replayed job is
    terminal `failed` or `canceled`,
  - does not auto-rerun for non-replayed jobs that fail (real failures stay failures),
  - is bounded (no unbounded retry loops).
- Add CLI UX controls:
  - `--replay-only`: never auto-rerun; strict replay behavior.
  - `--new-job`: always submit with a new idempotency key.
- Update CLI docs to describe retry modes and the reasons for them.
- Add tests that lock the behavior to prevent regressions.

## Deliverables

- [x] `convert-a-lot convert` auto-reruns when it replays a terminal failed/canceled job.
- [x] `--replay-only` and `--new-job` are available and mutually exclusive.
- [x] Tests cover auto-rerun vs strict replay behavior.

## Acceptance Criteria

- [x] Default CLI behavior:
  - running the same command twice after a previously failed replay results in a new job submission
    (no filename hacks required).
- [x] Flags:
  - `--replay-only` preserves deterministic replay semantics.
  - `--new-job` forces a new submission even when a prior job succeeded.
- [x] Quality gates:
  - `pdm run run-local-pdm typecheck-all` passes.
  - `pdm run run-local-pdm coverage-gate` remains >=90%.
  - `pdm run run-local-pdm validate-tasks` and `validate-docs` pass.

## Validation Commands

- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
- `pdm run run-local-pdm coverage-gate`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`

## Validation Evidence

- [x] Lint:
  - `pdm run run-local-pdm lint-fix` (pass, 2026-03-01).
- [x] Type safety:
  - `pdm run run-local-pdm typecheck-all`
    (pass: `Success: no issues found in 158 source files`, 2026-03-01).
- [x] Targeted tests:
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
    (pass: `15 passed`, 2026-03-01).
- [x] Full coverage gate:
  - `pdm run run-local-pdm coverage-gate`
    (pass: `397 passed, 5 skipped`; total coverage `95.24%`, 2026-03-01).
- [x] Docs gates:
  - `pdm run run-local-pdm validate-tasks` (pass: `Validated 88 backlog files`).
  - `pdm run run-local-pdm validate-docs` (pass: `Validated docs=110 rules=9`).

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
