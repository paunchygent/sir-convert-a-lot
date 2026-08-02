---
id: review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility
title: Ruthless review of Task 376 DigiExam artifact compatibility replay gate
type: review
status: completed
priority: high
created: '2026-06-30'
last_updated: '2026-06-30'
related:
  - docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/multi_format_conversion_service_api_v2.md
labels:
  - review
  - approved
  - task-376
  - service-api-v2
  - idempotency
  - replay
  - artifact-contract
---

Retained independent review for Task 376. This reviewer did not author the
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
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`

Reviewed Task 376 surfaces:

- `.codex/handoff.md`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/converters/multi_format_conversion_service_api_v2.md`
- `scripts/sir_convert_a_lot/domain/service_routes_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py`
- `scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py`
- `scripts/sir_convert_a_lot/domain/idempotency_replay_policy_v2.py`
- `scripts/sir_convert_a_lot/application/idempotency_replay_ports_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/idempotency_replay_adapters_v2.py`
- `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`
- `scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state_models.py`
- `scripts/sir_convert_a_lot/domain/digiexam_schema_versions.py`
- `tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py`
- `tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
- Task 375 preservation tests listed under verification.

Public/runtime surfaces affected:

- `POST /v2/convert/jobs` same-key/same-fingerprint replay for persisted
  `succeeded` DigiExam migration jobs.
- Route-policy metadata for `digiexam_dxe -> examnet_migration_bundle`.
- Persisted DigiExam migration bundle manifest and named artifact validation
  before strict replay.
- Public idempotency metadata state/reason for service-owned reattempts.

Out-of-scope worktree dirtiness observed but not approved:

- `pdm.lock`
- `docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md`
- `docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md`
- `docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md`
- Task 377 and Task 378 docs.
- Task 375 review/doc/code artifacts beyond their role as prior approved
  behavior authority.

## Findings

No blocking findings.

The implementation gates strict replay through the Task 375 application service
seam instead of adding DigiExam branching to HTTP. The HTTP adapter only composes
`RoutePolicyTerminalArtifactCompatibilityAdapterV2` into
`IdempotencyReplayServiceV2` and maps the resulting decision metadata
(`scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py:67`,
`:71`, `:144`, `:156`). The service evaluates route compatibility only for
`SUCCEEDED` jobs and otherwise preserves the Task 368/375 replay branches
(`scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py:104`,
`:114`, `:118`, `:123`, `:132`).

The route contract is scoped to DigiExam migration only. The domain route policy
declares the named `digiexam_migration_bundle_v3` compatibility contract and
attaches it only to `digiexam_dxe -> examnet_migration_bundle`
(`scripts/sir_convert_a_lot/domain/service_routes_v2.py:28`, `:172`, `:226`,
`:235`). Routes without a declared contract return compatible through the
adapter and keep existing strict replay semantics
(`scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py:68`,
`:74`).

The compatibility inspector enforces the closed Task 376 contract: strict
manifest parsing, matching job id, current required artifact keys, current
source/effective schema versions via Literal-backed DTOs, readiness and
answer-key review-state pointers, parsable target-readiness and review-state
reports, and size/hash/file existence for every available non-manifest artifact
(`scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py:92`,
`:97`, `:99`, `:101`, `:103`, `:110`, `:117`, `:127`, `:142`, `:150`, `:152`,
`:163`). Incompatibility returns the typed
`terminal_artifact_contract_incompatible` reason, which the replay service
publishes as `service_reattempt` metadata after admitting a fresh attempt
(`scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py:183`,
`:186`; `scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py:134`,
`:144`, `:156`, `:207`, `:219`).

The behavioral tests exercise the public create-job route, not just helper
internals. They prove stale successes missing `answer_key_review_state_report`,
missing available bytes, and schema-version drift are not strict-replayed, while
schema-valid `complete`, `partial`, `needs_review`, `failed`, and manual
follow-up states still strict replay when required reports/pointers/schema/bytes
are valid (`tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py:52`,
`:84`, `:96`, `:128`, `:133`, `:163`, `:168`, `:211`, `:215`). Route registry
tests prove the contract is declared only on the DigiExam migration route
(`tests/sir_convert_a_lot/test_create_job_route_registry_v2.py:82`, `:90`,
`:94`).

No forbidden remediation pattern was found in the reviewed Task 376 surface:
there is no caller-side salting, frontend retry workaround, production
idempotency-file surgery, latest-bytes lookup fallback, compatibility shim for
stale manifests, or correction replay implementation. Task 377 and Task 378
remain unapproved.

## Non-Blocking Observations

`pdm run typecheck-all` still fails on the same nine pre-existing test-helper
`no-any-return` errors documented in Review 60. None are in Task 376 production
or test files, so this does not block Task 376 approval. The debt should still
be closed in a separate cleanup slice before future reviews lose the ability to
distinguish task regressions from ambient helper drift.

`docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md`
was already marked `status: completed` before this retained review. Because this
review approves Task 376, the status is now truthful and no reviewer-owned task
doc correction is required.

If future work broadens
`RouteTerminalArtifactCompatibilityContractV2`, add an unsupported-contract
fail-closed test before registering a new value. The current Literal has only
the DigiExam bundle contract, so the default-compatible branch is not reachable
from current route-policy metadata.

## Checklist

- [x] Governing Story 58, Task 375 review, Task 376, API docs, and artifact
  contract read.
- [x] Current worktree status and untracked files inspected.
- [x] Production route policy, compatibility inspector, HTTP composition, and
  Task 375 replay service seam audited.
- [x] Tests audited under the testing skill for public behavior coverage.
- [x] Focused Task 376 and preservation tests rerun.
- [x] Decision recorded in retained review artifacts.

## Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py -q`
  passed: `14 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed: `112 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/domain/service_routes_v2.py scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  passed.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/domain/service_routes_v2.py scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  passed: `5 files already formatted`.
- `/opt/homebrew/bin/pdm run typecheck-all` failed only on nine existing
  test-helper `no-any-return` errors outside Task 376 files:
  `test_create_job_admission_multipart_replay_v2.py:87`,
  `test_audio_transcript_bundle_runtime_v2.py:685`,
  `http_routes_jobs_v2_edge_cases_test_support.py:128`,
  `digiexam_migration_bundle_api_fixtures.py:241`,
  `audio_transcript_task357_helpers.py:86`,
  `test_transcript_formatter_replay_v2.py:425`,
  `test_transcript_formatter_artifacts.py:326`,
  `test_public_exam_converter_grant_runtime_v2.py:358`, and
  `test_audio_transcription_route_admission_v2.py:546`.
- `/opt/homebrew/bin/pdm run docs-sync` passed and regenerated
  `docs/backlog/INDEX.md`, `docs/reference/INDEX.md`,
  `docs/runbooks/INDEX.md`, and `docs/index.md`.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 512 backlog files`; `Validated docs=588 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed.
- `/opt/homebrew/bin/pdm run handoff-validate` passed.
- `git diff --check` passed.

Validation not rerun by this reviewer:

- Full `format-all`, `lint-fix`, and `coverage-gate`; focused lint/format and
  the Task 376 plus preservation suites covered this review scope. OpenAPI export
  was not rerun because Task 376 does not change the response schema beyond the
  previously approved Task 375 idempotency reason metadata.

## Follow-up Actions

- Return the nine existing test-helper `no-any-return` errors to a separate
  cleanup slice; they remain repo validation debt, not Task 376 rejection
  criteria.
- Task 377 must still fail closed when correction replay source jobs are
  unavailable. This review does not approve that behavior.
- Task 378 must still bind correction replay artifacts to request-scoped
  identity. This review does not approve that behavior.
- Story 58 closeout, deployment, and live proof remain out of scope.

## Decision

approved

## Response

Task 376 is approved. The DigiExam stale-success replay gate is scoped to the
declared route artifact contract, preserves generic strict replay semantics,
admits service-owned reattempts with the public
`terminal_artifact_contract_incompatible` reason, and is covered by public-route
behavior tests plus preservation checks.

This approval does not cover Tasks 377-378, Story 58 closeout, deployment, live
proof, unrelated `pdm.lock` changes, or sibling epic/Story 57 edits beyond their
truthful references to Story 58.

## Completion

Decision: `approved`.
