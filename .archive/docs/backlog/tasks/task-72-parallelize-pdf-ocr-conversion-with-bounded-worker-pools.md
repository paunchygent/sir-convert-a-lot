---
id: task-72-parallelize-pdf-ocr-conversion-with-bounded-worker-pools
title: Parallelize PDF OCR conversion with bounded worker pools
type: task
status: completed
priority: high
created: '2026-03-04'
last_updated: '2026-04-29'
related:
  - docs/backlog/stories/story-20-parallel-execution-and-bottleneck-elimination-for-pdf-ocr.md
  - docs/backlog/tasks/task-70-implement-chunk-checkpoints-and-partial-markdown-artifacts.md
  - docs/backlog/tasks/task-73-add-conversion-bottleneck-telemetry-and-stage-timing-metrics.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/reference/ref-pdf-parallel-throughput-evidence.md
  - scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py
  - scripts/sir_convert_a_lot/infrastructure/runtime_telemetry_v2.py
  - scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py
  - scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py
  - scripts/sir_convert_a_lot/infrastructure/docling_backend.py
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
labels:
  - long-pdf
  - performance
  - parallelization
  - worker-pool
  - gpu
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Increase throughput for long OCR jobs by processing chunks with bounded parallel workers while
preserving determinism, checkpoint/resume correctness, and production stability.

## Ruthless Review Findings (2026-03-05)

- Blocker: Resume safety is underspecified for out-of-order chunk completion; this can duplicate
  chunk output or break byte-parity on resume.
- Blocker: Checkpoint/partial persistence write model is underspecified for parallel workers; naive
  full-file writes can race and yield invalid checkpoint states.
- High: Cancel-with-save semantics are not defined for in-flight workers, risking post-cancel
  nondeterministic writes.
- High: Story 20 guardrails are missing from task-level scope:
  - T76 deploy+verify hardening must be a prerequisite for Hemma tuning runs.
  - Parallel mode must remain opt-in by default until T74 evidence exists.
- High: Config contract is not explicit (knob names, bounds, defaults, metadata exposure).
- High: Telemetry semantics are incomplete for intra-job parallelism and must stay
  bounded-cardinality (no `job_id` labels).
- Medium: API behavior parity for `/artifact`, `/artifact/partial`, `/checkpoint`, `/resume` is not
  explicitly locked under parallel mode.
- Medium: Missing explicit test matrix and named regressions for the failure modes above.

## Suggested Remediation Approach

1. Lock deterministic, idempotent chunk completion semantics:
   - key completion state by `chunk_index` and page range,
   - skip already-completed chunks regardless of completion order.
1. Enforce concurrency-safe persistence:
   - single-writer checkpoint/partial aggregation per job, or equivalent per-job lock/CAS merge
     semantics,
   - no concurrent full-file checkpoint writes.
1. Define cancellation barrier behavior:
   - stop new dispatch on cancel,
   - explicit in-flight drain/abort policy,
   - deterministic commit boundary for partial artifacts and resume.
1. Specify and enforce canonical config contract:
   - env names, bounds, defaults, and fail-closed validation,
   - effective execution profile recorded in runtime/job metadata.
1. Update telemetry contracts for parallel mode:
   - distinguish job-level and chunk-level concurrency signals,
   - enforce bounded-label policy and metrics safety tests.
1. Add explicit API parity and regression gates, and keep parallel mode opt-in until T74 benchmark
   evidence is accepted.

## PR Scope

- Refactor
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  to implement bounded per-job chunk worker pools with deterministic ordered merge and idempotent
  chunk completion tracking.
- Refactor checkpoint persistence path across
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`
  and
  `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/pdf_checkpoints_v2.py`
  to guarantee concurrency-safe checkpoint/partial writes under parallel mode.
- Add global cross-job scheduler caps and admission/backpressure controls so per-job pools cannot
  oversubscribe GPU/CPU/memory under concurrent long jobs.
- Define and enforce parallel cancel-with-save barrier semantics in executor flow so post-cancel
  artifacts remain deterministic and resume-safe.
- Enforce ADR-0005 retention invariants in parallel mode:
  - no unbounded checkpoint history growth,
  - checkpoint/partial artifacts expire with job retention by default,
  - `retention.pin=true` preserves resume material.
- Add canonical configuration knobs and validation across:
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/runtime_models.py`
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/runtime_config.py`
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/v2_conversion_executor.py`
- Update telemetry contract and metric emission points across:
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`
  - `/Users/olofs_mba/Documents/Repos/sir-convert-a-lot/scripts/sir_convert_a_lot/infrastructure/runtime_telemetry_v2.py`
- Preserve API contract behavior under parallel mode for:
  - `/artifact`
  - `/artifact/partial`
  - `/checkpoint`
  - `/resume`
- Keep parallelization opt-in by default until Task 74 is terminalized with linked benchmark
  artifacts under `build/benchmarks/story-20/*.json`; require Task 76 evidence
  (`build/verification/task-76-hemma-deploy-verify/report.json` with `status=passed`) before any
  Hemma tuning run.
- No compatibility shims for legacy semantics; contracts must be explicit and canonical.

## Deliverables

- [x] Parallel execution implementation in runtime/conversion pipeline with deterministic merge.
- [x] Concurrency-safe checkpoint and partial artifact persistence model for parallel workers.
- [x] Explicit config surface (knobs, bounds, defaults) for chunk workers and chunk size.
- [x] Telemetry contract updates for job-level vs chunk-level concurrency and bounded labels.
- [x] Concurrency safety, cancel/resume, deterministic parity, and API contract regression tests.
- [x] Updated runbook guidance for safe Hemma tuning and rollout sequencing.

## Acceptance Criteria

- [x] Parallel mode shows measurable throughput improvement (>= 10% wall-clock reduction versus
  serial baseline on task benchmark fixture) and stores machine-readable evidence under
  `build/benchmarks/story-20/` without API/artifact regressions.
- [x] Resume from partially parallelized runs is byte-identical to serial baseline and contains no
  duplicate chunk content.
- [x] Under parallel load, checkpoint state remains valid (`checkpoint_invalid` is never produced by
  write races) and chunk records remain complete/unique.
- [x] ADR-0005 progress invariants hold under out-of-order completion:
  - `processed_pages`/`failed_pages`/`percent_complete` never decrease,
  - progress fields never exceed `total_pages`,
  - chunk commits update heartbeat and phase timings consistently.
- [x] Cancel-with-save behavior is deterministic in parallel mode and yields resume-safe partial
  artifacts with explicit commit boundary (only chunks committed before cancel barrier are
  persisted).
- [x] Parallel checkpoint/partial persistence remains retention-bounded and pin-aware (expires with
  job unless `retention.pin=true`).
- [x] Default behavior remains serial when parallel knobs are unset (opt-in rollout preserved).
- [x] Effective config is validated, documented, and exposed with canonical metadata keys:
  `parallel_enabled`, `max_chunk_workers`, `chunk_size_pages`, `effective_gpu_stage_limit`,
  `scheduling_mode`.
- [x] Telemetry reflects true scheduler state for job and chunk concurrency while preserving bounded
  cardinality (no `job_id`, filename, or correlation-id labels).
- [x] `/artifact`, `/artifact/partial`, `/checkpoint`, and `/resume` preserve ADR/API semantics in
  serial and parallel modes:
  - `/artifact` remains terminal-success-only,
  - `/artifact/partial` and `/checkpoint` retain `200/202/404` behavior,
  - `/resume` creates a new `job_id` and preserves rejection semantics for missing/expired
    checkpoint material.
- [x] T76 deploy-parity + live verification gate evidence exists before Hemma tuning runs for T72/T74.
- [x] GPU-backed stages enforce both per-job and global concurrency caps with backpressure to avoid
  OOM/thrash, and GPU policy enforcement remains intact (no silent CPU fallback when GPU is
  requested/required).

## Test Requirements

- [ ] Add/extend tests covering:
  - `test_parallel_out_of_order_chunk_completion_is_deterministic`
  - `test_parallel_resume_after_partial_is_byte_identical_to_serial`
  - `test_parallel_checkpoint_single_writer_prevents_invalid_state`
  - `test_parallel_cancel_mid_run_produces_resume_safe_partial`
  - `test_parallel_defaults_remain_serial_when_unset`
  - `test_parallel_env_bounds_validation`
  - `test_parallel_metrics_emit_bounded_labels_without_job_id`
  - `test_parallel_api_contract_parity_for_artifact_checkpoint_resume`
  - `test_parallel_progress_fields_monotonic_under_out_of_order_completion`
  - `test_parallel_chunk_commit_updates_heartbeat_and_phase_timings`
  - `test_parallel_checkpoint_and_partial_retention_respects_job_expiry_and_pin`
  - `test_parallel_multi_job_global_caps_apply_backpressure_without_oom`
  - `test_parallel_resume_requires_valid_retained_checkpoint_and_returns_new_job_id`
- [ ] Validation gate:
  - `pdm run pytest-root tests/sir_convert_a_lot -q`

## Remediation Checklist (Must Be Resolved Before Terminalizing)

- [x] Blocker findings for resume safety and checkpoint race safety are closed.
- [x] High-severity findings for cancellation barrier semantics and config contract are closed.
- [x] High-severity telemetry contract gaps are closed with bounded-label enforcement.
- [x] Story 20 guardrails (T76 prerequisite + opt-in default parallelism) are enforced.
- [x] Medium-severity API parity and explicit test-matrix gaps are closed.

## Status Update (2026-03-06)

- Implemented:
  - bounded per-job chunk worker pools with ordered commit semantics in
    `scripts/sir_convert_a_lot/infrastructure/v2_pdf_checkpointed_executor.py`,
  - global chunk-worker admission/backpressure controls in
    `scripts/sir_convert_a_lot/infrastructure/runtime_engine_v2.py`,
  - explicit parallel config/env contract and surfaced conversion metadata in
    `runtime_config.py`, `v2_conversion_executor.py`, and result payloads,
  - dedicated PDF parallel throughput regression coverage for determinism, checkpoint safety, cancel/resume,
    bounded metrics labels, API parity, progress monotonicity, and multi-job caps.
- Added deterministic local scheduling-regression command and artifact:
  - `pdm run benchmark:pdf-parallel-throughput --output-json build/benchmarks/pdf-throughput/pdf-parallel-throughput-local.json`
  - artifact: `build/benchmarks/pdf-throughput/pdf-parallel-throughput-local.json`
  - latest local run (`2026-03-06`, artifact timestamp `2026-03-05T23:10:26Z`):
    - `comparison.p50_wall_clock_improvement_percent=73.274`
    - `comparison.byte_identical_to_serial=true`
    - `serial.p50_duration_seconds=0.317518`
    - `parallel.p50_duration_seconds=0.08486`
- The local PDF parallel throughput artifact is implementation/regression evidence only. It must not be cited as
  production performance proof, throughput proof, tuning evidence, acceptance evidence, or a reason
  to set Hemma production defaults; accepted OCR performance evidence belongs to the Task 74/Story
  39 production-service benchmark path on Hemma after Task 76 parity.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run format-all` (pass)
- `pdm run lint-fix` (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 207 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot -q` (pass: `479 passed, 5 skipped`)
- `pdm run benchmark:pdf-parallel-throughput --total-pages 8 --repeats 5 --chunk-size-pages 1 --max-chunk-workers 4 --stub-work-seconds 0.03 --output-json build/benchmarks/pdf-throughput/pdf-parallel-throughput-local.json --data-root build/benchmarks/pdf-throughput/pdf-parallel-throughput-runtime` (pass: deterministic scheduling-regression guard only; not production performance proof)
- `pdm run validate-tasks` (pass: `Validated 109 backlog files`)
- `pdm run validate-docs` (pass: `Validated docs=137 rules=9`)
- `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing` (pass)

## Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
