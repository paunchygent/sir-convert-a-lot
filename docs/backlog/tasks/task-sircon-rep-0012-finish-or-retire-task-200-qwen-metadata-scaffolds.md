---
type: task
id: TASK-SIRCON-REP-0012
title: Finish or retire Task 200 Qwen metadata scaffolds
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- '- [ ] No active Qwen metadata control-plane module contains a governed placeholder
  `NotImplementedError`.'
- '- [ ] No compatibility shim is kept only to preserve old Task 200 import paths.'
- '- [ ] Task 200 status and checklist state match the actual source state.'
- '- [ ] Any deleted scaffold is proven unused by tests, import checks, or command
  help checks.'
- '- [ ] Close-out validation includes focused Qwen metadata tests, docs gates, and
  standard Python gates for touched source.'
retired_ids:
- task-289-finish-or-retire-task-200-qwen-metadata-scaffolds
---

## Context

## Impact And Escalation

## Decision And Assumption Ledger

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Readiness

## Closeout

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Finish or retire the remaining Task 200 Qwen metadata scaffolds so governed
`NotImplementedError` placeholders and migration leftovers do not remain as
permanent source-code furniture.

### PR Scope

- Re-read Task 200 and its related Story 28/Rule 096 authority before choosing
  completion or retirement.
- Inspect the Task 200 metadata loaders/renderers and any legacy metadata module
  references for `NotImplementedError`, placeholder methods, compatibility
  shims, or stale migration comments.
- Either complete the bounded control-plane modules with focused tests or
  retire the unused scaffolded surfaces with docs/tests updated.
- Reconcile Task 200 frontmatter, checklists, deliverables, and close-out notes
  so future developers can tell whether the lane is active, complete, or
  intentionally retired.
- Do not reopen Qwen experiment interpretation or delete historical
  evidence beyond the explicit Task 200 scaffold scope.

### Deliverables

- [ ] Source audit of Task 200 metadata scaffolds and legacy imports.
- [ ] Implemented or removed placeholder surfaces.
- [ ] Focused tests for the chosen completion path, or removal tests proving no
  active import/CLI path depends on retired scaffolds.
- [ ] Task 200 docs-state reconciliation.

### Acceptance Criteria

- [ ] No active Qwen metadata control-plane module contains a governed
  placeholder `NotImplementedError`.
- [ ] No compatibility shim is kept only to preserve old Task 200 import paths.
- [ ] Task 200 status and checklist state match the actual source state.
- [ ] Any deleted scaffold is proven unused by tests, import checks, or command
  help checks.
- [ ] Close-out validation includes focused Qwen metadata tests, docs gates, and
  standard Python gates for touched source.

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
