---
id: 'story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning'
title: 'Cloudflare R2-backed job artifact storage migration planning'
type: 'story'
status: 'completed'
priority: 'high'
created: '2026-07-02'
last_updated: '2026-07-04'
approval_protocol: 'agent-planning:user-closure-gate'
approval_note: 'User approval: Repair/approve the Story 59 planning closeout with the closure-gate marker.'
related:
  - docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md
  - docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md
  - docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md
  - docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md
  - docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md
labels:
  - r2
  - object-storage
  - artifacts
  - persistence
---

Implementation slice with acceptance-driven scope.

## Objective

Plan the Sir Convert-owned Cloudflare R2 migration for job and artifact storage
without changing runtime behavior or confusing product user-file storage with
conversion runtime storage.

## Scope

In scope:

- Accepted ADR for Sir Convert job/artifact storage ownership.
- Pre-runbook reference with config, Docker, contract, migration, and proof
  requirements.
- Task 380 planning package for the first implementation-ready slice.
- Review 65 retained approval before implementation.

Out of scope:

- Production `.env` sync.
- Moving active job coordination to R2 without a lock/claiming decision.
- Routing job artifacts through HuleEdu File Service.
- Exposing raw R2 object URLs to browsers or downstream products.

## Acceptance Criteria

- [x] `ADR-0014` is reviewed and either approved or revised.
- [x] The pre-runbook reference names every open question that would otherwise
  become an implementation assumption.
- [x] The first implementation task states which artifact classes move first and
  which remain local scratch.
- [x] Route behavior remains owner/grant checked before bytes are returned.
- [x] Retention, pin, purge, migration, rollback, and proof requirements are
  explicit before code changes.

## Test Requirements

- [x] Future implementation tasks must use red-first route/runtime tests for
  artifact read, named artifact read, missing object, retention delete,
  owner denial, and stale/mismatched artifact denial.
- [x] Future live proof must include submit, poll, terminal artifact download,
  named artifact download, retention/purge evidence, and readiness evidence.

## Done Definition

Done. Review 65 approved the planning package, and Task 380 closed or routed
the R2 storage questions that would otherwise become implementation
assumptions.

## Checklist

- [x] Implementation complete
- [x] Tests and validations complete
- [x] Docs synchronized
