---
id: 'review-65-review-cloudflare-r2-job-artifact-storage-decision-package'
title: 'Cloudflare R2 job artifact storage decision package'
type: 'review'
status: 'completed'
priority: 'high'
created: '2026-07-02'
last_updated: '2026-07-04'
approval_protocol: 'agent-planning:user-closure-gate'
approval_note: 'Final fixed-review approval after deletion-scope repair and validation.'
related:
  - docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md
  - docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md
  - docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md
  - docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md
  - docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md
labels:
  - r2
  - object-storage
  - artifacts
  - persistence
---

Structured review artifact for implementation or readiness checks.

This review records the planning package for the R2 storage boundary. It does
not approve a runtime adapter, production env sync, object copy/backfill, object
cleanup, or route contract changes.

## Review Scope

Review the Sir Convert R2 job/artifact storage planning package:

- `docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md`
- `docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md`
- `docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md`
- `docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md`
- `docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md`

The review must prove that no open storage, locking, route, retention, env, or
migration question is left for implementation to guess.

Independent fixed-reviewer pass on 2026-07-04 also reviewed `.codex/handoff.md`,
generated docs indexes touched by `docs-sync`, and the current docs-validation
wrapper/config diffs that make `pdm run docs-validate [paths...]` enforce the
shared authority guard.

Pass 2 fixed-reviewer re-review on 2026-07-04 checked the repaired
`docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md`
backend selector and the same Story 59, Task 380, Review 65, ADR-0014,
pre-runbook, Task 381, handoff, generated index, and docs-validation-wrapper
scope.

Final completion-audit re-review on 2026-07-04 checked that Task 381 and the
pre-runbook first implementation sketch do not require deletion, purge, or
reconciliation work, and searched the reviewed scope for delete/purge/
reconciliation terms.

## Findings

- [x] ADR-0014 keeps Sir Convert job/artifact storage Sir-owned.

- [x] HuleEdu File Service is not used as the Sir Convert runtime job store.

- [x] The reference states that R2 is not POSIX and names the adapter/locking
  questions before implementation.

- [x] Artifact route authorization remains Sir Convert-owned before any R2 bytes
  are returned.

- [x] Retention, delete, migration, rollback, config, Docker, and proof
  questions are all explicit.

- [x] Pass 1 backend-selector finding resolved. The pre-runbook now says compose
  validation must fail closed when backend `r2` is selected, matching
  `SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND=local|r2` and Task 381's R2
  fail-closed config validation requirement.

- [x] Implementation response applied for the final audit finding. The
  pre-runbook now scopes delete behavior and reconciliation to later
  retention/deletion/sweeper tasks, not Task 381.

### Finding 1 - high - Backend selector mismatch weakens fail-closed config authority

Resolved in pass 2.

`docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md:117`
now names backend `r2` as the trigger for required env validation. The same
reference approves `SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND=local|r2` at
`docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md:91`,
and Task 381 requires R2 config validation to fail closed at
`docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md:42`
and
`docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md:86`.

The repaired docs now keep Task 381's red-first config-validation proof tied to
the approved `r2` selector.

Pass 2 validation:

- `pdm run docs-validate docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md`
  passed: `Validated 4 scoped backlog files`; `Validated scoped docs=2 rules=0`.
- `pdm run docs-validate`
  passed: `Validated 520 backlog files`; `Validated docs=599 rules=11`.
- `git diff --check`
  passed.

### Finding 2 - high - Pre-runbook still requires delete/reconciliation in adapter contract

Resolved by final fixed-review pass.
`docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md`
now splits contract requirements by governed task. Task 381 must define only
artifact write/finalize, idempotent write/replay, bounded read/streaming read,
metadata lookup, and object keys. Delete behavior and reconciliation after
failed DB/job-state transitions are now explicitly required only for later
retention/deletion/sweeper tasks.

Why it matters: Task 381 is supposed to authorize primary terminal artifacts and
route-owned named terminal bundle artifacts behind a Sir-owned object-store
adapter, with deletion/purge/reconciliation deferred. A pre-runbook "must
define" requirement can pull delete semantics back into the first adapter
implementation even though the task now excludes that lane.

Applied fix: moved the delete/reconciliation contract bullet out of Task 381's
generic adapter requirements and qualified it as a later
retention/deletion/sweeper task requirement. Task 381's red-first and live proof
remain limited to artifact write/read, named artifact read, owner/grant denial
before object read, missing-object behavior, config validation, readiness, and
redacted secret-source labels.

Final pass validation/search evidence:

- `rg -n "delete|deletion|purge|reconciliation|cleanup|sweeper" docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md`
  showed Task 381 deletion-related matches only in out-of-scope or routed
  follow-up lines, and the pre-runbook delete/reconciliation contract bullet
  only under later retention/deletion/sweeper task requirements.
- `pdm run docs-validate docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md`
  passed: `Validated 4 scoped backlog files`; `Validated scoped docs=2 rules=0`.
- `pdm run docs-validate`
  passed: `Validated 520 backlog files`; `Validated docs=599 rules=11`.
- `git diff --check`
  passed.

Final audit search evidence:

- Task 381 confines deletion/purge/reconciliation to out-of-scope and follow-up
  lines.
- The pre-runbook first implementation sketch confines deletion/purge/
  reconciliation to out-of-scope and follow-up lines.
- The pre-runbook contract requirements now place delete/reconciliation under
  later retention/deletion/sweeper task requirements.

## Decision

approved

Approved for the docs-only Story 59 closeout repair and Task 381 scaffold. This
approval covers the terminal planning closeout and first implementation-task
authority only; it does not approve runtime code, production env sync, object
copy/backfill, object deletion/cleanup, raw/browser-facing R2 URLs, retention/
deletion reconciliation, purge flows, or a runtime adapter rollout outside Task
381's governed red-first proof.

## Response

Story 59, Task 380, ADR-0014, the pre-runbook, and Task 381 are aligned on the
first implementation boundary: primary terminal artifacts plus route-owned named
terminal bundle artifacts behind a Sir-owned object-store adapter. The scope
explicitly excludes production secrets/env sync, backfill, object copy,
deletion/cleanup of existing production or local data, raw inputs, resources,
manifests, lifecycle events, idempotency state, locks, partials, checkpoints,
logs, correction replay artifact sets, and browser-facing raw or presigned R2
URLs.

Task 381 implementation should continue to use the repaired pre-runbook scope:
terminal/cold artifact write/read and authorized streaming only, with
retention/deletion reconciliation routed to later governed work.

## Follow-up Actions

1. Start Task 381 only with its red-first route/object-store tests and live
   proof obligations.
1. Keep coordination, retention/deletion reconciliation, purge,
   backfill/rollback, cleanup, and presigned/browser-facing URL behavior in
   separate governed tasks if those lanes become active.

## Completion

Complete.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up task routing recorded
- [x] Review closed
