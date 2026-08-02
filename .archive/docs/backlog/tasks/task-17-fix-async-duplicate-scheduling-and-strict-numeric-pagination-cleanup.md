---
id: task-17-fix-async-duplicate-scheduling-and-strict-numeric-pagination-cleanup
title: Async duplicate scheduling and strict numeric pagination cleanup
type: task
status: completed
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
labels:
  - runtime
  - normalization
  - bugfix
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Close two reliability gaps found during live Hemma validation:

1. prevent duplicate async execution start for the same active `job_id`,
1. strip long standalone numeric pagination blocks that use 4+ digit numbering.

## PR Scope

- Update runtime async scheduler guard:
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
- Expand strict normalizer pagination regex coverage:
  - `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py`
- Add focused regression coverage:
  - `tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py`
  - `tests/sir_convert_a_lot/test_markdown_normalizer.py`

## Deliverables

- [x] Duplicate `run_job_async(job_id)` calls do not launch parallel threads for the same active job
- [x] Strict normalizer removes long standalone pagination runs with 4-digit numbers
- [x] Targeted tests added and passing

## Acceptance Criteria

- [x] Runtime dedupe behavior is deterministic and test-covered
- [x] Strict normalization removes long numeric blocks while preserving short numeric lines
- [x] No regressions in targeted runtime/normalizer test suites

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py::test_run_job_async_ignores_duplicate_active_job_id tests/sir_convert_a_lot/test_markdown_normalizer.py::test_strict_mode_removes_long_standalone_four_digit_number_blocks tests/sir_convert_a_lot/test_markdown_normalizer.py::test_strict_mode_preserves_short_numeric_lines -q`
