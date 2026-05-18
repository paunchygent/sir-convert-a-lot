---
id: review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit
title: Ruthless review of Task 328 proposed ADR product decision audit
type: review
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/backlog/tasks/task-328-audit-open-proposed-adr-product-decisions-before-further-architecture-expansion.md
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
labels:
  - review
  - adr
  - decision-audit
  - product-direction
---

Structured review artifact for implementation or readiness checks.

## Review Scope

- Review type: ruthless docs-as-code audit of open proposed ADR product
  decisions before further architecture expansion.
- Governing authority:
  - `AGENTS.md`
  - `.codex/handoff.md`
  - `.codex/rules/090-documentation-standards.md`
  - `docs/backlog/tasks/task-328-audit-open-proposed-adr-product-decisions-before-further-architecture-expansion.md`
  - `docs/decisions/0002-multi-format-service-api-v2.md`
  - `docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md`
  - `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md`
- Public surfaces affected:
  - Service API v2 product/contract authority.
  - Gateway-fronted public/internal/operator access decision state.
  - Source-neutral teacher correction/apply product direction.
- Compatibility posture:
  - Docs-only governance audit.
  - No ADR is accepted, superseded, or deprecated by this review.
  - Any ADR status change requires its own governed review or acceptance task.
- Evidence reviewed:
  - All `docs/decisions/*.md` files with `status: proposed`.
  - ADR-0002, ADR-0009, ADR-0011 frontmatter and status sections.
  - Task 33, Task 257, Task 327, Review 06, Epic 04, Epic 09, Epic 11, Story 49,
    and current handoff references.

## Findings

1. [x] `high` - ADR-0002 is still proposed even though Service API v2 is
   already active runtime and converter-contract authority.

   Evidence:

   - ADR-0002 frontmatter remains `status: proposed` at
     `docs/decisions/0002-multi-format-service-api-v2.md:5`.
   - The governing Task 33 that created the ADR and converter contract is
     completed at
     `docs/backlog/tasks/task-33-service-multi-format-api-v2-contract-adr.md:5`.
   - The converter contract now says Service API v2 is active and that v1
     conversion routes were removed from the runtime surface at
     `docs/converters/multi_format_conversion_service_api_v2.md:37`.

   Why it matters:
   A proposed ADR that already underpins active runtime behavior creates a false
   authority split: implementation and converter docs treat v2 as normative,
   while decision state says the product decision was never accepted. That makes
   future architecture expansion brittle because downstream tasks can cite v2
   behavior without a closed decision record.

   Required fix:
   Create or use a focused ADR-0002 closeout task that either accepts ADR-0002
   as implemented service API v2 authority, or supersedes it with a newer
   accepted decision if the active v2 shape has moved beyond the original
   February 2026 text. Do not silently flip the status inside unrelated
   implementation work.

   Proof requirement:
   The closeout task must compare ADR-0002 against the active converter
   contract, OpenAPI/runtime route set, and any accepted follow-on ADRs
   (ADR-0003 through ADR-0008). Run `pdm run docs-sync`,
   `pdm run docs-validate`, `pdm run skills-validate`,
   `pdm run handoff-validate`, and `git diff --check`.

1. [x] `medium` - ADR-0009 is review-ready but must remain proposed until its
   explicit Gateway acceptance task closes.

   Evidence:

   - ADR-0009 frontmatter remains `status: proposed` at
     `docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md:5`.
   - Review 06 closed ADR-0009 readiness as approved while explicitly stating
     the ADR itself remains proposed until Task 257 performs the acceptance
     update at
     `docs/backlog/reviews/review-06-ruthless-review-of-adr-0009-gateway-cutover-readiness.md:198`.
   - Task 257 is still proposed and its deliverable is the accepted ADR-0009 at
     `docs/backlog/tasks/task-257-publish-adr-0009-for-gateway-fronted-sir-convert-access.md:5`.

   Why it matters:
   Treating review readiness as decision acceptance would bypass the Gateway
   cutover governance gate and could let direct public-edge, internal identity,
   and operator-lane assumptions leak into implementation as accepted product
   architecture before Task 257 performs the explicit acceptance closeout.

   Required fix:
   Keep ADR-0009 proposed. The next action is Task 257, not a status edit inside
   Task 328.

   Proof requirement:
   Task 257 must update ADR-0009 and affected converter/runbook/backlog links
   together, then run the docs gates named above.

1. [x] `medium` - ADR-0011 is intentionally proposed and cannot authorize
   runtime route expansion until Task 327 and a separate acceptance step close.

   Evidence:

   - ADR-0011 frontmatter remains `status: proposed` at
     `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md:5`.
   - ADR-0011 names a later review or acceptance task as the acceptance gate at
     `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md:32`.
   - Task 327 says runtime implementation, HuleEdu proxy work, and Skriptoteket
     UI migration require separate governed slices after ADR-0011 and the
     contract are accepted at
     `docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md:93`.

   Why it matters:
   The unified correction route is a good product direction, but using it as
   accepted authority today would skip the contract-first guardrails that
   prevent one more item-specific route from becoming the de facto architecture.

   Required fix:
   Keep ADR-0011 proposed. Complete Task 327 as the contract slice, then create
   a separate ADR-0011 review/acceptance closeout before runtime or downstream
   migration treats `/v2/exam-authoring/corrections/apply` as accepted.

   Proof requirement:
   Task 327 must publish the typed correction-entry contract, source-binding
   validation, response projection, and consumer migration notes, then run the
   docs gates named above.

## Decision

approved

## Response

Task 328 audit is approved as a governance closeout: it identifies the complete
set of currently proposed ADRs, preserves all proposed statuses, and assigns one
concrete next action to each ADR.

This review does not approve any ADR acceptance. ADR-0002 needs a dedicated
closeout task because implemented runtime truth has overtaken its proposed
state. ADR-0009 remains governed by Task 257. ADR-0011 remains governed by Task
327 plus a later acceptance step.

## Follow-up Actions

1. Create or schedule an ADR-0002 closeout task: accept as implemented v2
   authority or supersede with an accepted current-state decision.
1. Continue Task 257 when the Gateway cutover lane is ready to accept ADR-0009.
1. Continue Task 327 before treating ADR-0011 as runtime or downstream
   migration authority.

## Completion

Review completed on 2026-05-18. No ADR status was changed by this review.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
