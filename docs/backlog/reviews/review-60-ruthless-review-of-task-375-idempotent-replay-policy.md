---
id: review-60-ruthless-review-of-task-375-idempotent-replay-policy
title: Ruthless review of Task 375 idempotent replay policy centralization
type: review
status: completed
priority: high
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - review
  - approved
  - task-375
  - service-api-v2
  - idempotency
  - replay
---

Retained independent review for Task 375. This reviewer did not author the
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
- `docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md`
- `docs/backlog/reviews/review-59-ruthless-review-of-task-374-advisory-candidate-replay.md`

Reviewed Task 375 surfaces:

- `.codex/handoff.md`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md`
- `docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md`
- `docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md`
- `docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `scripts/sir_convert_a_lot/application/contracts_v2.py`
- `scripts/sir_convert_a_lot/application/idempotency_replay_ports_v2.py`
- `scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py`
- `scripts/sir_convert_a_lot/domain/idempotency_replay_policy_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/idempotency_replay_adapters_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/idempotency_store.py`
- `scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py`
- `tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py`
- `tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py`
- `tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py`

Public/runtime surfaces affected:

- `POST /v2/convert/jobs` idempotency replay decision path.
- Create-job `idempotency` response metadata, including optional typed
  `reason`.
- Generated Service API v2 OpenAPI schema for idempotency metadata.
- Filesystem idempotency scope locking.

Compatibility posture:

- Additive current-v2 metadata extension: `idempotency.reason` is optional and
  defaults to `null` except for service-owned reattempt decisions.
- Existing Task 368 behavior for strict replay, fingerprint conflict,
  retryable failed reattempt, nonretryable failed replay, canceled replay, and
  missing active job is preserved.
- Route artifact compatibility and correction replay behavior are not approved
  here; Tasks 376-378 remain proposed/unimplemented.

Out-of-scope worktree dirtiness observed but not approved:

- `pdm.lock`
- `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`
- `docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md`
- `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`

## Findings

No blocking findings.

The implementation centralizes create-job replay decisions in
`scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py` while
keeping pure replay decision values in
`scripts/sir_convert_a_lot/domain/idempotency_replay_policy_v2.py`. The domain
module imports only domain/runtime-neutral types and does not depend on HTTP,
Pydantic DTOs, filesystem stores, or runtime engines.

The HTTP helper now maps application decisions and exceptions to existing HTTP
metadata/error behavior in
`scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py`; it no
longer owns the retryable-failed replay branch. The route compatibility seam is
neutral and default-compatible for Task 375. Task 376 must wire real
route-specific compatibility through that service seam rather than adding
DigiExam branches to HTTP code.

The filesystem idempotency store now combines the existing in-process scope
lock with a per-scope `fcntl.flock()` lock file. Reviewer-run concurrency tests
exercise one in-process store instance; code inspection confirms the production
path uses a shared scope lock file under the idempotency directory. This is
adequate for Task 375 local file-backed admission, with broader stale-success
compatibility still owned by Task 376.

Testing is behaviorally meaningful for this slice: public-route tests prove the
same-key/different-fingerprint conflict, retryable failed service reattempt,
nonretryable failed strict replay, active/succeeded/canceled strict replay,
concurrent retryable failed convergence, and missing active job behavior. The
new application-service tests prove the protocol-first service decision and
typed reason without HTTP helper branching.

## Checklist

- [x] Governing Story 58, Task 375, and prior Task 368 authority read.
- [x] Exact production, OpenAPI, docs, and test surfaces inspected.
- [x] Public contracts, data/runtime boundaries, typing risks, forbidden
  fallback risks, and verification evidence audited.
- [x] Focused Task 375 tests and validators rerun.
- [x] Decision recorded in retained review artifacts.

## Non-Blocking Observations

`pdm run typecheck-all` still fails, but the reviewer reproduced the same nine
pre-existing test-helper `no-any-return` errors reported by the implementation
agent. None are in the Task 375 production seam or new replay modules, so this
does not block Task 375 approval. A separate cleanup task should address the
repo-wide typecheck debt before it becomes ambiguous review noise.

The retained red evidence is sufficient for the architectural extraction slice:
the new application-service test failed before implementation because the
module did not exist. It is not evidence for Tasks 376-378; those tasks still
need their own red-first stale-success and correction replay tests.

## Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed: `94 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed: `4 passed`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/application/contracts_v2.py scripts/sir_convert_a_lot/application/idempotency_replay_ports_v2.py scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py scripts/sir_convert_a_lot/domain/idempotency_replay_policy_v2.py scripts/sir_convert_a_lot/infrastructure/idempotency_replay_adapters_v2.py scripts/sir_convert_a_lot/infrastructure/idempotency_store.py scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py`
  passed.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/application/contracts_v2.py scripts/sir_convert_a_lot/application/idempotency_replay_ports_v2.py scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py scripts/sir_convert_a_lot/domain/idempotency_replay_policy_v2.py scripts/sir_convert_a_lot/infrastructure/idempotency_replay_adapters_v2.py scripts/sir_convert_a_lot/infrastructure/idempotency_store.py scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py`
  passed: `10 files already formatted`.
- `/opt/homebrew/bin/pdm run typecheck-all` failed only on nine existing
  test-helper `no-any-return` errors outside the Task 375 production seam.
- `/opt/homebrew/bin/pdm run docs-sync` passed and regenerated
  `docs/backlog/INDEX.md`, `docs/reference/INDEX.md`,
  `docs/runbooks/INDEX.md`, and `docs/index.md`.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 510 backlog files`; `Validated docs=586 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed.
- `/opt/homebrew/bin/pdm run handoff-validate` passed.
- `git diff --check` passed before this review artifact was restored at the
  correct Sir Convert path.

Validation not rerun by this reviewer:

- Full `format-all`, `lint-fix`, and `coverage-gate`; focused equivalent
  checks and tests above covered the Task 375 seam. Implementation-reported
  broader gates are accepted for context except for the reproduced
  `typecheck-all` debt.

## Follow-up Actions

- Task 376 must add real route artifact compatibility inspection and
  stale-succeeded DigiExam replay proof. Task 375 does not approve that
  behavior.
- Tasks 377 and 378 must add correction replay source-job fail-closed behavior
  and request-scoped replay artifact identity. Task 375 does not approve those
  behaviors.
- Address the existing repo-wide test-helper `no-any-return` typecheck debt in
  a separate cleanup slice.

## Decision

approved

## Response

Task 375 is approved. The shared protocol-first replay policy seam is in place,
Task 368 behavior is preserved, `service_reattempt.reason` is modeled and
published, file-backed admission no longer relies only on process-local locks,
and the docs/OpenAPI updates are truthful for this slice.

This approval does not cover Tasks 376-378, Story 58 closeout, deployment, live
proof, unrelated `pdm.lock` changes, or sibling epic/Story 57 edits beyond their
truthful references to Story 58.

## Completion

Decision: `approved`.
