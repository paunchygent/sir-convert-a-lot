---
id: task-271-run-safe-hemma-dirty-pdf-ocr-benchmark-and-publish-tuning-evidence
title: Run safe Hemma dirty PDF OCR benchmark and publish tuning evidence
type: task
status: proposed
priority: high
created: '2026-04-27'
last_updated: '2026-04-29'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/backlog/tasks/task-270-add-dirty-pdf-ocr-corpus-manifest-and-benchmark-report-schema.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py
  - scripts/sir_convert_a_lot/devops/verify_hemma_v2_conversions.py
labels:
  - ocr
  - benchmark
  - dirty-data
  - hemma
  - performance
  - gpu
  - safety
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the dirty real-data OCR benchmark against the production service on Hemma
through the safe Task 74 command surface, publish sanitized tuning evidence,
and block Story 39 closeout on unsafe or non-representative performance proof.

## PR Scope

- Use the manifest/report schema from Task 270.
- Re-run Task 76 deploy/runtime parity on the current pushed revision before
  any final benchmark evidence is accepted.
- Accept no local, in-process, synthetic-corpus, or smoke-run metrics as
  performance proof; local surfaces may validate only schema, command wiring,
  manifest privacy, and fail-closed profile classification.
- Provide the private Hemma source root alongside the metadata-only manifest so
  the benchmark runner can hash executed PDFs, verify them against manifest
  `source_sha256` values, and copy only sanitized `source_id.pdf` names into the
  execution corpus.
- Run only Task 74-approved safe profiles:
  - `serial_baseline`,
  - `parallel_conservative`,
  - bounded 2-worker sweeps if needed.
- Treat the removed 4-worker ROCm HIP OOM profile as forbidden unless a new
  governed decision explicitly reopens it.
- Capture sanitized benchmark JSON/Markdown evidence with:
  - corpus manifest summary,
  - page counts and hashes,
  - OCR engine/language metadata,
  - throughput and wall-clock,
  - stage timings,
  - GPU runtime/utilization evidence,
  - metrics safety,
  - warning/failure taxonomy,
  - determinism/non-regression evidence.
- Publish recommended tuning defaults and rollback criteria, or leave the story
  open with a concrete blocker when the target is not met.

## Deliverables

- [ ] Task 76 parity evidence for the exact revision under benchmark.
- [ ] Dirty-corpus benchmark JSON and Markdown report.
- [ ] Safe-profile compliance proof.
- [ ] Runbook/defaults update or explicit blocker explaining why defaults must
  stay unchanged.
- [ ] Story 39 / Task 74 evidence links updated.

## Acceptance Criteria

- [ ] Final evidence is captured against the production service on Hemma,
  GPU-backed, and tied to the pushed revision under review.
- [ ] Runtime parity is proven through Task 76 before the benchmark result is
  accepted.
- [ ] No local, in-process, synthetic-corpus, or smoke output is used as
  performance, throughput, tuning, acceptance, or production default evidence.
- [ ] Smoke assertions and smoke command stdout remain schema/safety-only and
  do not print or assert p50/p90, latency, pages-per-minute, throughput, or
  improvement percentages.
- [ ] The dirty-corpus run uses the Task 74 report schema and command surface.
- [ ] The dirty-corpus report records `source_hashes_verified=true`,
  `executed_entry_count=entry_count`, and `real_data_gate_satisfied=true`;
  manifest-only validation cannot satisfy this gate.
- [ ] Sanitized JSON/Markdown evidence omits the manifest path, private source
  root, and private PDF filenames.
- [ ] Unsafe profiles fail closed:
  - no 4-worker OOM-profile rerun as acceptance evidence,
  - no profile outside the safe 2-worker boundary unless a new governed
    decision updates Task 74 first.
- [ ] Recommended profile records `success_rate=1.0`; lower success blocks
  closeout.
- [ ] Median wall-clock improves by >= 40% versus baseline for the selected
  dirty corpus, or Story 39 remains open with a documented blocker.
- [ ] The operator "300 PDFs" target is evaluated or explicitly projected from
  measured evidence:
  - \<= 60 minutes on tuned Hemma profile, or
  - a governed blocker keeps the target open.
- [ ] Metrics safety records `contains_job_id_label=false`.
- [ ] Reports include OCR quality evidence for Swedish diacritics where
  expected and classify failures by input quality, engine/runtime availability,
  timeout, GPU/resource pressure, or conversion bug.

## Entry Points

- `pdm run run-hemma -- pdm run benchmark:task-74-hemma --expected-revision <sha>`
- `pdm run run-hemma -- pdm run benchmark:task-74-two-worker-sweep-hemma --expected-revision <sha>`
- `pdm run run-hemma -- pdm run benchmark:task-74-hemma --expected-revision <sha> --dirty-corpus-manifest <metadata-only-manifest.json> --dirty-corpus-source-root <private-pdf-root>`
- `scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py`
- `scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Test Requirements

- [ ] No new benchmark profile can be accepted without Task 76 parity evidence.
- [ ] The report marks unsafe profile requests as hard failures.
- [ ] The evidence bundle includes deterministic artifact digests or equivalent
  stable-output checks for tuned vs baseline profiles.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout

- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Include any code/test gates required by the benchmark harness changes made
  in this task.
