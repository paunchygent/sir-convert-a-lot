---
id: 'task-378-bind-correction-replay-artifacts-to-request-scoped-identity'
title: 'Bind correction replay artifacts to request scoped identity'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-30'
related:
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - correction-apply
  - replay
  - artifacts
  - identity
  - exam-migration
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Bind correction replay artifacts to the exact correction request that produced
them so later requests for the same source job cannot overwrite, alias, or
silently replace earlier replay artifacts.

Correction replay currently writes static artifact names under a source-job
scoped directory. That is not enough identity for user-visible correction
downloads and saved artifacts after multiple correction applies.

## PR Scope

- Define request-scoped correction replay artifact identity from source binding,
  normalized correction payload digest, target set, and replay artifact content
  hashes.
- Store replay artifacts under that request-scoped identity through the Task 375
  artifact-store port.
- Return typed artifact references that include enough replay identity to verify
  a download belongs to the correction apply response that advertised it.
- Ensure named artifact downloads reject stale, missing, or mismatched
  request-scoped artifact references.
- Update correction apply contract docs and generated OpenAPI for the nested
  correction replay artifact route and typed artifact reference shape.
- Preserve content-safe artifact metadata; do not expose raw source payloads,
  private filesystem paths, teacher identity data, or provider responses.

## Closed Implementation Decisions

- Correction replay artifacts use immutable request-scoped artifact sets and
  the nested route
  `/v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}`.
  The existing `{job_id, artifact_key}` route with static
  `correction_replay_*` keys is insufficient and must not be preserved as the
  authority for corrected replay downloads.
- Artifact references include `schema_version`, `job_id`, `artifact_set_id`,
  `artifact_key`, `target`, `content_sha256`, and replay/request identity
  metadata.
- Request-scoped identity includes `request_id`, validated source-binding
  digest, `source_state_sha256`, normalized correction payload digest,
  requested target-set digest, replay profile/schema version, artifact content
  hashes, and created timestamp in an artifact-set manifest.
- Exact duplicate normalized requests may return the same verified artifact set.
  The same `request_id` with different normalized content returns
  `409 exam_authoring_correction_replay_request_conflict`. Different
  correction payloads for the same source job produce distinct artifact sets.
- Store immutable sets under
  `correction-replays/{artifact_set_id}/manifest.json` plus target files so a
  later sweeper can enforce retention by parent job, timestamp, status, and
  manifest version. Physical cleanup is deferred.
- Missing artifact sets return `404 correction_replay_artifact_set_not_found`.
  Wrong job/set/key/hash returns
  `409 correction_replay_artifact_reference_mismatch`. Never fall back to the
  latest bytes.
- The nested route and typed reference DTO require a bounded Skriptoteket slice
  for generated types, parser/adapter updates, file-action routing, and
  fail-closed UI behavior for missing producer references.

## Out of Scope

- No broad rewrite of original migration bundle artifact naming.
- No frontend-local mapping from old static artifact keys to new replay
  identities.
- No cleanup/deletion of historical production replay directories in this task.

## Deliverables

- [x] Request-scoped artifact identity model and storage adapter.
- [x] Correction replay writer updated to write into request-scoped artifact
  sets.
- [x] Download/read path validation for replay artifact identity.
- [x] Nested correction replay artifact route and typed reference DTO in
  contract docs/OpenAPI.
- [x] Bounded Skriptoteket companion slice identified or created if generated
  OpenAPI changes require consumer type/parser/file-action updates.
- [x] Tests proving non-aliasing across two correction apply requests for the
  same source job.

## Acceptance Criteria

- [x] Two correction apply requests for the same source job and different
  correction payloads produce distinct artifact identities.
- [x] Downloading the first response's artifact reference after the second apply
  still returns the first response's bytes or fails closed; it never returns
  the second response's bytes.
- [x] Exact duplicate correction apply retries can reuse or deterministically
  resolve the same request-scoped artifact set when the normalized request
  and source binding match.
- [x] Reusing the same `request_id` with different normalized content returns
  `409 exam_authoring_correction_replay_request_conflict`.
- [x] Artifact references include route/job/request identity needed for
  verification without leaking private paths or raw source content.
- [x] Stale or mismatched artifact references fail closed through the standard
  Service API error envelope.
- [x] Missing sets return `404 correction_replay_artifact_set_not_found`; wrong
  job/set/key/hash returns
  `409 correction_replay_artifact_reference_mismatch`.

## Red-First Test Plan

- Add a failing test where two correction apply requests for the same source job
  overwrite the same static `correction-replay` artifact path; expected failure
  before the fix is aliasing.
- Add a duplicate-retry test for the exact same normalized correction request.
- Add a same-request-id different-content conflict test.
- Add a stale-reference test proving mismatched artifact identity is rejected.
- Add contract/OpenAPI tests for the nested route and typed replay artifact
  reference DTO.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused correction replay artifact writer and route tests.
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Evidence

Task 378 implementation is approved in retained independent Review 63 as of
2026-06-30. Story 58 final closeout, deploy, and dev/prod live proof have not
been performed.

The implementation adds immutable request-scoped correction replay artifact
sets under `correction-replays/{artifact_set_id}/manifest.json` plus target
files. Correction apply now returns typed
`correction_replay_artifact_reference_v1` references with `job_id`,
`artifact_set_id`, `artifact_key`, `target`, `content_sha256`, `request_id`,
source-binding digest, `source_state_sha256`, normalized correction payload
digest, requested target-set digest, replay profile version, and created
timestamp. Exact duplicate normalized requests reuse the same verified artifact
set. Reusing a `request_id` with different normalized content returns
`409 exam_authoring_correction_replay_request_conflict`.

Corrected replay downloads now use the nested route
`/v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}`
with `content_sha256` as a required query parameter. Static
`correction_replay_*` keys on `/v2/convert/jobs/{job_id}/artifacts/{artifact_key}`
are no longer correction replay download authority. Missing artifact sets
return `404 correction_replay_artifact_set_not_found`; wrong job, set, key, or
hash returns `409 correction_replay_artifact_reference_mismatch`; there is no
latest-bytes fallback.

OpenAPI now exposes the nested correction replay artifact route and the typed
artifact reference DTO. This requires a bounded Skriptoteket companion slice
for generated types, parser/adapter updates, file-action routing, and
fail-closed UI behavior before Story 58 final closeout.

### Red Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_replay_artifact_sets_v2.py -q`
  failed before the production fix with `4 failed, 1 warning`: correction apply
  responses lacked typed `artifact_reference` objects, and reusing the same
  `request_id` with different normalized correction content still returned
  `200 OK`.

### Green Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_correction_replay_artifact_sets_v2.py tests/sir_convert_a_lot/test_digiexam_migration_corrections_api_v2.py tests/sir_convert_a_lot/test_digiexam_migration_labelled_choice_correction_replay.py tests/sir_convert_a_lot/test_exam_authoring_correction_source_job_fail_closed_v2.py tests/sir_convert_a_lot/test_exam_authoring_correction_apply_advisory_replay.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_non_matching.py tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed: `45 passed, 1 warning`.
- `/opt/homebrew/bin/pdm run openapi-export-v2` passed and refreshed
  `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.
- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py -q`
  passed: `4 passed`.
- Targeted `/opt/homebrew/bin/pdm run ruff format --check ...` over Task 378
  production/test files passed: `13 files already formatted`.
- Targeted `/opt/homebrew/bin/pdm run ruff check ...` over Task 378
  production/test files passed: `All checks passed!`.
- `/opt/homebrew/bin/pdm run coverage-gate` passed:
  `1788 passed, 6 skipped, 1 warning`, coverage `95.54%`.
- `/opt/homebrew/bin/pdm run format-all` passed after final local gate refresh:
  `1 file reformatted, 967 files left unchanged`.
- `/opt/homebrew/bin/pdm run lint-fix` passed after final local gate refresh:
  `All checks passed!` and `968 files left unchanged`.
- `/opt/homebrew/bin/pdm run typecheck-all` passed after repairing the
  pre-existing test-helper return-type errors: `Success: no issues found in 919 source files`.
- `/opt/homebrew/bin/pdm run docs-sync` passed and refreshed generated indexes.
- `/opt/homebrew/bin/pdm run docs-validate` passed:
  `Validated 514 backlog files` and `Validated docs=590 rules=11`.
- `/opt/homebrew/bin/pdm run skills-validate` passed: `skills-validate: ok`.
- `/opt/homebrew/bin/pdm run handoff-validate` passed: `handoff-validate: ok`.
- `git diff --check` passed.

### Remaining Story-Level Validation

Task 378 is locally validated and approved, but this is not Story 58 closeout.
Story 58 remains open until the bounded Skriptoteket companion slice,
deployment where production behavior is relevant, and dev/prod live service
proofs are complete.
