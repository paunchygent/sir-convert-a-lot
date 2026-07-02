---
id: 'task-380-job-store-r2-adapter-decision-and-runtime-proof-package'
title: 'Job store R2 adapter decision and runtime proof package'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-07-02'
last_updated: '2026-07-02'
related: []
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

- [ ] Reviewed ADR/reference/story/task package.
- [ ] Closed open-question ledger or follow-up tasks for every unresolved item.
- [ ] First implementation task sketch with red-first tests and live proof.
- [ ] Prod env sync checklist with secret-source labels only.

## Acceptance Criteria

- [ ] No implementation step assumes R2 is POSIX-compatible.
- [ ] No implementation step routes job runtime storage through HuleEdu File
  Service.
- [ ] Object key, metadata, retention, purge, migration, rollback, config, and
  proof obligations are explicit.
- [ ] Future tests cover object missing, owner denial, stale/mismatched artifact
  denial, purge delete, and successful terminal/named artifact reads.
- [ ] Docs sync and validation pass.

## Validation

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
