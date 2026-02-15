---
id: task-18-root-cause-fix-deterministic-service-execution-and-artifact-integrity
title: Root-Cause Fix Deterministic Service Execution and Artifact Integrity
type: task
status: completed
priority: critical
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
  - docs/backlog/tasks/task-16-add-canonical-hemma-docling-gpu-live-test-runner-and-shell-usage-guardrails.md
  - docs/backlog/tasks/task-17-fix-async-duplicate-scheduling-and-strict-numeric-pagination-cleanup.md
labels:
  - runtime
  - reliability
  - determinism
  - operations
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Fix deterministic service drift at the root cause level by removing import-time runtime
side effects, enforcing single-owner execution at the job-store boundary, and hardening
live result integrity checks for Hemma validation runs.

## PR Scope

P0 service/runtime correctness:

- eliminate import-time app/runtime creation side effects in HTTP service modules,
- add atomic queued-job claim with per-job filesystem locking,
- prevent terminal artifact overwrite by stale/parallel worker finalization.

P1 deterministic evidence and observability:

- harden live validation runner to require inline-result/artifact manifest consistency,
- add bounded retry for transient protocol disconnects and deterministic fail behavior,
- add conversion-phase heartbeat and timing observability to distinguish slow vs stalled jobs.

Ops hardening:

- enforce eval/prod data-root isolation checks,
- enforce post-pull service freshness/restart verification for 28085 and 28086,
- fail closed when live service revision does not match Hemma repo `HEAD`.

## Deliverables

- [x] `http_api` import no longer creates eager runtime side effects
- [x] `service_eval` creates only eval runtime/app with no hidden default runtime
- [x] `JobStore.claim_queued_job(job_id)` added with atomic lock-protected transition
- [x] Runtime exits cleanly when claim fails or stale finalization conflict occurs
- [x] Live runner validates hash/size consistency for inline result vs manifest artifact
- [x] Hemma verification checks include process freshness and data-root isolation
- [x] Service `/healthz` exposes deterministic revision/start metadata for freshness checks
- [x] Runtime emits deterministic conversion heartbeat timestamps during `_execute_conversion`
- [x] Runtime persists per-job phase timing diagnostics for root-cause analysis

## Acceptance Criteria

- [x] Cross-runtime same-job race yields one execution owner and one terminal artifact write
- [x] Terminal overwrite attempts after completion are rejected and not retried
- [x] Import-side-effect regression tests prove no hidden runtime creation on import
- [x] Live validation run fails if any job is not manifest-consistent
- [x] Live validation/verify tooling fails when service revision != Hemma `HEAD`
- [x] Existing runtime/API/job-store suites remain green with new determinism semantics
- [x] Long-running conversion can be classified deterministically as slow vs stalled from telemetry

## Implementation Plan

1. Refactor service module entrypoints to remove eager import-time runtime creation while
   preserving external compatibility.
1. Add atomic queued-claim semantics and terminal state preconditions in persistent store.
1. Wire runtime to claim first, handle stale-worker conflicts as deterministic no-op exits.
1. Add eval/prod isolation assertions and Hemma freshness/config checks in verify tooling.
1. Add deterministic service revision/start metadata to `/healthz` and enforce
   revision parity checks against Hemma `HEAD`.
1. Harden live validation runner acceptance rules to enforce manifest integrity invariants.
1. Add focused race/import/integrity regression tests plus targeted existing-suite updates.
1. Add runtime conversion heartbeat (`last_heartbeat_at`) and periodic progress update during
   `_execute_conversion` path.
1. Add conversion phase timing capture (backend call / formula enrichment / normalize / persist)
   into durable job diagnostics.
1. Add tests that assert heartbeat progression and diagnostic timing presence for long-running jobs.

## Validation Plan

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_job_store_persistence.py`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_api_contract_v1.py`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete (local)
- [x] Docs updated
- [x] Patched revision deployed on Hemma and `hemma-verify-gpu-runtime` re-run clean

## Validation Evidence

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- `pdm run run-local-pdm hemma-verify-gpu-runtime` (pass after Hemma pull+restart on `fbc559e`)
- `pdm run run-local-pdm hemma-verify-gpu-runtime` (pass on `d854d5e` after pull+restart)
- Local tunnel confirmation run (`http://127.0.0.1:28085`) produced
  `backend_used=docling`, `acceleration_used=cuda`, terminal `succeeded`.
