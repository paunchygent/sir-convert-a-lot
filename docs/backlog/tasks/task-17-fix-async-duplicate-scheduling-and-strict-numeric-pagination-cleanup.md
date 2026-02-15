---
id: 'task-17-fix-async-duplicate-scheduling-and-strict-numeric-pagination-cleanup'
title: 'Async duplicate scheduling and strict numeric pagination cleanup'
type: 'task'
status: 'in_progress'
priority: 'high'
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
2. strip long standalone numeric pagination blocks that use 4+ digit numbering.

## PR Scope

- Update runtime async scheduler guard:
  - `scripts/sir_convert_a_lot/infrastructure/runtime_engine.py`
- Expand strict normalizer pagination regex coverage:
  - `scripts/sir_convert_a_lot/infrastructure/markdown_normalizer.py`
- Add focused regression coverage:
  - `tests/sir_convert_a_lot/test_runtime_engine_conversion_failures.py`
  - `tests/sir_convert_a_lot/test_markdown_normalizer.py`

## Deliverables

- [ ] Duplicate `run_job_async(job_id)` calls do not launch parallel threads for the same active job
- [ ] Strict normalizer removes long standalone pagination runs with 4-digit numbers
- [ ] Targeted tests added and passing

## Acceptance Criteria

- [ ] Runtime dedupe behavior is deterministic and test-covered
- [ ] Strict normalization removes long numeric blocks while preserving short numeric lines
- [ ] No regressions in targeted runtime/normalizer test suites

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
