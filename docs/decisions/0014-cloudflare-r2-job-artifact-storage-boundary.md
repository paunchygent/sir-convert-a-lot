---
type: decision
id: ADR-0014
title: Cloudflare R2 job artifact storage boundary
status: accepted
created: 2026-07-02
updated: 2026-07-04
approval_protocol: agent-planning:user-closure-gate
approval_note: "User approval: Repair/approve the Story 59 planning closeout with the closure-gate marker."
owners:
  - platform
tags: []
links:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md
  - docs/backlog/tasks/task-23-durable-persistence-layout-retention-and-recovery-for-containerized-runtime.md
  - docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md
  - docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md
  - docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md
  - docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
---

## ADR-0014: Cloudflare R2 job artifact storage boundary

## Status

Accepted as the storage-boundary and first-slice planning decision. This
decision authorizes follow-up implementation-task creation, but it does not
authorize production env sync, object copy/backfill, object cleanup, route
contract changes, or a runtime adapter rollout until a later governed
implementation task is approved and proves the required red/green and live
runtime evidence.

## Context

Sir Convert-a-Lot currently treats the service data root as a shared POSIX
runtime surface. The API container, worker, sidecars, idempotency store,
manifest files, raw inputs, terminal artifacts, partial artifacts, checkpoints,
and logs all coordinate through local paths rooted under
`SIR_CONVERT_A_LOT_DATA_DIR` or `CONVERTER_STORAGE_ROOT`.

Cloudflare R2 is S3-compatible object storage. It can durably hold blobs, but it
is not a POSIX volume and cannot be dropped under the current runtime without
settling path, streaming, locking, metadata, sweeper, and recovery semantics.

The cross-repo storage direction keeps HuleEdu File Service focused on
product-owned user files. Sir Convert must keep its conversion job/artifact
runtime ownership separate.

## Decision

Adopt a Sir Convert-owned R2 artifact bucket and storage adapter boundary:

1. Sir Convert owns its job and artifact storage, including raw conversion
   inputs, terminal artifacts, named artifacts, partials, checkpoints,
   manifests, logs, retention, and pin semantics.
1. Sir Convert must not route its job runtime store through HuleEdu File
   Service. HuleEdu File Service may later receive selected user-saved outputs,
   but it is not the job store.
1. The first object-storage implementation must introduce an explicit storage
   port/adapter behind `JobStoreV2` and artifact resolution. Direct R2 calls
   must not scatter through parsers, renderers, HTTP routes, or worker code.
1. The first implementation may keep local scratch/work directories for active
   conversion execution while moving only terminal or cold artifacts to R2, if
   the adapter contract and recovery proof make that split explicit.
1. HTTP artifact routes must keep Sir Convert owner/grant checks. They may
   stream from R2 or proxy bytes after authorization, but must not expose raw R2
   object URLs as authorization.
1. Production R2 credentials are environment-only secrets. They must not be
   committed, printed, retained in proof, or copied into generated reports.

The first implementation slice is intentionally narrower than the full storage
migration:

1. Move only terminal/cold artifact blobs for successful jobs behind the new
   adapter: the primary terminal artifact and route-owned named terminal bundle
   artifacts.
1. Keep raw uploads, resources, reference DOCX files, manifests, lifecycle
   events, idempotency state, `.manifest.lock` files, active scratch/work
   directories, partial artifacts, checkpoints, logs, and correction replay
   artifact sets on the existing POSIX job store for the first slice.
1. Keep `JobStoreV2` as the job state and worker coordination authority for
   the first slice. A DB/object-aware job store, object-backed lock/claim
   semantics, and object-backed checkpoints require a separate task before
   they can replace POSIX coordination.
1. Use server-side authorized streaming/proxy responses for R2-backed artifact
   reads. Presigned or raw R2 URLs are not a browser/downstream authorization
   mechanism in the first slice.
1. Treat the Sir Convert sweeper as the source of truth for retention and pin
   semantics. R2 lifecycle rules may be configured only as a safety net for
   incomplete multipart uploads and maximum-age cleanup, with reconciliation
   evidence retained by Sir Convert.

## Consequences

Positive:

- Sir Convert can gain durable object-backed artifact storage without becoming
  dependent on HuleEdu File Service for conversion runtime state.
- Gateway and product consumers keep the same job/status/artifact API contract
  while storage internals evolve behind a port.
- A staged split lets terminal artifacts move before the hardest active-worker
  POSIX coordination questions are solved.

Tradeoffs:

- A direct filesystem-to-R2 swap is unsafe; storage abstractions and route
  streaming must be designed first.
- If only terminal artifacts move first, operators must understand which data
  remains local scratch and which data is object-backed.
- Retention and pin behavior must be proved against object deletion and
  lifecycle policies, not only local directory cleanup.

## Closed Decisions And Routed Follow-Ups

Closed for the first implementation task:

1. First artifact class: primary terminal artifacts and route-owned named
   terminal bundle artifacts only.
1. Active coordination: local POSIX remains authoritative for manifests,
   events, locks, raw material, worker claiming, partials, checkpoints, and
   logs.
1. Route behavior: Sir Convert authorization remains the gate before bytes are
   read; R2-backed reads stream through Sir Convert and do not expose raw R2
   URLs.
1. Retention: Sir Convert owns delete/pin decisions and records object delete
   reconciliation; R2 lifecycle is safety-net infrastructure, not the pin
   authority.
1. Test backend: default automated tests use a deterministic fake/local object
   adapter; MinIO or an R2 dev bucket is optional proof, not a default unit
   test dependency.
1. Production secrets: env-only by key name; retained proof may show presence
   and source label only, never values.

Routed follow-ups before broader migration:

1. Moving raw inputs, manifests, events, idempotency state, locks, partials,
   checkpoints, logs, or correction replay artifact sets to object storage.
1. Replacing `fcntl`/POSIX worker claim semantics with DB or object-aware
   coordination.
1. Production backfill from `/var/lib/sir-convert-a-lot/prod`, rollback, and
   deletion of any existing local data.
1. Any direct-to-browser presigned URL contract.

Implementation stops if code starts depending on an unstated POSIX behavior
while claiming R2-backed durability, or if a task tries to widen beyond the
closed first-slice boundary above without a new governed decision.
