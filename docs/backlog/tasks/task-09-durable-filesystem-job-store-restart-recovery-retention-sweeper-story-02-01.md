---
id: task-09-durable-filesystem-job-store-restart-recovery-retention-sweeper-story-02-01
title: Durable filesystem job store, restart recovery, retention sweeper (Story 02-01)
type: task
status: in_progress
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

- [ ] Filesystem-backed job store and durable idempotency records.
- [ ] Retention sweeper and expiry-aware `GET` semantics.
- [ ] Restart recovery behavior documented and test-covered.
- [ ] Updated contract docs to prefer `CONVERTER_STORAGE_ROOT` as the canonical env var
  while preserving `SIR_CONVERT_A_LOT_DATA_DIR` as an alias.

## Acceptance Criteria

- [ ] Jobs survive runtime restart: created job can be queried after re-instantiation of the runtime.
- [ ] Idempotency survives restart: same scope key + same fingerprint returns the same job id.
- [ ] Expiry works:
  - expired job returns `404` with `error.code="job_expired"`.
  - non-expired job returns the usual `job_not_found` only when unknown.
- [ ] Retention sweeper deletes expected files without deleting pinned jobs.
- [ ] Quality gates pass:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete (filesystem journal + idempotency + sweeper + restart recovery)
- [ ] Validation complete
- [ ] Docs updated
