---
id: review-24-ruthless-review-of-task-330-unified-correction-apply-api-contract-implementation
title: Ruthless review of Task 330 unified correction apply API contract implementation
type: review
status: completed
priority: critical
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/tasks/task-331-remediate-review-24-task-330-correction-apply-contract-blockers.md
  - docs/backlog/tasks/task-330-implement-unified-source-neutral-exam-authoring-correction-apply-route-hard-cut.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/reviews/review-23-ruthless-review-of-adr-0011-source-neutral-correction-apply-contract.md
labels:
  - review
  - approved
  - task-330
  - api-contract
  - exam-authoring
  - source-neutral
  - correction-apply
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless API contract implementation review of the latest
  Task 330 unified correction apply route state.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/070-testing-and-quality-gates.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-330-implement-unified-source-neutral-exam-authoring-correction-apply-route-hard-cut.md`
  - `docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md`
  - `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md`
  - `docs/converters/exam-authoring-corrections-apply-contract.md`
  - `docs/converters/exam-authoring-ir-v1-contract.md`
  - `docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md`
- Scope under review:
  - `POST /v2/exam-authoring/corrections/apply`
  - Task 330 runtime/OpenAPI hard cut from the superseded Task 324 matching
    route.
  - Source-neutral `manual_matching_answer_key` correction application.
  - Request validation, source binding, effective state, correction report,
    target readiness, artifact availability, and privacy semantics.
- Files reviewed:
  - `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_models.py`
  - `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py`
  - `scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_api.py`
  - `tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py`
  - `tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  - `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
  - `docs/converters/exam-authoring-corrections-apply-contract.md`
  - `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md`
- Public surfaces affected:
  - `POST /v2/exam-authoring/corrections/apply`
  - Generated v2 OpenAPI contract.
  - HuleEdu `/sir-convert` proxy target route.
  - Skriptoteket PR-0332 teacher-correction consumer contract.
- Compatibility posture:
  - Clean hard cut is correct: the Task 324
    `/v2/exam-authoring/matching/manual-answer-key/apply` route must remain
    absent and must not reappear as an adapter, shim, alias, wrapper,
    transitional route, or compatibility layer.
  - Review does not request compatibility for the old route.
  - Blocking gaps are in unified-route contract completeness: producer-state
    authority, advisory lineage, batch unlock semantics, and privacy-safe
    validation errors.
- Evidence reviewed:
  - Working-tree re-review on 2026-05-18, starting from latest commit
    `7a791f0a11dc25c7b37bd714e5ceec11d9ec6dbf`.
  - Focused route/OpenAPI tests passed:
    `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_openapi_contract_v2.py`
    -> 9 passed.
  - Live probes against HEAD reproduced the source-state tampering, candidate
    digest, mixed-batch unlock, and validation-error privacy failures described
    below.

## Findings

1. [x] `blocker` - Source binding is only client self-consistency, not producer
   authority.

   Evidence:

   - The route validates only that
     `source_binding.source_state_sha256` equals
     `source_authoring_state.source_state_sha256` in
     `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py:124`.
   - Both values are submitted by the caller, and the implementation does not
     resolve a canonical producer state, stored job state, signed state token,
     or server-side digest before applying corrections.
   - Live probe: mutating a submitted matching source choice ID to
     `browser-local-source`, updating the correction pair to reference that
     browser-local ID, and leaving the submitted source-state digest unchanged
     returned `200`, accepted `manual_matching_answer_key`, and reported
     `examnet_pdf` ready.
   - ADR-0011 requires Sir Convert to own source-binding checks, effective-state
     projection, target readiness, and artifact availability at
     `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md:97`.
   - The converter contract says browser-local edits are never authoritative
     and consumers can enable export only after Sir Convert returns accepted
     effective state and readiness at
     `docs/converters/exam-authoring-corrections-apply-contract.md:66`.

   Why it matters:
   A consumer can submit browser-local or stale source state and have Sir Convert
   treat it as producer-owned authority. That collapses the core ADR-0011
   boundary: downstream browser drafts become the source of truth for readiness
   and artifact availability.

   Required fix:
   Bind correction requests to server-verifiable producer state. Acceptable
   shapes include a job/source-state token resolved by Sir Convert, a stored
   source-state digest loaded server-side from the conversion bundle, or a
   signed producer state envelope. The route must validate corrections against
   the canonical producer-returned state, not against caller-supplied state
   alone.

   Proof requirement:
   Add a regression test that mutates `source_authoring_state` while keeping the
   submitted binding self-consistent and expects fail-closed before effective
   state, readiness, or artifact availability is projected. Run the focused
   route tests, OpenAPI tests, typecheck, coverage gate, and docs gates.

   Re-review disposition:
   Still blocked on 2026-05-18. Task 331 now rejects a stale submitted digest,
   but it still verifies only the caller-submitted source state against a
   caller-refreshable canonical digest in
   `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py:171`
   and
   `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_integrity.py:33`.
   Live re-review probe: after mutating a matching source choice to
   `browser-local-source` and recomputing the submitted digest, the route still
   returned `200`, accepted `manual_matching_answer_key`, and reported
   `examnet_pdf` ready. The remaining fix must bind to server-verifiable
   producer state, not merely a canonical digest of the submitted payload.

   Remediation response after follow-up:
   Task 331 now requires `source_binding.source_state_signature`, a Sir Convert
   server signature over source-state digest, source-authoring schema version,
   source bundle ID, and source file digest. The correction route verifies this
   signature with
   `SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET` before
   applying corrections. The forged browser-local source-state probe now
   recomputes the canonical digest but keeps the original producer signature and
   fails closed with `stale_exam_authoring_source_state_authority`. This finding
   remains unchecked until independent re-review verifies the remediation.

   Re-review disposition after signed-authority follow-up:
   Still blocked on 2026-05-18. The verifier now rejects forged source state
   when the caller recomputes the digest but cannot recompute Sir Convert's
   signature. However, repo-wide search found `source_state_authority_signature`
   used only by the verifier and test fixture, not by a runtime producer route
   or source-state issuance surface. The contract says consumers may echo
   `source_state_signature` from producer-returned state, but current
   runtime/OpenAPI only verifies the field on
   `POST /v2/exam-authoring/corrections/apply`; it does not expose the
   producer-owned source-authoring state with that signature. A downstream
   consumer therefore cannot submit a legitimate signed request without knowing
   the server secret, which it must not know. The remaining fix is to add or
   wire the producer-owned source-state issuance path that returns the signed
   `source_authoring_state`/`source_binding` bundle, or explicitly scope
   downstream use as blocked until that separate governed surface exists.

   Remediation response after source-state issuance follow-up:
   Task 331 now adds
   `POST /v2/exam-authoring/corrections/source-state/issue`, a Service API v2
   runtime/OpenAPI surface that canonicalizes sanitized producer
   `source_authoring_state`, recomputes `source_state_sha256`, and returns the
   signed `source_binding` bundle using the server-held
   `SIR_CONVERT_A_LOT_EXAM_AUTHORING_SOURCE_STATE_SIGNATURE_SECRET`. The
   focused route regression issues a bundle through that route and then echoes
   the returned `source_authoring_state`/`source_binding` into
   `POST /v2/exam-authoring/corrections/apply`, which returns `200` without the
   test or downstream caller minting a signature. This finding remains
   unchecked until independent re-review verifies the remediation.

   Re-review disposition after source-state issuance follow-up:
   Still blocked on 2026-05-18. The new issuance route exists in
   `scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py:51`
   and delegates to
   `scripts/sir_convert_a_lot/application/exam_authoring_correction_source_state_issuer.py:51`,
   but the issuer canonicalizes and signs the caller-submitted
   `source_authoring_state`, `source_bundle_id`, and `source_file_sha256`
   without resolving or verifying producer-owned conversion/job state. Live
   re-review probe: mutate the source choice to `browser-local-source`, post
   that forged state to
   `/v2/exam-authoring/corrections/source-state/issue`, then echo the returned
   signed bundle into `/v2/exam-authoring/corrections/apply`; the apply route
   returned `200`, accepted `manual_matching_answer_key`, and projected
   readiness. That means the new issuer lets a consumer mint authority for
   browser-local state through Sir Convert, even though the contract says
   consumers may only echo producer-returned signatures and browser drafts must
   not mint their own signatures. The remaining fix is to bind issuance to a
   server-owned producer artifact, job, bundle manifest, or internal producer
   call path before signing, and to add a regression that the public consumer
   path cannot get forged browser-local state signed and accepted.

   Remediation response after producer-artifact issuance follow-up:
   Task 331 changed the issuance request so consumers submit only a `job_id`
   plus an optional expected digest, never `source_authoring_state`. The route
   now resolves the v2 job through the normal job access path, requires a
   succeeded producer job, loads the server-owned
   `exam-authoring-correction-source-state.json` artifact from that job's
   artifact directory, canonicalizes that persisted artifact, and signs a
   binding whose `source_bundle_id` is the job ID and whose `source_file_sha256`
   is derived from server-stored upload bytes. The focused regression
   `test_correction_source_state_issue_route_rejects_caller_supplied_forged_state`
   posts forged browser-local state to the issuer and receives a privacy-safe
   validation failure instead of a signed bundle. This finding remains
   unchecked until independent re-review verifies the remediation.

   Re-review disposition after producer-artifact issuance follow-up:
   Still blocked on 2026-05-18. The issuer no longer signs caller-submitted
   `source_authoring_state`, which closes the direct public-signer hole.
   However, the product path is still incomplete: the issuer now requires a
   server-side `exam-authoring-correction-source-state.json` beside the job
   artifact in
   `scripts/sir_convert_a_lot/application/exam_authoring_correction_source_state_issuer.py:137`,
   but repo-wide search found the artifact writer used only by the route test
   fixture at
   `tests/sir_convert_a_lot/exam_authoring_corrections_apply_fixtures.py:204`,
   not by any production producer/conversion path. Live re-review probe: a
   succeeded normal v2 job without the test-only sidecar returned `409` with
   `exam_authoring_source_state_artifact_missing` from
   `/v2/exam-authoring/corrections/source-state/issue`. A downstream consumer
   still cannot obtain the signed source-authoring bundle from an actual
   producer job. The remaining fix is to have the governed producer job that
   downstream PR-0332 depends on persist the sanitized source-state artifact as
   part of its normal runtime output, with a regression that creates/executes
   that real producer path and then issues and applies the returned bundle
   without test-only artifact seeding.

   Remediation response after real producer emission follow-up:
   Task 331 now writes `exam-authoring-correction-source-state.json` from the
   normal DigiExam `digiexam_dxe -> examnet_migration_bundle` producer path,
   projected from producer-owned effective exam state rather than a test
   fixture. The focused regression
   `test_digiexam_migration_job_emits_correction_source_state_for_issuer`
   creates and executes a real authenticated DigiExam migration job, calls the
   source-state issuer with only the job ID, receives a signed
   `source_authoring_state`/`source_binding` bundle, and submits that bundle to
   `/v2/exam-authoring/corrections/apply` without manual sidecar seeding. This
   finding remains unchecked until independent re-review verifies the
   remediation.

   Re-review disposition after real producer emission follow-up:
   Resolved for producer authority on 2026-05-18. A real authenticated
   `digiexam_dxe -> examnet_migration_bundle` job now emits the source-state
   sidecar, and the issuer returns `200` with a signed bundle for that job
   without fixture-only artifact seeding. The old direct public-signer and
   missing-sidecar blockers are closed.

1. [x] `blocker` - The real producer-issued source state cannot exercise the
   route's only supported correction kind.

   Evidence:

   - Task 330's initial runtime support is `manual_matching_answer_key`; the
     review scope and converter contract make matching correction application
     the first supported apply path.
   - The real producer projection added for Task 331 hardcodes
     `matching_interactions=()` for every emitted item in
     `scripts/sir_convert_a_lot/application/exam_authoring_correction_source_state_projection.py:44`.
   - The source enum used by that projection has no `matching` item type in
     `scripts/sir_convert_a_lot/domain/digiexam_contracts.py:21`.
   - Live re-review probe: a real authenticated
     `digiexam_dxe -> examnet_migration_bundle` job succeeded, the source-state
     issuer returned `200`, but the issued state contained three items with item
     types `open_ended`, `single_choice`, and `multiple_response`, all with zero
     `matching_interactions`; total matching interactions was `0`.
   - The newly added producer regression proves only issue plus apply with an
     unsupported `point_correction` rejected row in
     `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py:212`.
     It does not prove a real producer can issue state for, and then accept, a
     `manual_matching_answer_key`.
   - The contract requires source-state projection to expose nested interaction
     IDs, matching source IDs, and matching target IDs where present at
     `docs/converters/exam-authoring-corrections-apply-contract.md:202`, and
     the `manual_matching_answer_key` entry binds to a matching interaction ID
     plus source/target IDs at
     `docs/converters/exam-authoring-corrections-apply-contract.md:361`.

   Why it matters:
   Review 24 can no longer fail on "no real producer sidecar", but it still
   cannot approve the product contract as complete. The only implemented apply
   entry is matching, while the only real producer issuance path emits no
   matching interaction surface. Downstream PR-0332 would have a signed bundle
   mechanism but no producer-issued state that can drive the supported
   correction workflow.

   Required fix:
   Either wire the source-neutral matching producer from Tasks 322/323 into a
   real producer/issuance path that emits `matching` items with
   `matching_interactions`, source choices, target choices, bounds, and current
   answer-key provenance, or explicitly govern Task 330's current runtime as
   blocked for downstream matching use until that producer exists. Do not prove
   this with an unsupported correction kind.

   Proof requirement:
   Add a runtime regression that creates or resolves a real producer-owned
   matching source state, calls
   `/v2/exam-authoring/corrections/source-state/issue`, then submits a
   `manual_matching_answer_key` correction against the returned
   `source_authoring_state`/`source_binding` and receives an accepted entry plus
   target readiness. Run focused correction route tests, the real producer
   source-state test, OpenAPI tests, typecheck, coverage gate, and docs gates.

   Remediation response after final Task 331 pass:
   Resolved by explicit downstream block rather than by fabricated DigiExam
   matching. Task 331 now expands the real DigiExam producer-issued source
   state for the correction families DigiExam can truthfully support after the
   HuleEdu auth-edge widening lane: visible text state, bounded `max_score`,
   choice interaction IDs/options/current key provenance, and gap/open-cloze
   interaction IDs/gaps/current accepted-value provenance. DigiExam still emits
   zero `matching_interactions` because the current DigiExam IR has no
   canonical matching item type. Task 332 now governs the required
   matching-capable producer path before any downstream consumer may treat
   `manual_matching_answer_key` as usable product authority.

   Focused proof added:
   `test_digiexam_migration_job_emits_correction_source_state_for_issuer`
   now proves text/point/choice source-state surfaces from a real producer job
   and explicitly asserts zero matching interactions for DigiExam.
   `test_digiexam_migration_job_emits_gap_correction_source_state_for_issuer`
   proves the real producer/issuer path emits gap/open-cloze state. This
   review finding remains available for independent re-review, but downstream
   matching use is no longer silently authorized by Task 331.

1. [x] `blocker` - Accepted advisory candidates are promoted to reviewed
   provenance without validating `candidate_payload_digest`.

   Evidence:

   - The matching correction model only requires candidate lineage to be present
     for non-`teacher_authored` submissions in
     `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_models.py:232`.
   - `_matching_submission` maps `accepted_advisory_candidate` directly to
     reviewed provenance in
     `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py:240`.
   - Live probe: setting `submission_origin` to `accepted_advisory_candidate`
     and providing a deliberately wrong `candidate_payload_digest` returned
     `200`, accepted the correction, and emitted `effective_provenance: reviewed`.
   - The contract requires accepted advisory candidates to digest to
     `candidate_lineage.candidate_payload_digest` at
     `docs/converters/exam-authoring-corrections-apply-contract.md:333`.

   Why it matters:
   The API can launder an arbitrary teacher/browser payload as a reviewed model
   candidate. That breaks answer-key provenance, auditability, and the
   two-pass reviewed-completion contract that downstream PR-0332 work depends
   on.

   Required fix:
   Canonicalize the submitted answer-key payload for advisory-origin entries and
   compare its digest with `candidate_lineage.candidate_payload_digest` before
   applying the correction or setting reviewed provenance. Keep
   `teacher_edited_advisory_candidate` distinct: it may differ from the
   candidate digest but must still carry lineage and map to teacher-provided
   effective provenance.

   Proof requirement:
   Add tests for accepted advisory candidate digest match, accepted advisory
   candidate digest mismatch, teacher-edited advisory candidate with different
   payload, and missing lineage. Run the focused route tests and any existing
   reviewed-completion lineage tests.

   Re-review disposition:
   Resolved on 2026-05-18. The accepted advisory mismatch live probe now returns
   `422` with `advisory_candidate_payload_digest_mismatch`, and focused route
   tests cover digest match, mismatch, teacher-edited digest drift, and missing
   lineage.

1. [x] `high` - Mixed accepted/rejected batches can partially unlock artifacts
   despite the contract saying rejected entries must not partially unlock files.

   Evidence:

   - The loop applies supported matching corrections immediately and records
     unsupported entries as rejected in the same pass in
     `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py:79`.
   - Readiness and artifact availability are projected for accepted entries even
     when the same request has rejected entries at
     `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py:97`.
   - Live probe: a batch with one valid `manual_matching_answer_key` and one
     unsupported `point_correction` returned `200`, reported the point
     correction rejected, but still returned `examnet_pdf` as available.
   - The contract states all entries are validated before effective state,
     readiness, or artifact availability is projected and that rejected entries
     must not partially unlock files at
     `docs/converters/exam-authoring-corrections-apply-contract.md:89`.

   Why it matters:
   Consumers can get a file-ready signal from a batch whose correction set was
   not fully accepted. That is especially risky for teacher review workflows
   because one rejected correction can be hidden behind another accepted
   correction that unlocks download/export.

   Required fix:
   Use a two-phase validation/apply flow. Validate every entry and its
   entry-specific semantics before mutating effective state or projecting
   readiness. If partial success is actually desired, change the governed
   contract explicitly and make artifact availability conditional on
   item/target-level accepted state with clear rejected-entry UX semantics.

   Proof requirement:
   Add a mixed accepted/rejected batch test that proves rejected entries cannot
   unlock artifacts or target readiness. Run the focused route tests and OpenAPI
   tests.

   Re-review disposition:
   Resolved on 2026-05-18. A mixed valid matching correction plus unsupported
   point correction now returns no accepted entries, no target readiness, no
   artifact availability, and an unchanged absent effective matching key.

1. [x] `high` - Request validation errors echo forbidden submitted payload
   values.

   Evidence:

   - The global `RequestValidationError` handler returns `exc.errors()` directly
     in `scripts/sir_convert_a_lot/interfaces/http_api.py:171`.
   - Live probe: adding extra field `student_result_data: SECRET_STUDENT_ANSWER` under `source_authoring_state.items[0]` returned a
     `422` response whose error details included `"input": "SECRET_STUDENT_ANSWER"`.
   - The unified correction contract forbids returned reports from echoing raw
     overlay JSON, raw provider payloads, raw source text, credentials, student
     data, or identity markers at
     `docs/converters/exam-authoring-corrections-apply-contract.md:455`.
   - ADR-0011 requires the unified contract to preserve current DXE overlay
     privacy and provenance guarantees, including no raw provider data, no
     credentials, no identity markers, no earned scores, no wrong selections,
     no free-text student answers, and no per-student performance history at
     `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md:118`.

   Why it matters:
   The route accepts a rich source-state payload by design. Even when strict
   models reject extra fields, the error envelope can leak exactly the data the
   contract says must not come back to consumers or logs.

   Required fix:
   Sanitize request-validation error details before returning them. Preserve
   location, error type, and message, but strip raw `input`, `ctx` values that
   can carry payloads, and other submitted data fragments. Apply this at least
   to the unified correction route, and preferably to the shared v2 validation
   error envelope if compatible with existing API error contracts.

   Proof requirement:
   Add a route-level privacy regression proving forbidden submitted values do
   not appear in the `422` response body. Run focused route tests and any
   existing v2 error-envelope tests.

   Re-review disposition:
   Resolved on 2026-05-18. The validation-error live probe no longer echoes
   `SECRET_STUDENT_ANSWER` or raw `"input"` in the response body, while
   preserving bounded location/type/message diagnostics.

## Decision

approved

## Response

Task 330 is directionally aligned with ADR-0011 in the hard-cut shape: the
unified `/v2/exam-authoring/corrections/apply` route exists, the old Task 324
matching-specific route is absent from runtime/OpenAPI, the generated OpenAPI
snapshot is synchronized, and the focused route/OpenAPI tests pass.

Approval is granted for Task 331 / Review 24. Task 331 now has a signed
producer-state authority verifier, the earlier advisory-origin digest
validation, mixed-batch artifact unlock semantics, validation-error privacy
fixes, a runtime/OpenAPI source-state issuance route that no longer accepts
caller-supplied source state for signing, and normal DigiExam producer emission
of the server-owned source-state artifact the issuer requires. The final
remediation pass widens that real producer state for DigiExam-backed
text/point/choice/gap correction families and blocks downstream matching use on
Task 332 rather than inventing matching from DigiExam state.

This approval does not authorize downstream `manual_matching_answer_key`
submission for PR-0332. That remains gated on Task 332, which must add a real
matching-capable producer-issued source state before consumers treat matching
correction application as product-ready.

## Remediation Response

Task 331 implemented a remediation pass while keeping this review available for
independent re-review before downstream PR-0332 work treats Task 330 as
approved.

Remediation summary:

- source binding now validates both the submitted source state against a
  canonical stable digest and a Sir Convert-signed producer-state authority
  signature before correction application, the source-state issuer now refuses
  caller-supplied source state, and the DigiExam migration producer writes the
  server-owned source-state artifact required by the issuer;
- DigiExam producer source state now exposes source-owned title, prompt,
  bounded point, choice interaction, and gap/open-cloze interaction surfaces
  for future unified correction runtime slices after the HuleEdu auth-edge
  widening lane;
- DigiExam source state still emits no matching interactions by design, and
  Task 332 blocks downstream `manual_matching_answer_key` use until a real
  matching-capable producer exists;
- `accepted_advisory_candidate` matching keys now require submitted payload
  digest equality with `candidate_lineage.candidate_payload_digest`;
- correction application now validates the batch before mutating effective
  state or projecting target readiness/artifacts, and any rejected entry blocks
  correction-derived unlocks for the batch;
- shared v2 request-validation errors now return bounded location/type/message
  diagnostics without raw submitted `input` or unsafe `ctx` fragments;
- the old Task 324 matching-specific route remains absent from runtime and
  OpenAPI.

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py`
  -> 13 passed, including the forged source-state/recomputed-digest authority
  regression.
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2.py::test_requires_api_key_with_standard_error_envelope`
  -> 18 passed.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_correction_source_state_for_issuer`
  -> 1 passed, proving real producer emission plus issue/apply without
  fixture-only sidecar seeding.
- `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_correction_source_state_for_issuer tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_gap_correction_source_state_for_issuer`
  -> 2 passed, proving real producer-issued text/point/choice/gap source-state
  surfaces and explicit DigiExam non-matching state.
- `pdm run openapi-export-v2` -> refreshed
  `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`.
- `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  -> 4 passed.
- `pdm run typecheck-all` -> success across 736 source files.
- 2026-05-18 independent re-review:
  `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_api_contract_v2.py::test_requires_api_key_with_standard_error_envelope tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_correction_source_state_for_issuer tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_job_emits_gap_correction_source_state_for_issuer`
  -> 22 passed.
- 2026-05-18 independent re-review: `pdm run typecheck-all` -> success across
  736 source files.
- 2026-05-18 independent re-review: `pdm run coverage-gate` -> 1395 passed,
  6 skipped, 95.56% coverage.
- 2026-05-18 independent re-review: `pdm run docs-sync`,
  `pdm run docs-validate`, `pdm run skills-validate`,
  `pdm run handoff-validate`, and `git diff --check` -> passed.

## Follow-up Actions

1. Complete Task 332 before downstream consumers submit
   `manual_matching_answer_key` through PR-0332. Review 24 approval closes
   Task 331's remediation only; it does not turn DigiExam source state into
   matching authority.
1. Keep the old Task 324 matching-specific route absent; remediation must not
   reintroduce it as an adapter, shim, alias, wrapper, transitional route, or
   compatibility layer.

## Completion

Closed as approved on 2026-05-18. Task 331 follow-up remediation added signed
producer-state verification, a source-state issuance route, real DigiExam
producer emission of the source-state sidecar, source-state coverage for
DigiExam-backed text/point/choice/gap correction families, and Task 332 as the
explicit governed block before downstream matching use.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
