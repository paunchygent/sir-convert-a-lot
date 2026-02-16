---
id: current-task
title: Current Task Log
type: task-log
status: active
priority: critical
created: '2026-02-11'
last_updated: '2026-02-16'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization.md
  - docs/backlog/tasks/task-26-docling-form-cluster-ordering-source-patch-with-deterministic-quality-gate-and-fallback.md
  - docs/reference/ref-docling-form-ordering-exam-pdf-2026-02-16.md
labels:
  - session-log
  - active-work
---

## Context

Active focus is Story 02-01 completion on ordering correctness for exam/form
PDFs with source-level Docling mitigation and deterministic fallback behavior.

- Task 25 is in progress:
  `docs/backlog/tasks/task-25-heavier-default-conversion-profile-and-exam-question-ordering-normalization.md`
- Task 26 is in progress:
  `docs/backlog/tasks/task-26-docling-form-cluster-ordering-source-patch-with-deterministic-quality-gate-and-fallback.md`

## Worklog

- 2026-02-16:

  - Implemented Task 26 local slice:
    - source-level Docling form ordering patch,
    - structural ordering quality gate,
    - deterministic layout-model fallback selection,
    - backend refactor to keep module size below guardrail.
  - Added focused tests:
    - `tests/sir_convert_a_lot/test_docling_ordering_fallback.py`
  - Local gates passed:
    - `pdm run format-all`
    - `pdm run lint-fix`
    - `pdm run typecheck-all`
    - `pdm run pytest-root tests/sir_convert_a_lot/test_docling_backend.py tests/sir_convert_a_lot/test_docling_ordering_fallback.py`
    - `pdm run validate-tasks`
    - `pdm run validate-docs`
    - `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
  - Hemma lane validation remains pending for Task 26 close-out.

- 2026-02-16:

  - Task 26 created and linked to reproducible bug report evidence:
    - `docs/reference/ref-docling-form-ordering-exam-pdf-2026-02-16.md`
  - Locked direction from isolation A/B:
    - `_sort_cells + _sort_clusters` required for Heron-class repair,
    - default `egret_large` requires quality-gated fallback for residual Q13 defect.

## Next Actions

- Execute Task 26 Hemma lane verification:
  - push latest revision,
  - pull/rebuild/restart on Hemma,
  - run target exam conversion and confirm quality-gate/fallback behavior.
- Update Task 26 with Hemma evidence and close validation checklist once
  operational proof is captured.
- Keep `current.md` as the concise long-term canonical log; keep
  `.agents/session/handoff.md` for between-session transient handoff only.
