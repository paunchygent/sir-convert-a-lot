---
id: 'task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility'
title: 'Gate idempotent succeeded replays on route artifact contract compatibility'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-30'
related:
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md
  - docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - service-api-v2
  - idempotency
  - replay
  - artifact-contract
  - exam-migration
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Prevent stale `succeeded` jobs from being strict-replayed when their persisted
terminal artifacts no longer satisfy the current route artifact contract.

The production failure that opened Story 58 replayed an old successful DigiExam
job lacking `answer_key_review_state_report`. Same-key/same-fingerprint replay
is correct only when the old terminal job is compatible with the current route
contract.

## PR Scope

- Implement route artifact compatibility inspection behind the Task 375 replay
  service port.
- Define the DigiExam migration bundle terminal artifact requirements in
  product-neutral Sir Convert terms, including `answer_key_review_state_report`
  and current schema versions where required.
- Inspect persisted job manifest/artifact metadata before returning a
  `succeeded` strict replay.
- When an old terminal job is incompatible, admit a service-owned reattempt or
  fail closed with a typed reason if reattempt cannot be safely admitted.
- Preserve old job lineage and content-safe reason metadata for observability
  and retained proof.
- Keep generic routes strict-replay compatible unless they declare their own
  terminal artifact requirements.
- Update converter/API docs and generated OpenAPI for typed reattempt reason
  metadata and compatibility failure errors.

## Closed Implementation Decisions

- DigiExam `succeeded` strict replay is compatible only when the persisted
  `digiexam_dxe -> examnet_migration_bundle` job satisfies the current terminal
  route artifact contract.
- Compatibility requires a valid `digiexam_migration_bundle_v3` manifest,
  matching job id, current required artifact keys, `readiness.artifact_key = target_readiness_report`, `answer_key_review_state.artifact_key = answer_key_review_state_report`, current source/effective schema versions,
  parsable `target_readiness_report_v1`, parsable
  `digiexam_answer_key_review_state_v1`, and existing bytes with matching
  size/hash for every `available` artifact entry. The manifest self-entry may
  remain hash/size exempt unless the writer changes.
- Manual follow-up and schema-valid `complete`, `partial`, `needs_review`, and
  `failed` bundle statuses are compatible terminal workflow states only when
  required reports, pointers, schema versions, and available bytes are valid.
  Strict replay must not require all PDF/QTI targets to be exportable;
  `target_readiness_report_v1` remains the export authority.
- Correction replay artifact presence is not part of Task 376 compatibility
  until Tasks 377 and 378 close source-job fail-closed behavior and
  request-scoped replay identity.
- A stale incompatible success admits a service-owned reattempt when the current
  create-job request can be safely admitted. The public state remains
  `service_reattempt`; the reason is
  `terminal_artifact_contract_incompatible`.
- If no safe fresh admission can be made, return the standard non-2xx error
  envelope, not a synthetic failed job. Use
  `409 idempotent_terminal_artifact_contract_incompatible` unless a more
  specific admission error applies.
- Register route terminal-artifact compatibility beside the v2 route policy via
  a named contract/inspector port. HTTP routes must not contain route-specific
  DigiExam compatibility branches.
- Routes without a declared terminal-artifact compatibility contract remain
  strict-replay compatible under existing semantics.

## Out of Scope

- No Skriptoteket-specific labels or UI behavior in Sir Convert contracts.
- No broad invalidation of all `succeeded` idempotency records.
- No deletion or manual editing of production idempotency pointers as the fix.
- No correction replay artifact identity changes; Task 378 owns that.

## Deliverables

- [x] Artifact compatibility inspector infrastructure adapter over persisted
  job manifests and named artifacts.
- [x] Route compatibility policy for DigiExam migration bundles.
- [x] Replay service integration that gates strict `succeeded` replay on the
  compatibility result.
- [x] Typed reason/action for contract-incompatible terminal artifacts.
- [x] Tests for incompatible DigiExam success, compatible DigiExam success,
  generic-route success, missing artifact bytes, and schema/version drift.
- [x] Structured compatibility parser/result with stable reason codes; do not
  rely on the existing narrow result-metadata loader alone.
- [x] Contract docs updated for typed `service_reattempt` reasons and
  `idempotent_terminal_artifact_contract_incompatible`.

## Acceptance Criteria

- [x] A same-key/same-fingerprint DigiExam upload whose active job lacks
  `answer_key_review_state_report` is not returned as a strict replay.
- [x] A same-key/same-fingerprint DigiExam upload whose active job satisfies the
  current artifact contract still strict replays.
- [x] A generic route with no declared terminal artifact compatibility rule
  keeps the current strict replay behavior.
- [x] Missing artifact metadata, missing artifact bytes, or incompatible schema
  versions produce a typed compatibility failure instead of a misleading
  `succeeded` replay.
- [x] `partial`, `needs_review`, `failed`, and manual-follow-up states remain
  compatible terminal replays when the required reports, schema versions,
  pointers, and available bytes are valid.
- [x] Route compatibility policy is registered through the v2 route policy
  surface and a protocol-backed inspector, not scattered in HTTP route
  conditionals.
- [x] No synthetic failed job is created for compatibility/admission failure
  before runtime execution actually admits and fails a job.
- [x] The remediation path is service-owned and bounded: no caller salting, no
  frontend retry workaround, and no production idempotency-file surgery.
- [x] Logs and retained proof expose only content-safe job ids, route ids,
  replay action, and compatibility reasons.

## Red-First Test Plan

- Add a failing create-job replay test for a legacy DigiExam terminal job whose
  manifest lacks `answer_key_review_state_report`; expected failure before the
  fix is strict replay of the stale job.
- Add a passing-control test for a compatible DigiExam terminal job.
- Add a passing-control test for a generic document conversion route.
- Add a missing-bytes test where the manifest advertises a required artifact
  but the artifact cannot be read.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused `pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py ...`
- Focused DigiExam bundle tests where artifact metadata is produced.
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

## Implementation Notes

2026-06-30 implementation is approved by retained independent Review 61. It
registers the named
`digiexam_migration_bundle_v3` terminal artifact compatibility contract on the
`digiexam_dxe -> examnet_migration_bundle` route policy. The HTTP create-job
adapter still delegates replay decisions to the Task 375 application service;
it now composes `RoutePolicyTerminalArtifactCompatibilityAdapterV2`, which
resolves the stored job, reads the route policy contract, and validates
persisted DigiExam terminal artifacts through a bounded infrastructure
inspector.

The inspector treats routes without a declared contract as compatible. For the
DigiExam contract it validates the strict manifest DTO, matching job id,
current required artifact keys, readiness/review-state pointers, source and
effective schema versions, parsable `target_readiness_report_v1`, parsable
`digiexam_answer_key_review_state_v1`, and matching size/hash bytes for every
non-manifest `available` artifact entry. The manifest self-entry remains
hash/size exempt. `complete`, `partial`, `needs_review`, schema-valid
`failed`, and manual-follow-up states remain compatible when the required
reports, pointers, schema versions, and available bytes are valid.

Task 376 does not implement correction replay source-job fail-closed behavior,
request-scoped correction replay artifact identity, production idempotency-file
surgery, caller-side salting, or a Skriptoteket retry workaround. Tasks 377 and
378 remain unimplemented.

### Red Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py -q`
  failed before the production fix with `3 failed, 4 passed`: legacy missing
  `answer_key_review_state_report`, missing available artifact bytes, and
  source schema-version drift all returned `200 OK` strict replay instead of a
  `service_reattempt`.

### Green Evidence

- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py -q`
  passed: `14 passed`.
- `/opt/homebrew/bin/pdm run pytest-root tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed: `112 passed`.
- `/opt/homebrew/bin/pdm run ruff check scripts/sir_convert_a_lot/domain/service_routes_v2.py scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  passed.
- `/opt/homebrew/bin/pdm run ruff format --check scripts/sir_convert_a_lot/domain/service_routes_v2.py scripts/sir_convert_a_lot/infrastructure/route_terminal_artifact_compatibility_v2.py scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py tests/sir_convert_a_lot/test_idempotent_replay_digiexam_artifact_compatibility_v2.py tests/sir_convert_a_lot/test_create_job_route_registry_v2.py`
  passed: `5 files already formatted`.

### Skipped Or Blocked Validation

- `/opt/homebrew/bin/pdm run typecheck-all` was rerun and still fails on the
  same nine pre-existing test-helper `no-any-return` errors documented in
  Review 60. No Task 376 production or test files are reported.
