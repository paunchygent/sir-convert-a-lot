---
id: task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332
title: Add source-neutral matching correction apply route for Skriptoteket PR-0332
type: task
status: completed
priority: critical
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md
  - docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - answer-key-completion
  - matching
  - exam-authoring-ir
  - skriptoteket
  - api-contract
---

Producer-owned route/application prerequisite before Skriptoteket implements
the `PR-0332` source-neutral matching correction UI.

Architecture note: this matching-specific route is now superseded and abandoned
as a product path. It must not set product direction toward one exam-authoring
correction route per item type, and it must not survive as an adapter, shim,
alias, wrapper, transitional route, or compatibility layer. Task 327 defines the
source-neutral correction/apply contract, and Task 330 removes this route while
moving matching semantics into `manual_matching_answer_key`.

## Objective

Add the Sir Convert route/application contract that accepts the Task 323
`ExamAuthoringMatchingManualAnswerKey` DTO for matching-capable
`ExamAuthoringIR v1` source flows and returns a producer-owned corrected bundle
that Skriptoteket can use as the sole authority for file readiness.

Skriptoteket `PR-0332` confirmed on 2026-05-18 that Task 323 publishes the
generated DTO, but the active v2 create-job request body only accepts
`digiexam_ingestion_overlay` as a correction upload part. The Task 323
component is present under `x-sir-convert-contract-components`, not as an
accepted request body part or dedicated source-neutral authoring route.

This task closes that route/effective-state gap. Skriptoteket must not invent a
consumer-local transport, must not force matching into
`DigiExamIngestionOverlay`, and must not unlock PDF/QTI artifacts from
browser-local matching drafts.

## PR Scope

- Define the producer-owned submit/apply surface for source-neutral matching
  manual answer keys. The implementation may use a dedicated authoring apply
  route or an explicitly governed multipart part on an existing v2 route, but
  it must be represented in OpenAPI request-body semantics, not only in
  extension metadata.
- Accept the Task 323 DTO shape exactly:
  `schema_version: "exam_authoring_ir_v1"`, `kind: "matching"`,
  `interaction_id`, optional `source_item_fingerprint`, and exact
  `source_id`/`target_id` directed pairs.
- Bind the submitted key to an existing source-neutral matching interaction
  and validate schema version, interaction id, exact source/target ids,
  duplicate pairs, association bounds, and neutral matching validation rules
  before target rendering.
- Preserve the `PR-0332` source-binding invariant: when the matched source
  interaction or manifest carries a source item fingerprint, missing or
  mismatched `source_item_fingerprint` submissions fail before target
  rendering. Skriptoteket must submit this binding from returned producer
  state rather than browser-local inference.
- Return enough producer-owned state for Skriptoteket to project the corrected
  result without local inference: updated/effective `ExamAuthoringIR v1`
  matching state, target readiness, and artifact availability for PDF/QTI.
- Preserve current DigiExam boundaries: DigiExam `.dxe` ingestion overlays stay
  choice/gap-fill only and do not gain `DigiExamOverlayMatchingManualAnswerKey`.
- Update OpenAPI and converter docs so the route, accepted request shape,
  returned state, and blocked/degraded states are reviewable by consumers.

## Out of Scope

- Skriptoteket UI or consumer implementation.
- DigiExam keyed matching overlays or DigiExam `.dxe` matching inference.
- LLM advisory/reviewed-completion matching suggestions.
- Per-pair provenance or aggregate `mixed` matching provenance.
- Retired `left_id`/`right_id` aliases or compatibility translation.
- Inferring correct matching pairs from prompt text, PDF layout, or target
  labels without trusted source, teacher/manual, or reviewed evidence.

## Deliverables

- [x] Source-neutral matching manual-answer-key submit/apply route or
  explicitly accepted multipart part implemented.
- [x] OpenAPI request-body semantics expose the accepted matching correction
  input, not only `x-sir-convert-contract-components`.
- [x] Application code applies the matching key to the source-neutral
  `ExamAuthoringIR v1` interaction and returns corrected producer-owned state.
- [x] Target readiness distinguishes ready artifacts, missing matching pairs,
  stale bindings, invalid pair ids, and association-bound failures without
  silent degradation.
- [x] PDF/QTI artifact proof covers matching pairs where the target profiles
  support them and blocks unsafe/unbound outputs.
- [x] Docs and generated contract surfaces are regenerated for Sir Convert and
  Skriptoteket.

## Acceptance Criteria

- [x] Submitting a valid `ExamAuthoringMatchingManualAnswerKey` against a
  matching-capable source-neutral interaction returns corrected effective
  state with the submitted directed pairs.
- [x] Submissions with stale schema version, stale interaction id, missing or
  mismatched source item fingerprint when the producer state carries one,
  unknown source/target ids, duplicate pairs, association-limit violations,
  non-empty pairs with `absent` provenance, or retired `left_id`/`right_id`
  fields fail before target rendering.
- [x] The accepted request shape is visible to generated OpenAPI consumers as a
  route/request-body contract.
- [x] DigiExam ingestion overlay OpenAPI components remain choice/gap-fill
  only; no `DigiExamOverlayMatchingManualAnswerKey` component exists.
- [x] Returned readiness/artifact state is sufficient for Skriptoteket to keep
  local edits non-authoritative until the corrected Sir Convert bundle returns.
- [x] Internal diagnostics, raw overlay JSON, raw provider data, credentials,
  identity markers, and student-result data are absent from generated teacher
  artifacts.

## Implementation Evidence

Task 324 originally implemented the dedicated source-neutral apply route instead
of adding a matching field to DigiExam multipart overlays:

- `POST /v2/exam-authoring/matching/manual-answer-key/apply` accepts
  `ExamAuthoringMatchingManualAnswerKeyApplyRequest` as JSON request body.
- The request carries producer-returned `source_interaction`, the exact Task 323
  `exam_authoring_matching_manual_answer_key` DTO, and optional
  `requested_targets`.
- The application applies the DTO through
  `apply_exam_authoring_matching_manual_answer_key(...)` and passes the
  producer interaction's `source_item_fingerprint` as the expected binding.
  Missing or mismatched submitted fingerprints therefore fail with
  `stale_matching_source_item_fingerprint` before target readiness is projected.
- The response returns `exam_authoring_matching_apply_result_v1` with corrected
  `effective_interaction`, `target_readiness`, and `artifact_availability`.
- `examnet_pdf` readiness is projected through the existing Exam.net PDF
  matching profile. `qti_package` remains unavailable with
  `examnet_qti_matching_import_unproven` until governed Exam.net QTI import
  proof exists.
- The v2 create-job multipart body still accepts only the existing job parts for
  this lane; `exam_authoring_matching_manual_answer_key` is not accepted through
  `digiexam_ingestion_overlay`.
- DigiExam overlay components remain choice/gap-fill only; no
  `DigiExamOverlayMatchingManualAnswerKey` component exists.

Runtime/code authority:

- Superseded by
  `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py`
  and
  `scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py`
  in Task 330.
- `scripts/sir_convert_a_lot/interfaces/http_api.py`

Durable contract authority:

- `docs/converters/exam-authoring-ir-v1-contract.md`
- `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`

Focused proof:

- `tests/sir_convert_a_lot/test_exam_authoring_matching_apply_route.py`
- `tests/sir_convert_a_lot/test_openapi_contract_v2.py`

## Validation Plan

- [x] `pdm run openapi-export-v2`
- [x] Focused pytest for the new source-neutral matching apply route/request
  boundary.
- [x] Focused pytest proving rejected matching submissions fail before rendering.
- [x] Focused pytest proving OpenAPI request-body exposure and continued absence
  of DigiExam matching overlay components.
- [x] PDF/QTI readiness/artifact-availability proof for supported and blocked
  matching outputs.
- [x] Regenerate Skriptoteket's Sir Convert OpenAPI consumer types and run the
  focused generated-type/preflight spec.
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Stop Conditions

- Stop if the implementation requires placing matching keys inside
  `DigiExamIngestionOverlay`.
- Stop if no matching-capable source-neutral interaction is available to bind
  the submitted key.
- Stop if PDF/QTI output would omit source items or submitted matching pairs
  while reporting ready artifacts.
- Stop if the route cannot return producer-owned effective state/readiness for
  Skriptoteket to consume.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
