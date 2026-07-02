---
id: 'story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning'
title: 'Cloudflare R2-backed job artifact storage migration planning'
type: 'story'
status: 'proposed'
priority: 'high'
created: '2026-07-02'
last_updated: '2026-07-02'
related: []
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

- Proposed ADR for Sir Convert job/artifact storage ownership.
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

- [ ] `ADR-0014` is reviewed and either approved or revised.
- [ ] The pre-runbook reference names every open question that would otherwise
  become an implementation assumption.
- [ ] The first implementation task states which artifact classes move first and
  which remain local scratch.
- [ ] Route behavior remains owner/grant checked before bytes are returned.
- [ ] Retention, pin, purge, migration, rollback, and proof requirements are
  explicit before code changes.

## Test Requirements

- [ ] Future implementation tasks must use red-first route/runtime tests for
  artifact read, named artifact read, missing object, retention delete,
  owner denial, and stale/mismatched artifact denial.
- [ ] Future live proof must include submit, poll, terminal artifact download,
  named artifact download, retention/purge evidence, and readiness evidence.

## Done Definition

Done when Review 65 approves the planning package and Task 380 is ready to be
executed without unresolved storage decisions.

## Checklist

- [ ] Implementation complete
- [ ] Tests and validations complete
- [ ] Docs synchronized
