---
type: adr
id: ADR-SIRCON-0010
title: Source-neutral Exam Authoring Correction Apply Contract
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: accepted
links:
  governing: []
deciders:
- platform
retired_ids:
- ADR-0011
---

## Context

## Decision

## Non-Decisions

## Consequences

## Historical Source Content

### Purpose

Define the target teacher-correction API direction for exam authoring before
Sir Convert adds more item families, source adapters, or authenticated
HuleEdu/Skriptoteket teacher-edit routes.

This decision keeps the current DigiExam `.dxe` conversion overlay acceptable
for the implemented DXE-only pipeline while preventing the historical
matching-specific Task 324 route from becoming the product pattern or a
long-lived compatibility surface.

### Status

- Accepted
- Date: 2026-05-18
- Acceptance evidence:
  `docs/backlog/reviews/review-23-ruthless-review-of-adr-0011-source-neutral-correction-apply-contract.md`
  approved this decision after the PR-0332 continuation gate was tightened.

### 1. Problem and Context

Sir Convert currently has two teacher-correction surfaces:

- `digiexam_ingestion_overlay_v2` on the DXE migration route, which covers
  visible item patches, point corrections, manual choice keys, manual gap-fill
  accepted values, reviewed completion keys, and historical accepted-current-state
  review decisions for the implemented DigiExam `.dxe` pipeline.
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
historical review decisions already had DigiExam-overlay paths. Task 337
supersedes the accepted-current-state portion of that history because
accepted-current-state is export policy, not authoring/correction state. That
asymmetry is not a clean target architecture.

### 2. Decision

Sir Convert will converge future teacher exam-authoring corrections on one
producer-owned, source-neutral apply contract:

```text
POST /v2/exam-authoring/corrections/apply
```

### Superseded Portion: Accepted-current-state Review Decision

Task 337 supersedes the original inclusion of `review_decision` /
`accept_current_state_for_export` in the unified correction contract. That entry
kind encoded export policy as authoring/correction state, which violates the
now-explicit boundary:

```text
authoring corrections mutate effective exam state
export policy consumes effective exam state and produces artifacts
```

The unified correction contract therefore keeps real authoring corrections such
as item text, point, manual answer-key, reviewed answer-key, matching, and
candidate-suppression entries, but removes accepted-current-state export
decisions. Missing answer keys remain missing until a real authoring correction
supplies key state. Any future incomplete/best-effort export must be governed by
a separate export-only request contract, not by correction replay, ingestion
overlay, source IR, or effective IR.

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

Task 324 is superseded historical route work for the already-built matching
gap. It must not be used as precedent for adding more item-specific
teacher-correction routes or for steering new `PR-0332` implementation back
into the abandoned adapter/route-per-item pattern. Task 330 hard-cuts from the
Task 324 route to `POST /v2/exam-authoring/corrections/apply`; it does not keep
the matching-specific route callable through an adapter, shim, alias, wrapper,
or compatibility layer.

Task 327 published the contract artifact at
`docs/reference/ref-sircon-general-exam-authoring-corrections-apply-contract-exam-authoring-corrections-apply-contract.md`. Task 330 adds
the runtime route and generated OpenAPI surface for the initial
`manual_matching_answer_key` implementation.

### 3. Boundary Rules

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

### 4. Current DXE Contract Position

The current `digiexam_ingestion_overlay_v2` path remains satisfactory for the
implemented DXE conversion pipeline. It can continue to serve Skriptoteket's
current DXE correction flow while Task 327 defines the unified contract.

This ADR does not remove or break the existing DXE overlay path. Migration from
DXE overlay semantics into the unified correction contract is a later governed
implementation concern.

### 5. HuleEdu And Skriptoteket Shape

HuleEdu should expose the unified route through the authenticated
`/sir-convert` edge when the Gateway lane is ready. HuleEdu should not add one
Gateway route per correction family unless a later governed task proves why the
unified contract cannot cover that case.

Skriptoteket should consume the unified route as the teacher-correction API and
treat returned Sir Convert effective state, target readiness, and artifact
availability as authoritative. Browser drafts remain non-authoritative until
Sir Convert applies the correction and returns producer state. Existing Task 324
matching transport is superseded historical route work only; new PR-0332
teacher-correction work must not target that path as the product architecture,
and Task 330 removes the matching-specific transport rather than preserving it
as compatibility.

ADR-0009 remains separate Gateway/public-edge authority. This ADR does not
accept ADR-0009 or change its proposed status.

### 6. Decision Closure For This Lane

This ADR closes the product-direction questions for Task 327:

- Current DXE overlay is acceptable for implemented DXE-only conversion.
- Task 324 is superseded historical route work, not a route-proliferation precedent or
  compatibility surface.
- Future teacher correction expansion should converge on one source-neutral
  correction/apply API.
- PR-0332 continuation may target the unified correction/apply contract after
  Task 327 completion and this accepted ADR, but runtime or consumer work still
  requires its own governed implementation slice. It must not target the old
  adapter/route-per-item path.
- Sir Convert owns validation, effective projection, target readiness, and
  artifact availability.
- HuleEdu proxies the unified producer route; Skriptoteket consumes it as the
  teacher correction API.

Other proposed decisions are not closed here. Task 328 owns the separate audit
of proposed ADRs before further architecture expansion.

### 7. Consequences

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
- Existing DXE overlay and Task 324 semantics need an explicit hard-cut
  migration plan before runtime convergence.
- Downstream migration must be sequenced separately after Sir Convert accepts
  and implements the unified contract.

### 8. Follow-up

- Task 327 defines the contract and hard-cut migration plan in
  `docs/reference/ref-sircon-general-exam-authoring-corrections-apply-contract-exam-authoring-corrections-apply-contract.md`.
- A later implementation task adds the route and OpenAPI/request-validation
  proof; it must remove the Task 324 matching-specific route/dead code in the
  same governed hard-cut slice.
- HuleEdu and Skriptoteket follow-up tasks migrate authenticated edge proxying
  and teacher-correction consumption after the Sir Convert contract exists.
- Task 328 audits remaining proposed ADR states, especially ADR-0002 and
  ADR-0009, without treating this ADR as acceptance for those decisions.
