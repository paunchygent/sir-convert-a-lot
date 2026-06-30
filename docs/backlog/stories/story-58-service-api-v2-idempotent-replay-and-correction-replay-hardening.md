---
id: 'story-58-service-api-v2-idempotent-replay-and-correction-replay-hardening'
title: 'Service API v2 idempotent replay and correction replay hardening'
type: 'story'
status: 'in_progress'
priority: 'high'
created: '2026-06-29'
last_updated: '2026-06-30'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-57-cross-repo-compact-answer-key-review-state-production-proof.md
  - docs/backlog/tasks/task-368-centralize-retryable-failed-idempotency-reattempts-in-service-api-v2.md
  - docs/backlog/tasks/task-373-project-compact-digiexam-answer-key-review-state-for-skriptoteket.md
  - docs/backlog/tasks/task-374-preserve-advisory-candidates-during-correction-apply-replay.md
  - docs/backlog/tasks/task-375-centralize-protocol-first-idempotent-replay-policy-in-service-api-v2.md
  - docs/backlog/tasks/task-376-gate-idempotent-succeeded-replays-on-route-artifact-contract-compatibility.md
  - docs/backlog/tasks/task-377-fail-closed-when-correction-replay-source-jobs-are-unavailable.md
  - docs/backlog/tasks/task-378-bind-correction-replay-artifacts-to-request-scoped-identity.md
  - docs/backlog/tasks/task-379-retain-story-58-live-replay-closeout-proof.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/reference/ref-story-58-live-proof-operator-manifest-contract.md
labels:
  - service-api-v2
  - idempotency
  - replay
  - correction-apply
  - exam-migration
  - ddd
  - dishka
  - skriptoteket
---

Implementation slice with acceptance-driven scope.

## Objective

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

## Scope

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

## Implementation Tasks

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

## Closed Decision Ledger

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

## Acceptance Criteria

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

## Test Requirements

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

## Done Definition

Story 58 is complete only when Tasks 375-378 are implemented, independently
reviewed, deployed to Hemma where behavior is production-relevant, and retained
proof shows the production Exam Converter path no longer replays stale
contract-incompatible DigiExam jobs or aliases correction replay artifacts.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized

## Current Implementation Status

Task 376 is implemented and approved in Review 61 as of 2026-06-30. Service
API v2 now declares the `digiexam_migration_bundle_v3` terminal artifact
compatibility contract on the DigiExam migration route policy and composes an
infrastructure inspector through the Task 375 replay service seam. A stale
same-key, same-fingerprint DigiExam `succeeded` job missing the current
`answer_key_review_state_report` contract no longer returns as strict replay
when the fresh request can be safely admitted; it returns
`idempotency.state = service_reattempt` and
`idempotency.reason = terminal_artifact_contract_incompatible`.

Task 377 is implemented and approved in Review 62 as of 2026-06-30. Source-bound
correction apply now validates request schema, source-state digest, and
source-state signature before source-job lookup, then fails closed with
`409 exam_authoring_correction_source_job_unavailable` when a validated
`source_bundle_id` no longer resolves. Wrong-owner source jobs remain
`403 exam_authoring_correction_replay_access_denied`, and valid producer-backed
DigiExam correction apply still returns replay artifacts. Task 377 does not
implement request-scoped correction replay artifact identity.

Task 378 is implemented and approved in Review 63 as of 2026-06-30. Correction
replay artifacts now use
request-scoped immutable artifact sets under
`correction-replays/{artifact_set_id}/manifest.json`, typed
`correction_replay_artifact_reference_v1` references, and the nested download
route
`/v2/convert/jobs/{job_id}/correction-replays/{artifact_set_id}/artifacts/{artifact_key}`.
Exact duplicate normalized correction requests reuse the same verified
artifact set, reusing the same `request_id` with different normalized content
returns `409 exam_authoring_correction_replay_request_conflict`, missing sets
return `404 correction_replay_artifact_set_not_found`, and wrong job/set/key or
hash returns `409 correction_replay_artifact_reference_mismatch`. Static
`correction_replay_*` keys on the named-artifact route are no longer the
download authority for corrected replay artifacts. Generated OpenAPI now
exposes the nested route and typed reference shape; a bounded Skriptoteket
consumer slice remains required before Story 58 closeout for generated types,
parser/adapter updates, file-action routing, and fail-closed UI behavior.

2026-06-30 correction replay download/save incident closeout: production
download and Save to My Files failed for `ak7_lag_och_ratt_with_image.dxe`
after successful correction conversion because HuleEdu Gateway did not expose
Sir Convert's nested correction replay artifact route. This was not a Sir
Convert replay/idempotency failure, not a File Service failure, and not a
Skriptoteket stale-reference fallback. HuleEdu fixed the Gateway route in
commit `f72e7c6cdb1a` and deployed it to production. Retained downstream proof
now shows the real `ak7_lag_och_ratt_with_image.dxe` production path passing
after the Sir Convert `7a32e47857019b2c0077c0976e573c7d928aa1a9`
deploy at
`/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/.artifacts/playwright-pr-0337-correction-session-live/20260630T154502Z/manifest.redacted.json`.
The proof uses the canonical HuleEdu browser-session Playwright helper,
retains `service-monitoring.json` and service logs from the active
Gateway/File/Sir Convert/Skriptoteket services, and proves AI key accept/edit
flows, auto-next/reload state, nested replay PDF/QTI downloads `200`, Save to
My Files `200`, PDF/QTI content inspection, mobile files/report surfaces, and
`409 correction_replay_artifact_reference_mismatch` for a mismatched nested
replay artifact reference. It also retained a private request-capture manifest
outside the repo at
`/Users/olofs_mba/.story58-private-captures/20260630T-prod-gateway-owner-proof-rerun2/manifest.json`
with 30 captured Gateway requests: 8 correction apply calls and 22 source-state
issue calls. Earlier Dev/Prod downstream bundles remain retained at
`20260630T111643Z`, `20260630T110339Z`, and `20260630T133443Z`.

Final closeout for this story is a story-level gate, not the end of any single
task. Tasks 375-378 are necessary prerequisites only. Story 58 remains open
until live dev and production evidence proves the changed idempotency/replay
contracts through the Sir Convert service surfaces and downstream product
consumers, including the Skriptoteket companion slice for Task 378's nested
correction replay artifact references. The correction replay download/save
incident is closed by the Dev/Prod evidence above; the broader stale-success
replay acceptance remains open until the explicit stale incompatible replay
proof is retained.

Task 379 is implemented, repaired after Review 64 `changes_requested`, and
approved in the Review 64 pass-2 follow-up. It adds
`pdm run proof:story58-live-replay`, a manifest-driven runner that executes
operator-declared safe Service API v2 requests, writes redacted evidence under
`build/verification/story-58-live-replay-proof/<timestamp>/`, records every
Story 58 matrix case as `passed`, `failed`, `skipped`, or
`requires_governed_setup`, preserves only approved metadata, enforces
code-owned Story 58 case invariants, and fails overall proof when `/readyz`
does not prove readiness plus `service_revision`. This is proof support, not
final proof: Story 58 remains open until the actual Dev/Prod manifests are run
and retained for the full matrix.
The operator manifest and private-input contract for that final proof is
`docs/reference/ref-story-58-live-proof-operator-manifest-contract.md`.
The runner now retains v2 `route_key` metadata from result responses and
matches it to the idempotency job id when create-job responses carry replay
state but not route metadata.

2026-06-30 current partial live Service API proof was refreshed after both Dev
and Prod lanes were on `e49cb9efdf23f8202a6de155a88ad5851fa83b6e`. The
real-DXE Dev proof is retained at
`build/verification/story-58-live-replay-proof-dev-digiexam-real/20260630T133051Z/summary.json`.
It uses the real `1776888013-ak7-lag-och-ratt.dxe` fixture with HuleEdu-signed
local internal identity headers, captures `sir_convert_a_lot_dev` Docker logs
to file, and proves `compatible_strict_digiexam_replay` passed: fresh admission
`200`, strict replay `200` with the same job id, and result metadata `200` with
`route_key = digiexam_dxe_to_examnet_migration_bundle`.

The safe generic idempotency smoke bundles are retained at
`build/verification/story-58-live-replay-proof-dev-e49-generic/20260630T133156Z/summary.json`
and
`build/verification/story-58-live-replay-proof-prod-e49-generic/20260630T133223Z/summary.json`.
Both runs prove deployed revision `e49cb9efdf23f8202a6de155a88ad5851fa83b6e`
and retain per-request Service API responses showing generic `fresh_admission`
followed by `strict_replay` against the same live job id. The Dev and Prod
bundles also retain log-capture files or monitoring pointers for the test
window. These bundles prove the shared generic idempotency path remains live in
Dev and Prod, but their `overall_status` is `requires_governed_setup` and they
do not close the story-level DigiExam stale replay/correction replay matrix.
Current production generic Service API proof after the proof-runner multipart
transport follow-up is retained at
`build/verification/story-58-live-replay-proof-prod-current-generic-7a32/20260630T160411Z/summary.json`.
It proves deployed revision `7a32e47857019b2c0077c0976e573c7d928aa1a9`,
`fresh_admission` followed by `strict_replay` for
`jobv2_450466bdb3ec4c85bcaf01e87f`, and redacted
`sir_convert_a_lot_prod` Docker log capture for the same live request window.
Its `overall_status` remains `requires_governed_setup` because the broader
Story 58 matrix cases were intentionally undeclared in that safe smoke run.

2026-06-30 Dev correction replay Service API proof now covers the correction
matrix rows with private signed bodies derived from the real downstream `ak7`
DXE product proof. Duplicate retry and mismatched nested artifact evidence is
retained at
`build/verification/story-58-live-replay-proof-dev-service-correction-matrix/20260630T150721Z/summary.json`:
the exact duplicate correction apply returned `200` twice and reused
`crset_c7002ca4a1e4d63ef9ffb8fdb88b43ba`, while the nested artifact route
returned `409 correction_replay_artifact_reference_mismatch` for a mismatched
content hash. Distinct correction apply evidence is retained at
`build/verification/story-58-live-replay-proof-dev-service-correction-distinct/20260630T151122Z/summary.json`:
the baseline correction apply used `crset_c7002ca4a1e4d63ef9ffb8fdb88b43ba`
and the changed teacher correction produced
`crset_ae5da7ef4dac170d9e53e72858bedaf3`. Missing-source correction apply
evidence is retained at
`build/verification/story-58-live-replay-proof-dev-service-correction-missing-source/20260630T151411Z/summary.json`:
a validly signed request for an unavailable source job returned
`409 exam_authoring_correction_source_job_unavailable`. These are live Dev
Service API rows with retained Docker log evidence, but they do not close the
full story because Prod correction matrix and stale incompatible DigiExam replay
proof remain separate final-closeout requirements.

2026-06-30 production `ak7` idempotency lineage evidence is retained at
`build/verification/story-58-prod-ak7-idempotency-lineage/20260630T075602Z/summary.json`.
It proves, from production filesystem metadata only, that the stale
`jobv2_ee82aa292cbe4a0f9a32be439a` identity-owned `ak7` DigiExam success lacks
`answer_key_review_state_report` while the active idempotency successor
`jobv2_4d3f85b3252e49879ee632ce30` has that current report artifact. This is
useful production lineage, but it is not final Story 58 proof: closeout still
requires retained live Service API or Gateway response evidence for the stale
incompatible replay with `idempotency.state = service_reattempt` and
`idempotency.reason = terminal_artifact_contract_incompatible`, plus the
remaining compatible replay and correction replay matrix cases.

2026-06-30 owner-scope discovery confirmed that API-key-only Service API calls
cannot replay production correction requests owned by the HuleEdu browser
identity. HuleEdu Gateway signs `InternalIdentityContextV1` with
`source_app = skriptoteket` and the required route grants, while Sir Convert's
owner scope derives from that signed identity context. A direct Prod Service
API correction proof therefore requires a sanctioned HuleEdu surface that
provides fresh owner-matching signed headers; reconstructing or self-minting
headers from production data is not acceptable story evidence. Until such a
surface exists, the production owner-scoped proof lane is the Gateway/browser
route, and direct API-key runner evidence remains transport proof only.

2026-06-30 proof-readiness snapshot is retained at
`build/verification/story-58-proof-readiness/20260630T080317Z/summary.json`.
It confirms Dev and Prod `/readyz` still expose the expected service revisions
and records the current private-input gap without retaining any private values:
this shell has the Service API key, but not the operator-private identity/grant
headers, historical `ak7` idempotency key and source, source-state signing
material, or prepared signed correction request bodies needed to execute the
full matrix. The proof runner can execute prepared private JSON bodies and
metadata-only dependent path/query/header interpolation; body interpolation is
not part of the approved Task 379 contract.

Latest local gate refresh after the route-key proof-runner follow-up passed:
focused Story 58 proof-runner route-key suite `6 passed`; `format-all`
`983 files left unchanged`; `lint-fix` passed; `typecheck-all` passed over
`934 source files`; and `coverage-gate` passed `1799 passed, 6 skipped`,
coverage `95.54%`.
