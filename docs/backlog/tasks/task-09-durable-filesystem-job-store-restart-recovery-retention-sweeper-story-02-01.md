---
id: task-09-durable-filesystem-job-store-restart-recovery-retention-sweeper-story-02-01
title: Durable filesystem job store, restart recovery, retention sweeper (Story 02-01)
type: task
status: completed
priority: critical
created: '2026-02-14'
last_updated: '2026-02-14'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine.py
labels:
  - filesystem
  - durability
  - retention
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace in-memory job state with a contract-accurate filesystem journal so jobs are durable across
service restarts, idempotency remains correct, and retention/expiry behavior is enforced.

## PR Scope

- Implement v1 storage layout under the configured storage root:
  - `jobs/<job_id>/raw/input.pdf`
  - `jobs/<job_id>/artifacts/output.md`
  - `jobs/<job_id>/logs/run.log`
  - `jobs/<job_id>/manifest.json`
- Add a job-store abstraction that reads/writes `manifest.json` as the source of truth.
- Persist idempotency records to disk so create-job replay survives restarts.
- Implement deterministic restart recovery:
  - jobs marked `running` with no active worker are reverted to `queued`.
- Implement a retention sweeper aligned to v1 policy:
  - raw uploads: 24h
  - artifacts/manifests: 7d
  - pinned jobs are exempt
- Ensure expired jobs return `404` with `error.code="job_expired"`.

## Deliverables

- [x] Filesystem-backed job store and durable idempotency records.
- [x] Retention sweeper and expiry-aware `GET` semantics.
- [x] Restart recovery behavior documented and test-covered.
- [x] Updated contract docs to prefer `CONVERTER_STORAGE_ROOT` as the canonical env var
  while preserving `SIR_CONVERT_A_LOT_DATA_DIR` as an alias.

## Acceptance Criteria

- [x] Jobs survive runtime restart: created job can be queried after re-instantiation of the runtime.
- [x] Idempotency survives restart: same scope key + same fingerprint returns the same job id.
- [x] Expiry works:
  - expired job returns `404` with `error.code="job_expired"`.
  - non-expired job returns the usual `job_not_found` only when unknown.
- [x] Retention sweeper deletes expected files without deleting pinned jobs.
- [x] Quality gates pass:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Execution Plan

1. Implement filesystem-backed `JobStore` and durable `IdempotencyStore` under `infrastructure/`
   with manifest-as-source-of-truth semantics.
1. Ensure restart recovery:
   - orphaned `running` jobs become `queued` on service start.
   - supervisor worker-slot tracking does not leak (recovered jobs can be scheduled).
1. Implement retention sweeper with tombstones so `job_expired` is distinguishable from `job_not_found`:
   - raw uploads deleted after TTL
   - artifacts/manifests deleted after TTL
   - pinned jobs are exempt
1. Enforce SRP and size rules:
   - split infrastructure persistence modules before 500 LoC.
1. Add durability/retention tests and run full code + docs gates.

## Implementation Artifacts

- Infrastructure:
  - `scripts/sir_convert_a_lot/infrastructure/job_store.py`
  - `scripts/sir_convert_a_lot/infrastructure/idempotency_store.py`
  - `scripts/sir_convert_a_lot/infrastructure/filesystem_journal.py`
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
- Tests:
  - `tests/sir_convert_a_lot/test_job_store_persistence.py`

## Validation Evidence

- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass)
- `pdm run pytest-root tests/sir_convert_a_lot` (pass)
- `pdm run validate-tasks` (pass)
- `pdm run validate-docs` (pass)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Checklist

- [x] Implementation complete (filesystem journal + idempotency + sweeper + restart recovery)
- [x] Validation complete
- [x] Docs updated
