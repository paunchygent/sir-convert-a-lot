---
id: task-270-add-dirty-pdf-ocr-corpus-manifest-and-benchmark-report-schema
title: Add dirty PDF OCR corpus manifest and benchmark report schema
type: task
status: completed
priority: high
created: '2026-04-27'
last_updated: '2026-04-29'
related:
  - docs/backlog/epics/epic-06-long-pdf-conversion-reliability-progress-and-throughput-scaling.md
  - docs/backlog/stories/story-39-harden-and-align-pdf-ocr-path-with-dirty-real-data-performance-gate.md
  - docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md
  - docs/backlog/tasks/task-76-harden-hemma-deploy-parity-and-live-verification-workflow.md
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py
  - scripts/sir_convert_a_lot/benchmarking/dirty_pdf_corpus.py
  - scripts/sir_convert_a_lot/benchmarking/story20_http_profile.py
  - scripts/sir_convert_a_lot/benchmarking/story20_profile_runner.py
  - scripts/sir_convert_a_lot/benchmarking/story20_profiles.py
  - scripts/sir_convert_a_lot/benchmarking/story20_runtime_parity.py
  - scripts/sir_convert_a_lot/benchmarking/story20_throughput_cli.py
  - scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py
  - tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py
  - tests/sir_convert_a_lot/test_task270_dirty_pdf_ocr_corpus_schema.py
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

## Implementation Notes

- The manifest schema version is `dirty_pdf_ocr_corpus_manifest_v1`.
- The Task 74 dirty-corpus report extension schema version is
  `dirty_pdf_ocr_benchmark_report_extension_v1`.
- Manifest rows are metadata-only and include:
  - `source_id`,
  - `source_sha256`,
  - `page_count`,
  - `dirty_data_classes`,
  - `expected_ocr_languages`,
  - `privacy_state`,
  - `safe_excerpts_may_be_reported`.
- Forbidden manifest fields include local/private path fields such as
  `source_pdf_path`, `source_path`, `local_path`, `absolute_path`, `pdf_path`,
  and `file_path`.
- Manifest validation is schema-only. It never satisfies the dirty real-data
  gate by itself.
- The local generated scanned corpus remains harness smoke/regression input
  only. It is intentionally synthetic and cannot satisfy the real-data
  acceptance gate.
- Local in-process benchmark execution is command-surface smoke/regression only.
  Task 74/Story 39 acceptance benchmark evidence must run against the
  production service on Hemma and must use the governed Hemma command surface
  after Task 76 parity proof.
- Dirty-corpus benchmark evidence requires both `--dirty-corpus-manifest` and
  `--dirty-corpus-source-root`; the runner hashes private PDF bytes, matches
  them against manifest `source_sha256` values, verifies page counts, copies
  only sanitized `source_id.pdf` filenames into the execution corpus, and only
  then marks `source_hashes_verified=true` and
  `real_data_gate_satisfied=true`.
- Reportable dirty-corpus summaries must never include the operator-supplied
  manifest path, private source root, or private PDF filenames.
- Smoke assertions and stdout are schema/safety-only. They must not assert or
  print local or Hemma performance numbers such as p50/p90, latency,
  pages-per-minute, throughput, or improvement percentages.
- Hemma runner stdout is limited to artifact locations and safety/parity status;
  performance conclusions such as recommended profile, p50 improvement, and
  target pass/fail belong only in governed JSON/Markdown benchmark artifacts.
- Dirty-corpus benchmark runs fail closed before corpus generation when any
  resolved profile leaves Task 74's safe 2-worker boundary or matches the
  removed 4-worker OOM profile family.
- Operators can validate a metadata-only manifest without private PDFs via:
  `pdm run benchmark:task-270-validate-dirty-corpus-manifest --manifest <manifest.json>`.

## Deliverables

- [x] Dirty-corpus manifest schema.
- [x] Report schema extension for dirty-corpus evidence.
- [x] Validation tests for manifest/report parsing without private PDFs.
- [x] Runbook/docs update showing where private corpus files live and what may
  be committed.

## Acceptance Criteria

- [x] A developer/operator can validate a manifest locally without access to the
  private source PDFs, but that validation is schema-only and does not satisfy
  the real-data gate.
- [x] Reports generated from the manifest cannot omit Task 76 parity fields,
  profile safety classification, OCR metadata summary, or failure taxonomy.
- [x] The report schema extends Task 74 outputs under
  `build/benchmarks/story-20/` or a governed successor path.
- [x] The schema rejects or marks unsafe any profile outside Task 74's current
  safe matrix, especially the removed 4-worker profile that caused ROCm HIP OOM.
- [x] No private PDFs, local `.env` files, or PII excerpts are committed.
- [x] Synthetic fixtures remain test inputs only and cannot satisfy the
  real-data acceptance gate.
- [x] Dirty-corpus benchmark evidence cannot be generated from manifest
  metadata alone; executed PDF bytes must be hash-bound to manifest entries.
- [x] Smoke assertions and command stdout exclude performance/throughput
  metrics; accepted performance evidence belongs only in governed production
  Hemma benchmark artifacts.

## Entry Points

- `scripts/sir_convert_a_lot/benchmark_story20_throughput_report.py`
- `scripts/sir_convert_a_lot/benchmarking/dirty_pdf_corpus.py`
- `scripts/sir_convert_a_lot/benchmarking/story20_profile_runner.py`
- `scripts/sir_convert_a_lot/benchmarking/story20_http_profile.py`
- `scripts/sir_convert_a_lot/benchmarking/story20_profiles.py`
- `scripts/sir_convert_a_lot/benchmarking/story20_throughput_report.py`
- `tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py`
- `tests/sir_convert_a_lot/test_task270_dirty_pdf_ocr_corpus_schema.py`
- `docs/backlog/tasks/task-74-run-throughput-benchmark-and-publish-performance-tuning-report.md`
- `docs/runbooks/runbook-hemma-devops-and-gpu.md`

## Test Requirements

- [x] Manifest schema tests with synthetic metadata-only fixtures.
- [x] Report schema tests proving Task 76 parity and safe-profile fields are
  required.
- [x] Privacy test or docs check proving source PDF paths are not treated as
  commit-ready artifacts.
- [x] Regression test proving manifest-only dirty-corpus benchmark attempts
  fail closed before synthetic corpus output can masquerade as real data.
- [x] Regression test proving verified private source PDFs are copied under
  sanitized `source_id.pdf` names and reportable output omits private paths.
- [x] Regression test proving Hemma runner stdout excludes performance
  conclusions while still printing artifact locations and safety/parity status.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run pytest-root tests/sir_convert_a_lot/test_benchmark_story20_throughput_report.py tests/sir_convert_a_lot/test_task270_dirty_pdf_ocr_corpus_schema.py tests/sir_convert_a_lot/test_run_task74_hemma_benchmark.py -q`
  (pass)
- `pdm run typecheck-all` (pass: `Success: no issues found in 584 source files`)
- `pdm run docs-sync` (pass)
- `pdm run docs-validate` (pass: `Validated 334 backlog files`, `docs=387 rules=11`)
- `pdm run skills-validate` (pass)
- `pdm run handoff-validate` (pass)
- `git diff --check` (pass)

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
