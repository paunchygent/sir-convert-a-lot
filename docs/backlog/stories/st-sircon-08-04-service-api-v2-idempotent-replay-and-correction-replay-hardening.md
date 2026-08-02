---
type: story
id: ST-SIRCON-08-04
title: Service API v2 idempotent replay and correction replay hardening
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: active
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SIRCON-08
links:
  decisions: []
acceptance_criteria:
- Same-key/same-fingerprint `succeeded` replays remain strict only when the active
  job satisfies the current route artifact compatibility contract.
- A legacy DigiExam `succeeded` job that lacks `answer_key_review_state_report` is
  not returned as a strict replay for a fresh upload of the same file/key.
- The stale-success remediation preserves lineage to the old job and records a typed,
  content-safe reason for the service-owned reattempt or fail-closed response.
- Same-key/different-fingerprint conflicts and retryable failed service reattempts
  keep the Task 368 behavior.
- Idempotency/correction replay business policy is centralized in domain/application
  services with protocol ports; HTTP routes and filesystem stores do not own replay
  decisions.
- Correction apply fails closed when a signed source binding points to a missing or
  inaccessible source job.
- Correction replay artifacts are request-scoped and cannot be overwritten or aliased
  by a later correction apply for the same source job.
- Contract docs and OpenAPI are synchronized for any new admission reason, replay
  action, route compatibility, or artifact-reference shape.
- Deployed production proof covers a stale incompatible DigiExam replay, a compatible
  strict replay, correction apply missing-source fail-closed behavior, and request-scoped
  correction replay downloads.
retired_ids:
- story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening
---

## Context

## Epic Contract Slice

## ADR Coverage

## Contract Inputs

## Live Verification Plan

## Non-Goals

## Notes

## Decision And Assumption Ledger

## Plan Document Review

## Story Closeout Review

## Historical Source Content

Implementation slice with acceptance-driven scope.

### Objective

Harden Service API v2 replay semantics so idempotent replays remain safe after
route contracts evolve and correction replay artifacts stay bound to the exact
teacher request that produced them.

The 2026-06-29 production incident showed a same-owner, same-key, same-source
fingerprint DigiExam upload replaying an old `succeeded` job that predated the
`answer_key_review_state_report` artifact. The Service API returned the stale
job as a strict idempotent replay, while Skriptoteket now requires the compact
review-state report to render the exam converter workflow. A separate review of
the correction apply path found two related replay risks: missing source jobs
can be skipped instead of failing closed, and correction replay artifacts are
stored under source-job scoped static names rather than request-scoped
identity.

This story centralizes idempotent replay and correction replay policy behind
protocol-first application/domain services, keeps filesystem/runtime details in
infrastructure adapters composed through Dishka where beneficial, and preserves
Sir Convert as the product-neutral producer of route artifact contracts.

### Scope

- Move Service API v2 replay policy out of interface-edge helper logic and into
  a small application service backed by domain decision types and protocol
  ports.
- Keep the HTTP routes thin: routes validate transport/auth/body concerns,
  then call the replay service for business decisions.
- Define route-specific terminal artifact compatibility as a Sir Convert
  contract concern. For DigiExam migration bundles, a `succeeded` replay is
  compatible only when the persisted manifest/artifacts satisfy the current
  route contract, including `answer_key_review_state_report` where required.
- Preserve existing idempotency semantics for same-key/different-fingerprint
  conflicts and retryable failed reattempts from Task 368.
- Make correction apply fail closed when a signed source binding references a
  source job that cannot be resolved.
- Bind correction replay artifacts to request-scoped identity so two correction
  applies for the same source job cannot overwrite, alias, or expose each
  other's artifacts.
- Update API/converter contract docs and generated OpenAPI where route
  response or artifact-reference shapes change.
- Require a downstream Skriptoteket proof after deployment, but do not solve
  producer replay drift with a consumer-local fallback or browser-side
  re-inference.

### Implementation Tasks

1. `docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md`
   creates the shared policy spine, ports, and DI seam. Implementation is
   approved in retained Review 60.
1. `docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md`
   is implemented and approved in retained Review 61 for route artifact
   compatibility inspection and stale succeeded replay remediation.
1. `docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md`
   is implemented and review-ready after Review 62 missing-grant remediation.
1. `docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md`
   makes replay artifact references request-scoped and non-aliasing.
1. `docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md`
   adds the retained Story 58 proof-runner support for live Service API replay
   evidence without mutating production idempotency or artifact state.

### Closed Decision Ledger

Three read-only explorers mapped the current idempotency, DigiExam artifact,
and correction replay code paths before these decisions were closed. The
implementation agent must treat these as the Story 58 decision authority and
must not rebuild on the brittle current behavior where it conflicts with this
ledger.

### Architecture Decisions

- Public replay vocabulary keeps `idempotency.state = service_reattempt` for
  every service-admitted fresh attempt under an existing idempotency scope. A
  typed `idempotency.reason` distinguishes causes, including
  `retryable_failed_terminal` and
  `terminal_artifact_contract_incompatible`. Do not add
  `contract_reattempt`.
- Domain decision types live in `domain/idempotency_replay_policy_v2.py` and
  cannot import HTTP, filesystem stores, runtime engines, or Pydantic response
  DTOs.
- Application ports live in `application/idempotency_replay_ports_v2.py`; the
  orchestration service lives in `application/idempotency_replay_service_v2.py`.
- Infrastructure adapters own filesystem idempotency records, job
  lookup/admission, DigiExam terminal artifact compatibility inspection, and
  correction replay artifact identity/storage.
- Compose infrastructure-backed adapters and the replay service through a small
  app-scope Dishka provider or equivalent app-state composition seam. Pure
  domain decision values remain directly constructible.
- HTTP routes validate transport/auth/body/upload inputs and map application
  decisions to responses; they do not own replay branching.
- The implementation must harden admission locking before broadening reattempt
  causes: add file-level/CAS locking for idempotency writes or prove the
  production admission path is single-process. Do not bless the current
  process-local lock as a durable foundation without proof.

### Route Compatibility Decisions

- DigiExam strict replay compatibility applies only to persisted `succeeded`
  jobs for route `digiexam_dxe -> examnet_migration_bundle`.
- A DigiExam success is strict-replay compatible only when its current terminal
  artifact contract is satisfied: valid `digiexam_migration_bundle_v3`
  manifest, matching job id, current required artifact keys, valid readiness
  and answer-key review-state pointers, current source/effective schema
  versions, parsable `target_readiness_report_v1`, parsable
  `digiexam_answer_key_review_state_v1`, and existing bytes with matching
  size/hash for every `available` artifact entry. The manifest self-entry may
  remain hash/size exempt unless the writer changes.
- `complete`, `partial`, `needs_review`, and schema-valid `failed` bundle
  statuses can be compatible terminal workflow states when required reports,
  pointers, schema versions, and available bytes are valid. Manual follow-up is
  also compatible. Strict replay must not require all PDF/QTI targets to be
  exportable; `target_readiness_report_v1` remains the export authority.
- Correction replay artifact presence is not part of Task 376 strict replay
  compatibility. Tasks 377 and 378 must first close source-job fail-closed
  behavior and request-scoped replay identity.
- A stale incompatible success admits a service-owned reattempt when the current
  create-job request can be safely admitted. The public action remains
  `service_reattempt`; the reason is
  `terminal_artifact_contract_incompatible`.
- If no safe fresh admission can be made, return a standard non-2xx error
  envelope, not a synthetic failed job. Use
  `409 idempotent_terminal_artifact_contract_incompatible` unless a more
  specific admission error applies.
- Register route terminal-artifact compatibility beside the v2 route policy,
  using a named contract/inspector port. HTTP routes must not contain
  route-specific DigiExam compatibility branches.
- Routes without a declared terminal-artifact compatibility contract remain
  strict-replay compatible under the existing semantics.

### Correction Replay Decisions

- Correction apply validates request schema, source-state digest, and
  source-state signature before source-job lookup. This preserves stale/forged
  binding behavior and prevents source-job probing.
- When a validated binding carries `source_bundle_id`, the application service
  resolves and authorizes that source job before returning any success that
  includes exportable target readiness, artifact availability, or replay
  references.
- A missing or expired source job returns
  `409 exam_authoring_correction_source_job_unavailable`. Wrong owner or
  missing grant remains `403 exam_authoring_correction_replay_access_denied`.
- Success without source-job lookup is only allowed for a future explicitly
  non-artifact correction mode with no `source_bundle_id`, no exportable target
  rows, no available artifact availability, and no replay references. Current
  DigiExam correction apply must fail closed if the bound source job is gone.
- Correction replay artifacts use immutable request-scoped artifact sets and
  the nested route
  `/v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}`.
  Static `correction_replay_*` keys on the existing named-artifact route are not
  sufficient identity.
- Request-scoped identity includes `request_id`, validated source-binding
  digest, `source_state_sha256`, normalized correction payload digest,
  requested target-set digest, replay profile/schema version, artifact content
  hashes, and created timestamp in an artifact-set manifest.
- Exact duplicate normalized requests may return the same verified artifact set.
  Reusing the same `request_id` with different normalized content returns
  `409 exam_authoring_correction_replay_request_conflict`. Different correction
  payloads for the same source job produce distinct artifact sets.
- Store immutable sets under
  `correction-replays/{artifact_set_id}/manifest.json` plus target files so a
  later sweeper can enforce retention by parent job, timestamp, status, and
  manifest version. Physical cleanup is deferred from this story.
- Missing artifact sets return `404 correction_replay_artifact_set_not_found`.
  Wrong job/set/key/hash returns
  `409 correction_replay_artifact_reference_mismatch`. Never fall back to
  latest bytes.

### Cross-Repo And Proof Decisions

- Generated OpenAPI changes to correction replay references require a bounded
  Skriptoteket slice in the same story closeout for generated types,
  parser/adapter updates, file-action routing, and fail-closed UI behavior for
  missing producer references.
- The active API/converter docs must be updated when implementation lands.
  Before code changes, Story 58 and Tasks 375-378 are the planning authority;
  do not edit active API contracts to claim behavior that has not shipped.
- Production proof must include the previously failing
  `ak7_lag_och_ratt_with_image.dxe` case, one compatible strict replay, one
  stale incompatible replay, missing-source correction apply, exact duplicate
  retry, two different correction applies for the same source job, and
  stale/mismatched reference download failure.
- Historical incompatible production idempotency records remain untouched unless
  a separate governed operations task authorizes cleanup. Production
  idempotency or artifact surgery is not the remediation.
- Retained proof may record redacted job ids, route id, replay action/reason,
  source-state/schema versions, request id, source-binding digest,
  correction-request digest, artifact-set id, artifact key, content hash, HTTP
  status/error code, and UI screenshots where relevant. It must not retain raw
  exam content, signatures, private paths, secrets, idempotency keys, raw
  identity/grant envelopes, uploaded bytes, source text, or provider prompts.

### Live Proof Current State

- The canonical Skriptoteket Gateway proof for stale DigiExam replay is
  `scripts/story58_gateway_stale_replay_proof.py`; it uses HuleEdu
  browser-session login, CSRF, multipart DXE upload, and Gateway `/sir-convert`
  routing. It remains the route-true stale proof surface when an unexpired
  same-owner stale idempotency scope is available.
- The 2026-06-30 production stale smoke at
  `.artifacts/story-58-gateway-stale-replay/20260630T033858Z/manifest.redacted.json`
  computed the expected request/scope digests for a projected stale row but
  observed `idempotency.state = fresh_admission`, so it does not close the
  stale replay requirement.
- Current read-only production state on service revision
  `7a32e47857019b2c0077c0976e573c7d928aa1a9` is retained at
  `build/verification/story-58-prod-stale-replay-current-state/20260630T171951Z/summary.json`.
  It records that the previously expected stale scope digest and both
  recovered-owner projection digests are absent from the production idempotency
  volume. Re-running those expired projected rows would produce fresh admission
  rather than proving `service_reattempt`.
- The stale replay closeout therefore requires a new unexpired same-owner stale
  idempotency scope or an approved non-production stale setup. Do not mutate
  production idempotency records, artifacts, or source jobs to manufacture this
  proof.

### Acceptance Criteria

- [ ] Same-key/same-fingerprint `succeeded` replays remain strict only when the
  active job satisfies the current route artifact compatibility contract.
- [ ] A legacy DigiExam `succeeded` job that lacks
  `answer_key_review_state_report` is not returned as a strict replay for a
  fresh upload of the same file/key.
- [ ] The stale-success remediation preserves lineage to the old job and records
  a typed, content-safe reason for the service-owned reattempt or fail-closed
  response.
- [ ] Same-key/different-fingerprint conflicts and retryable failed service
  reattempts keep the Task 368 behavior.
- [ ] Idempotency/correction replay business policy is centralized in
  domain/application services with protocol ports; HTTP routes and
  filesystem stores do not own replay decisions.
- [x] Correction apply fails closed when a signed source binding points to a
  missing or inaccessible source job.
- [x] Correction replay artifacts are request-scoped and cannot be overwritten
  or aliased by a later correction apply for the same source job.
- [x] Contract docs and OpenAPI are synchronized for any new admission reason,
  replay action, route compatibility, or artifact-reference shape.
- [ ] Deployed production proof covers a stale incompatible DigiExam replay, a
  compatible strict replay, correction apply missing-source fail-closed
  behavior, and request-scoped correction replay downloads.

### Test Requirements

- [ ] Red-first tests prove a legacy DigiExam success missing the current
  review-state artifact does not strict replay.
- [ ] Red-first tests prove a compatible generic document success still strict
  replays.
- [x] Red-first tests prove a signed correction apply with missing source job
  does not return HTTP 200 with partial replay artifacts.
- [x] Red-first tests prove two correction apply requests for the same source
  job return distinct artifact identities and the first reference does not
  resolve to the second request's bytes.
- [ ] Focused tests run through `pdm run pytest-root ...`; closeout also runs
  `pdm run format-all`, `pdm run lint-fix`, `pdm run typecheck-all`,
  `pdm run coverage-gate`, `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

### Done Definition

Story 58 is complete only when Tasks 375-378 are implemented, independently
reviewed, deployed to Hemma where behavior is production-relevant, and retained
proof shows the production Exam Converter path no longer replays stale
contract-incompatible DigiExam jobs or aliases correction replay artifacts.

### Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

### Current Implementation Status

- Tasks 376, 377, and 378 are implemented and approved in Reviews 61–63
  (2026-06-30). The service now gates DigiExam strict replay on the current
  terminal-artifact contract, fails closed on unavailable signed source jobs,
  and stores correction replay artifacts in immutable request-scoped sets.
- Incompatible DigiExam successes are admitted as
  `idempotency.state = service_reattempt` with reason
  `terminal_artifact_contract_incompatible`; unavailable source jobs return
  `409 exam_authoring_correction_source_job_unavailable`; request conflicts,
  missing sets, and reference mismatches use the typed errors in the ledger.
- Task 379 adds the manifest-driven `pdm run proof:story58-live-replay` runner.
  It retains redacted matrix metadata and fails when readiness/revision proof or
  declared case invariants are missing. It is proof support, not story closeout.
- The HuleEdu Gateway route omission that blocked correction replay download/save
  was fixed in commit `f72e7c6cdb1a`; retained Dev/Prod evidence shows nested
  replay downloads, Save to My Files, and mismatch handling passing. No producer
  replay or idempotency fallback was introduced.
- Story closeout remains open: retained Dev evidence covers compatible replay,
  duplicate/distinct correction sets, and missing-source fail-closed behavior,
  but the full production stale-incompatible DigiExam replay and owner-scoped
  correction matrix still require sanctioned fresh evidence. Production records
  must not be mutated to manufacture that proof.
- Latest focused proof-runner tests passed (6 tests); format, lint, typecheck,
  and coverage gates passed in the retained refresh (`1799 passed, 6 skipped`,
  95.54% coverage).
