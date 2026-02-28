---
id: task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths
title: Purge conflicting legacy docs and stale v1 code paths
type: task
status: proposed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/stories/story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification.md
  - docs/backlog/reviews/review-01-brutal-review-service-api-v2-multi-format-pivot/README.md
labels:
  - cleanup
  - docs
  - v1-removal
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Remove stale and conflicting docs/code references so the codebase narrative is consistent and easy to reason about.

## PR Scope

- Remove/replace stale references to v1 coexistence and local/hybrid converter behavior.
- Clean stale module docstrings that no longer match runtime behavior.
- Remove conflicting docs around capability matrix and route policy where outdated.
- Ensure converter/API docs describe only active architecture and routes.

## Deliverables

- [ ] Converter, runbook, reference, and README docs aligned to active v2-only architecture.
- [ ] Stale v1/local-hybrid code path references removed from active modules.
- [ ] Validation gates and indexing pass after cleanup.

## Acceptance Criteria

- [ ] Grep-based hygiene checks show no stale references to removed v1 conversion surfaces.
- [ ] Docs users follow match actual runtime/CLI behavior.
- [ ] Backlog current-context references are synchronized with new epic direction.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
