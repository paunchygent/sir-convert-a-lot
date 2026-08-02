---
id: story-12-legacy-path-removal-docs-cleanup-and-runtime-simplification
title: Legacy path removal docs cleanup and runtime simplification
type: story
status: completed
priority: high
created: '2026-02-28'
last_updated: '2026-02-28'
related:
  - docs/backlog/epics/epic-05-v2-only-unified-conversion-core-and-template-first-markdown-pathways.md
  - docs/backlog/tasks/task-50-remove-eval-container-and-simplify-compose-runtime-topology.md
  - docs/backlog/tasks/task-51-purge-conflicting-legacy-docs-and-stale-v1-code-paths.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - cleanup
  - docs
  - runtime
---

Implementation slice with acceptance-driven scope.

## Objective

Remove obsolete and conflicting code/documentation/runtime paths so the codebase is easy to reason
about and aligned to one hardened production direction.

## Scope

- Remove eval container/profile paths and associated scripts/docs references.
- Remove stale local/hybrid/v1 references in READMEs, converter docs, runbooks, and backlog pointers.
- Remove stale compatibility facades or code paths that no longer map to active architecture.
- Keep SRP and module-boundary clarity as cleanup is applied.

## Acceptance Criteria

- [x] Compose/runtime topology uses a single canonical conversion runtime path.
- [x] No active docs instruct users to use removed v1/eval/local-hybrid conversion behavior.
- [x] Stale code paths are removed or explicitly marked deprecated with planned deletion date if blocked.
- [x] Docs-as-code validators pass after cleanup.

## Test Requirements

- [x] Ops smoke checks still pass on canonical lane after eval path removal.
- [x] Regression test suite passes with simplified runtime topology.
- [x] Grep-based hygiene checks for stale references are added and passing.

## Done Definition

Repository narrative, runtime topology, and code paths all tell the same story: one hardened v2 core.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
