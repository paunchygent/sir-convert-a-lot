---
id: task-273-run-chunk-size-8-production-baseline-tuning-proof-with-warm-up-and-gpu-sampling
title: Run chunk-size 8 production baseline tuning proof with warm-up and GPU sampling
type: task
status: proposed
priority: high
created: '2026-04-30'
last_updated: '2026-04-30'
related:
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/reviews/review-10-ruthless-review-of-story-39-follow-up-task-272-and-task-273-drafts.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/devops/run_pdf_throughput_hemma_benchmark.py
  - scripts/sir_convert_a_lot/benchmarking/pdf_throughput_profile_runner.py
labels:
  - ocr
  - benchmark
  - hemma
  - performance
  - gpu
  - dirty-data
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Treat the Task 271 production-service result as the new baseline and test
whether `chunk_size_pages=8` improves throughput on the same dirty 157-page
corpus without reducing OCR/output quality.

This task must not rerun a serial baseline. The comparison baseline is the
already captured Task 271 production-service proof:

- profile: `production_service_current`
- `max_chunk_workers=2`
- `chunk_size_pages=4`
- `gpu_stage_max_concurrency=2`
- total pages: `157`
- total wall-clock: `2179.0` seconds
- success rate: `1.0`

## PR Scope

- Run a production-service Hemma candidate proof with:
  - `max_chunk_workers=2`,
  - `chunk_size_pages=8`,
  - `gpu_stage_max_concurrency=2`,
  - unchanged MIOpen cache/scratch settings,
  - unchanged OCR engine/languages unless a governed quality task changes them.
- Add a warm-up conversion before measured dirty-corpus execution so model and
  converter initialization are not counted as candidate throughput.
- Improve GPU/resource sampling so the benchmark no longer records
  non-credible `0.0` GPU busy/memory evidence for a GPU-backed OCR run.
- Compare candidate results against the Task 271 baseline artifact, not against
  a rerun serial baseline.
- Keep the run strictly on the production service on Hemma after Task 76 parity.
  Local or in-process runs may validate command wiring only and cannot be cited
  as performance evidence.
- Record rollback criteria:
  - if success rate drops below `1.0`,
  - if formula/image placeholder counts exceed the numeric gates below,
  - if warning/failure taxonomy worsens,
  - if GPU/resource evidence is unavailable, placeholder-only, or shows unsafe
    pressure,
  - if wall-clock improvement does not meet the numeric promotion gate below.
- Use these promotion gates:
  - baseline wall-clock is Task 271 `2179.0` seconds,
  - promote `chunk_size_pages=8` only if candidate wall-clock is `<=1961.1`
    seconds, a `>=10%` improvement versus Task 271,
  - keep `chunk_size_pages=4` if candidate wall-clock is `>2070.0` seconds, a
    `<5%` improvement,
  - if candidate wall-clock is `>1961.1` and `<=2070.0` seconds, do not
    promote by default; record a blocker or run one governed follow-up candidate
    such as `chunk_size_pages=6`.
- Use these quality non-regression gates:
  - success rate must remain `1.0`,
  - failed jobs must remain `0`,
  - `<!-- formula-not-decoded -->` count must not exceed Task 271 baseline
    `168`,
  - bare `<!-- image -->` marker count must not exceed the Task 271 baseline
    count measured from the same artifact set,
  - long-document Swedish diacritic total must remain at least `95%` of the
    Task 271 baseline `18615`, so the minimum accepted count is `17684`,
  - warning count must not exceed Task 271 baseline `4`,
  - engine/runtime, timeout, GPU/resource, and conversion-bug failure counts
    must remain `0`.
- Use these resource-sampling gates:
  - sampler output must include at least `60` timestamped samples during the
    measured run or at least one sample every `30` seconds, whichever yields
    fewer required samples for the final measured wall-clock,
  - required sample fields are timestamp, GPU busy percent, GPU memory used
    bytes or percent, process/container identifier, and sample source,
  - all-zero GPU busy samples fail closed unless accompanied by a documented
    probe explaining why ROCm counters are unavailable and an alternate
    measured GPU-memory/process signal is present,
  - missing, placeholder-only, or unparsable sampler output blocks promotion,
  - GPU memory pressure above `90%` of available GPU memory blocks promotion.

## Out Of Scope

- Testing `max_chunk_workers=4` or reopening the known unsafe 4-worker ROCm OOM
  profile.
- Running a serial baseline.
- Changing formula/image output quality behavior; Task 272 owns that quality
  implementation.
- Treating local smoke output as performance, throughput, tuning, acceptance,
  or production default evidence.

## Review Gate

- Review 10 re-reviewed and approved this draft on 2026-04-30.
- Implementation must preserve the numeric wall-clock, quality, and
  GPU/resource sampling gates below.

## Deliverables

- [ ] Candidate production-service benchmark artifact for `chunk_size_pages=8`.
- [ ] Warm-up evidence proving the measured run excluded initialization cost.
- [ ] GPU/resource sampling evidence with credible non-placeholder values or a
  documented blocker explaining why the sampler is still inadequate.
- [ ] Sanitized comparison against the Task 271 baseline result.
- [ ] Recommendation: keep `chunk_size_pages=4`, promote `8`, or run one more
  bounded candidate such as `6`.
- [ ] Runbook/task evidence update with default and rollback guidance.

## Acceptance Criteria

- [ ] Task 76 parity passes for the exact revision and deployed configuration
  before the candidate benchmark.
- [ ] The candidate run is captured against the production service on Hemma with
  `runtime_surface.mode=production_service`.
- [ ] Candidate config records:
  - `max_chunk_workers=2`,
  - `chunk_size_pages=8`,
  - `gpu_stage_max_concurrency=2`,
  - MIOpen cache/scratch settings unchanged from Task 271.
- [ ] The benchmark includes a warm-up conversion whose timing is excluded from
  the candidate wall-clock proof.
- [ ] The report compares candidate wall-clock, success rate, warnings,
  placeholder counts, Swedish diacritic counts, and resource evidence against
  the Task 271 baseline.
- [ ] Candidate success rate is `1.0`; any failed job blocks promotion.
- [ ] Candidate wall-clock is evaluated against the numeric gates:
  - `<=1961.1` seconds may promote if all other gates pass,
  - `>2070.0` seconds keeps `chunk_size_pages=4`,
  - intermediate results require a blocker or one more governed candidate.
- [ ] Candidate output quality does not regress:
  - `<!-- formula-not-decoded -->` count `<=168`,
  - bare `<!-- image -->` marker count does not exceed the Task 271 baseline
    measured from the same artifact set,
  - long-document Swedish diacritic count `>=17684`,
  - total warning count `<=4`,
  - no new engine/runtime, timeout, GPU/resource, or conversion-bug failures.
- [ ] Resource sampling passes the required sample-count and field gates; all
  missing, placeholder-only, unparsable, all-zero-without-alternate-proof, or
  `>90%` GPU-memory-pressure evidence blocks promotion.
- [ ] Metrics safety remains true: no forbidden high-cardinality job labels.
- [ ] The final recommendation is explicit and conservative:
  promote `chunk_size_pages=8` only if it improves wall-clock while preserving
  quality and resource safety; otherwise keep `4` as the baseline.

## Entry Points

- `pdm run run-hemma -- pdm run benchmark:pdf-throughput-hemma --expected-revision <sha> --dirty-corpus-manifest <manifest> --dirty-corpus-source-root <source-root>`
- `scripts/sir_convert_a_lot/devops/run_pdf_throughput_hemma_benchmark.py`
- `scripts/sir_convert_a_lot/benchmarking/pdf_throughput_profile_runner.py`
- `scripts/sir_convert_a_lot/benchmarking/pdf_throughput_service_profile.py`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Test Requirements

- [ ] Regression tests prove warm-up jobs are excluded from measured throughput.
- [ ] Regression tests prove candidate reports can compare against an existing
  Task 271 baseline artifact without rerunning a serial baseline.
- [ ] Regression tests prove GPU/resource sampler output is represented as
  measured evidence and fails closed when unavailable or placeholder-only.
- [ ] Focused docs/runbook validation after evidence capture.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
