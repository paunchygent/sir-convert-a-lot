---
type: task
id: TASK-SIRCON-03-01-03
title: Run throughput benchmark and publish performance tuning report
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-03-01
task_kind: story
acceptance_criteria:
- '- [ ] Benchmark report is reproducible with documented command surface and dataset profile.'
- '- [ ] Final benchmark evidence is captured on Hemma against the current pushed revision after a passing `T76` deploy-parity
  run on that same revision.'
- '- [ ] The report documents the exact benchmark matrix used (profile names + worker/chunk/GPU caps) and the runtime surface
  declaration (`mode`, lane/parity note, revision).'
- '- [ ] Tuned profile demonstrates >= 40% median runtime improvement vs baseline.'
- '- [ ] The final evidence bundle records `success_rate=1.0` for the recommended profile on the benchmark corpus; any lower
  success rate blocks task closeout.'
- '- [ ] Recommended defaults include explicit safety limits (workers/chunk size/memory).'
- '- [ ] Recommended defaults are justified by recorded queue/worker saturation and GPU busy/memory evidence, not by latency
  alone.'
- '- [ ] If safe 2-worker tuning still fails to reach the >= 40% target, the service default remains serial and parallel execution
  is exposed only through explicit `.env` override.'
- '- [ ] Metrics-safety evidence is explicit: no forbidden high-cardinality metric labels are present (`contains_job_id_label=false`).'
- '- [ ] Parallel tuning evidence includes explicit determinism/non-regression proof against the serial baseline (artifact
  digest or equivalent stable-output check).'
- '- [ ] Report includes rollback path when runtime conditions deviate from benchmark assumptions.'
retired_ids:
- task-74-run-throughput-benchmark-and-publish-performance-tuning-report
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Produce reproducible performance evidence and recommended runtime defaults for long scanned PDF OCR
conversions on Hemma.

### PR Scope

- Define benchmark corpus representative of 100-300+ page scanned textbook workloads.
- Run baseline vs tuned profiles (serial, parallel worker configs, chunk-size variants).
- Capture throughput, wall-clock, error rate, GPU utilization, and stage timing metrics.
- Publish tuning report and operational defaults in runbook form.
- Pin the benchmark matrix to the committed Task 74 harness defaults unless this task doc is updated
  first:
  - `serial_baseline`: `parallel_enabled=false`, `max_chunk_workers=1`,
    `chunk_size_pages=8`, `gpu_stage_max_concurrency=1`
  - `parallel_conservative`: `parallel_enabled=true`, `max_chunk_workers=2`,
    `chunk_size_pages=4`, `gpu_stage_max_concurrency=2`
- The unsafe 4-worker benchmark profile was removed after the 2026-03-06 Hemma run proved it can
  hit ROCm HIP OOM and must not remain as an accidentally reusable command-surface default.
- Further tuning work is limited to safe 2-worker experiments first (for example chunk size and
  closely related bounded parameters) until evidence proves a different setting is both stable and
  materially faster.
- A dedicated bounded sweep command surface now exists for that follow-up work:
  - local smoke/schema only: `pdm run benchmark:pdf-throughput-two-worker-sweep`
  - production Hemma evidence: `pdm run run-hemma -- pdm run benchmark:pdf-throughput-two-worker-sweep-hemma --expected-revision <sha>`
- Dirty real-data OCR evidence added by Story 39 must extend this Task 74 report schema and command
  surface rather than bypassing it. Story 39 evidence is not acceptance evidence for Task 74 unless it
  also preserves this task's Task 76 parity requirement, safe profile matrix, executed-source hash
  verification, and forbidden 4-worker OOM-profile guardrail.
- Make the runtime surface explicit in the evidence bundle:
  - `mode=in_process_app` is acceptable only for harness development, schema validation, and
    command-surface smoke checks,
  - local/in-process runs must not be cited as performance proof, throughput proof, tuning proof, or
    production default evidence,
  - final closeout evidence must run against the production service on Hemma, prove deploy/runtime
    parity via `T76`, and document why the measured service lane is representative of the
    production OCR path.

Measurement rules (must be explicit in report):

- Primary metric: wall-clock time from `created_at` to terminal `succeeded` for `pdf -> md` jobs.
- Report percentiles at minimum: p50 and p90, with N documented.
- Include resource evidence:
  - worker pool saturation and queue depth metrics,
  - GPU busy/utilization snapshot for the run (ROCm equivalent when applicable),
  - peak memory notes when available.

### Ruthless Review Gaps To Close

- Runtime-parity ambiguity:
  - the local harness can run `mode=in_process_app`, which is not the deployed Hemma service/runtime
    image and cannot produce accepted performance evidence.
  - `T74` must not be terminalized on harness-only evidence; accepted performance evidence requires
    the production service on Hemma, explicit `T76` deploy parity, and a written parity statement in
    the report.
- Evidence sufficiency ambiguity:
  - local CPU-only smoke artifacts are command-surface/schema evidence only and must never be
    presented as performance, throughput, tuning, or acceptance evidence for Story 20 / Epic 06
    closeout.
  - smoke assertions and smoke command stdout must not print or assert p50/p90, latency,
    pages-per-minute, throughput, or improvement percentages.
  - final performance evidence must be captured against the production service on Hemma, be
    GPU-backed, and be tied to the pushed revision under review.
- Determinism gap:
  - Story 20 requires no output-determinism/API-contract regression under parallel mode; `T74`
    therefore needs explicit artifact-digest or equivalent determinism evidence in addition to
    latency gains.
- Metrics-safety gap:
  - the benchmark report must explicitly state whether forbidden high-cardinality labels were absent
    (`contains_job_id_label=false`) and treat any violation as a hard fail.
- Rollback-threshold gap:
  - rollback criteria must be written as concrete thresholds tied to observed metrics, not narrative
    prose only.

### Hardened Execution Plan

1. Re-run `T76` on the current pushed revision and record the exact `expected_revision`,
   `remote_revision`, and `service_revision`.
1. Execute the canonical `T74` profile matrix against the production service on Hemma with
   GPU-backed settings:
   - `page_counts=120,180,240`
   - `acceleration_policy=gpu_required`
   - `ocr_mode=force`
   - `ocr_engine=easyocr`
   - `ocr_languages=sv,en`
   - `profile matrix = serial_baseline + parallel_conservative` only
1. Capture one evidence bundle containing:
   - benchmark JSON,
   - markdown report,
   - profile matrix and recommended profile,
   - runtime-surface declaration (`mode`, host, revision, parity note),
   - resource evidence (`peak_jobs_queued`, worker/chunk saturation, GPU busy/memory),
   - metrics-safety result (`contains_job_id_label`),
   - determinism evidence for recommended parallel profile vs baseline behavior.
1. Derive recommended defaults and rollback thresholds from the evidence bundle, then update
   `docs/runbooks/run-sircon-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot-hemma-devops-and-gpu-runbook-for-sir-convert-a-lot.md`.
1. If the first Hemma benchmark misses the target without stability regressions, run the bounded
   2-worker sweep to evaluate chunk-size and bounded GPU-cap variants before deciding whether the
   service default can move off serial.
1. Only after the above is complete, terminalize `T74`, then Story 20, then Epic 06 in strict
   status/checkbox order.

### Implementation Checklist

- [x] Extend the Task 74 benchmark payload schema with explicit runtime-surface and Task 76 parity
  metadata.
- [x] Teach the benchmark harness to ingest Task 76 parity evidence (`report.json` or explicit
  parity flags) and compute `runtime_parity.parity_proven`.
- [x] Render runtime parity state into the markdown report so reviewers can assess representativeness
  without opening raw JSON.
- [x] Add focused regression tests for:
  - parity metadata ingestion from Task 76 report JSON,
  - parity-unproven behavior when required checks are missing,
  - report output containing runtime surface + parity fields.
- [x] Update Task 74 acceptance commands/runbook usage to pass the parity metadata explicitly during
  the Hemma benchmark run.
- [x] Add a canonical Hemma benchmark workflow that repairs env/runtime drift before running the
  long OCR benchmark (`benchmark:pdf-throughput-hemma`).
- [x] Fail fast when the in-process benchmark runtime is missing required OCR dependencies/models so
  Task 74 cannot silently emit bogus all-503 benchmark output.

### Deliverables

- [ ] Benchmark execution artifacts (raw results + summary tables/plots).
- [ ] Written tuning report with recommended defaults and guardrails.
- [ ] Updated runbook section with production settings and rollback criteria.
- [ ] Acceptance evidence linked from epic/story/task docs.
- [ ] Runtime-parity note included in final evidence bundle (`mode`, revision, Hemma parity gate).
- [ ] Determinism evidence included for tuned profile vs serial baseline.
- [ ] Metrics-safety result included (`contains_job_id_label=false`).

### Acceptance Criteria

- [ ] Benchmark report is reproducible with documented command surface and dataset profile.
- [ ] Final benchmark evidence is captured on Hemma against the current pushed revision after a
  passing `T76` deploy-parity run on that same revision.
- [ ] The report documents the exact benchmark matrix used (profile names + worker/chunk/GPU caps)
  and the runtime surface declaration (`mode`, lane/parity note, revision).
- [ ] Tuned profile demonstrates >= 40% median runtime improvement vs baseline.
- [ ] The final evidence bundle records `success_rate=1.0` for the recommended profile on the
  benchmark corpus; any lower success rate blocks task closeout.
- [ ] Recommended defaults include explicit safety limits (workers/chunk size/memory).
- [ ] Recommended defaults are justified by recorded queue/worker saturation and GPU busy/memory
  evidence, not by latency alone.
- [ ] If safe 2-worker tuning still fails to reach the >= 40% target, the service default remains
  serial and parallel execution is exposed only through explicit `.env` override.
- [ ] Metrics-safety evidence is explicit: no forbidden high-cardinality metric labels are present
  (`contains_job_id_label=false`).
- [ ] Parallel tuning evidence includes explicit determinism/non-regression proof against the serial
  baseline (artifact digest or equivalent stable-output check).
- [ ] Report includes rollback path when runtime conditions deviate from benchmark assumptions.

### Status Update (2026-03-06)

- Implemented the Task 74 benchmark/report command surface:
  - `pdm run benchmark:pdf-throughput`
  - benchmark harness: `scripts/sir_convert_a_lot/pdf_throughput_benchmark_report.py`
  - markdown report writer: `scripts/sir_convert_a_lot/benchmarking/pdf_throughput_report.py`
- The harness now:
  - generates deterministic scanned-PDF corpus files for command-surface smoke and regression
    checks,
  - can run baseline and tuned runtime profiles through the v2 API/runtime path,
  - emits JSON + markdown artifacts under `build/benchmarks/story-20/`.
- Performance fields in local smoke artifacts are diagnostic byproducts only; they are not
  acceptance, tuning, throughput, or production default evidence.
- Added regression coverage:
  - `tests/sir_convert_a_lot/test_pdf_throughput_benchmark_report.py`
- Started the first closeout blocker for final evidence integrity:
  - benchmark payload/report now embed explicit runtime-surface declaration,
  - Task 76 parity metadata can be loaded from `report.json` or explicit CLI flags,
  - the evidence bundle now computes and records `runtime_parity.parity_proven`.
- Local smoke command completed on laptop using CPU-only overrides. This is command-surface/schema
  evidence only and does not prove performance, throughput, tuning, or production defaults:
  - `build/benchmarks/story-20/task-74-throughput-smoke-local.json`
  - `build/benchmarks/story-20/task-74-throughput-smoke-local.md`
- Historical Task 74 closeout remains open for true baseline-vs-tuned comparison:
  Task 271 later captured a production-service dirty-corpus proof on Hemma, but
  that run records the fixed deployed service profile as
  `production_service_current` and does not by itself satisfy the `>=40%`
  baseline-vs-tuned improvement gate.

### Benchmark Decision Update (2026-03-06)

- Hemma benchmark evidence was captured on revision
  `470e44afac29baf92abe56e0e06097663adfd57d` with runtime parity proven.
- `parallel_conservative` was the best stable profile, improving p50 wall-clock by `11.4286%`
  versus `serial_baseline`, which is below the Task 74 target of `>= 40%`.
- The removed 4-worker profile failed all benchmark jobs with ROCm HIP OOM and is no longer an
  allowed benchmark default or rollout candidate.
- Next tuning work is constrained to safe 2-worker experiments only and now uses the bounded sweep
  command surface to vary chunk size plus bounded GPU stage cap; if those experiments still fail to
  reach the `>= 40%` target, production default stays serial and parallel mode remains opt-in via
  explicit `.env` override.

### Dirty-Corpus Production-Service Evidence (2026-04-30)

- Task 271 captured a safe dirty real-data production-service benchmark on
  Hemma for revision `405cddc59d02974f43eaf03556bad92cdd1c2341` after passing
  Task 76 deploy/runtime parity on that same revision.
- Artifact locations are ignored `build/` evidence paths:
  - `build/benchmarks/story-39/task-271-dirty-pdf-ocr-benchmark-hemma.json`,
  - `build/benchmarks/story-39/task-271-dirty-pdf-ocr-benchmark-report-hemma.md`.
- Sanitized result facts:
  - runtime mode: `production_service`,
  - profile: `production_service_current`,
  - source hashes verified: `true`,
  - executed entries: `10` of `10`,
  - total pages: `157`,
  - success rate: `1.0`,
  - failed jobs: `0`,
  - metrics safety: `contains_job_id_label=false`,
  - 150-page target: `157` pages in `2179.0` seconds.
- This run is valid Task 271 production-service proof for the 150-page target.
  It is not a standalone Task 74 closeout for the `>=40%` improvement target
  because the benchmark report truthfully records only the current deployed
  profile and therefore reports `p50_improvement_percent=0.0`.

### Validation Evidence

- `pdm run typecheck-all` (pass: `Success: no issues found in 211 source files`)
- `pdm run pytest-root tests/sir_convert_a_lot/test_pdf_parallel_throughput_benchmark.py tests/sir_convert_a_lot/test_pdf_telemetry_overhead_benchmark.py tests/sir_convert_a_lot/test_pdf_throughput_benchmark_report.py -q` (pass: `9 passed`)
- Local smoke command (pass for command surface/schema only; not performance, throughput, tuning, or
  acceptance evidence):
  - `pdm run benchmark:pdf-throughput --page-counts 2,3 --acceleration-policy cpu_only --ocr-mode off --ocr-engine auto --ocr-languages en --no-gpu-available --max-poll-seconds 120 --output-json build/benchmarks/story-20/task-74-throughput-smoke-local.json --output-report build/benchmarks/story-20/task-74-throughput-smoke-local.md --corpus-root build/benchmarks/story-20/task-74-smoke-corpus --data-root build/benchmarks/story-20/task-74-smoke-runtime`

### Planned Acceptance Commands

- Deploy parity preflight:
  - `pdm run hemma-deploy-and-verify --expected-revision "$(git rev-parse HEAD)" --lane host`
- Hemma benchmark run:
  - `pdm run run-hemma -- pdm run benchmark:pdf-throughput-hemma --expected-revision <sha>`
- Required closeout gates after evidence capture:
  - `pdm run format-all`
  - `pdm run lint-fix`
  - `pdm run typecheck-all`
  - `pdm run pytest-root tests/sir_convert_a_lot`
  - `pdm run validate-tasks`
  - `pdm run validate-docs`
  - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

### Closeout (Mandatory)

- Follow the Epic 06 per-task closeout checklist:
  - `docs/backlog/epics/epic-sircon-03-long-pdf-conversion-reliability-progress-and-throughput-scaling.md`
- Terminalize this task doc (`status: completed`) before checking any epic/story checkboxes.
