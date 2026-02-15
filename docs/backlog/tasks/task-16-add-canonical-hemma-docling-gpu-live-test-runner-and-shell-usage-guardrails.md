---
id: task-16-add-canonical-hemma-docling-gpu-live-test-runner-and-shell-usage-guardrails
title: add canonical hemma docling gpu live-test runner and shell-usage guardrails
type: task
status: completed
priority: high
created: '2026-02-15'
last_updated: '2026-02-15'
related:
  - docs/runbooks/runbook-hemma-devops-and-gpu.md
  - docs/backlog/tasks/task-13-enforce-hemma-gpu-runtime-compliance-gate-and-rocm-verification.md
  - docs/backlog/tasks/task-14-enforce-global-docling-gpu-only-invariant-and-remove-cpu-execution-paths.md
labels:
  - hemma
  - gpu
  - devops
  - guardrails
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Provide a canonical, committed live-run command for real Hemma Docling+GPU validation and harden
agent guardrails against fragile inline `run-hemma --shell` payloads.

## PR Scope

- Add a typed Python live-runner module for real corpus execution on Hemma with strict Docling
  GPU-required settings and deterministic output artifacts.
- Add a PDM command surface for this runner.
- Add focused tests for critical parsing/safety logic (GPU utilization extraction).
- Harden AGENTS policy in this repo and HuleEdu repo to prohibit ad hoc multiline inline shell
  payloads for remote workflows.

## Deliverables

- [x] Canonical live-runner command exists and is executable via `run-hemma --` argv mode.
- [x] Output summary captures backend/acceleration invariants and per-file result metadata.
- [x] GPU utilization parsing is tested with representative `rocm-smi` output.
- [x] AGENTS guidance tightened with explicit anti-pattern prohibition.

## Acceptance Criteria

- [x] Live runner enforces `backend_strategy=docling` + `acceleration_policy=gpu_required`.
- [x] Successful run summary flags any non-Docling/non-cuda metadata as mismatch.
- [x] No dependence on ad hoc inline heredoc/python blobs through `run-hemma --shell` for routine
  live-run execution.
- [x] Focused tests and docs validators pass.

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Validation Evidence

- `pdm run run-local-pdm format-all`
- `pdm run run-local-pdm lint-fix`
- `pdm run run-local-pdm typecheck-all`
- `pdm run run-local-pdm pytest-root tests/sir_convert_a_lot/test_live_docling_gpu_quality.py tests/sir_convert_a_lot/test_run_hemma_wrapper.py -q`
- `pdm run run-local-pdm validate-tasks`
- `pdm run run-local-pdm validate-docs`
- `pdm run run-local-pdm index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
