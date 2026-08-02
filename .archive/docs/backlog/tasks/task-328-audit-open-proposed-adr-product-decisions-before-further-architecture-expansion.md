---
id: task-328-audit-open-proposed-adr-product-decisions-before-further-architecture-expansion
title: Audit open proposed ADR product decisions before further architecture expansion
type: task
status: completed
priority: high
created: '2026-05-18'
last_updated: '2026-05-18'
related:
  - docs/decisions/0002-multi-format-service-api-v2.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/tasks/task-327-define-unified-source-neutral-exam-authoring-correction-apply-contract.md
  - docs/backlog/epics/epic-11-machine-marked-answer-key-completion-for-exam-conversion.md
  - docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md
labels:
  - adr
  - decision-audit
  - product-direction
  - governance
---

Separate governance slice for proposed decision cleanup.

## Objective

Audit open proposed ADRs before further architecture expansion so product
direction is explicit and stale proposed decisions do not accidentally become
implicit authority.

This task is separate from ADR-0011. Creating ADR-0011 closes the
teacher-authoring correction direction inside that lane, but it does not accept
or supersede older repo-wide proposed ADRs.

## PR Scope

- Inventory all `docs/decisions/*.md` files with `status: proposed`.
- Classify each proposed ADR as:
  - still intentionally proposed;
  - ready for an explicit review/acceptance task;
  - superseded by accepted decisions or implemented runtime truth;
  - stale and requiring a replacement task before status changes.
- Start with the currently known proposed ADRs:
  - ADR-0002, `Multi-format Conversion Service API v2`;
  - ADR-0009, `Gateway-Fronted Sir Convert Public Access and Internal Service Boundary`;
  - ADR-0011, `Source-neutral Exam Authoring Correction Apply Contract`.
- Preserve the ADR-0009 rule: review readiness and ADR acceptance are separate;
  do not accept ADR-0009 without its explicit Gateway acceptance task.
- Produce a recommended closeout map with one concrete next action per
  proposed ADR.

## Out of Scope

- Accepting, superseding, or deprecating an ADR without the required governed
  review or acceptance evidence.
- Runtime implementation.
- HuleEdu or Skriptoteket repo changes.
- Rewriting accepted ADRs unless the audit finds a direct status conflict.

## Deliverables

- [x] Proposed-ADR inventory with file paths, current status, owning lane, and
  linked backlog authority.
- [x] Recommendation for each proposed ADR: keep proposed, prepare acceptance,
  prepare supersession, or create replacement task.
- [x] Explicit ADR-0009 note preserving the proposed state until its Gateway
  acceptance path closes.
- [x] Docs/handoff updates that make the next decision-audit action visible.

## Acceptance Criteria

- [x] No proposed ADR is silently accepted or superseded.
- [x] Every proposed ADR has a current owner, reason for remaining proposed, and
  next governed action.
- [x] ADR-0011 remains separate from the ADR-0002/ADR-0009 audit outcome.
- [x] The audit output distinguishes product-direction uncertainty from
  implementation backlog work.
- [x] Validation passes with `pdm run docs-sync`, `pdm run docs-validate`,
  `pdm run skills-validate`, `pdm run handoff-validate`, and
  `git diff --check`.

## Proposed ADR Inventory

Inventory command:

```bash
rg -n "^status: proposed|^id: ADR-|^title:" docs/decisions -g "*.md"
```

The only decision files with `status: proposed` are ADR-0002, ADR-0009, and
ADR-0011.

| ADR | File | Current status | Owning lane | Backlog authority | Audit classification | Next governed action |
| --- | --- | --- | --- | --- | --- | --- |
| ADR-0002, Multi-format Conversion Service API v2 | `docs/decisions/0002-multi-format-service-api-v2.md` | proposed | Service API v2 / Epic 04 converter-suite parity | Completed Task 33 plus active `docs/converters/multi_format_conversion_service_api_v2.md` | Stale proposed decision overtaken by implemented runtime truth | Create a focused ADR-0002 closeout task to accept ADR-0002 as implemented v2 authority or supersede it with a current-state accepted decision. |
| ADR-0009, Gateway-Fronted Sir Convert Public Access and Internal Service Boundary | `docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md` | proposed | Epic 09 Gateway cutover and internal/operator access | Review 06 approved readiness; Task 257 remains the explicit acceptance task | Intentionally proposed until Gateway acceptance path closes | Keep proposed. Continue Task 257 when ready; do not treat Review 06 approval as ADR acceptance. |
| ADR-0011, Source-neutral Exam Authoring Correction Apply Contract | `docs/decisions/0011-source-neutral-exam-authoring-correction-apply-contract.md` | proposed | Epic 11 / Story 49 teacher correction API direction | Task 327 defines the contract slice; this Task 328 audits repo-wide proposed ADR state | Intentionally proposed product direction for the correction/apply lane | Keep proposed. Complete Task 327, then add a separate ADR-0011 review/acceptance closeout before runtime expansion or downstream migration treats it as accepted. |

## Audit Decision

No ADR is accepted, superseded, or deprecated by this task.

ADR-0002 is the only proposed decision whose state appears stale against
implemented runtime truth. Service API v2 is already active contract authority,
Task 33 is completed, and later accepted ADRs extend v2. The clean next action
is not an inline status flip; it is a focused ADR-0002 closeout task that
compares the original decision against the current active v2 contract and then
accepts or supersedes it with evidence.

ADR-0009 remains proposed by design. Review 06 approved readiness, but Task 257
is still the acceptance authority. This audit preserves the rule that Gateway
review readiness and ADR acceptance are separate states.

ADR-0011 remains separate from ADR-0002 and ADR-0009. It is the proposed
teacher-correction direction for one source-neutral
`/v2/exam-authoring/corrections/apply` contract, and Task 327 must complete the
contract before a later acceptance task can treat the route as accepted product
architecture.

## Review Record

Ruthless review findings are retained in
`docs/backlog/reviews/review-21-ruthless-review-of-task-328-proposed-adr-product-decision-audit.md`.

## Validation Evidence

- [x] `pdm run docs-sync` refreshed generated indexes.
- [x] `pdm run docs-validate` passed: `Validated 413 backlog files`,
  `Validated docs=484 rules=11`.
- [x] `pdm run skills-validate` passed.
- [x] `pdm run handoff-validate` passed.
- [x] `git diff --check` passed.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
