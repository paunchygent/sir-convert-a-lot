---
id: 'task-380-job-store-r2-adapter-decision-and-runtime-proof-package'
title: 'Job store R2 adapter decision and runtime proof package'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-07-02'
last_updated: '2026-07-04'
approval_protocol: 'agent-planning:user-closure-gate'
approval_note: 'User approval: Repair/approve the Story 59 planning closeout with the closure-gate marker.'
related:
  - docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md
  - docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md
  - docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md
  - docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md
  - docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md
labels:
  - r2
  - object-storage
  - job-store
  - persistence
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Produce the implementation-ready package for a Sir Convert R2-backed storage
adapter without changing runtime code. The task must close or route every open
question in `REF-cloudflare-r2-job-artifact-storage-migration-pre-runbook`.

## PR Scope

In scope:

- Decide first artifact classes to migrate.
- Define storage port and adapter responsibilities.
- Define config/env names and compose validation.
- Define route streaming/proxy requirements that replace `FileResponse(path=...)`
  safely.
- Define retention, delete, migration, rollback, and live proof requirements.

Out of scope:

- Implementing the adapter.
- Mutating production `.env`.
- Deleting or moving existing prod data.
- Changing Sir Convert job API contracts except where a later ADR explicitly
  approves an additive field.

## Deliverables

- [x] Reviewed ADR/reference/story/task package.
- [x] Closed open-question ledger or follow-up tasks for every unresolved item.
- [x] First implementation task sketch with red-first tests and live proof.
- [x] Prod env sync checklist with secret-source labels only.

## Acceptance Criteria

- [x] No implementation step assumes R2 is POSIX-compatible.
- [x] No implementation step routes job runtime storage through HuleEdu File
  Service.
- [x] Object key, metadata, retention, purge, migration, rollback, config, and
  proof obligations are explicit.
- [x] Future tests cover object missing, owner denial, stale/mismatched artifact
  denial, purge delete, and successful terminal/named artifact reads.
- [x] Docs sync and validation pass.

## Decision Summary

- First implementation slice: terminal/cold artifact blobs only, covering the
  primary terminal artifact and route-owned named terminal bundle artifacts.
- Explicit non-goals: raw uploads, resources, reference DOCX files, manifests,
  lifecycle events, idempotency state, POSIX locks, active scratch/work dirs,
  partials, checkpoints, logs, correction replay artifact sets, production
  backfill, production env mutation, and raw/presigned R2 browser URLs.
- Storage key and metadata requirements, approved env names, readiness fields,
  retention/delete reconciliation, test backend, and live-proof obligations are
  captured in
  `docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md`.
- Wider migration questions are routed to named follow-up task sketches in the
  reference instead of being left as implementer assumptions.

## Validation

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
