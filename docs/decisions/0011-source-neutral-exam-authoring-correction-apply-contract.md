---
type: decision
id: ADR-0011
title: Source-neutral Exam Authoring Correction Apply Contract
status: proposed
created: 2026-05-18
updated: 2026-05-18
owners:
  - platform
tags:
  - adr
  - exam-authoring
  - correction-contract
  - source-neutral
  - skriptoteket
  - huleedu
  - api
links:
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-322-add-points-scoring-correction-producer-dto-before-pr-0332.md
  - docs/backlog/tasks/task-323-expose-source-neutral-matching-manual-answer-key-producer-dto-for-skriptoteket.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-328-audit-open-proposed-adr-product-decisions-before-further-architecture-expansion.md
  - docs/converters/exam-authoring-ir-v1-contract.md
  - docs/converters/digiexam-migration-service-api-artifact-contract.md
---

## Purpose

Define the target teacher-correction API direction for exam authoring before
Sir Convert adds more item families, source adapters, or authenticated
HuleEdu/Skriptoteket teacher-edit routes.

This decision keeps the current DigiExam `.dxe` conversion overlay acceptable
for the implemented DXE-only pipeline while preventing the historical
matching-specific Task 324 route from becoming the product pattern.

## Status

- Proposed
- Date: 2026-05-18
- Acceptance gate: a later review or acceptance task must approve this ADR
  before runtime implementation or downstream migration treats it as accepted.

## 1. Problem and Context

Sir Convert currently has two teacher-correction surfaces:

- `digiexam_ingestion_overlay_v2` on the DXE migration route, which covers
  visible item patches, point corrections, manual choice keys, manual gap-fill
  accepted values, reviewed completion keys, and accepted-current-state review
  decisions for the implemented DigiExam `.dxe` pipeline.
- `POST /v2/exam-authoring/matching/manual-answer-key/apply`, added by Task
  324 so Skriptoteket can submit source-neutral matching manual keys for
  matching-capable `ExamAuthoringIR v1` flows without forcing matching into the
  DigiExam overlay.

The current DXE-only path is satisfactory for the implemented conversion
pipeline. DigiExam `.dxe` sources do not provide canonical matching items, so
matching must stay out of the DigiExam ingestion overlay.

The architectural risk is different: Task 324 exists because matching was the
first correction family without a callable neutral producer route. Choice,
gap/open-cloze, point corrections, item-content patches, reviewed keys, and
review decisions already had historical DigiExam-overlay paths. That asymmetry
is not a clean target architecture.

## 2. Decision

Sir Convert will converge future teacher exam-authoring corrections on one
producer-owned, source-neutral apply contract:

```text
POST /v2/exam-authoring/corrections/apply
```

The contract must use typed correction entries rather than one route per item
type or one route per source adapter. Initial correction-entry families are:

- item text, stem, prompt, or visible option correction;
- point correction;
- manual choice answer key;
- manual gap/open-cloze accepted values;
- manual matching answer key;
- review decision and candidate suppression.

The API must be source-neutral from the consumer perspective. A teacher-facing
consumer should not need to know whether the original item came from DigiExam,
Exam.net, CSV, DOCX, Markdown, or a future importer in order to submit a
correction.

Source adapters remain ingestion details. They may own source-native parse
models, source evidence, fingerprints, and adapter mapping into
`ExamAuthoringIR v1` or another governed neutral authoring state. Sir Convert
owns correction validation, source-binding checks, effective-state projection,
target readiness, and artifact availability.

Task 324 remains valid bridge work. It must not be used as precedent for adding
more item-specific teacher-correction routes.

## 3. Boundary Rules

The unified correction contract must preserve at least the current DXE overlay
privacy and provenance guarantees:

- no raw `.dxe`;
- no raw PDF text;
- no raw overlay JSON in returned reports;
- no raw provider data;
- no credentials;
- no identity markers beyond governed auth context;
- no earned scores;
- no wrong selections;
- no free-text student answers;
- no per-student performance history.

Corrections must be validated against producer-returned state, source binding,
schema versions, item or interaction identifiers, item type compatibility, and
target-specific readiness policy before artifacts are reported ready.

Teacher corrections must change effective renderer input or effective
authoring state only. They must not mutate parser-owned source IR or reclassify
teacher/reviewed data as parser evidence.

## 4. Current DXE Contract Position

The current `digiexam_ingestion_overlay_v2` path remains satisfactory for the
implemented DXE conversion pipeline. It can continue to serve Skriptoteket's
current DXE correction flow while Task 327 defines the unified contract.

This ADR does not remove or break the existing DXE overlay path. Migration from
DXE overlay semantics into the unified correction contract is a later governed
implementation concern.

## 5. HuleEdu And Skriptoteket Shape

HuleEdu should expose the unified route through the authenticated
`/sir-convert` edge when the Gateway lane is ready. HuleEdu should not add one
Gateway route per correction family unless a later governed task proves why the
unified contract cannot cover that case.

Skriptoteket should consume the unified route as the teacher-correction API and
treat returned Sir Convert effective state, target readiness, and artifact
availability as authoritative. Browser drafts remain non-authoritative until
Sir Convert applies the correction and returns producer state.

ADR-0009 remains separate Gateway/public-edge authority. This ADR does not
accept ADR-0009 or change its proposed status.

## 6. Decision Closure For This Lane

This ADR closes the product-direction questions for Task 327:

- Current DXE overlay is acceptable for implemented DXE-only conversion.
- Task 324 is bridge work, not a route-proliferation precedent.
- Future teacher correction expansion should converge on one source-neutral
  correction/apply API.
- Sir Convert owns validation, effective projection, target readiness, and
  artifact availability.
- HuleEdu proxies the unified producer route; Skriptoteket consumes it as the
  teacher correction API.

Repo-wide proposed decisions are not closed here. Task 328 owns the separate
audit of open proposed ADRs before further architecture expansion.

## 7. Consequences

### Positive

- Future item families and source adapters share one product-facing correction
  API direction.
- Skriptoteket avoids source-specific or item-type-specific correction
  transports.
- HuleEdu Gateway can proxy one stable teacher-correction route instead of
  accumulating family-specific endpoints.
- Existing DXE work is not blocked or invalidated.

### Costs

- Task 327 must design a typed correction union carefully enough to avoid a
  weak generic payload.
- Existing DXE overlay and Task 324 semantics need an explicit compatibility
  plan before runtime convergence.
- Downstream migration must be sequenced separately after Sir Convert accepts
  and implements the unified contract.

## 8. Follow-up

- Task 327 defines the contract and compatibility plan.
- A later implementation task adds the route and OpenAPI/request-validation
  proof after this ADR is accepted.
- HuleEdu and Skriptoteket follow-up tasks migrate authenticated edge proxying
  and teacher-correction consumption after the Sir Convert contract exists.
- Task 328 audits remaining proposed ADR states, especially ADR-0002 and
  ADR-0009, without treating this ADR as acceptance for those decisions.
