---
id: 'task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof'
title: 'Implement terminal R2 artifact adapter and authorized streaming proof'
type: 'task'
status: 'completed'
priority: 'high'
created: '2026-07-04'
last_updated: '2026-07-04'
approval_protocol: 'agent-planning:user-closure-gate'
approval_note: 'User approval: Approved: close Review 66 and Task 381 with approval_protocol: agent-planning:user-closure-gate based on the Task 381 overseer ledger.'
related:
  - docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md
  - docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md
  - docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md
  - docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md
  - docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md
labels:
  - r2
  - object-storage
  - artifacts
  - route-auth
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first Sir Convert-owned object-storage slice for terminal/cold
artifact blobs only. The slice must place primary terminal artifacts and
route-owned named terminal bundle artifacts behind an object-store adapter while
preserving the existing Sir Convert job, route, owner, and grant authority
before any bytes are returned.

## PR Scope

In scope:

- Introduce a Sir-owned object-store port for terminal artifact persistence,
  metadata lookup, and streaming reads.
- Add local/fake object-store implementations for deterministic tests and an
  R2 implementation behind the same port.
- Wire the port through the existing artifact persistence and route resolution
  boundary without scattering R2 calls through routes, parsers, renderers, or
  worker-specific logic.
- Validate object-store config fail-closed when `r2` is selected, including
  endpoint, region, bucket, access key, secret key, and key prefix.
- Expose readiness that distinguishes local scratch health, object-store
  config readiness, object-store reachability, and API versus worker access.
- Stream or proxy artifact bytes through Sir Convert only after existing
  owner/grant checks pass.
- Keep proof redacted: secret values, signed URLs, access keys, secret keys, and
  token material must not appear in logs, reports, or retained artifacts.

Out of scope:

- Production env sync or production secret mutation.
- Backfill, object copy, rollback execution, retention/deletion
  reconciliation, purge flows, or deletion/cleanup of existing production or
  local data.
- Raw inputs, resources, reference DOCX files, manifests, lifecycle events,
  idempotency state, locks, active scratch/work directories, partial artifacts,
  checkpoints, logs, and correction replay artifact sets.
- Browser-facing raw R2 URLs or presigned R2 URLs.
- Replacing `JobStoreV2` as job state, worker claiming, retention timestamp, or
  visibility authority.

## Deliverables

- [x] Object-store port plus local/fake and R2 adapters for terminal artifact
  blobs.
- [x] Config parsing, validation, and readiness fields for API and worker
  runtime paths.
- [x] Authorized route streaming/proxy integration after existing owner/grant
  checks.
- [x] Focused red-first route/object-store tests retained in the implementation
  evidence.
- [x] Live proof package showing terminal and named artifact reads, missing
  object handling, authorization denial before object read, readiness, and
  redacted secret-source labels.

## Acceptance Criteria

- [x] Primary terminal artifacts and route-owned named terminal bundle artifacts
  can be stored and read through the object-store adapter.
- [x] Owner/grant denial prevents any object read attempt.
- [x] Missing object reads fail through the existing guarded route semantics
  without leaking bucket, key, credential, or signed URL data.
- [x] R2 config validation fails closed when required env values are missing.
- [x] `/readyz` distinguishes local scratch readiness, object-store config
  readiness, object-store reachability, and API versus worker access when
  the R2 backend is selected.
- [x] Tests use deterministic local/fake object storage by default; MinIO or an
  R2 dev bucket is optional live proof and not required for normal tests.
- [x] No raw inputs, resources, manifests, lifecycle events, idempotency state,
  locks, partials, checkpoints, logs, correction replay artifact sets,
  production env sync, backfill, or browser-facing raw/presigned R2 URLs
  are introduced.

## Red-First Test Plan

- Add a terminal artifact route test that fails while successful jobs still
  resolve only filesystem paths and cannot stream from an object reference.
- Add a named bundle artifact route test that fails if route resolution bypasses
  the object-store adapter.
- Add an owner/grant denial test that fails if any object read is attempted
  before authorization completes.
- Add a missing-object route test that fails until adapter miss handling maps to
  the existing guarded route failure behavior.
- Add a config-validation test that fails until selecting backend `r2` without
  required env values is rejected before runtime startup.

## Green Validation Plan

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- Focused `pdm run pytest-root <object-store-and-route-tests>`
- `pdm run coverage-gate` when conversion-core coverage applies
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Live Proof Requirements

- Submit and poll a route that produces both a primary terminal artifact and a
  route-owned named terminal bundle artifact.
- Download both artifacts through Sir Convert routes.
- Prove owner/grant denial happens before object reads.
- Prove missing-object behavior.
- Prove readiness fields and redacted secret-source labels.
- Retain proof without mutating production data, syncing production env, or
  backfilling objects.

## Completion Evidence

- Retained review:
  `docs/backlog/reviews/review-66-task-381-terminal-r2-artifact-adapter-implementation-review.md`
  decision `approved`.
- Proof package:
  `build/verification/task-381-terminal-object-store-proof/summary.json`.
- Live proof covers primary download `200`, named download `200`, denial before
  object read `401` with `0` object reads, missing object `404` as
  `artifact_not_available`, `/readyz` API and worker `read_write`, and redacted
  secret-source labels only.
- Closure authority:
  `approval_protocol: agent-planning:user-closure-gate` with the user approval
  quoted in frontmatter.

## Routed Follow-Up Work

- Retention/deletion reconciliation, purge flows, object delete attempts, and
  sweeper-to-object-store behavior.
- Production backfill, rollback execution, object copy, and post-cutover
  cleanup.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
