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
  - docs/backlog/tasks/task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning.md
  - docs/reference/ref-docling-form-ordering-exam-pdf-2026-02-16.md
  - docs/reference/ref-dockerized-hemma-gpu-passthrough-gap-2026-02-16.md
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
- Task 27 is completed:
  `docs/backlog/tasks/task-27-dockerized-hemma-rocm-gpu-passthrough-and-runtime-wheel-pinning.md`

## Worklog

- 2026-02-16:

  - Task 27 completed with docker-lane GPU runtime compliance on Hemma.
  - Delivered docker lane runtime fixes:
    - pinned ROCm wheel installation in image build (`2.10.0+rocm7.1` stack),
    - ROCm device passthrough (`/dev/kfd`, `/dev/dri`),
    - verifier lane support (`host|docker`) and readiness-check reliability fixes,
    - container runtime fixes (`ensurepip`, required `video`/`render` groups,
      Docling shared runtime libs including `libxcb1`).
  - Hemma evidence:
    - in-container probe: `torch==2.10.0+rocm7.1`, HIP present, GPU available,
    - `8085/8086` `readyz` returned `ready=true` with revision match,
    - docker-lane verify passed:
      - `SIR_CONVERT_A_LOT_VERIFY_LANE=docker pdm run run-local-pdm hemma-verify-gpu-runtime`
      - live result: `acceleration_used="cuda"`, `gpu_busy_peak=99`.
  - Compose build topology optimized to one shared runtime image for prod/eval
    runtime overlays, removing duplicate image builds by default.

- 2026-02-16:

  - Task 27 created to close docker-lane GPU gap on Hemma.
  - Baseline recorded:
    - dockerized `8085/8086` lane is revision-ready but not GPU-ready,
    - container probe showed `torch==2.10.0+cu128`, `is_available=false`,
    - `/dev/kfd` and `/dev/dri` missing in container.
  - Reference:
    - `docs/reference/ref-dockerized-hemma-gpu-passthrough-gap-2026-02-16.md`

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
  - capture output evidence for source-order fallback behavior and close checklist.
