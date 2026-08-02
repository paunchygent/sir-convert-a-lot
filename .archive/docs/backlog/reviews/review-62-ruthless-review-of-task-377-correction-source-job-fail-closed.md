---
id: review-62-ruthless-review-of-task-377-correction-source-job-fail-closed
title: Ruthless review of Task 377 correction source-job fail-closed behavior
type: review
status: completed
priority: high
created: '2026-06-30'
last_updated: '2026-06-30'
related:
  - docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md
  - docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md
  - docs/backlog/reviews/review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility.md
  - docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md
  - docs/backlog/reviews/review-59-ruthless-review-of-task-374-advisory-candidate-replay.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - review
  - approved
  - task-377
  - correction-apply
  - replay
  - fail-closed
---

Retained independent review for Task 377. This reviewer did not author the
implementation or tests, did not deploy, did not commit, and did not modify
production or test implementation files. The only intentional Sir Convert
mutation from this review pass is this retained review artifact plus generated
docs index updates from validation.

## Review Scope

Authorities and instructions read:

- `AGENTS.md`
- `.codex/handoff.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/ruthless-code-review/references/forbidden-patterns.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/testing/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/SKILL.md`
- `/Users/olofs_mba/Documents/Repos/skill-repository/skills/agent-docs-governance/references/sir-convert-a-lot.md`
- `.codex/rules/000-rule-index.md`
- `.codex/rules/010-foundational-principles.md`
- `.codex/rules/030-conversion-workflows.md`
- `.codex/rules/070-testing-and-quality-gates.md`
- `.codex/rules/090-documentation-standards.md`
- `docs/index.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md`
- `docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md`
- `docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md`
- `docs/backlog/reviews/review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility.md`
- `docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md`
- `docs/backlog/reviews/review-59-ruthless-review-of-task-374-advisory-candidate-replay.md`

Reviewed Task 377 surfaces:

- `.codex/handoff.md`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `scripts/sir_convert_a_lot/application/exam_authoring_correction_source_job_policy.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_auth_v2.py`
- `tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`
- `tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py`
- `tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py`
- `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py`
- `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
- Task 374 advisory replay preservation tests listed under verification.

Public/runtime surfaces affected:

- `POST /v2/exam-authoring/corrections/apply`
- `POST /v2/exam-authoring/corrections/source-state/issue` only as source-state
  provenance setup for the apply path.
- Source-state digest/signature validation ordering.
- Correction replay source-job lookup, ownership/grant authorization, and
  public error envelope codes.

Out-of-scope worktree dirtiness observed but not approved:

- `docker/service-deps/service-dependency-inputs-cpu.json`
- `docker/service-deps/service-dependency-inputs-rocm.json`
- `docker/service-deps/service-requirements.txt`
- `pdm.lock`
- Task 375 and Task 376 code/docs/review artifacts beyond their approved prior
  authority role.
- Task 378 docs and any request-scoped correction replay identity behavior.
- Story 58 closeout, deployment, dev/prod live proof, and sibling epic/Story 57
  updates beyond truthful references to Story 58.

## Findings

No blocking findings remain after Cicero's Review 62 remediation.

### Resolved High: Missing-grant source-job access now uses the correction replay code

The original finding was valid: identity-owned source-job access without
`sir-convert:artifacts:read-own` returned
`403 auth_missing_internal_identity_grant` before the correction apply route could
map the failure to
`403 exam_authoring_correction_replay_access_denied`.

The remediation is acceptably narrow. The shared v2 auth helpers now accept an
optional `missing_grant_code` while preserving
`auth_missing_internal_identity_grant` as the default
(`scripts/sir_convert_a_lot/interfaces/http_auth_v2.py:141`,
`:154`, `:173`, `:184`). Existing callers continue to use that default; the
only reviewed override is the correction apply source-job authorization path
(`scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py:145`,
`:150`). Owner mismatch still flows through
`require_job_access_v2` with the same correction replay access-denied code
(`scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py:152`,
`:156`).

The new public-route test obtains a valid producer-issued source binding with
artifact-read grants, then applies as the same owner without
`sir-convert:artifacts:read-own` and asserts
`403 exam_authoring_correction_replay_access_denied`
(`tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py:196`,
`:214`, `:233`, `:263`). It also asserts the failure body does not include
correction replay artifact references or raw source-state signature material
(`tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py:267`).
Reviewer reruns of the remediation node and focused correction suite passed.

## What Passed Review

The missing-source branch itself is fail-closed: after request schema,
canonical source-state digest, and source-state signature validation, the route
resolves `source_bundle_id`, maps missing or expired jobs to
`409 exam_authoring_correction_source_job_unavailable`, and does not return
replay artifacts (`scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py:110`,
`:123`, `:127`, `:133`, `:137`; `tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py:35`,
`:107`, `:112`).

The stale/forged binding ordering is preserved: apply validation runs before
source-job lookup, and the focused test makes source-job lookup raise if it is
called for a stale source-state digest
(`scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py:110`,
`:115`; `tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py:273`,
`:311`, `:341`).

The valid source-bound correction path still succeeds and returns producer-backed
replay readiness/artifact availability when the source job exists and is
authorized (`tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py:345`,
`:407`, `:411`, `:413`).

The synthetic correction tests were narrowed truthfully to the explicit
non-artifact shape: no `source_bundle_id`, no requested targets, and no available
artifact rows (`tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py:64`,
`:70`, `:144`; `tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py:27`,
`:33`, `:77`; `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py:92`,
`:269`). That prevents the old synthetic fixtures from serving as a fail-open
stand-in for current DigiExam correction replay.

No browser fallback, synthetic failed job, latest-bytes fallback,
request-scoped artifact migration, or Task 378 artifact-set behavior was found
in the reviewed Task 377 production surface.

## Documentation Truth

`docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md`
is marked `status: completed`; after this rereview approval, that status is
acceptance-truthful for Task 377 only. The task and story docs record the Review
62 remediation red/green evidence and keep Task 378 behavior out of scope.

Story 58 correctly remains `in_progress`, and Task 378 remains unimplemented.
This review does not approve Story 58 closeout, deployment, or dev/prod live
proof.

## Checklist

- [x] Governing Story 58, Task 375/376 reviews, Task 377, correction apply
  contract, and Task 374 advisory replay authority read.
- [x] Current worktree status and untracked files inspected.
- [x] Production route, source-job policy helper, auth helper behavior, fixture
  changes, and tests audited.
- [x] Tests audited under the testing skill for public behavior coverage.
- [x] Focused Task 377 tests and targeted lint/typecheck gates rerun.
- [x] Decision recorded in retained review artifacts.

## Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py::test_correction_apply_missing_grant_source_job_remains_access_denied -q`
  passed after remediation: `1 passed, 1 warning`.

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py -q`
  passed after remediation: `36 passed, 1 warning`.

- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/interfaces/http_auth_v2.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`
  passed: `3 files already formatted`.

- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/interfaces/http_auth_v2.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`
  passed: `All checks passed!`.

- `/opt/homebrew/bin/pdm run typecheck-all` failed only on the existing nine
  test-helper `no-any-return` errors documented in Reviews 60 and 61. No Task
  377 remediation production or test file is reported.

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py -q`
  passed before the Review 62 remediation: `35 passed, 1 warning`.

- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/application/exam_authoring_correction_source_job_policy.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
  passed before the Review 62 remediation: `7 files already formatted`.

- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/application/exam_authoring_correction_source_job_policy.py scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/exam_authoring_advisory_replay_fixtures.py tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
  passed before the Review 62 remediation.

- `/opt/homebrew/bin/pdm run docs-sync` passed and regenerated
  `docs/backlog/INDEX.md`, `docs/reference/INDEX.md`,
  `docs/runbooks/INDEX.md`, and `docs/index.md`.

- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 513 backlog files`; `Validated docs=589 rules=11`.

- `/opt/homebrew/bin/pdm run skills-validate` passed.

- `/opt/homebrew/bin/pdm run handoff-validate` passed.

- `git diff --check` passed.

Validation not rerun by this reviewer:

- Full `format-all`, `lint-fix`, and `coverage-gate`; targeted ruff and focused
  tests covered the Task 377 remediation surface. The implementation-reported
  `coverage-gate` result remains unverified in this rereview pass.

## Follow-up Actions

- Task 378 must still bind correction replay artifacts to request-scoped
  identity. This review does not approve that behavior.
- Story 58 closeout, deployment, and dev/prod live proof remain out of scope.
- The existing nine `typecheck-all` test-helper `no-any-return` errors remain a
  repo debt outside Task 377 remediation scope.

## Decision

approved

## Response

Task 377 can proceed to overseer acceptance. The Review 62 missing-grant finding
is resolved with a narrow auth-helper extension, public-route proof, and focused
green validation. This approval is only for Task 377; it does not approve Task
378, Story 58 final closeout, deployment, or dev/prod live proof.

## Completion

Decision: `approved`.
