---
type: reference
id: REF-cloudflare-r2-job-artifact-storage-migration-pre-runbook
title: Cloudflare R2 job artifact storage migration pre-runbook
status: active
created: 2026-07-02
updated: 2026-07-02
owners:
  - platform
tags: []
links:
  - docs/decisions/0014-cloudflare-r2-job-artifact-storage-boundary.md
  - docs/decisions/0005-v2-long-job-progress-checkpoints-partials-cancel-resume-and-retention.md
  - docs/decisions/0009-gateway-fronted-sir-convert-public-access-and-internal-service-boundary.md
  - docs/backlog/stories/story-05-dockerized-service-hardening-with-robust-persistence.md
  - docs/backlog/stories/story-59-cloudflare-r2-backed-job-artifact-storage-migration-planning.md
  - docs/backlog/tasks/task-23-durable-persistence-layout-retention-and-recovery-for-containerized-runtime.md
  - docs/backlog/tasks/task-380-job-store-r2-adapter-decision-and-runtime-proof-package.md
---

## Cloudflare R2 Job Artifact Storage Migration Pre-Runbook

## Purpose

Capture the architecture, config, Docker, contract, and proof decisions required
before Sir Convert job/artifact storage can move to Cloudflare R2. This is a
pre-runbook: it blocks implementation until the open question ledger is closed.

## Current Architecture

| Surface | Current owner | Current storage assumption | R2 migration risk |
| --- | --- | --- | --- |
| Job creation upload | Sir Convert API | Multipart bytes passed into `runtime.create_job` | Large bytes enter API before storage abstraction. |
| Job store | `JobStoreV2` under `data_root/jobs_v2` | POSIX directories and files | R2 is not a POSIX directory tree. |
| API/worker coordination | Shared prod data volume | API and GPU worker see the same files | Object store needs explicit locking and state ownership. |
| Artifact routes | Sir Convert HTTP routes | `FileResponse(path=...)` | Must become authorized stream/proxy responses. |
| Retention/pin/sweeper | Sir Convert runtime | Directory lifecycle | Must map to object delete/lifecycle and reconciliation. |
| Gateway access | HuleEdu Gateway product edge | Signed identity and grants, Sir Convert verifies | Must remain authorization layer before any bytes leave storage. |

## Proposed Storage Boundary

- Add a lower-level object-store port in Sir Convert infrastructure.
- Compose store-specific adapters behind job and artifact ports, rather than
  calling R2 from HTTP routes or conversion logic.
- Keep active scratch local until a specific task proves object-aware worker
  coordination.
- Move terminal artifacts first only if the reference records exactly which
  artifact classes remain local and how recovery works.
- Preserve current `/v2/convert/jobs/...` API semantics for consumers.

## Config And Secret Surfaces

Proposed environment variables must be finalized before implementation. Names
below are placeholders until approved:

- `SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND=local|s3`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_ENDPOINT_URL`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_REGION`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_BUCKET`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_ACCESS_KEY_ID`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_SECRET_ACCESS_KEY`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_KEY_PREFIX`
- `SIR_CONVERT_A_LOT_OBJECT_STORE_FORCE_PATH_STYLE=true|false`

R2 expectations:

- endpoint: `https://<account_id>.r2.cloudflarestorage.com`;
- region: `auto`;
- private bucket;
- service-specific token with least privilege;
- no retained secret values in logs, reports, or proof.

## Docker And Runtime Surfaces

- Prod API and GPU worker currently share the same data volume. Any R2 slice
  must state which paths remain mounted and which move to objects.
- Readiness must distinguish local scratch health, object-store config,
  object-store reachability, and worker access.
- Compose validation must fail closed if `s3` backend is selected and required
  env values are missing.
- BuildKit remains mandatory for image work.

## Contract Requirements

The storage adapter must define:

- atomic write/finalize behavior for artifacts;
- idempotent write/replay behavior;
- bounded read or streaming read behavior;
- metadata lookup without full download;
- delete behavior and reconciliation after failed DB/job-state transitions;
- object keys that do not expose unsafe filenames or owner-private material;
- migration/backfill manifest format with count, byte size, SHA-256, and source
  path/object mapping.

## Open Question Ledger

| Question | Required before | Status |
| --- | --- | --- |
| First artifact classes to move | Task scope | Open |
| Local scratch versus full object-backed job store | Architecture | Open |
| Job locking/claiming replacement for POSIX assumptions | Worker proof | Open |
| Object key schema | Adapter implementation | Open |
| Required object metadata | Adapter implementation | Open |
| Streaming route design replacing `FileResponse(path=...)` | Route implementation | Open |
| Retention pin mapping to object lifecycle/delete | Purge implementation | Open |
| Existing prod data migration and rollback | Prod migration | Open |
| Local test backend and fake/MinIO/R2 profile | Test plan | Open |
| Exact env names and compose validation | Config implementation | Open |
| Readiness and observability metrics | Runtime proof | Open |
| Secret-source labels and proof redaction | Retained review | Open |

## Stop Conditions

- Stop if a task treats R2 as a mounted filesystem.
- Stop if HuleEdu File Service is proposed as the Sir Convert job store.
- Stop if artifact routes expose raw R2 URLs before Sir Convert authorization.
- Stop if retention only updates local metadata while R2 objects remain
  undeleted and untracked.
- Stop if an implementation changes production env before migration and
  rollback proofs exist.
