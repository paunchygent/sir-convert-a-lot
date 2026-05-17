---
id: review-17-ruthless-review-of-task-306-reviewed-completion-apply
title: Ruthless review of Task 306 reviewed completion apply
type: review
status: completed
priority: high
created: '2026-05-15'
last_updated: '2026-05-17'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md
  - docs/backlog/tasks/task-296-extract-structured-chat-provider-harness-for-local-first-completion.md
  - docs/backlog/tasks/task-297-implement-advisory-answer-key-completion-reports-for-choice-and-gap-fill-items.md
  - docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md
  - docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json
labels:
  - review
  - task-306
  - reviewed-completion
  - effective-ir
  - openapi
  - skriptoteket-sync
  - approved
  - closed
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless post-implementation review of Task 306.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `docs/backlog/tasks/task-306-apply-reviewed-answer-key-completion-into-effective-ir.md`
  - `docs/backlog/stories/story-48-digiexam-overlay-and-effective-ir-contract-for-answer-key-completion.md`
  - `docs/converters/digiexam-migration-service-api-artifact-contract.md`
  - `docs/converters/digiexam-intermediate-exam-representation-contract.md`
  - `docs/reference/ref-digiexam-machine-marked-answer-key-completion-architecture.md`
- Sir Convert files reviewed:
  - `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay_contracts.py`
  - `scripts/sir_convert_a_lot/domain/digiexam_reviewed_completion_application.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py`
  - `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py`
  - `scripts/sir_convert_a_lot/application/openapi_contracts_v2.py`
  - `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json`
  - focused Task 306 tests under `tests/sir_convert_a_lot/`
- Downstream consumer files reviewed:
  - Skriptoteket `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts`
  - Skriptoteket `frontend/apps/skriptoteket/src/api/sirConvertGateway/types.ts`
  - Skriptoteket `frontend/apps/skriptoteket/src/api/sirConvertGateway/jobSpec.ts`
  - Skriptoteket `frontend/apps/skriptoteket/src/api/sirConvertGateway/contractValues.ts`
- Public surfaces affected:
  - `DigiExamIngestionOverlay` multipart JSON component.
  - `DigiExamEffectiveExamV1` / `digiexam_effective_exam_v2`.
  - `DigiExamEffectiveAnswerKeyV1` lineage fields.
  - `DigiExamOverlayReviewedCompletionAnswerKey` and related reviewed
    completion payload schemas.
  - Skriptoteket generated Sir Convert OpenAPI TypeScript surface.
- Compatibility posture:
  - Sir Convert source IR remains parser-owned. Reviewed completion may only
    change effective renderer input and effective answer-key metadata.
  - Structured-provider execution remains opt-in advisory only. The reviewed
    apply mode must not call a provider and must fail closed without a
    reviewed-completion overlay.
  - OpenAPI consumers must regenerate against the changed Sir Convert snapshot
    rather than relying on stale local generated types.
- Evidence reviewed:
  - Line-numbered inspection of the Task 306 implementation, tests, docs, and
    generated OpenAPI snapshot.
  - Cross-repo generated-type drift probe:
    `frontend/apps/skriptoteket/node_modules/.bin/openapi-typescript /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json -o /tmp/sirConvertOpenapi.task306.d.ts`
    followed by a diff against Skriptoteket's checked-in
    `sirConvertOpenapi.d.ts`.
  - Focused Sir Convert validation commands are recorded below.

## Findings

1. [x] `historical-high` - Skriptoteket's checked-in Sir Convert generated OpenAPI types
   are stale after Task 306 changed the producer snapshot.

   Evidence:

   - Sir Convert's committed v2 OpenAPI snapshot now publishes
     `DigiExamEffectiveAnswerKeyLineageV1` at
     `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json:661`, wires
     `DigiExamEffectiveAnswerKeyV1.lineage` at
     `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json:747`, and
     adds `reviewed_completion_answer_key` to `DigiExamIngestionOverlayItem` at
     `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json:1102`.
   - The same snapshot publishes the reviewed completion payload schemas
     starting at
     `docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json:2198`.
   - Skriptoteket's generated
     `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` still defines
     `DigiExamEffectiveAnswerKeyV1` without `lineage` at
     `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts:589`.
   - The same Skriptoteket generated file still defines
     `DigiExamIngestionOverlayItem` without `reviewed_completion_answer_key`
     at `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts:712`.
   - Skriptoteket's Sir Convert Gateway wrapper derives the consumer overlay
     type from that generated file at
     `frontend/apps/skriptoteket/src/api/sirConvertGateway/types.ts:13`, then
     exports `DigiExamIngestionOverlay` from the stale schema at
     `frontend/apps/skriptoteket/src/api/sirConvertGateway/types.ts:33`.
   - A direct `openapi-typescript` regeneration from Sir Convert's Task 306
     snapshot adds the missing lineage component, the `lineage` field, the
     `reviewed_completion_answer_key` field, and the reviewed-completion
     payload/outcome schemas to the generated TypeScript output.

   Why it matters:
   Task 306 is explicitly a producer/consumer contract change, not only a
   Sir-local runtime patch. With Skriptoteket's generated type surface stale,
   a consumer cannot type a reviewed-completion overlay or inspect effective
   answer-key lineage through the committed generated contract. That recreates
   the known cross-repo failure mode where Sir publishes a schema shape and
   Skriptoteket keeps compiling against an older artifact contract.

   Required fix:
   The next implementation slice must be a narrow Skriptoteket consumer-sync
   pass, not new Sir Convert feature work. Regenerate
   `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts` from Sir
   Convert's committed v2 OpenAPI snapshot, then make only the minimal
   derived-type, constant, fixture, and focused-test adjustments needed for
   the regenerated contract to type-check. Keep the slice scoped to generated
   contract sync and existing Gateway client behavior; do not add new reviewed
   completion UX, new provider execution, or new conversion features in that
   pass.

   Proof requirement:
   In Skriptoteket, run the sanctioned frontend/typecheck gates for the Sir
   Convert Gateway package plus focused tests around
   `frontend/apps/skriptoteket/src/api/sirConvertGateway/` and the
   authenticated Exam Converter fixtures. The proof must show the regenerated
   generated file contains `DigiExamEffectiveAnswerKeyLineageV1`,
   `DigiExamEffectiveAnswerKeyV1.lineage`, and
   `DigiExamIngestionOverlayItem.reviewed_completion_answer_key`.

   Closeout:
   The finding is retained as historical review evidence, but it is no longer
   active. On 2026-05-17 a fresh regeneration from the current Sir Convert v2
   OpenAPI snapshot produced no diff against Skriptoteket's checked-in
   `frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts`, and the
   checked-in file contains `DigiExamEffectiveAnswerKeyLineageV1`,
   `DigiExamEffectiveAnswerKeyV1.lineage`, and
   `DigiExamIngestionOverlayItem.reviewed_completion_answer_key`.

## Verified Checks

- Task 306 semantics pass locally: reviewed candidates are accepted only through
  `reviewed_completion_answer_key` overlay data gated by
  `allow_reviewed_completion`, and application replaces only the effective
  renderer input. Source IR is written before overlay application in
  `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_builder.py:142`
  and Task 306 tests assert source IR provenance remains `absent` while the
  effective IR carries `reviewed` lineage in
  `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py:373`.
- Source/parser provenance remains separate: parser provenance enums in
  `scripts/sir_convert_a_lot/domain/digiexam_contracts.py:55` were not widened
  with LLM states; effective-only provenance lives in
  `scripts/sir_convert_a_lot/domain/digiexam_ingestion_overlay_contracts.py:344`.
- Apply mode no-provider proof passes by code path: the completion runtime
  returns before Dishka provider composition when
  `completion_mode=local_llm_apply_missing_machine_marked_with_review` at
  `scripts/sir_convert_a_lot/infrastructure/digiexam_answer_key_completion_runtime.py:67`.
  Tests monkeypatch provider calls as forbidden and assert no calls for both
  default artifact routing and apply mode at
  `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py:162` and
  `tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py:294`.

## Decision

approved

## Response

Sir Convert's Task 306 implementation passes the reviewed-overlay/effective-IR
semantics and no-provider checks reviewed above. The original downstream
generated-type drift finding is closed by current regeneration proof and should
not be used as active evidence for later Skriptoteket `PR-0331` work. Future
staleness claims must be grounded in current producer contract changes and a
fresh consumer regeneration/diff, not this historical review state.

## Follow-up Actions

None for Task 306. Later Skriptoteket reviewed-key artifact proof remains
governed by Skriptoteket `PR-0331`, not by this review.

## Completion

Review retained on 2026-05-15 with `changes_requested`, then closed as
`approved` on 2026-05-17 after current consumer regeneration proof.

Validation evidence:

- `frontend/apps/skriptoteket/node_modules/.bin/openapi-typescript /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json -o /tmp/sirConvertOpenapi.task306.d.ts`
  confirmed generated-type drift against Skriptoteket's checked-in
  `sirConvertOpenapi.d.ts`.
- Focused Sir Convert validation was rerun after this review artifact was
  written:
  `pdm run pytest-root tests/sir_convert_a_lot/test_digiexam_ingestion_overlay.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_default_artifact_route_does_not_call_structured_llm tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_reviewed_completion_apply_uses_overlay_without_provider tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py::test_digiexam_migration_reviewed_completion_apply_requires_overlay tests/sir_convert_a_lot/test_openapi_contract_v2.py`
  -> 17 passed.
- Current closeout proof on 2026-05-17:
  `frontend/apps/skriptoteket/node_modules/.bin/openapi-typescript /Users/olofs_mba/Documents/Repos/sir-convert-a-lot/docs/_generated/openapi/sir-convert-a-lot-v2.openapi.json -o /tmp/sirConvertOpenapi.current.d.ts`
  followed by
  `diff -u frontend/apps/skriptoteket/src/api/sirConvertOpenapi.d.ts /tmp/sirConvertOpenapi.current.d.ts`
  -> no diff.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
