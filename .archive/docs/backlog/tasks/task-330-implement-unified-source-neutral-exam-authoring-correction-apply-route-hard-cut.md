---
id: task-330-implement-unified-source-neutral-exam-authoring-correction-apply-route-hard-cut
title: Implement unified source-neutral exam authoring correction apply route hard cut
type: task
status: completed
priority: critical
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/converters/exam-authoring-ir-v1-contract.md
labels:
  - exam-authoring-ir
  - source-neutral
  - correction-contract
  - service-api-v2
  - openapi
---

Runtime implementation slice for the accepted ADR-0011 correction/apply
contract.

## Objective

Implement the source-neutral v2 correction apply route:

```text
POST /v2/exam-authoring/corrections/apply
```

and remove the superseded Task 324 matching-specific route in the same governed
change. This task is the hard cut that turns the Task 327 contract artifact into
runtime/OpenAPI authority for the matching correction family without retaining
the old route as an adapter, shim, alias, wrapper, compatibility layer, or
transitional route.

Task 324 is abandoned as a product path. Its reusable matching DTO and domain
validation semantics may survive only where they are consumed by the unified
`manual_matching_answer_key` correction entry.

## PR Scope

- Add application request/response models for
  `exam_authoring_corrections_apply_request_v1` and
  `exam_authoring_corrections_apply_result_v1`.
- Add the v2 HTTP route
  `POST /v2/exam-authoring/corrections/apply` with API-key enforcement and
  service-error mapping consistent with the existing v2 routers.
- Implement the first runtime-supported correction entry:
  `manual_matching_answer_key`, mapped from the Task 324 semantics into the
  unified correction-entry surface.
- Publish the typed correction-entry union in OpenAPI so downstream consumers
  see the unified route and `manual_matching_answer_key` entry.
- Remove
  `POST /v2/exam-authoring/matching/manual-answer-key/apply` from router
  registration, runtime paths, OpenAPI, route tests, and route-only
  request/response contracts.
- Keep the source-neutral matching manual-answer-key DTO and domain validator
  only as reusable implementation internals for the unified entry.
- Prove the old matching-specific route is not accepted.
- Update the contract docs, Story 49, and handoff to mark the unified route
  runtime/OpenAPI slice as implemented and the old route as removed.

The initial runtime supports matching correction application. Other entry kinds
from the Task 327 contract remain governed contract shapes but return explicit
unsupported-entry rejection from this route until a later task implements their
source-neutral runtime application. The existing DigiExam ingestion overlay
continues to own already-implemented DXE-only point/choice/gap/review flows
until a separate governed migration slice moves those families into the unified
route.

## Deliverables

- [x] New unified correction apply application contract and router.
- [x] Runtime support for `manual_matching_answer_key` entries with source
  binding, effective state projection, target readiness, artifact availability,
  and accepted/rejected correction report rows.
- [x] Explicit unsupported-entry rejection for non-matching correction kinds,
  without mutating effective state or unlocking artifacts.
- [x] Old Task 324 matching route removed from FastAPI registration and
  generated OpenAPI.
- [x] Old route-specific request/response contracts and route tests removed or
  rewritten.
- [x] Focused tests proving the new route returns effective matching state,
  fails closed on stale fingerprints, rejects invalid pairs before readiness,
  reports unsupported non-matching entries, and rejects the old route path.
- [x] OpenAPI snapshot regenerated and tests updated to protect the unified
  route instead of the old route.
- [x] Contract docs, Story 49, and handoff updated.

## Acceptance Criteria

- [x] `POST /v2/exam-authoring/corrections/apply` appears in runtime OpenAPI
  with request schema `ExamAuthoringCorrectionsApplyRequestV1` and response
  schema `ExamAuthoringCorrectionsApplyResultV1`.
- [x] `/v2/exam-authoring/matching/manual-answer-key/apply` is absent from
  generated OpenAPI and returns a non-success response from the FastAPI app.
- [x] A valid `manual_matching_answer_key` correction applies through the
  unified route and returns effective matching answer-key state with
  `teacher_provided` provenance.
- [x] Matching source-item fingerprint, schema version, interaction ID, and
  source/target choice IDs fail closed before target readiness or artifacts are
  reported ready.
- [x] Non-matching correction entries are explicit rejected entries in the
  correction report in this first runtime slice; they do not mutate effective
  state or unlock targets.
- [x] Reusable Task 323 matching DTO/domain validation remains available for
  `manual_matching_answer_key`; Task 324 route-only request/response plumbing is
  gone.
- [x] Docs no longer describe the Task 324 route as a tolerated transitional route or
  continuation path.
- [x] Validation gates pass.

## Validation Plan

- [x] `pdm run openapi-export-v2`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_openapi_contract_v2.py`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_matching_manual_answer_key.py`
- [x] `pdm run coverage-gate`
- [x] `pdm run docs-sync`
- [x] `pdm run docs-validate`
- [x] `pdm run skills-validate`
- [x] `pdm run handoff-validate`
- [x] `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Evidence

- Added the unified source-neutral v2 route
  `POST /v2/exam-authoring/corrections/apply` through
  `scripts/sir_convert_a_lot/interfaces/http_routes_exam_authoring_corrections_v2.py`.
- Added unified request/response and correction-entry DTOs in
  `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_models.py`.
- Added runtime application logic in
  `scripts/sir_convert_a_lot/application/exam_authoring_corrections_apply_contracts.py`,
  including source binding validation, matching answer-key application,
  readiness/artifact projection, accepted report rows, and explicit unsupported
  report rows for non-matching entries.
- Removed the Task 324 matching-specific route from active FastAPI registration
  and OpenAPI publication. The old path is protected by a negative route test
  and by OpenAPI absence checks.
- Updated the governing contract docs, Story 49, Epic 11, Task 324, Task 327,
  and handoff so Task 324 is historical evidence only, not a tolerated product
  path.

## Validation Evidence

- `pdm run openapi-export-v2`
- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- `pdm run pytest-root tests/sir_convert_a_lot/test_exam_authoring_corrections_apply_route.py tests/sir_convert_a_lot/test_openapi_contract_v2.py tests/sir_convert_a_lot/test_exam_authoring_matching_manual_answer_key.py`
  passed 15 tests.
- `pdm run coverage-gate` passed 1382 tests, skipped 6 tests, and reached
  95.56% total coverage against the 90.0% gate.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
