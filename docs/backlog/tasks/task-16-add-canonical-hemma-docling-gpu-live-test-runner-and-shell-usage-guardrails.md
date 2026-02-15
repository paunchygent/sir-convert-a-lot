---
id: task-16-add-canonical-hemma-docling-gpu-live-test-runner-and-shell-usage-guardrails
title: add canonical hemma docling gpu live-test runner and shell-usage guardrails
type: task
status: in_progress
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

- [ ] Canonical live-runner command exists and is executable via `run-hemma --` argv mode.
- [ ] Output summary captures backend/acceleration invariants and per-file result metadata.
- [ ] GPU utilization parsing is tested with representative `rocm-smi` output.
- [ ] AGENTS guidance tightened in both repos with explicit anti-pattern prohibition.

## Acceptance Criteria

- [ ] Live runner enforces `backend_strategy=docling` + `acceleration_policy=gpu_required`.
- [ ] Successful run summary flags any non-Docling/non-cuda metadata as mismatch.
- [ ] No dependence on ad hoc inline heredoc/python blobs through `run-hemma --shell` for routine
  live-run execution.
- [ ] Focused tests and docs validators pass.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
