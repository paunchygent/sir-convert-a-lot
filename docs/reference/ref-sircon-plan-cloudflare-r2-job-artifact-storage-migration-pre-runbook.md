---
type: reference
id: REF-SIRCON-PLAN-cloudflare-r2-job-artifact-storage-migration-pre-runbook
title: Cloudflare R2 job artifact storage migration pre-runbook
repository: sir-convert-a-lot
owners:
  - kind: service
    id: sir-convert-a-lot
created: '2026-08-02'
status: active
reference_kind: plan
retired_ids:
  - REF-cloudflare-r2-job-artifact-storage-migration-pre-runbook
summary: Cloudflare R2 job artifact storage migration pre-runbook
---

## Outcome And Purpose

State the outcome this planning must make possible, who needs it, and why a
durable planning reference is required.

## Planning Boundary

State included scope, explicit non-goals, authority, owning decision ledger,
and the boundary between planning and implementation.

## Evidence Basis

List the authoritative decisions, current-system facts, research, affected
consumers, conflicts, and evidence gaps used to form the contract.

## Confirmed Contract

State only accepted requirements, boundaries, dependencies, non-goals, proof
expectations, and completion conditions. Link unresolved material choices to
the owning `decisions` reference.

## Backlog Derivation

Map the confirmed contract into the governing epic, stories, and tasks, or the
appropriate repository task. State ownership and dependency boundaries without
duplicating backlog status.

## Planning Stop Conditions

- Stop before backlog derivation when a material decision, authority source, or
  required fact remains unresolved.
- Stop when proposed work exceeds the confirmed contract or duplicates an
  existing authority owner.

## Source Body Preservation

## Cloudflare R2 Job Artifact Storage Migration Pre-Runbook

## Purpose

Capture the architecture, config, Docker, contract, and proof decisions required before Sir Convert job/artifact storage can move to Cloudflare R2. This is a pre-runbook: it blocks implementation until the open question ledger is closed.

## Current Architecture

| Surface                 | Current owner                          | Current storage assumption                       | R2 migration risk                                               |
| ----------------------- | -------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------- |
| Job creation upload     | Sir Convert API                        | Multipart bytes passed into `runtime.create_job` | Large bytes enter API before storage abstraction.               |
| Job store               | `JobStoreV2` under `data_root/jobs_v2` | POSIX directories and files                      | R2 is not a POSIX directory tree.                               |
| API/worker coordination | Shared prod data volume                | API and GPU worker see the same files            | Object store needs explicit locking and state ownership.        |
| Artifact routes         | Sir Convert HTTP routes                | `FileResponse(path=...)`                         | Must become authorized stream/proxy responses.                  |
| Retention/pin/sweeper   | Sir Convert runtime                    | Directory lifecycle                              | Must map to object delete/lifecycle and reconciliation.         |
| Gateway access          | HuleEdu Gateway product edge           | Signed identity and grants, Sir Convert verifies | Must remain authorization layer before any bytes leave storage. |

## Approved Storage Boundary

- Add a lower-level object-store port in Sir Convert infrastructure.
- Compose store-specific adapters behind job and artifact ports, rather than
  calling R2 from HTTP routes or conversion logic.
- Keep active scratch local until a specific task proves object-aware worker
  coordination.
- Move terminal artifacts first only if the reference records exactly which
  artifact classes remain local and how recovery works.
- Preserve current `/v2/convert/jobs/...` API semantics for consumers.

## First Implementation Boundary

The approved first implementation boundary is terminal/cold artifacts only:

- Move primary terminal artifacts and route-owned named terminal bundle
  artifacts behind the object-store adapter.
- Keep raw uploads, resources, reference DOCX files, manifests, lifecycle
  events, idempotency state, `.manifest.lock` files, active scratch/work directories,
  partial artifacts, checkpoints, and logs on the existing POSIX job store.
- Keep `JobStoreV2` as the source of job state, worker claiming, retention
  timestamps, and visibility decisions.
- Treat any broader move of job coordination, checkpoints, partials, or replay
  artifact sets as a separate governed task.

## External R2 Facts

Checked against Cloudflare R2 documentation on 2026-07-03:

- R2 is consumed through the S3-compatible API endpoint
  `https://<account_id>.r2.cloudflarestorage.com`.
- R2 S3 API clients use region `auto`.
- S3-compatible clients can `head_object`, `get_object`, upload, and
  `delete_object`; the implementation must still keep SDK calls behind a Sir Convert adapter.
- Presigned URLs grant time-limited direct access to one object operation.
  They are not authorized for browser/downstream artifact delivery in the first Sir Convert slice.
- R2 lifecycle rules can delete objects, transition storage class, and abort
  incomplete multipart uploads. Lifecycle delete is not the Sir Convert pin authority because deletion may lag the configured expiration.
- Multipart upload is appropriate for large artifacts; incomplete multipart
  uploads are safety-net cleanup concerns and must not become durable job state.

## Config And Secret Surfaces

Approved first-slice environment names:

- `SIR_CONVERT_A_LOT_OBJECT_STORE_BACKEND=local|r2`
- `SIR_CONVERT_A_LOT_R2_ENDPOINT_URL`
- `SIR_CONVERT_A_LOT_R2_REGION`
- `SIR_CONVERT_A_LOT_R2_BUCKET`
- `SIR_CONVERT_A_LOT_R2_ACCESS_KEY_ID`
- `SIR_CONVERT_A_LOT_R2_SECRET_ACCESS_KEY`
- `SIR_CONVERT_A_LOT_R2_KEY_PREFIX`
- `SIR_CONVERT_A_LOT_R2_FORCE_PATH_STYLE=true|false`
  R2 expectations:
- endpoint: `https://<account_id>.r2.cloudflarestorage.com`;
- region: `auto`;
- private bucket;
- service-specific token with least privilege;
- no retained secret values in logs, reports, or proof.
- `SIR_CONVERT_A_LOT_R2_FORCE_PATH_STYLE=false` for production R2 unless a
  future proof shows the selected SDK requires otherwise; local S3-compatible test services may opt into path-style addressing.

## Docker And Runtime Surfaces

- Prod API and GPU worker currently share the same data volume. Any R2 slice
  must state which paths remain mounted and which move to objects.
- Readiness must distinguish local scratch health, object-store config,
  object-store reachability, and worker access.
- Compose validation must fail closed if `r2` backend is selected and required
  env values are missing.
- BuildKit remains mandatory for image work.

## Contract Requirements

The storage contract is split by governed task. Task 381 must define:

- atomic write/finalize behavior for artifacts;
- idempotent write/replay behavior;
- bounded read or streaming read behavior;
- metadata lookup without full download;
- object keys that do not expose unsafe filenames or owner-private material;
  Later migration/backfill tasks must define:
- migration/backfill manifest format with count, byte size, SHA-256, and source
  path/object mapping.
  Later retention/deletion/sweeper tasks must define:
- delete behavior and reconciliation after failed DB/job-state transitions.

## Decision Ledger

- First artifact classes to move: closed. Move primary terminal artifacts and
  route-owned named terminal bundle artifacts only.
- Local scratch versus full object-backed job store: closed. Keep local POSIX
  job state and active scratch for the first slice.
- Job locking/claiming replacement: routed. Do not replace `fcntl` or POSIX
  manifest locking in the first slice; create a later DB/object-aware coordination task before moving manifests, events, claims, partials, or checkpoints.
- Object key schema: closed. Use
  `<key_prefix>/<runtime_profile>/<route_key>/<owner_scope_sha256>/<job_id>/<artifact_class>/<artifact_key>/<content_sha256>.<extension>`. `key_prefix` must be environment/lane specific, for example a prod or eval prefix, so buckets can be shared only when prefixes remain isolated.
- Required object metadata: closed. Store `schema_version`, `job_id`,
  `artifact_class`, `artifact_key`, `route_key`, `source_format`, `output_format`, `owner_scope_sha256`, `retention_pin`, `retention_class`, `created_at`, `content_type`, `size_bytes`, `sha256`, `correlation_id` when available, and `migration_batch_id` when written by a migration/backfill. Do not store raw owner-private claims or unsafe source filenames in keys or metadata.
- Streaming route design: closed. Existing Sir Convert owner/grant checks run
  before object reads. The adapter returns metadata plus a bounded server-side stream/proxy response. Raw R2 or presigned URLs are not returned to browsers or downstream products in the first slice.
- Retention and pin mapping: closed. Sir Convert sweeper decisions are the
  source of truth. Object delete attempts must be idempotent and recorded in a reconciliation ledger. R2 lifecycle may only enforce maximum-age and incomplete multipart cleanup as a safety net.
- Existing prod data migration and rollback: routed. No copy, delete, backfill,
  or prod env mutation belongs to the first adapter implementation. A later migration task must keep local artifacts as rollback source until R2 read-after-copy proof passes for count, byte size, SHA-256, and route reads.
- Local test backend: closed. Default tests use the existing local filesystem
  backend plus a deterministic fake/local object adapter. MinIO or an R2 dev bucket is optional integration/live proof and must not be required for normal unit or route tests.
- Exact env names and compose validation: closed. Use the approved names above.
  Compose/config validation must fail closed when backend `r2` is selected and endpoint, region, bucket, access key, secret key, or key prefix is missing.
- Readiness and observability: closed. `/readyz` must distinguish local scratch
  readiness, object-store config readiness, object-store reachability, and API versus worker access when backend `r2` is selected. `/healthz` remains liveness-only. Task 381 live proof must exercise write/read of a small sentinel object under the configured prefix; delete sentinel proof belongs to a later retention/deletion reconciliation task.
- Secret-source labels and proof redaction: closed. Retained proof may name the
  secret source label and whether each required key is present; it must not print values, signed URLs, access keys, secret keys, or token material.

## First Implementation Task Sketch

Title: Implement terminal R2 artifact adapter and authorized streaming proof.
Governed task: `docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md`.
Scope:

- Add an object-store port plus local/fake and R2 implementations behind
  `JobStoreV2` terminal artifact persistence and artifact resolution.
- Add R2 config parsing, fail-closed validation, and readiness fields for API
  and worker containers.
- Stream/proxy authorized artifact bytes after existing owner/grant checks.
- Keep raw inputs, manifests, locks, partials, checkpoints, logs, correction
  replay artifact sets, retention/deletion reconciliation, purge flows, and prod migration out of scope.
  Red-first tests:
- terminal artifact read fails red when a successful job references an object
  that the adapter cannot find;
- named bundle artifact read fails red when route resolution bypasses the
  adapter;
- owner/grant denial proves no object read is attempted before authorization;
- backend `r2` config validation fails closed when required env values are
  missing;
- stale or mismatched artifact access remains denied by the existing guarded
  route semantics.
  Green validation:
- focused route/object-store tests;
- `pdm run format-all`;
- `pdm run lint-fix`;
- `pdm run typecheck-all`;
- focused `pdm run pytest-root <object-store-and-route-tests>`;
- `pdm run coverage-gate` when conversion-core coverage applies;
- docs/governance gates from Task 380.
  Live proof:
- submit and poll a route with terminal and named artifacts;
- download terminal and named artifacts through Sir Convert routes;
- prove owner/grant denial before object read;
- prove missing object behavior;
- prove readiness fields and redacted secret-source labels;
- do not mutate production data or backfill objects.

## Routed Follow-Up Task Sketches

- Decide object-backed job coordination, claims, manifests, partials, and
  checkpoints.
- Decide retention/deletion reconciliation, purge flows, object delete
  attempts, and sweeper-to-object-store behavior.
- Prove production artifact backfill, rollback, and post-cutover cleanup.
- Decide any direct presigned URL or browser-facing object-access contract.

## Stop Conditions

- Stop if a task treats R2 as a mounted filesystem.
- Stop if HuleEdu File Service is proposed as the Sir Convert job store.
- Stop if artifact routes expose raw R2 URLs before Sir Convert authorization.
- Stop if retention only updates local metadata while R2 objects remain
  undeleted and untracked.
- Stop if an implementation changes production env before migration and
  rollback proofs exist.
