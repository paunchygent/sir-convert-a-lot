---
id: task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket
title: Expose source-neutral matching manual answer-key producer DTO for Skriptoteket
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
  - docs/backlog/tasks/task-322-add-points-scoring-correction-producer-dto-before-pr-0332.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
labels:
  - answer-key-completion
  - matching
  - exam-authoring-ir
  - openapi
  - skriptoteket
---

Producer-owned contract prerequisite before Skriptoteket implements matching
manual answer-key editing.

## Objective

Publish a Sir Convert-owned, source-neutral `ExamAuthoringIR v1` matching
manual-answer-key DTO and generated OpenAPI contract so Skriptoteket can
edit and submit matching keys without inventing a consumer-local shape or
reusing DigiExam-specific overlay DTOs.

This task closes the producer DTO gap only. The current generated Skriptoteket
OpenAPI consumer surface exposes `manual_answer_key` for DigiExam `choice` and
`gap_fill`, while source-neutral matching lives in `ExamAuthoringIR v1` and is
not currently exposed as a matching manual-answer-key producer DTO. That gap is
not a product claim that matching is unsupported. It means the producer-owned
matching DTO slice must land before Skriptoteket consumer work starts.

The contract must preserve the existing architecture boundary:

```text
source parser -> source adapter -> ExamAuthoringIR v1 -> target validators/exporters
```

DigiExam `.dxe` migration must not gain a keyed matching overlay in this task.
Matching-capable source flows use `ExamAuthoringIR v1` and exact
`source_id`/`target_id` directed pairs.

## PR Scope

- Define source-neutral Pydantic/OpenAPI DTOs for matching manual answer keys
  using `kind: "matching"`, stable `interaction_id`, source binding where
  available, and exact directed pairs.
- Use the already governed `ExamAuthoringIR v1` field names:
  `source_id` and `target_id`. Do not accept `left_id` or `right_id` aliases,
  compatibility shims, or dual schema parsing.
- Preserve whole-key matching provenance in this slice:
  `teacher_provided`, `source_provided`, `reviewed`, or `absent` where
  structurally needed. Do not introduce aggregate `mixed` matching provenance
  until a later governed task adds per-pair provenance and evidence.
- Reuse the existing source-neutral matching validation semantics for unknown
  IDs, duplicate pairs, malformed bounds, association-limit violations, absent
  provenance with non-empty pairs, and opaque `mixed` provenance.
- Publish the DTO through Sir Convert's generated v2 OpenAPI contract surface
  so downstream consumers can generate types from producer authority.
- Keep DigiExam-specific `DigiExamIngestionOverlay.manual_answer_key` limited
  to the currently supported `choice` and `gap_fill` shapes. This task must
  not add `DigiExamOverlayMatchingManualAnswerKey` or keyed DigiExam matching
  runtime behavior.
- Add generated-contract tests proving the matching DTO appears in the correct
  source-neutral OpenAPI surface and does not reappear in the DigiExam overlay
  surface.
- Regenerate checked-in/generated types after implementation in both repos:
  Sir Convert's generated OpenAPI snapshot and corresponding Sir-side schema
  surfaces, plus Skriptoteket's generated Sir Convert consumer types.
- Update the converter docs and handoff pointers so Skriptoteket starts from
  this producer contract rather than a local inferred matching shape.

## Out of Scope

- Skriptoteket UI, adapter, or workflow implementation beyond regenerating and
  checking the generated consumer type surface.
- DigiExam keyed matching support.
- LLM advisory or reviewed-completion matching suggestions.
- QTI or Exam.net import-readiness promotion beyond current proof-gated target
  status.
- Per-pair matching provenance or mixed-provenance matching keys.
- Accepting retired `left_id`/`right_id` payloads through aliases or migration
  compatibility.

## Deliverables

- [x] Source-neutral matching manual-answer-key DTOs added to the producer
  contract.
- [x] OpenAPI export publishes the matching DTOs without adding DigiExam
  matching overlay components.
- [x] Producer validation rejects stale or malformed matching key payloads
  before target rendering.
- [x] Generated type surfaces are refreshed in both Sir Convert and
  Skriptoteket after implementation.
- [x] Converter docs and `.codex/handoff.md` identify this task as the
  producer prerequisite before Skriptoteket matching-key consumer work.
- [x] Focused tests cover DTO schema, OpenAPI visibility, retired alias
  rejection, and neutral matching validation reuse.

## Acceptance Criteria

- [x] Skriptoteket can regenerate from Sir Convert's OpenAPI snapshot and see a
  source-neutral matching manual-answer-key DTO with `kind: "matching"`,
  `source_id`, and `target_id`.
- [x] The generated DigiExam overlay consumer type still exposes manual answer
  keys only for `choice` and `gap_fill`.
- [x] Matching pairs are exact ID-bound data. Unknown source or target IDs,
  duplicate pairs, missing required pairs for the selected profile, and
  association-limit violations fail closed.
- [x] Matching manual answer keys do not mutate parser-owned source IR or
  source/parser provenance.
- [x] Non-empty matching pairs with `absent` provenance fail closed.
- [x] Aggregate `mixed` matching provenance fails closed until a future
  governed per-pair provenance contract exists.
- [x] Retired `left_id` and `right_id` payloads fail schema validation rather
  than being translated.
- [x] The implementation regenerates generated type surfaces in both repos
  before closeout: Sir Convert OpenAPI/schema artifacts and Skriptoteket's
  generated Sir Convert consumer types.

## Validation Plan

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`
- Focused tests for any new source-neutral matching DTO module and OpenAPI
  component names.
- In Skriptoteket, regenerate the Sir Convert OpenAPI consumer types from the
  Task 323 snapshot and run the focused generated-type/preflight checks owned
  by the consumer repo.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Stop Conditions

- Stop if the proposed DTO has to live under DigiExam overlay names to pass
  consumer code.
- Stop if matching readiness or artifact export would require inferring correct
  pairs from prompt text without trusted source, teacher/manual, or reviewed
  evidence.
- Stop if the implementation cannot publish a stable generated OpenAPI surface
  before Skriptoteket consumer work begins.
- Stop if both repos cannot regenerate their generated type surfaces in the
  same closeout lane or in a documented blocked handoff.

## Implementation Evidence

Completed on 2026-05-18.

- Added `domain.exam_authoring_matching_manual_answer_key` as the
  source-neutral producer DTO and application boundary for Task 323 matching
  manual answer-key submissions.
- The DTO publishes `kind: "matching"`, `schema_version: "exam_authoring_ir_v1"`, `interaction_id`, optional
  `source_item_fingerprint`, and exact `source_id`/`target_id` directed pairs.
- The submission DTO allows only `absent`, `source_provided`,
  `teacher_provided`, and `reviewed` provenance. It does not expose `mixed` in
  generated OpenAPI or Skriptoteket's generated TypeScript consumer type.
- Runtime application validates schema version, interaction id, optional
  source fingerprint, unknown IDs, duplicate pairs, association bounds,
  non-empty pairs with `absent` provenance, and the existing neutral matching
  validation rules before returning an updated `ExamAuthoringIR v1`
  interaction.
- The implementation rejects retired `left_id`/`right_id` aliases through
  strict Pydantic `extra="forbid"` DTOs instead of translating them.
- Sir Convert's generated v2 OpenAPI snapshot now includes
  `ExamAuthoringMatchingManualAnswerKey`,
  `ExamAuthoringMatchingManualAnswerKeyPayload`, and
  `ExamAuthoringMatchingManualAnswerKeyPair`, and exposes the component through
  `x-sir-convert-contract-components`.
- DigiExam ingestion overlays remain choice/gap-only; OpenAPI tests continue
  to assert that no `DigiExamOverlayMatchingManualAnswerKey` component exists.
- Regenerated Skriptoteket's
  `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` from the Task
  323 OpenAPI snapshot and added a focused generated-contract preflight spec
  for the matching DTO.

Validation evidence:

- `pdm run openapi-export-v2`
- `pnpm -C frontend --filter @skriptoteket/spa exec openapi-typescript /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json -o ./src/api/sirConvertOpenapi.d.ts`
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_manual_answer_key.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`
- `pnpm -C frontend --filter @skriptoteket/spa test -- src/api/sirConvertGateway/matchingContract.spec.ts`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run coverage-gate`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check` in Sir Convert and Skriptoteket

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
