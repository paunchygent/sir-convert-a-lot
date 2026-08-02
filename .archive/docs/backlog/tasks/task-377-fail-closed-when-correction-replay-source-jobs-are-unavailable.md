---
id: 'task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable'
title: 'Fail closed when correction replay source jobs are unavailable'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-30'
related:
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - correction-apply
  - replay
  - fail-closed
  - exam-migration
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Make source-bound correction apply fail closed when the source job referenced by
the signed source binding cannot be resolved.

The current correction apply route can skip replay artifact writing when
`source_bundle_id` lookup returns no job, then still return a successful apply
response. That is unsafe: a correction replay that cannot prove its source job
must not look successful to Skriptoteket or any other downstream consumer.

## PR Scope

- Route source-job lookup through the Task 375 replay/application service or a
  dedicated port owned by that service boundary.
- Treat missing, inaccessible, or incompatible source jobs referenced by a
  signed correction source binding as fail-closed correction apply errors.
- Return the standard Service API error envelope or typed domain error mapping;
  do not return HTTP 200 with missing replay artifacts.
- Preserve valid correction apply behavior when no replay artifacts are required
  by the source binding and contract.
- Update `exam-authoring-corrections-apply-contract.md` with the fail-closed
  behavior and reason code.
- Keep logs content-safe and avoid leaking source text, private paths, raw
  payloads, identity markers, or provider data.

## Closed Implementation Decisions

- Correction apply validates request schema, source-state digest, and
  source-state signature before source-job lookup. This preserves stale/forged
  binding behavior and prevents source-job probing.
- When a validated binding carries `source_bundle_id`, the application service
  must resolve and authorize that source job before returning any success that
  includes exportable target readiness, artifact availability, or replay
  references.
- A missing or expired source job returns
  `409 exam_authoring_correction_source_job_unavailable` through the standard
  Service API error envelope.
- Wrong owner or missing grant remains
  `403 exam_authoring_correction_replay_access_denied`.
- Success without source-job lookup is only allowed for a future explicitly
  non-artifact correction mode with no `source_bundle_id`, no exportable target
  rows, no available artifact availability, and no replay references. Current
  DigiExam correction apply must fail closed if the bound source job is gone.

## Out of Scope

- No browser or Skriptoteket fallback that treats a missing source job as a
  recoverable local draft state.
- No manual production repair of old correction replay artifacts.
- No request-scoped replay artifact storage migration; Task 378 owns artifact
  identity after this path fails closed.

## Deliverables

- [x] Source-job lookup fail-closed behavior in correction apply.
- [x] Typed reason code for missing or inaccessible correction replay source
  job.
- [x] Route/domain tests covering signed source-state issue followed by missing
  source job at apply time.
- [x] Contract docs update for the fail-closed branch.
- [x] Observability/logging assertions where existing test surfaces support
  them.

## Acceptance Criteria

- [x] A signed correction apply request whose `source_bundle_id` no longer
  resolves does not return HTTP 200.
- [x] The response uses the standard error envelope or accepted domain error
  mapping with a stable typed reason.
- [x] A missing source job returns
  `409 exam_authoring_correction_source_job_unavailable`; unauthorized
  source-job access remains
  `403 exam_authoring_correction_replay_access_denied`.
- [x] No replay artifact references are produced when the source job cannot be
  resolved.
- [x] No HTTP 200 response may advertise corrected target readiness, available
  artifact rows, or replay references without producer-backed source-job
  evidence.
- [x] Valid source-bound correction apply behavior remains unchanged when the
  source job exists and the source-state signature/digest is valid.
- [x] Tests prove source-state signature validation is still enforced before
  source-job fail-closed handling.

## Red-First Test Plan

- Add a failing route test using an issued source state whose source job is
  removed or cannot be found before correction apply; expected failure before
  the fix is HTTP 200 without replay artifacts.
- Add a control test for a valid source job that still returns replay artifacts.
- Add an authorization test proving a wrong-owner or missing-grant source job
  remains `403 exam_authoring_correction_replay_access_denied`.
- Add a negative test for stale or invalid source-state digest to prove the new
  fail-closed branch does not weaken existing signature checks.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py ...`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Task 377 is implemented and approved in retained independent Review 62 as of
2026-06-30. Correction apply
still validates request schema, canonical source-state digest, and signed
producer authority before source-job lookup. When the validated binding carries
`source_bundle_id`, the route now requires that source job to resolve through a
small application policy helper before any success response or replay artifact
projection. Missing or expired source jobs map to the standard Service API
error envelope with
`409 exam_authoring_correction_source_job_unavailable`; wrong-owner and
missing-grant source-job access keep
`403 exam_authoring_correction_replay_access_denied`.

The implementation adds:

- `scripts/sir_convert_a_lot/application/exam_authoring_correction_source_job_policy.py`
- `tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`

The existing synthetic advisory preservation fixture was narrowed to the
explicit non-artifact shape: no `source_bundle_id` and no requested targets.
Producer-backed advisory preservation remains covered through the source-state
issuer path. Legacy synthetic correction apply fixtures were also narrowed to
that non-artifact shape so they no longer fake producer-backed source jobs.
Task 377 does not implement request-scoped replay artifact-set identity,
artifact-set download routes, duplicate request conflict handling, or Task 378
storage layout.

### Red Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py -q`
  failed before the production fix with `1 failed, 3 passed`: the missing
  source-job test received `200 OK` instead of
  `409 exam_authoring_correction_source_job_unavailable`.
- Review 62 remediation red:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py::test_correction_apply_missing_grant_source_job_remains_access_denied -q`
  failed before the remediation with `1 failed`: same-owner correction apply
  without `sir-convert:artifacts:read-own` returned
  `auth_missing_internal_identity_grant` instead of
  `exam_authoring_correction_replay_access_denied`.

### Green Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py -q`
  passed before Review 62 remediation: `4 passed, 1 warning`.
- Review 62 remediation node:
  `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py::test_correction_apply_missing_grant_source_job_remains_access_denied -q`
  passed: `1 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py -q`
  passed after Review 62 remediation: `36 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/interfaces/http_auth_v2.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`
  passed: `3 files already formatted`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/interfaces/http_auth_v2.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`
  passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/application/exam_authoring_correction_source_job_policy.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
  passed before Review 62 remediation: `7 files already formatted`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/application/exam_authoring_correction_source_job_policy.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
  passed before Review 62 remediation: `All checks passed!`.
- `/opt/homebrew/bin/pdm run coverage-gate` passed:
  `1784 passed, 6 skipped, 1 warning`, coverage `95.54%`.

### Skipped Or Blocked Validation

- `/opt/homebrew/bin/pdm run typecheck-all` was rerun and still fails on the
  nine pre-existing test-helper `no-any-return` errors documented in Reviews
  60 and 61. No Task 377 production or test file is reported.
- Full `format-all` and `lint-fix` were not run to avoid normalizing unrelated
  dirty worktree files from approved Tasks 375-376. Targeted ruff
  format/check passed over every Task 377 production and test file.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
