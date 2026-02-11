---
id: fix-01-harden-cli-timeout-handling-for-long-running-background-jobs
title: Harden CLI timeout handling for long-running background jobs
type: fix
status: completed
priority: critical
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/converters/sir_convert_a_lot.md
  - scripts/sir_convert_a_lot/interfaces/cli_app.py
  - tests/sir_convert_a_lot/test_convert_a_lot_cli.py
labels:
  - cli
  - reliability
  - background-jobs
---

Focused correction of a known issue.

## Context

CLI used synchronous submit+poll flow and treated `job_timeout` as terminal failure, even though
jobs can continue running server-side.

## Objective

Harden CLI behavior so timeout on poll is treated as "submitted and still running" for background
completion workflows.

## Scope

- Update CLI timeout handling for `ClientError(code="job_timeout")`.
- Add regression test coverage for timeout -> running manifest behavior.
- Update user-facing docs for long-running job semantics.

## Acceptance Criteria

- [x] CLI records timed-out jobs as `status: running` with `job_id`.
- [x] CLI does not exit with failure solely due to `job_timeout`.
- [x] Manifest remains deterministic and includes `error_code: job_timeout`.
- [x] Docs describe background completion semantics.

## Validation

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run mypy --config-file pyproject.toml --no-incremental`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_convert_a_lot_cli.py`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Implementation Notes

- `scripts/sir_convert_a_lot/interfaces/cli_app.py` now maps
  `ClientError(code="job_timeout", job_id=<id>)` to manifest `status: running`.
- Manifest behavior remains deterministic; timeout entries preserve `job_id` and
  `error_code: job_timeout` for later status/result retrieval.
- `tests/sir_convert_a_lot/test_convert_a_lot_cli.py` includes a dedicated
  timeout regression test that verifies CLI success exit code for timeout-only runs.

## Validation Results

- `pdm run run-local-pdm format-all` (pass)
- `pdm run run-local-pdm lint-fix` (pass)
- `pdm run mypy --config-file pyproject.toml --no-incremental` (pass)
- `pdm run run-local-pdm typecheck-all --no-incremental` (pass)
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot` (pass)
- `pdm run run-local-pdm validate-tasks` (pass)
- `pdm run run-local-pdm validate-docs` (pass)
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Root cause documented
- [x] Fix implemented
- [x] Regression checks passed
