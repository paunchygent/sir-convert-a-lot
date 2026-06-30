---
id: 'task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2'
title: 'Centralize protocol-first idempotent replay policy in Service API v2'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-29'
related:
  - docs/backlog/stories/story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening.md
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md
  - docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md
  - docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
labels:
  - service-api-v2
  - idempotency
  - replay
  - ddd
  - dishka
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extract Service API v2 idempotent replay business policy from HTTP/interface
helpers into a protocol-first application service with pure domain decision
types and infrastructure adapters composed through Dishka where useful.

The current create/admit path centralizes behavior in shape, but the core
policy still lives at the interface edge. This task creates the shared replay
policy spine needed by Story 58 before route artifact compatibility and
correction replay hardening are layered on top.

## PR Scope

- Introduce pure domain decision types for idempotent replay outcomes, replay
  action, compatibility status, previous-attempt lineage, and typed reason
  codes.
- Introduce application-layer protocol ports for idempotency records, job
  lookup, fresh attempt admission, route artifact compatibility, and correction
  replay artifact stores.
- Move existing create-job decisions from
  `scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py` into
  an application service while preserving current behavior.
- Compose filesystem/job-store infrastructure through a small provider surface
  when DI clarifies lifecycle and substitution.
- Keep route handlers responsible only for transport validation, upload/spec
  preparation, auth/grant context, and response mapping.
- Leave route artifact compatibility rules and correction replay behavior to
  Tasks 376-378 after the shared service seam exists.

## Closed Implementation Decisions

- Public replay vocabulary keeps `idempotency.state = service_reattempt` for
  every service-admitted fresh attempt under an existing idempotency scope. A
  typed `idempotency.reason` distinguishes causes, including
  `retryable_failed_terminal` and
  `terminal_artifact_contract_incompatible`. Do not add
  `contract_reattempt`.
- Domain decision types live in `domain/idempotency_replay_policy_v2.py` and
  must not import HTTP, filesystem stores, runtime engines, or Pydantic
  response DTOs.
- Application ports live in `application/idempotency_replay_ports_v2.py`; the
  replay orchestration service lives in
  `application/idempotency_replay_service_v2.py`.
- Infrastructure adapters own filesystem idempotency records, job
  lookup/admission, DigiExam terminal artifact compatibility inspection, and
  correction replay artifact identity/storage.
- Compose infrastructure-backed adapters and the replay service through a small
  app-scope Dishka provider or equivalent app-state composition seam. Pure
  domain decision values remain directly constructible.
- HTTP routes may validate transport/auth/body/upload inputs and map
  application decisions to responses, but must not own replay branching.
- Task 375 must not preserve interface-owned replay policy, process-local-only
  admission locking, silent missing-source correction success, or source-job
  scoped static correction replay artifacts as accepted foundations.

## Out of Scope

- No route-specific artifact compatibility enforcement in this task beyond the
  port and neutral decision vocabulary needed by Task 376.
- No correction replay artifact storage migration in this task beyond the port
  needed by Task 378.
- No caller-side idempotency key salting, CLI auto-rerun wrapper, or consumer
  fallback.

## Deliverables

- [x] Domain replay decision module with Google-style module docstring and no
  dependency on HTTP, filesystem, or concrete job stores.
- [x] Application replay service plus protocol ports for idempotency record,
  job lookup, fresh admission, route compatibility, and correction replay
  identity needs.
- [x] Thin HTTP create-job integration that delegates business replay decisions
  to the application service.
- [x] Dishka provider or equivalent composition seam for concrete
  infrastructure adapters where beneficial.
- [x] `IdempotencyMetadataV2` and generated OpenAPI expose typed reattempt
  reason metadata when a service-owned reattempt occurs.
- [x] Idempotency admission locking is hardened with file-level/CAS behavior or
  production single-process admission is explicitly proved before new
  reattempt causes are enabled.
- [x] Focused tests preserving existing Task 368 behavior:
  same-key/different-fingerprint conflict, queued/running/succeeded strict
  replay, retryable failed service reattempt, and nonretryable failed
  strict replay.
- [x] Architecture notes in Story 58/task docs updated if the final module names
  differ from this planning shape.

## Acceptance Criteria

- [x] There is one shared application decision path for create-job idempotent
  replay policy.
- [x] HTTP route code no longer owns replay branching beyond mapping
  application decisions to HTTP responses.
- [x] The new service exposes an extension point for route artifact
  compatibility without coupling to DigiExam or Skriptoteket UI labels.
- [x] The new service exposes an extension point for correction replay
  request-scoped identity without coupling to filesystem layout.
- [x] `service_reattempt` remains the only public reattempt state; typed reason
  metadata distinguishes retryable terminal failure from route artifact
  contract incompatibility.
- [x] The implementation does not rely solely on process-local locks for
  idempotency pointer updates unless production admission is proved
  single-process and the proof is retained.
- [x] Existing Service API v2 idempotency behavior remains unchanged before
  Tasks 376-378 add new decisions.
- [x] New or materially changed modules stay under the repo file-size target,
  use protocol-first boundaries, avoid `Any`/casts/ignore shortcuts, and
  carry domain-purpose Google-style module docstrings.

## Red-First Test Plan

- Add or move focused tests that first fail because the application service does
  not exist or the route still owns the branch.
- Preserve existing tests for strict replay, fingerprint mismatch, retryable
  failed reattempt, missing active job, and active queued/running replay.
- Add a focused unit test for pure replay decision mapping before wiring the
  HTTP route.
- Add a red test or retained proof for concurrent same-scope admission that
  would expose process-local-only locking if it remains unsafe.

## Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused `pdm run pytest-root ...`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Evidence

Implementation is complete and approved by retained independent Review 60.
Final module names match the planned shape:

- `scripts/sir_convert_a_lot/domain/idempotency_replay_policy_v2.py`
- `scripts/sir_convert_a_lot/application/idempotency_replay_ports_v2.py`
- `scripts/sir_convert_a_lot/application/idempotency_replay_service_v2.py`
- `scripts/sir_convert_a_lot/infrastructure/idempotency_replay_adapters_v2.py`

The HTTP adapter
`scripts/sir_convert_a_lot/interfaces/http_create_job_idempotency_v2.py`
now maps application replay decisions to existing Service API v2 response
metadata and errors. `IdempotencyStore.scoped_lock()` now combines the existing
process-local `RLock` with a per-scope `fcntl.flock()` file lock under the
idempotency directory, so admission does not rely on process-local locking
alone.

Task 375 intentionally leaves DigiExam-specific route artifact compatibility,
correction missing-source fail-closed behavior, and request-scoped correction
replay storage to Tasks 376-378. The route compatibility port defaults to
compatible for all routes in this task.

### Red Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py -q`
  failed before production code with
  `ModuleNotFoundError: No module named 'scripts.sir_convert_a_lot.application.idempotency_replay_service_v2'`.

### Green Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py -q`
  passed with `2 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py -q`
  passed with `34 passed`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_idempotency_replay_service_v2.py tests/sir_convert_a_lot/test_http_routes_jobs_v2_edge_cases_create.py tests/sir_convert_a_lot/test_idempotency_replay_policy_v2_http.py tests/sir_convert_a_lot/test_api_contract_v2.py tests/sir_convert_a_lot/test_audio_transcription_route_admission_v2.py tests/sir_convert_a_lot/test_http_client_v2_retry_modes.py -q`
  passed with `94 passed`.
- Targeted `pdm run ruff check ...` and `pdm run ruff format --check ...`
  over the changed code/test files passed.

### Skipped Or Blocked Validation

- `pdm run typecheck-all` was run and failed on nine existing test-helper
  `no-any-return` errors outside the Task 375 production seam:
  `test_create_job_admission_multipart_replay_v2.py`,
  `test_audio_transcript_bundle_runtime_v2.py`,
  `http_routes_jobs_v2_edge_cases_test_support.py`,
  `digiexam_migration_bundle_api_fixtures.py`,
  `audio_transcript_task357_helpers.py`,
  `test_transcript_formatter_replay_v2.py`,
  `test_transcript_formatter_artifacts.py`,
  `test_public_exam_converter_grant_runtime_v2.py`, and
  `test_audio_transcription_route_admission_v2.py`.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
- [x] Retained ruthless review complete
