---
id: review-19-ruthless-review-of-task-323-matching-manual-answer-key-producer-dto
title: Ruthless review of Task 323 matching manual answer-key producer DTO
type: review
status: completed
priority: high
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
  - review
  - task-323
  - answer-key-completion
  - matching
  - exam-authoring-ir
  - openapi
  - approved
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-implementation review of Task 323.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/000-rule-index.md`
  - `docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md`
  - `docs/backlog/tasks/task-298-define-matching-answer-key-pair-ir-contract.md`
  - `docs/backlog/tasks/task-307-define-source-neutral-exam-authoring-ir-v1-and-adapter-boundary.md`
  - `docs/converters/exam-authoring-ir-v1-contract.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
- Primary files reviewed:
  - `scripts/sir_convert_a_lot/domain/exam_authoring_matching_manual_answer_key.py`
  - `scripts/sir_convert_a_lot/domain/exam_authoring_ir_contracts.py`
  - `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`
  - `scripts/sir_convert_a_lot/interfaces/http_openapi_contract_v2.py`
  - `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
  - `tests/sir_convert_a_lot/test_exam_authoring_matching_manual_answer_key.py`
  - `tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`
  - `tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts`
  - `/Users/olofs_mba/Documents/Repos/CascadeProjects/windsurf-project/frontend/apps/skriptoteket/src/api/sirConvertGateway/matchingContract.spec.ts`
- Public surfaces affected:
  - Generated Sir Convert v2 OpenAPI snapshot.
  - `x-sir-convert-contract-components` component doorway for consumer type generation.
  - Source-neutral `ExamAuthoringIR v1` matching manual-answer-key DTOs.
  - Skriptoteket generated Sir Convert consumer types.
- Compatibility posture:
  - Clean contract cutover: no retired `left_id`/`right_id` aliases and no compatibility parser.
  - DigiExam ingestion overlay stays choice/gap-only.
  - Matching manual answer keys stay source-neutral and whole-key provenance only until a future governed per-pair provenance task exists.

## Findings

None.

## Verified Checks

- Task 323 stays aligned with production intent: it exposes a producer-owned,
  source-neutral `ExamAuthoringMatchingManualAnswerKey` DTO and application
  boundary instead of adding a DigiExam matching overlay or consumer-local shape.
- The DTO publishes `kind: "matching"`, `schema_version:
  "exam_authoring_ir_v1"`, `interaction_id`, optional
  `source_item_fingerprint`, and directed `source_id`/`target_id` pairs.
- Schema validation forbids extra fields, rejects retired `left_id`/`right_id`
  aliases, rejects aggregate `mixed` provenance, and rejects non-empty pairs
  with `absent` provenance.
- Runtime application validates schema version, interaction id, optional source
  fingerprint, unknown IDs, duplicate pairs, association bounds, and neutral
  matching validation before returning an updated `ExamAuthoringIR v1`
  interaction.
- OpenAPI publishes `ExamAuthoringMatchingManualAnswerKey`,
  `ExamAuthoringMatchingManualAnswerKeyPayload`, and
  `ExamAuthoringMatchingManualAnswerKeyPair`; it does not publish
  `DigiExamOverlayMatchingManualAnswerKey`.
- Skriptoteket generated consumer types expose the matching DTO with
  `source_id`/`target_id`, and the focused preflight spec consumes the generated
  type rather than a local inferred shape.
- Review found one docs-alignment gap: Epic 11 and Story 49 did not yet name
  Task 323 as the production prerequisite. This review amended those governed
  docs so the parent surfaces now match the completed task and handoff intent.

## Decision

approved

## Response

Task 323 is approved after review. The implemented slice is narrow, source-neutral,
and aligned with production intent: it gives Skriptoteket a generated producer
DTO for matching-capable source flows without widening DigiExam overlays or
claiming DigiExam keyed matching support.

## Follow-up Actions

1. None for Task 323 review closure. Future matching runtime/UI work must remain
   governed by a separate task and must keep source-native parsers behind the
   `source parser -> source adapter -> ExamAuthoringIR v1 -> target validators/exporters`
   boundary.

## Completion

Review retained on 2026-05-18 with `approved`.

Validation evidence:

- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_manual_answer_key.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_exam_authoring_matching_contracts.py`
  -> 21 passed.
- `pdm run docs-validate`
  -> validated backlog docs and durable docs.
- `pdm run handoff-validate`
  -> ok.
- `pdm run typecheck-all`
  -> success, no issues in 712 source files.
- `pdm run docs-sync`
  -> refreshed generated docs indexes.
- `pdm run skills-validate`
  -> ok.
- `pdm run coverage-gate`
  -> 1348 passed, 6 skipped, coverage 95.49%.
- `git diff --check`
  -> no whitespace errors.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
