---
id: task-331-remediate-review-24-task-330-correction-apply-contract-blockers
title: Remediate Review 24 Task 330 correction apply contract blockers
type: task
status: completed
priority: critical
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/reviews/review-24-ruthless-review-of-task-330-unified-correction-apply-api-contract-implementation.md
  - docs/backlog/tasks/task-330-implement-unified-source-neutral-exam-authoring-correction-apply-route-hard-cut.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-332-implement-matching-capable-source-state-producer-for-unified-corrections.md
labels:
  - review-remediation
  - task-330
  - correction-contract
  - service-api-v2
  - privacy
  - source-authority
---

PR-sized remediation unit for retained Review 24 blockers against the Task 330
unified correction apply API implementation.

## Objective

Remediate the four Review 24 findings before downstream PR-0332 treats
`POST /v2/exam-authoring/corrections/apply` as approved product authority:

1. Producer-state authority: the route must not treat caller-mutated source
   state as producer truth.
1. Advisory candidate digest validation: accepted advisory candidates must match
   their candidate payload digest before gaining reviewed provenance.
1. Mixed-batch artifact unlock: rejected entries must not partially unlock
   readiness or artifacts in the same batch.
1. Validation-error privacy: request validation failures must not echo raw
   submitted payload values.

This task does not reintroduce the abandoned Task 324 matching route and does
not add an adapter, shim, alias, wrapper, compatibility layer, or transitional
route.

## PR Scope

- Add server-verifiable source-state integrity for the unified correction route.
  The initial runtime may keep the source state in the request body, but it must
  verify both that the supplied `source_state_sha256` is the canonical digest of
  the supplied source-authoring state and that the source binding carries a
  Sir Convert-signed producer-state authority signature before any correction is
  applied. Review 24 re-review found that the first issuance route signed
  caller-submitted state; the remediated route now resolves a server-owned
  source-state artifact from a succeeded producer job before signing, and the
  DigiExam migration bundle producer writes that artifact during normal runtime
  output. The follow-up remediation widens the DigiExam source-state sidecar
  for text, point, choice, and gap/open-cloze correction families that can be
  grounded in real DigiExam producer state. DigiExam still emits zero matching
  interactions because `.dxe` runtime state has no canonical matching item
  type; downstream `manual_matching_answer_key` use is explicitly blocked on
  Task 332 until a matching-capable producer emits real matching state.
- Validate `accepted_advisory_candidate` payload digests against
  `candidate_lineage.candidate_payload_digest`. Preserve
  `teacher_edited_advisory_candidate` as teacher-provided provenance while still
  requiring lineage.
- Convert correction application to a two-phase flow: validate all entries and
  batch semantics before mutating effective state or projecting target readiness
  and artifact availability. Any rejected entry blocks artifact/readiness
  unlock for the batch.
- Sanitize FastAPI/Pydantic request-validation error details returned through
  the v2 service error envelope so raw submitted values, context payloads, and
  forbidden student/provider/source data fragments are not echoed.
- Add focused regression tests for all four Review 24 findings and keep the
  old Task 324 route absent from runtime/OpenAPI.
- Update Review 24 response status, Task 330/331 evidence, contract docs, and
  handoff after validation.

## Deliverables

- [x] Source-state digest verification rejects caller-mutated state even when
  the submitted binding is self-consistent.
- [x] Server-verifiable source-state authority rejects browser-local forged
  state even when the caller recomputes the canonical digest.
- [x] A producer-owned runtime/OpenAPI surface returns the signed
  `source_authoring_state`/`source_binding` bundle that downstream consumers may
  echo without knowing the signing secret, or downstream use is explicitly
  blocked on a separate governed task.
- [x] The source-state issuer refuses to sign browser-local or caller-forged
  state that is not resolved from server-owned producer state.
- [x] A real governed producer job writes
  `exam-authoring-correction-source-state.json` during normal runtime output;
  tests must not rely on manual fixture-only sidecar seeding.
- [x] A real producer-owned matching source state can be issued and accepted
  through the initial `manual_matching_answer_key` apply path, or downstream
  matching use is explicitly blocked on a separate governed task.
- [x] Advisory candidate digest validation accepts digest-matching reviewed
  candidates and rejects mismatches before provenance changes.
- [x] Teacher-edited advisory candidates with lineage stay teacher-provided and
  may differ from the candidate digest.
- [x] Mixed accepted/rejected batches return rejected report rows but do not
  unlock target readiness or artifacts.
- [x] Request validation errors omit raw submitted `input` and unsafe `ctx`
  values from the response body.
- [x] Review 24 is updated with remediation evidence, while remaining available
  for independent re-review.
- [x] Handoff blocks downstream `manual_matching_answer_key` use on Task 332
  even after Review 24 approval.

## Acceptance Criteria

- [x] A request whose supplied `source_authoring_state` is mutated without a
  matching canonical state digest fails closed before effective state, readiness,
  or artifacts are projected.
- [x] A request whose supplied `source_authoring_state` is forged and then
  re-digested by the caller fails closed against server-verifiable producer
  state before effective state, readiness, or artifacts are projected.
- [x] A downstream consumer can obtain the signed producer-state binding from a
  Sir Convert-owned runtime surface without access to
  `SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET`, or the docs
  explicitly block downstream use until that surface is implemented.
- [x] A caller cannot post forged source-authoring state to the issuance route,
  receive a valid signature, and then use that bundle to unlock readiness or
  artifacts through `/v2/exam-authoring/corrections/apply`.
- [x] A runtime test issues a real producer-owned matching state and applies a
  `manual_matching_answer_key` correction successfully; using an unsupported
  correction kind does not satisfy this criterion, or a governed follow-up task
  blocks downstream matching use until a real matching-capable producer exists.
- [x] `accepted_advisory_candidate` corrections require canonical submitted pair
  payload digest equality with `candidate_lineage.candidate_payload_digest`.
- [x] Advisory digest mismatch and missing lineage fail closed with
  privacy-safe error details.
- [x] `teacher_edited_advisory_candidate` corrections require lineage but map
  to `teacher_provided` effective provenance even when the teacher-submitted
  payload differs from the advisory digest.
- [x] Any batch containing a rejected entry returns no available artifacts and
  no ready target rows, unless a later governed contract explicitly introduces
  item/target-level partial success semantics.
- [x] Validation-error responses preserve location, error type, and message
  while removing raw submitted values and unsafe context fragments.
- [x] OpenAPI continues to expose the unified route and continues to omit the
  abandoned Task 324 route.
- [x] Validation gates pass after the real producer-owned matching apply fix or
  explicit downstream block.

## Validation Plan

- [x] `pdm run docs-validate`
- [x] `pdm run openapi-export-v2`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_api_contract_v2.py::test_requires_api_key_with_standard_error_envelope`
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Implementation Evidence

- Added canonical source-state and advisory-candidate digest helpers for the
  unified correction-apply route.
- Added a required `source_state_signature` binding over source-state digest,
  schema, bundle, and source-file identifiers. The route verifies it with
  `SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET` before
  applying corrections.
- Converted matching correction application to a two-phase flow that blocks
  effective-state mutation, readiness, and artifacts when any batch entry is
  rejected.
- Sanitized shared v2 request-validation error details so responses preserve
  bounded diagnostics without raw submitted values.
- Kept the superseded Task 324 route absent from runtime and OpenAPI.
- Added
  `POST /v2/exam-authoring/corrections/source-state/issue`, then remediated it
  so requests submit only `job_id` and the route signs only a server-owned
  source-state artifact from a succeeded producer job.
- Added normal runtime emission of
  `exam-authoring-correction-source-state.json` to the DigiExam migration bundle
  producer path, projected from producer-owned effective exam state.
- Re-review found that the emitted DigiExam source state contains no matching
  interactions, so it cannot exercise the initial supported
  `manual_matching_answer_key` correction path.
- Split the correction source-state DTOs into
  `exam_authoring_correction_source_state_models.py` to keep the apply DTO
  module scoped and under the repo module-size rule.
- Expanded DigiExam producer source-state projection so the normal runtime
  sidecar now exposes source-owned item title, prompt HTML, prompt lines,
  bounded `max_score`, choice interaction IDs/options/current key provenance,
  and gap/open-cloze interaction IDs/gaps/current accepted-value provenance.
- Kept DigiExam `matching_interactions` empty by design because the current
  DigiExam IR has no canonical matching item type. Task 332 is the governed
  follow-up for real `manual_matching_answer_key` downstream use against a
  matching-capable producer.

## Validation Evidence

- Focused correction-apply route tests: 12 passed.
- Focused route/OpenAPI/API-contract tests: 17 passed.
- `pdm run coverage-gate`: 1391 passed, 6 skipped, 95.56% coverage.
- Docs and handoff gates passed after closeout.
- 2026-05-18 follow-up remediation: focused correction route tests now include
  the forged source-state/recomputed-digest case and pass with 13 tests.
  Focused route/OpenAPI/API-contract tests pass with 18 tests; typecheck passes
  across 733 source files.
- 2026-05-18 re-review: signed verification rejects forged source state, but
  repo-wide search found no runtime producer-state issuance path that returns
  the signature to consumers.
- 2026-05-18 follow-up remediation: focused correction route tests now include
  source-state issuance and echoing the issued bundle into
  `/v2/exam-authoring/corrections/apply`; focused route tests pass with
  14 tests, OpenAPI contract tests pass with 4 tests, and `coverage-gate`
  passes with 1392 passed, 6 skipped, 95.56% coverage.
- 2026-05-18 re-review after source-state issuance: live forged
  issuer-to-apply probe returned `200`, proving the current issuer can mint
  authority for browser-local caller state. Review 24 remains
  `changes_requested`.
- 2026-05-18 follow-up remediation: the issuer now resolves job access, reads
  server-owned `exam-authoring-correction-source-state.json`, signs the binding
  from job/upload authority, and rejects caller-submitted
  `source_authoring_state`; focused correction route tests pass with 15 tests.
- 2026-05-18 re-review after producer-artifact issuance: repo-wide search found
  the source-state artifact writer used only by the correction-route test
  fixture, and a succeeded normal v2 job without fixture seeding returns
  `409 exam_authoring_source_state_artifact_missing` from the issuer. Review 24
  remains `changes_requested`.
- 2026-05-18 follow-up remediation: the DigiExam migration bundle producer now
  writes the source-state sidecar during normal runtime output. A real
  `digiexam_dxe -> examnet_migration_bundle` job can issue a signed bundle and
  pass that bundle through `/v2/exam-authoring/corrections/apply` without
  test-only sidecar seeding; the focused producer regression
  `test_digiexam_migration_job_emits_correction_source_state_for_issuer`
  passes.
- 2026-05-18 final remediation pass: the producer source-state sidecar now
  includes DigiExam-backed text/point/choice/gap surfaces and explicitly leaves
  matching absent. Focused producer source-state tests pass with 2 tests, the
  focused OpenAPI contract tests pass with 4 tests, `typecheck-all` passes over
  736 source files, and `openapi-export-v2` succeeds.
- 2026-05-18 re-review after real producer emission: producer authority is
  resolved, but the real issued state has zero matching interactions and the
  producer regression applies only an unsupported `point_correction`.
  Task 331 resolves this by expanding the DigiExam producer state for the
  correction kinds DigiExam can truthfully support and by creating Task 332 to
  block downstream matching use until a real matching-capable producer exists.
- 2026-05-18 independent Review 24 closeout: focused correction/OpenAPI/API
  contract and real DigiExam source-state tests pass with 22 tests;
  `typecheck-all` passes over 736 source files; `coverage-gate` passes with
  1395 passed, 6 skipped, and 95.56% coverage; docs-sync/docs-validate/
  skills-validate/handoff-validate and `git diff --check` pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
