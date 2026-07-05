---
id: 'review-66-task-381-terminal-r2-artifact-adapter-implementation-review'
title: 'Terminal R2 artifact adapter implementation review'
type: 'review'
status: 'completed'
priority: 'high'
created: '2026-07-04'
last_updated: '2026-07-04'
approval_protocol: 'agent-planning:user-closure-gate'
approval_note: 'User approval: Approved: close Review 66 and Task 381 with approval_protocol: agent-planning:user-closure-gate based on the Task 381 overseer ledger.'
related:
  - docs/backlog/tasks/task-381-implement-terminal-r2-artifact-adapter-and-authorized-streaming-proof.md
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

Structured review artifact for implementation or readiness checks.

## Review Scope

Fixed independent review of the current Task 381 worktree implementation. This
review covers only the first authorized storage slice: primary terminal
artifacts and route-owned named terminal bundle artifacts behind a Sir-owned
object-store adapter, with Sir Convert owner/grant checks before object reads.

Reviewed implementation surfaces:

- New object-store modules under `scripts/sir_convert_a_lot/infrastructure/`.
- Config parsing, runtime model, and `/readyz` object-store readiness changes.
- `JobStoreV2` terminal artifact persistence and manifest parsing.
- Primary and named artifact HTTP route wiring.
- DigiExam and transcript named bundle artifact resolver changes.
- Task 381 proof runner and retained proof artifacts under
  `build/verification/task-381-terminal-object-store-proof/`.
- Focused Task 381 tests and dependency metadata changes.

Explicitly out of scope for approval: raw inputs, manifests as migrated
storage, locks, partials, checkpoints, logs, correction replay artifact sets,
production env sync, backfill, object delete/purge/cleanup, browser-facing raw
or presigned R2 URLs, `JobStoreV2` replacement, deploy, and runtime data
mutation.

## Findings

### Prior Finding 1 - high - Named bundle artifacts are not cold-object safe

Resolved in the 2026-07-04 re-review.

The repair routes private DigiExam named-artifact manifest loading through the
object-store-aware JSON loader:

- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py:87`
  calls `_load_manifest(job=job, object_store=object_store)`.
- `scripts/sir_convert_a_lot/infrastructure/digiexam_migration_bundle_artifacts.py:151`
  uses `load_terminal_artifact_json_v2`.
- `scripts/sir_convert_a_lot/infrastructure/terminal_artifact_json_loader_v2.py:56`
  reads the local file when present and otherwise reads the terminal object ref.

Public bundle manifest lease generation now uses the same object-store-aware
loader:

- `scripts/sir_convert_a_lot/interfaces/http_public_exam_converter_artifacts_v2.py:46`
  loads the public bundle manifest through `_load_manifest_object`.
- `scripts/sir_convert_a_lot/interfaces/http_public_exam_converter_artifacts_v2.py:63`
  calls `load_terminal_artifact_json_v2`.

Transcript formatter manifest availability now stays true when the formatter
file is cold but the terminal object ref exists:

- `scripts/sir_convert_a_lot/infrastructure/audio_transcript_bundle_artifacts.py:196`
  checks `job.terminal_artifact_object_refs` before reporting unavailable.

Truthful test proof:

- `tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py:165`
  deletes both the primary bundle manifest and named file, then proves the
  private named artifact route returns `200` through object-store reads.
- `tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py:217`
  deletes the public primary manifest and proves public lease generation still
  returns a named artifact read lease.
- `tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py:269`
  deletes a transcript formatter file and proves the artifact listing remains
  `available` with object-ref metadata.

### Prior Finding 2 - high - `/readyz` does not actually distinguish API and worker object-store access

Resolved in the 2026-07-04 re-review.

`/readyz` now combines distinct API and worker object-store readiness:

- `scripts/sir_convert_a_lot/interfaces/http_routes_health.py:69` gets the API
  runtime store.
- `scripts/sir_convert_a_lot/interfaces/http_routes_health.py:178` reads an
  optional `app.state.worker_terminal_artifact_store`.
- `scripts/sir_convert_a_lot/interfaces/http_routes_health.py:180` fails closed
  for R2 when no worker probe is configured.
- `scripts/sir_convert_a_lot/interfaces/http_routes_health.py:199` combines
  API and worker readiness while preserving separate `api_access` and
  `worker_access` fields.

Truthful test proof:

- `tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py:415`
  proves API-ready/worker-unreachable yields `api_access=read_write`,
  `worker_access=unreachable`, and `503`.
- `tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py:469`
  proves API-unreachable/worker-ready yields `api_access=unreachable`,
  `worker_access=read_write`, and `503`.

### Open Findings

None.

### Delta Review 2026-07-04 - normal service worker readiness wiring

Scope reviewed for this delta only:

- `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
- `scripts/sir_convert_a_lot/interfaces/http_app_state.py`
- `tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py`

Findings: none.

The normal service runtime now constructs both the API terminal artifact store
and the worker terminal artifact probe store from the same governed object-store
configuration, with distinct `service-api` and `service-worker` runtime
profiles. `JobStoreV2` still receives only the API store used for terminal
artifact persistence, while `app.state.worker_terminal_artifact_store` is
exposed as readiness evidence for the worker role. The HTTP artifact routes
still complete owner/grant checks before calling the terminal artifact response
helper, so this delta does not weaken artifact authorization or expose raw R2
URLs.

Readiness continues to perform bounded sentinel write/read probes for API and
worker access. That creates readiness sentinel objects under the configured
Task 381 key prefix and runtime-profile segment, but it does not create job
state, terminal artifact refs, route leases, presigned URLs, deletes, backfill,
or production data mutation. This is acceptable for the Task 381 readiness
contract because `/readyz` is explicitly required to prove API versus worker
object-store access.

The new focused test is truthful enough for the production failure: it builds a
normal `create_app(...)` service app with `backend="r2"`, monkeypatches only the
object-store adapter factory to avoid network I/O, asserts both runtime
profiles are constructed from the production config, and verifies `/readyz`
returns `200` with API and worker `read_write`. The surrounding readiness tests
continue to prove role-distinct fail-closed `503` behavior when either side is
unreachable.

## Decision

approved

The implementation can proceed to overseer closeout ledger. This approval is
limited to Task 381's terminal/cold artifact adapter slice and does not approve
production env sync, production data mutation, object copy/backfill,
delete/purge/cleanup, browser-facing raw or presigned R2 URLs, or replacing
`JobStoreV2` as job-state/worker-coordination authority.

## Verification

Commands run by this reviewer:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py tests/sir_convert_a_lot/test_object_store_runtime_config.py
```

Result: `16 passed, 1 warning` in 55.59 seconds. This verified the repaired
cold private named artifact route, public bundle manifest lease generation,
transcript formatter listing availability, R2 config fail-closed tests, and
role-distinct `/readyz` behavior.

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py tests/sir_convert_a_lot/test_object_store_runtime_config.py tests/sir_convert_a_lot/test_digiexam_migration_bundle_api_v2.py tests/sir_convert_a_lot/test_audio_transcript_bundle_runtime_v2.py
```

Result: `37 passed, 1 warning` in 100.09 seconds.

Delta review rerun:

```bash
pdm run pytest-root tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py tests/sir_convert_a_lot/test_object_store_runtime_config.py
```

Result: `17 passed, 1 warning` in 7.08 seconds.

```bash
git diff --check -- scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py scripts/sir_convert_a_lot/interfaces/http_app_state.py tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py docs/backlog/reviews/review-66-task-381-terminal-r2-artifact-adapter-implementation-review.md
```

Result: no whitespace errors.

```bash
rg -n "\bAny\b|typing\.cast|\bcast\(|type: ignore|# noqa|delete_object|presign|presigned|generate_presigned|copy_object|backfill|purge|cleanup|raw R2|signed URL|browser-facing" scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py scripts/sir_convert_a_lot/interfaces/http_app_state.py tests/sir_convert_a_lot/test_terminal_artifact_object_store_v2.py
```

Result: no matches.

```bash
pdm run typecheck-all
```

Result: `Success: no issues found in 946 source files`.

```bash
rg -n "minioadmin|task381-dev-access|task381-dev-secret|127\\.0\\.0\\.1:19000|localhost:19000|X-Amz-|AWSAccessKeyId|Signature=|SIR_CONVERT_A_LOT_R2_SECRET_ACCESS_KEY=.*[^ ]|SIR_CONVERT_A_LOT_R2_ACCESS_KEY_ID=.*[^ ]|http://|https://" build/verification/task-381-terminal-object-store-proof/summary.json build/verification/task-381-terminal-object-store-proof/readyz.json build/verification/task-381-terminal-object-store-proof/live-r2-or-minio-readyz.json
```

Result: no matches. The retained proof JSON does not expose the dev
access-key value, dev secret value, endpoint URL, or signed URL markers.

```bash
rg -n "delete_object|presign|presigned|generate_presigned|backfill|copy_object|upload_file|download_file|production env|prod env|purge|cleanup|HuleEdu File Service|File Service" <Task 381 touched files>
```

Result: no matches in Task 381 touched files.

```bash
rg -n "\\bAny\\b|typing\\.cast|\\bcast\\(|type: ignore|# noqa" <Task 381 touched files>
```

Result: no matches in Task 381 touched files.

Proof artifact review:

- `build/verification/task-381-terminal-object-store-proof/summary.json`
  records `live_r2_or_minio.status` as `passed`.
- The proof records primary download `200`, named download `200`, denial before
  read `401` with `0` object reads, missing object `404` with
  `artifact_not_available`, and no bucket/key/signed URL leak.
- `build/verification/task-381-terminal-object-store-proof/live-r2-or-minio-readyz.json`
  records backend `r2`, `config_ready=true`, `reachable=true`,
  `api_access=read_write`, `worker_access=read_write`, and secret-source labels
  only.

Not rerun by this reviewer:

- `pdm run coverage-gate` was not rerun in this pass. The implementation report
  states it passed after the Review 66 repair and before the later
  proof-script-only continuation; this re-review independently reran focused
  behavioral tests and `typecheck-all`.
- The live MinIO proof command itself was not rerun to avoid overwriting the
  retained proof package or depending on the parent-provisioned dev credential
  surface. The retained proof artifacts were inspected directly and redaction
  was verified with the command above.

## Residual Risk

Non-blocking: DigiExam `/result` route-specific metadata still reads the local
bundle manifest via `load_digiexam_migration_result_metadata`. Task 381's
accepted slice is artifact-byte streaming and route-owned named terminal bundle
artifacts, so this is not an approval blocker here. A later broader cold-result
metadata task should cover it if the product needs fully cold `/result`
metadata after local terminal manifests are removed.

## Response

The two previous Review 66 blockers are repaired with behavior-level tests at
the HTTP route and readiness boundaries. The live MinIO proof is retained and
redacted, and the reviewed code stays inside Task 381's terminal artifact
adapter scope.

## Follow-up Actions

1. Proceed to overseer closeout ledger for Task 381.
1. Keep retention/deletion reconciliation, production backfill/rollback,
   cleanup, browser-facing presigned/raw R2 URL behavior, and full job-store
   replacement in separate governed tasks.

## Completion

Approved for Task 381 overseer closeout. This review intentionally does not
mark Task 381 done by inference. The terminal review closeout is now user
approved through `approval_protocol: agent-planning:user-closure-gate`.

## Checklist

- [x] Findings captured
- [x] Decision recorded
- [x] Response recorded
- [x] Follow-up tasks linked
- [x] Review closed
