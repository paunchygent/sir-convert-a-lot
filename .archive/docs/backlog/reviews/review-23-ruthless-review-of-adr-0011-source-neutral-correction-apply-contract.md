---
id: review-23-ruthless-review-of-adr-0011-source-neutral-correction-apply-contract
title: Ruthless review of ADR-0011 source-neutral correction apply contract
type: review
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/converters/exam-authoring-corrections-apply-contract.md
  - docs/backlog/stories/story-49-skriptoteket-teacher-review-workflow-for-answer-key-completion.md
  - docs/backlog/tasks/task-324-add-source-neutral-matching-correction-apply-route-for-skriptoteket-pr-0332.md
  - docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md
labels:
  - review
  - adr
  - exam-authoring
  - correction-contract
  - source-neutral
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless docs-as-code review of ADR-0011 as the proposed
  source-neutral teacher-correction apply decision.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/010-foundational-principles.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md`
  - `docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md`
- Scope under review:
  - ADR-0011 proposed decision text and status guardrails.
  - Task 327 completion state and its draft contract deliverable.
  - `docs/converters/exam-authoring-corrections-apply-contract.md` as the
    delegated typed contract surface.
- Public surfaces affected:
  - Future `POST /v2/exam-authoring/corrections/apply` API direction.
  - Existing Task 324
    `POST /v2/exam-authoring/matching/manual-answer-key/apply` route.
  - HuleEdu `/sir-convert` proxy shape and Skriptoteket teacher-correction
    consumer sequencing.
- Compatibility posture:
  - Docs-only decision/readiness review.
  - The Task 324 matching-specific route must be hard-cut in the later unified
    route implementation; no adapter, shim, alias, wrapper, or compatibility
    layer may keep it callable.
  - This review does not implement runtime code, remove routes, change
    OpenAPI/runtime artifacts, or accept ADR-0011 by status edit.
- Evidence reviewed:
  - ADR-0011 lines 42-47, 72-114, 140-167, 169-219.
  - Task 327 lines 122-132, 184-233, 235-260.
  - Draft correction/apply contract lines 42-44, 86-89, 143-174, 389-409,
    462-511, 513-532.
  - Handoff ADR-0011 active pointers and next actions.

## Findings

1. [x] `medium` - ADR-0011's closure summary weakens its own acceptance gate for
   PR-0332 continuation.

   Evidence:

   - ADR-0011 correctly keeps the decision proposed and requires a later review
     or acceptance task before runtime implementation or downstream migration
     treats it as accepted at
     `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md:46`.
   - The delegated contract repeats that ADR acceptance must happen before
     runtime implementation treats the direction as accepted at
     `docs/converters/exam-authoring-corrections-apply-contract.md:503`.
   - Original blocker before remediation: the closure summary said PR-0332
     continuation should target the unified contract "once Task 327 closes",
     which did not include the ADR acceptance gate.
   - Task 327 is already completed at
     `docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md:5`.

   Why it matters:
   Task 327 completion alone is not the acceptance gate ADR-0011 defines. Leaving
   the summary keyed only to Task 327 creates a governance ambiguity where a
   downstream Skriptoteket or HuleEdu slice could cite ADR-0011 as product
   authority while the ADR still says `status: proposed`.

   Required fix:
   Amend the closure summary to use the same gate as the rest of the docs:
   PR-0332 continuation may target the unified correction/apply contract only
   after Task 327 is complete, ADR-0011 is accepted through the retained
   review/acceptance path, and any runtime consumer work is attached to its own
   governed implementation slice. Keep the no-adapter/no-shim hard-cut language.

   Proof requirement:
   Run `pdm run docs-sync`, `pdm run docs-validate`,
   `pdm run skills-validate`, `pdm run handoff-validate`, and
   `git diff --check`.

   Re-review disposition:
   Resolved on 2026-05-18. ADR-0011 now states that PR-0332 continuation should
   target the unified correction/apply contract only after Task 327 is complete,
   ADR-0011 is accepted through the retained review/acceptance path, and runtime
   or consumer work has its own governed implementation slice at
   `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md:178`.
   The linked Story 49 and draft contract preserve the same conditional
   sequencing.

## Decision

approved

## Response

ADR-0011 is architecturally sound in its main direction: one producer-owned,
source-neutral correction/apply contract; typed entries rather than route
proliferation; source adapters kept behind ingestion boundaries; explicit
privacy/provenance rules; and a hard cut away from the Task 324 matching route
with no adapter, shim, alias, wrapper, or compatibility layer.

The re-review blocker is resolved. ADR-0011 now consistently keeps the unified
correction/apply contract conditional on ADR acceptance before runtime,
HuleEdu, or Skriptoteket work treats it as accepted authority.

## Follow-up Actions

No blocking follow-up for ADR-0011 review acceptance.

The later runtime implementation task must still add
`POST /v2/exam-authoring/corrections/apply` and remove the Task 324
matching-specific route/dead code atomically, with no adapter, shim, alias,
wrapper, or compatibility layer.

## Completion

Re-reviewed and completed as `approved` on 2026-05-18. ADR-0011 status was not
changed by this review.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
