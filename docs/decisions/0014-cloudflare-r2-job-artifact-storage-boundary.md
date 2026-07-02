---
type: decision
id: ADR-0014
title: Cloudflare R2 job artifact storage boundary
status: proposed
created: 2026-07-02
updated: 2026-07-02
owners:
  - platform
tags: []
links:
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md
  - docs/backlog/tasks/task-23-durable-persistence-layout-retention-and-recovery-for-containerized-runtime.md
  - docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md
  - docs/backlog/reviews/review-65-review-cloudflare-r2-job-artifact-storage-decision-package.md
  - docs/reference/ref-cloudflare-r2-job-artifact-storage-migration-pre-runbook.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
---

## ADR-0014: Cloudflare R2 job artifact storage boundary

## Status

Proposed. This decision does not authorize storage implementation, production
env sync, job-store migration, object deletion, or route changes until Review 65
is approved and every open question in the reference pre-runbook is closed or
routed to a named research/decision task.

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

Propose a Sir Convert-owned R2 artifact bucket and storage adapter boundary:

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

## Open Questions Blocking Implementation

1. Which artifact classes move first: terminal artifacts only, raw inputs,
   named artifacts, partials, checkpoints, manifests, logs, or all job data?
1. Does active job coordination remain local POSIX while R2 holds terminal/cold
   artifacts, or is a DB/object-aware job store required first?
1. What object-key schema represents job id, owner scope, artifact name, route
   profile, retention pin, and environment?
1. What metadata is mandatory on each object: content type, byte size,
   SHA-256, route kind, owner scope, retention class, created timestamp, source
   request id, and migration batch id?
1. How do current `FileResponse(path=...)` routes become authorized streaming
   responses without reading unbounded bytes into memory?
1. How do API and GPU worker containers coordinate if the shared volume no
   longer contains every manifest and artifact?
1. What lock/claim semantics replace local path assumptions for job creation,
   worker execution, resume, cancel-with-save, partials, and idempotent replay?
1. Does R2 lifecycle policy delete objects, does the Sir Convert sweeper delete
   objects, or do both run with a reconciliation ledger?
1. What is the migration and rollback plan for existing
   `/var/lib/sir-convert-a-lot/prod` data?
1. Which local/dev object store is used for tests: local filesystem, MinIO, R2
   dev bucket, or a fake adapter?
1. What production `.env` names, compose variables, and health/readiness probes
   prove object-store reachability without exposing secrets?
1. What exact live proof demonstrates submit, poll, terminal artifact download,
   named artifact download, partial/checkpoint behavior, retention purge, and
   stale/mismatched artifact denial after R2 migration?

Implementation stops if any answer is unknown or if code starts depending on an
unstated POSIX behavior while claiming R2-backed durability.
