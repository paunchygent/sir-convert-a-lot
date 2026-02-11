---
id: task-05-enforce-gpu-first-lock-and-benchmark-evidence-for-story-003b
title: Enforce GPU-first lock and benchmark evidence for Story 003b
type: task
status: completed
priority: critical
created: '2026-02-11'
last_updated: '2026-02-11'
related:
  - docs/backlog/stories/story-03-02-gpu-first-execution-and-fallback-governance.md
  - docs/converters/pdf_to_md_service_api_v1.md
  - docs/decisions/0001-pdf-to-md-service-v1-contract-and-phase0-decisions.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - gpu
  - benchmark
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Deliver Story 003b in one combined execution unit: enforce hard GPU-first rollout defaults,
expand GPU-governance tests, and produce benchmark evidence artifacts with documented two-stage
execution (local deterministic run + Hemma runbook path).

## PR Scope

- Runtime policy hardening in `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`.
- Contract/README alignment for fallback lock policy.
- Benchmark runner and benchmark fixture corpus for repeatable evidence.
- Benchmark report + JSON appendix in `docs/reference/`.
- Story/task/epic/current/handoff docs closure updates.

## Deliverables

- [ ] Hard GPU-first lock defaults implemented (no env-controlled CPU fallback toggles in normal startup).
- [ ] API/runtime tests cover GPU unavailable + policy behavior for `gpu_required`, `gpu_prefer`, and
  `cpu_only`.
- [ ] Test-only explicit CPU unlock path validated and documented.
- [ ] Benchmark runner script created with deterministic JSON output.
- [ ] Canonical benchmark PDF fixture set (5 files) added under `tests/fixtures/`.
- [ ] Benchmark evidence committed under `docs/reference/` (report + JSON appendix).

## Acceptance Criteria

1. Requests that cannot execute under rollout lock fail with `gpu_not_available` and standard envelope.
1. Successful conversion results include mandatory `conversion_metadata.acceleration_used`.
1. Benchmark report includes latency distribution, throughput, and resource profile summary.
1. Fallback policy remains decision-gated by ADR and is not runtime env-switchable by default.
1. Full quality/docs gates pass after implementation.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Implementation Notes (2026-02-11)

- Runtime rollout lock hardened in:
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
- Added Story 003b tests:
  - `tests/sir_convert_a_lot/test_api_contract_v1.py`
  - `tests/sir_convert_a_lot/test_runtime_engine_gpu_policy.py`
  - `tests/sir_convert_a_lot/test_benchmark_gpu_governance.py`
- Added benchmark runner and corpus:
  - `scripts/sir_convert_a_lot/benchmark_gpu_governance.py`
  - `tests/fixtures/benchmark_pdfs/`
- Added benchmark evidence artifacts:
  - `docs/reference/benchmark-story-003b-gpu-governance-local.json`
  - `docs/reference/ref-story-003b-gpu-governance-benchmark-evidence.md`
- Validation evidence:
  - `pdm run run-local-pdm format-all`
  - `pdm run run-local-pdm lint-fix`
  - `pdm run run-local-pdm typecheck-all`
  - `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
  - `pdm run run-local-pdm validate-tasks`
  - `pdm run run-local-pdm validate-docs`
  - `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
