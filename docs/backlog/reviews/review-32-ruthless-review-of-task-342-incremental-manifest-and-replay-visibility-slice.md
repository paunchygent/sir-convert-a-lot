---
id: 'review-32-ruthless-review-of-task-342-incremental-manifest-and-replay-visibility-slice'
title: 'Ruthless review of Task 342 incremental manifest and replay visibility slice'
type: 'review'
status: 'completed'
priority: 'high'
created: '2026-06-10'
last_updated: '2026-06-10'
related:
  - docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md
  - docs/converters/sir_convert_a_lot.md
labels:
  - review
  - approved
  - task-342
  - cli
  - manifest
  - progress
  - idempotency
---
Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless implementation review of the Task 342 incremental
  manifest and replay visibility slice.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md`
  - `docs/converters/sir_convert_a_lot.md`
- Files reviewed:
  - `scripts/sir_convert_a_lot/interfaces/cli_incremental_manifest_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_route_submission_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_manifest_writer_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_progress_messages_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_client_v2_conversion.py`
  - `scripts/sir_convert_a_lot/interfaces/cli_app.py`
  - `tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py`
  - `tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py`
  - `docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md`
  - `docs/converters/sir_convert_a_lot.md`
  - `.codex/handoff.md`
- Scope exclusions:
  - Unrelated STT Task 352 live-observation worktree files.
  - DeepSeek implementation or OCR candidate promotion.
  - Submit-ahead queueing, new status/recover command, or service idempotency
    semantic changes.

## Findings

### Resolved: Fresh running submissions were not emitted as submitted lines

Severity: high.

Initial review found that fresh jobs returned from `POST /v2/convert/jobs` as
`running` without a `progress` object were recorded in the incremental manifest
but did not emit the immediate submitted CLI line. That violated Task 342's
operator-visibility requirement because a normal fresh-running submit response
could still look silent until later polling or terminal output.

Resolution:

- `scripts/sir_convert_a_lot/interfaces/cli_progress_messages_v2.py` now routes
  running/no-progress submission payloads through the submitted-message
  formatter for both fresh jobs and idempotent replays.
- `tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py` covers
  fresh-running CLI output.
- `tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py` covers the fresh
  running submit callback payload.

Second review pass found no remaining issues.

## Decision

Approved.

## Response

The Task 342 incremental manifest/replay visibility slice is accepted.

The accepted behavior:

- v2 client reports an immediate submission progress callback after job
  creation, including idempotent replay state.
- CLI emits submitted/replayed lines for queued/running/terminal submission
  responses.
- CLI writes `sir_convert_a_lot_manifest.json` incrementally when a non-terminal
  job id is observed and atomically replaces entries on terminal outcomes.
- `KeyboardInterrupt` after job-id observation preserves a running manifest
  entry with `error_code: client_interrupted`.
- DeepSeek remains out of scope and governed follow-up only.

## Follow-up Actions

1. Continue Task 342 with first-class status/recovery UX for existing manifests
   or job ids.
1. Add richer safe idempotency/request diagnostics in a later governed slice.

## Completion

- First review pass: `changes_requested`.
- Second review pass: `approved`.
- Reviewer: separate overseer-loop subagent `Zeno`.
- Validation evidence:
  - `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_convert_upload_to_artifact_reports_submitted_replay_to_progress_callback tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_convert_upload_to_artifact_reports_fresh_running_submit_to_progress_callback`
    -> `8 passed`.
  - `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_api_contract_v2_pdf_to_md_and_v1_absence.py::test_pdf_to_md_lifecycle_result_and_artifact`
    -> `15 passed`.
  - Focused `ruff check` passed.
  - Focused mypy passed.
  - `pdm run docs-sync`, `pdm run docs-validate`,
    `pdm run skills-validate`, `pdm run handoff-validate`,
    `pdm run typecheck-all`, and `git diff --check` passed; docs and handoff
    validators were rerun after this review artifact was persisted.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
