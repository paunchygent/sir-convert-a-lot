---
id: task-270-add-dirty-pdf-ocr-corpus-manifest-and-benchmark-report-schema
title: Add dirty PDF OCR corpus manifest and benchmark report schema
type: task
status: proposed
priority: high
created: '2026-04-27'
last_updated: '2026-04-27'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py
  - scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py
  - tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py
labels:
  - ocr
  - corpus
  - dirty-data
  - benchmark
  - privacy
  - schema
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Add a governed dirty-PDF OCR corpus manifest and sanitized benchmark report
schema that extends the committed Task 74 benchmark surface without committing
private/PII-bearing PDFs.

## PR Scope

- Extend the Task 74 benchmark/report schema rather than inventing a parallel
  evidence format.
- Define a corpus manifest for hard and dirty OCR inputs:
  - scanned,
  - mixed scanned/text,
  - low-contrast,
  - rotated/skewed,
  - table/form-heavy,
  - Swedish-diacritic,
  - long-document.
- Require each manifest row to include safe metadata:
  - stable source id,
  - source hash,
  - page count,
  - dirty-data class,
  - expected OCR languages,
  - privacy/sanitization state,
  - whether safe excerpts may be reported.
- Keep source PDFs out of git unless a task explicitly promotes sanitized
  committed fixtures.
- Extend benchmark reports with manifest summary, source hashes, profile
  matrix, Task 76 parity evidence, safe-profile compliance, warning/failure
  taxonomy, and OCR metadata summary.
- Preserve Task 74 safety constraints:
  - final evidence must prove Task 76 runtime parity,
  - dirty-corpus runs must use the committed Task 74 command surface,
  - the unsafe 4-worker OOM profile must fail closed unless a later governed
    decision reopens that boundary.

## Deliverables

- [ ] Dirty-corpus manifest schema.
- [ ] Report schema extension for dirty-corpus evidence.
- [ ] Validation tests for manifest/report parsing without private PDFs.
- [ ] Runbook/docs update showing where private corpus files live and what may
  be committed.

## Acceptance Criteria

- [ ] A developer/operator can validate a manifest locally without access to the
  private source PDFs.
- [ ] Reports generated from the manifest cannot omit Task 76 parity fields,
  profile safety classification, OCR metadata summary, or failure taxonomy.
- [ ] The report schema extends Task 74 outputs under
  `build/benchmarks/story-20/` or a governed successor path.
- [ ] The schema rejects or marks unsafe any profile outside Task 74's current
  safe matrix, especially the removed 4-worker profile that caused ROCm HIP OOM.
- [ ] No private PDFs, local `.env` files, or PII excerpts are committed.
- [ ] Synthetic fixtures remain test inputs only and cannot satisfy the
  real-data acceptance gate.

## Entry Points

- `scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py`
- `scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py`
- `tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py`
- `docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Test Requirements

- [ ] Manifest schema tests with synthetic metadata-only fixtures.
- [ ] Report schema tests proving Task 76 parity and safe-profile fields are
  required.
- [ ] Privacy test or docs check proving source PDF paths are not treated as
  commit-ready artifacts.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated

## Closeout

- `pdm run format-all`
- `pdm run lint-fix`
- `pdm run typecheck-all`
- focused `pdm run pytest-root tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py -q`
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run skills-validate`
- `pdm run handoff-validate`
- `git diff --check`
