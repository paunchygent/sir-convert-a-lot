---
id: task-14-enforce-global-docling-gpu-only-invariant-and-remove-cpu-execution-paths
title: Enforce global Docling GPU-only invariant and remove CPU execution paths
type: task
status: completed
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/backlog/stories/story-02-01-hemma-offloaded-pdf-to-markdown-conversion-pipeline.md
  - docs/backlog/tasks/task-12-scientific-paper-workload-evidence-harness-hemma-tunnel-acceptance-report-10-10-corpus.md
  - docs/backlog/tasks/task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification.md
labels:
  - docling
  - gpu
  - governance
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Guarantee a strict global invariant: Docling conversions never execute on CPU
in any code path (service runtime, direct backend calls, and tests).

## PR Scope

- Enforce GPU runtime requirement directly in Docling backend acceleration
  resolution.
- Align runtime validation so Docling GPU-runtime absence fails deterministically.
- Update tests and helper fixtures to stop relying on Docling CPU execution.
- Preserve PyMuPDF CPU behavior and existing API envelope shapes.

## Deliverables

- [x] Docling backend rejects CPU execution unconditionally
- [x] Runtime policy checks enforce Docling GPU-runtime availability consistently
- [x] Tests updated to model GPU availability explicitly
- [x] Converter docs reflect global Docling GPU-only invariant

## Acceptance Criteria

- [x] No successful Docling conversion can occur when GPU runtime probe is unavailable
- [x] Direct backend calls with `gpu_available=False` fail with `BackendGpuUnavailableError`
- [x] API/runtime error mapping remains deterministic (`503 gpu_not_available`)
- [x] Targeted test suite passes without Docling CPU fallback assumptions

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
