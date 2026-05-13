---
id: task-289-finish-or-retire-task-200-qwen-metadata-scaffolds
title: Finish or retire Task 200 Qwen metadata scaffolds
type: task
status: proposed
priority: high
created: '2026-05-13'
last_updated: '2026-05-13'
related:
  - docs/backlog/stories/story-46-service-source-simplification-and-active-surface-truth-cleanup-before-exam-net-runtime.md
  - docs/backlog/tasks/task-200-refactor-qwen-training-metadata-module-into-bounded-control-plane-modules-without-compatibility-shims.md
  - docs/backlog/stories/story-28-permanently-harden-qwen-training-srp-and-ddd-boundaries.md
  - .codex/rules/096-qwen-experiment-governance.md
labels:
  - qwen
  - scaffolds
  - cleanup
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Finish or retire the remaining Task 200 Qwen metadata scaffolds so governed
`NotImplementedError` placeholders and migration leftovers do not remain as
permanent source-code furniture.

## PR Scope

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
- Do not reopen Task 101 experiment interpretation or delete historical
  evidence beyond the explicit Task 200 scaffold scope.

## Deliverables

- [ ] Source audit of Task 200 metadata scaffolds and legacy imports.
- [ ] Implemented or removed placeholder surfaces.
- [ ] Focused tests for the chosen completion path, or removal tests proving no
  active import/CLI path depends on retired scaffolds.
- [ ] Task 200 docs-state reconciliation.

## Acceptance Criteria

- [ ] No active Qwen metadata control-plane module contains a governed
  placeholder `NotImplementedError`.
- [ ] No compatibility shim is kept only to preserve old Task 200 import paths.
- [ ] Task 200 status and checklist state match the actual source state.
- [ ] Any deleted scaffold is proven unused by tests, import checks, or command
  help checks.
- [ ] Close-out validation includes focused Qwen metadata tests, docs gates, and
  standard Python gates for touched source.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
