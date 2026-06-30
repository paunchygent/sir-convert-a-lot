---
id: review-63-ruthless-review-of-task-378-correction-replay-artifact-sets
title: Ruthless review of Task 378 correction replay artifact sets
type: review
status: completed
priority: high
created: '2026-06-30'
last_updated: '2026-06-30'
related:
  - docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/reviews/review-60-ruthless-review-of-task-375-idempotent-replay-policy.md
  - docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md
  - docs/backlog/reviews/review-61-ruthless-review-of-task-376-digiexam-artifact-compatibility.md
  - docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md
  - docs/backlog/reviews/review-62-ruthless-review-of-task-377-correction-source-job-fail-closed.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - review
  - approved
  - task-378
  - correction-apply
  - replay
  - artifacts
  - identity
---

Retained independent review for Task 378. This reviewer did not author the
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
- `docs/backlog/reviews/review-62-ruthless-review-of-task-377-correction-source-job-fail-closed.md`
- `docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`

Reviewed Task 378 surfaces:

- `.codex/handoff.md`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
- `docs/backlog/INDEX.md`
- `docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md`
- `docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md`
- `docs/converters/exam-authoring-corrections-apply-contract.md`
- `docs/index.md`
- `docs/reference/INDEX.md`
- `docs/runbooks/INDEX.md`
- `scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py`
- `scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state_models.py`
- `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_models.py`
- `scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_sets.py`
- `scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_writer.py`
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_correction_replay_artifacts_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py`
- `tests/sir_convert_a_lot/test_exam_authoring_correction_replay_artifact_sets_v2.py`
- `tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py`
- `tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py`
- `tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py`
- `tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py`
- `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py`
- `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py`
- `tests/sir_convert_a_lot/test_openapi_contract_v2.py`

Public/runtime surfaces affected:

- `POST /v2/exam-authoring/corrections/apply`
- `GET /v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}?content_sha256=...`
- Existing named-artifact route behavior for static artifact keys.
- OpenAPI response contracts for correction replay artifact references.

Out-of-scope worktree dirtiness observed but not approved:

- `docker/service-deps/service-dependency-inputs-cpu.json`
- `docker/service-deps/service-dependency-inputs-rocm.json`
- `docker/service-deps/service-requirements.txt`
- `pdm.lock`
- Task 375, Task 376, and Task 377 code/docs/review artifacts except as
  prior authority and preservation checks for Task 378.
- Story 57, sibling epic updates, Story 58 final closeout, deployment,
  dev/prod live proof, and any Skriptoteket implementation work.

## Findings

No blocking findings.

Task 378 satisfies the request-scoped replay artifact contract. The identity
payload includes job id, request id, source binding digest, source-state digest,
normalized correction payload digest, requested target-set digest, and replay
profile version before deriving a stable artifact set id
(`scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_sets.py:114`,
`:136`, `:137`). The writer stores target files under that immutable set and
then writes the manifest (`scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_writer.py:148`,
`:179`; `scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_sets.py:180`,
`:209`, `:287`).

Duplicate and conflict behavior is fail-closed. Existing manifests are reused
only when the request identity digest matches; the same `request_id` with a
different normalized identity returns
`409 exam_authoring_correction_replay_request_conflict`
(`scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_sets.py:163`,
`:166`). The public tests prove non-aliasing across different payloads, exact
duplicate reuse, and request-id conflict behavior
(`tests/sir_convert_a_lot/test_exam_authoring_correction_replay_artifact_sets_v2.py:37`,
`:85`, `:93`, `:126`, `:131`, `:170`).

The nested download route is the authority for corrected replay artifacts and
requires `content_sha256`. It is registered at
`/v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}`
and resolves through the correction replay artifact writer
(`scripts/sir_convert_a_lot/interfaces/http_routes_correction_replay_artifacts_v2.py:34`,
`:42`, `:48`, `:89`, `:93`, `:95`). Missing sets return
`404 correction_replay_artifact_set_not_found`; wrong job, set, key, hash, or
bytes return `409 correction_replay_artifact_reference_mismatch`
(`scripts/sir_convert_a_lot/infrastructure/correction_replay_artifact_sets.py:252`,
`:256`, `:262`, `:268`, `:274`, `:369`). The public route tests cover those
codes and the content-hash gate
(`tests/sir_convert_a_lot/test_exam_authoring_correction_replay_artifact_sets_v2.py:174`,
`:204`, `:216`, `:234`, `:236`, `:238`, `:241`).

Static `correction_replay_*` keys on the existing named-artifact route are no
longer download authority. The named route delegates DigiExam artifacts to the
manifest resolver only (`scripts/sir_convert_a_lot/interfaces/http_routes_job_artifacts_v2.py:104`,
`:352`), and that resolver normalizes keys through
`DigiExamMigrationArtifactKey`, which rejects correction replay keys instead of
falling back to latest bytes
(`scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py:59`,
`:67`, `:120`). No compatibility shim or latest-bytes fallback was found.

The public reference DTO is explicit and does not expose private paths, raw
source, signatures, grants, or provider payloads. The Service API DTO includes
`schema_version`, `job_id`, `artifact_set_id`, `artifact_key`, `target`,
`content_sha256`, `request_id`, `source_binding_digest`,
`source_state_sha256`, `correction_payload_digest`, `target_set_digest`,
`replay_profile_version`, and `created_at`
(`scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_models.py:263`,
`:268`, `:273`, `:274`, `:275`, `:278`). The answer-key review-state projection
keeps the same typed replay reference shape for exportable target rows
(`scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state_models.py:130`,
`:133`, `:135`, `:136`, `:137`, `:140`;
`scripts/sir_convert_a_lot/application/digiexam_answer_key_review_state.py:379`,
`:393`, `:395`).

Task 377 fail-closed behavior and Task 374 advisory candidate behavior remain
covered in the focused preservation suite. The correction replay tests are
public-route behavior tests rather than helper-only tests, and OpenAPI tests
assert the nested route, required `content_sha256`, and typed reference schemas
(`tests/sir_convert_a_lot/test_openapi_contract_v2.py:96`, `:133`, `:144`,
`:273`, `:283`, `:287`, `:293`, `:300`).

## Non-Blocking Observations

The Task 375 placeholder correction replay identity port remains deferred and
unused after Task 378 (`scripts/sir_convert_a_lot/application/idempotency_replay_ports_v2.py:106`,
`:109`, `:116`; `scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py:60`,
`:72`). This does not block Task 378 because the reviewed implementation keeps
the concrete artifact identity and file resolution in infrastructure and proves
the public contract, but the deferred port should be reconciled in a later
cleanup if it is no longer an intended seam.

`scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py`
still has a stale module docstring reference to a correction replay store
(`scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py:5`,
`:13`). The executable resolver no longer implements that fallback, so this is
documentation hygiene rather than a behavior failure.

## Documentation Truth

The Task 378 task doc is `status: in_progress` and says implementation is
review-ready, with retained review, Story 58 final closeout, deployment, and
dev/prod live proof not yet performed
(`docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md:5`,
`:152`, `:153`). That was truthful at review start; approval is recorded here,
not by silently closing Story 58.

Story 58 remains `status: in_progress` and explicitly keeps retained review
approval, deployment, and dev/prod live proof separate from Task 378
implementation readiness
(`docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md:5`,
`:298`, `:299`, `:313`). The correction apply contract records the immutable
artifact set route, typed reference requirements, and fail-closed mismatch
envelope (`docs/converters/exam-authoring-corrections-apply-contract.md:681`,
`:685`, `:692`, `:698`, `:701`, `:736`).

## Checklist

- [x] Governing Story 58, Tasks 375-378, Reviews 60-62, correction apply
  contract, skills, and targeted rules read.
- [x] Current worktree status and untracked files inspected.
- [x] Production route, writer, artifact-set store, named artifact resolver,
  DTO/projection models, OpenAPI, and Task 378 tests audited.
- [x] Tests audited under the testing skill for public behavior coverage.
- [x] Focused preservation suite, OpenAPI export/contract, targeted ruff,
  coverage, and typecheck evidence rerun.
- [x] Decision recorded in retained review artifact.

## Verification

Reviewer-run evidence:

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_replay_artifact_sets_v2.py tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed: `45 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run openapi-export-v2` passed and regenerated
  `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.
- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed: `4 passed`.
- `/opt/homebrew/bin/pdm run ruff format --check ...` over the 13 reviewed
  Task 378 production/test/OpenAPI files passed: `13 files already formatted`.
- `/opt/homebrew/bin/pdm run ruff check ...` over the same 13 files passed:
  `All checks passed!`.
- `/opt/homebrew/bin/pdm run coverage-gate` passed:
  `1788 passed, 6 skipped, 1 warning`; coverage `95.54%`.
- `/opt/homebrew/bin/pdm run typecheck-all` failed only on the known nine
  unrelated test-helper `no-any-return` errors already documented in Reviews
  60-62. No Task 378 production or test file was reported.
- `/opt/homebrew/bin/pdm run docs-sync` passed and regenerated generated docs
  indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed.
- `/opt/homebrew/bin/pdm run skills-validate` passed.
- `/opt/homebrew/bin/pdm run handoff-validate` passed.
- `git diff --check` passed.

Validation not run:

- Full `format-all` and `lint-fix` were not run to avoid normalizing unrelated
  dirty worktree files. Targeted ruff checks ran on the reviewed Task 378 files.
- Story 58 final closeout gates, deployment, dev/prod service live proof, and
  Skriptoteket companion implementation/proof were not run because they are
  explicitly outside Task 378 retained review scope.

## Follow-up Actions

- Story 58 still needs its separate final closeout after Tasks 375-378 are
  accepted, final gates run, deployment is performed where production behavior
  is relevant, and real dev/prod service live proofs cover all workflows using
  touched idempotency/replay code.
- The bounded Skriptoteket companion slice remains required before Story 58
  final closeout for generated types, download client behavior, and fail-closed
  UI behavior.
- Existing unrelated typecheck helper errors remain outside Task 378 and should
  not be hidden by this approval.
- Consider a later cleanup to reconcile the deferred Task 375 correction replay
  identity port and the stale DigiExam artifact resolver docstring.

## Decision

Approved for Task 378 only.

This approval does not approve Story 58 final closeout, deployment, dev/prod
live proof, or unrelated worktree dirtiness.

## Response

Approved. No blocking Task 378 findings were found. The implementation can
proceed to overseer acceptance for Task 378 only; Story 58 closeout remains a
separate later gate.

## Completion

Task 378 can proceed to overseer acceptance. Story 58 remains open until the
separate closeout and live-proof requirements are satisfied.
