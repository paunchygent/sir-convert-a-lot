---
id: task-369-remove-cli-auto-rerun-wrappers-after-service-api-v2-owns-retryable-reattempts
title: Remove CLI auto-rerun wrappers after Service API v2 owns retryable reattempts
type: task
status: in_progress
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-63-cli-auto-rerun-on-idempotent-failed-replays.md
  - docs/backlog/tasks/task-342-harden-batch-cli-live-progress-and-idempotent-replay-visibility-for-long-conversions.md
  - docs/converters/sir_convert_a_lot.md
  - docs/converters/multi_format_conversion_service_api_v2.md
  - docs/converters/downstream_integration_contract_v2.md
labels:
  - cli
  - v2
  - idempotency
  - service-boundary
  - cleanup
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove the historical CLI-side auto-rerun wrapper introduced by Task 63 after
Task 368 makes retryable-failed idempotency reattempts a central Service API v2
responsibility.

This is intentionally slotted immediately after Task 368. The codebase must not
preserve a compatibility wrapper that teaches future agents that failed-replay
recovery belongs in callers. All Sir Convert callers, including the CLI, must
align with the service-owned idempotency state machine.

## PR Scope

- Require Task 368 to be completed, reviewed, deployed, and live-proved before
  implementation starts.
- Remove client-side logic that detects a terminal failed/canceled idempotent
  replay and submits a second create-job request with a new idempotency key.
- Remove or simplify CLI flags and internal retry-mode types that exist only to
  support the old failed-replay workaround.
- Preserve explicit "start an independent new conversion" behavior only if it
  is already separate from failed-replay recovery and remains clearly
  documented as user intent, not remediation. If that distinction cannot be
  made cleanly, remove the flag and create a separate CLI UX task.
- Keep CLI progress, manifest, idempotent replay visibility, status polling,
  and artifact download behavior intact.
- Update CLI docs so they point to the Task 368 service-owned replay policy and
  no longer instruct users or agents to solve retryable failed replays with
  client-side key salting.
- Do not change Service API v2 behavior in this task. Any discovered service
  contract gap must return to Task 368 or a new service-boundary task.

## Deliverables

- [x] Red-first CLI/client test proving the current DDD violation: the CLI
  performs a second client-side create-job request after a terminal failed
  idempotent replay.
- [x] Removal of client-owned failed-replay auto-rerun logic from the v2 HTTP
  client and CLI command path.
- [x] Simplified CLI option/help text and docs with no `replay-only` workaround
  language and no failed-replay compatibility mode.
- [x] Updated tests proving the CLI submits once and accepts the service-owned
  response, including Task 368 reattempt metadata when present.
- [x] Independent retained review focused on removal completeness, no hidden
  compatibility shim, and preserved CLI progress/artifact behavior.
- [ ] Hemma live CLI proof after deploy showing the CLI does not issue a
  caller-side reattempt and still succeeds through the service-owned
  Task 368 policy.

## Acceptance Criteria

- [x] The CLI and v2 HTTP client no longer synthesize a new idempotency key
  because a replayed job is terminal failed or canceled.
- [x] No remaining public docs describe CLI auto-rerun of terminal failed or
  canceled idempotent replays as accepted behavior.
- [x] Tests prove the CLI handles service responses for:
  - strict replay of active/succeeded/non-retryable failed jobs;
  - service-owned reattempt after retryable failed replay;
  - explicit independent-new-job user intent only if that behavior remains in
    scope.
- [x] Any retained "new job" affordance is named and documented as a deliberate
  independent conversion request, not as retry remediation.
- [x] CLI manifests remain truthful: they must record the job actually returned
  by the service and must not hide a second caller-side POST.
- [x] Red/green evidence includes the same focused command failing before the
  removal and passing after it.
- [ ] Close-out includes live Hemma evidence:
  - deployed service revision includes Task 368;
  - deployed CLI revision includes this task;
  - a same-payload retryable-failed idempotency scenario is exercised without
    manual pointer deletion or filename/key mutation;
  - captured CLI/service evidence shows one create-job submission from the CLI
    invocation;
  - the service admits or reuses the Task 368-governed active attempt and the
    job reaches `succeeded`;
  - bounded logs show no CLI-side second-submit compatibility path in the proof
    interval.

## Red-First Test Plan

First failing proof:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_cli_does_not_client_side_rerun_retryable_failed_replay -q
```

The test must fail on current code because the Task 63 behavior still performs
client-side auto-rerun for terminal failed/canceled idempotent replays.

Green focused proof should include:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py -q
```

Broader close-out gates:

```bash
pdm run format-all
pdm run lint-fix
pdm run typecheck-all
pdm run coverage-gate
pdm run docs-sync
pdm run docs-validate
pdm run skills-validate
pdm run handoff-validate
git diff --check
```

## Live Verification Gate

Before this task can be marked completed, run a retained Hemma CLI proof against
the deployed Task 368 service. The proof must use the same logical payload/spec
after a retained retryable failed attempt and must not depend on filename
changes, caller-side idempotency-key salting, or manual idempotency-store
cleanup.

Required evidence bundle:

- deployed Task 368 service revision and deployed CLI revision;
- CLI invocation transcript or manifest proving one create-job submission for
  the command;
- service-side job lineage proving the new attempt came from Task 368 policy,
  not from a CLI-generated alternate key;
- terminal success manifest and artifact fetch proof;
- bounded log scan for the proof interval.

## Implementation Evidence

Corrected implementation worker evidence only; review, deploy, and live proof
remain for the overseer loop.

- Red-first evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_cli_does_not_client_side_rerun_retryable_failed_replay -q`
  failed before production edits with `Failed: DID NOT RAISE ClientErrorV2`, proving the old client performed a caller-side second submit
  after the terminal failed replay.
- Green same-node evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py::test_cli_does_not_client_side_rerun_retryable_failed_replay -q`
  passed after removing the Task 63 compatibility path.
- Focused green evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py -q`
  passed with `17 passed`.
- Manifest-focused evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py -q`
  passed with `6 passed`.
- Removal/source-search evidence:
  code and active tests no longer contain `replay_only`, `--replay-only`,
  `_rerun_`, or `rerun_of_job_id`.
- Broad local gates:
  `pdm run typecheck-all`, `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `pdm run coverage-gate` passed. `coverage-gate` passed with
  `1748 passed, 6 skipped`; total coverage `95.53%`.
- Skipped gates:
  whole-repo mutating `pdm run format-all` and `pdm run lint-fix` were not run
  in this corrected worker pass because the worktree contains unrelated Task
  367 and Task 370/Qwen changes. Check-only `pdm run lint` found no Python
  issues but failed on pre-existing Markdown formatting drift in Task 368 docs.
  `git diff --check` is run after recording this evidence.

## Review Evidence

- Retained review:
  `docs/backlog/reviews/review-54-ruthless-review-of-task-369-remove-cli-auto-rerun-wrappers.md`
- Decision: approved.
- Reviewer-run evidence:
  `pdm run pytest-root tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py tests/sir_convert_a_lot/test_cli_v2_routes.py tests/sir_convert_a_lot/test_convert_a_lot_cli.py -q`
  passed with `17 passed`;
  `pdm run pytest-root tests/sir_convert_a_lot/test_cli_route_submission_and_manifest_v2.py -q`
  passed with `6 passed`; `docs-sync`, `docs-validate`,
  `skills-validate`, `handoff-validate`, and scoped `git diff --check`
  passed.
- Review scope explicitly approved removal of the failed-replay client
  second-submit path, removal of `--replay-only`, retained `--new-job` as
  independent user intent only, and manifest truth around the service-returned
  job.

## Stop Conditions

- Stop if Task 368 has not been completed, reviewed, deployed, and live-proved.
- Stop before preserving a compatibility shim whose only purpose is
  failed-replay remediation outside the service boundary.
- Stop before changing Service API v2 semantics; this task is CLI/client
  cleanup only.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
