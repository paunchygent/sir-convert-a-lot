---
id: task-315-extract-exam-net-pdf-item-rendering-policy-strategies-from-item-type-branch-ladder
title: Extract Exam.net PDF item rendering policy strategies from item-type branch ladder
type: task
status: proposed
priority: high
created: '2026-05-15'
last_updated: '2026-05-15'
related:
  - docs/backlog/epics/epic-10-digiexam-to-exam-net-exam-migration-pipeline.md
  - docs/backlog/stories/story-50-solid-domain-coupling-audit-for-exam-converter-implementation-boundaries.md
  - docs/backlog/tasks/task-313-audit-solid-domain-coupling-and-implementation-branch-hotspots-across-exam-converter-surfaces.md
  - docs/reference/ref-exam-converter-solid-domain-coupling-audit.md
  - scripts/sir_convert_a_lot/domain/digiexam_examnet_pdf_items.py
labels:
  - solid
  - ddd
  - exam-converter
  - examnet-pdf
  - target-policy
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Extract Exam.net PDF item rendering policy from the centralized
`DigiExamItemType` branch ladder in `digiexam_examnet_pdf_items.py` into
explicit item-rendering policies or strategies.

The goal is not to remove all conditionals. The goal is to stop one function
family from owning item-type support, answer-key trust, accepted-current-state
fallbacks, warning semantics, target support, and HTML assembly at the same
time.

## PR Scope

- Introduce a domain-facing rendering strategy/protocol for Exam.net PDF item
  rendering, keyed by item kind or target policy in one owned registry.
- Move choice, multiple-response, gap-fill, open-ended, and unsupported item
  policy decisions out of `_render_item` while preserving the existing artifact
  contract.
- Keep prompt rendering, escaping, and HTML shell helpers pure and local.
- Preserve the Task 308 accepted-current-state manual/unkeyed profile for
  missing-key choice items and item-013-style multi-gap items.
- Do not expand supported item types, alter target readiness semantics, or
  change artifact availability in this task.

## Deliverables

- [ ] Exam.net PDF item-renderer strategy/protocol.
- [ ] Registry or factory selected by domain item kind/target profile.
- [ ] Existing choice, multiple-response, gap-fill, open-ended, manual
  unkeyed, and unsupported rendering paths moved behind the strategy boundary.
- [ ] Focused tests proving rendered output and warnings are unchanged.

## Acceptance Criteria

- [ ] Adding a new governed PDF item profile does not require widening
  `_render_item` with another item-type branch.
- [ ] Answer-key trust and accepted-current-state decisions for PDF rendering
  live in policy objects, not ad hoc renderer branches.
- [ ] Manual/unkeyed choice and gap-fill rendering remains available only when
  explicitly requested through accepted-current-state policy.
- [ ] Unsupported item types still fail closed with typed warnings.
- [ ] No source IR, effective IR, QTI, bundle manifest, or target-readiness
  behavior changes are introduced.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
