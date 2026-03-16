---
id: task-196-make-task-101-gradient-accumulation-runtime-configurable-for-bounded-proof-runs
title: Make Task 101 gradient accumulation runtime-configurable for bounded proof runs
type: task
status: proposed
priority: high
created: '2026-03-16'
last_updated: '2026-03-16'
related:
  - docs/backlog/stories/story-29-counteract-task-101-codec-span-text-pad-instability-and-gate-the-next-clean-restart.md
  - docs/backlog/tasks/task-194-debug-the-task-101-pre-clip-text-embedding-gradient-failure-at-step-1405.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - accumulation
  - stability
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Replace the Task 101 hard-coded accumulation posture with a runtime-configurable
setting so bounded mitigation proofs can compare `gradient_accumulation_steps`
`4`, `2`, and `1` without code edits.

## PR Scope

- Add `--gradient-accumulation-steps` to the committed `qwen-train` control
  plane surfaces used by:
  - `launch`
  - `resume`
  - `capture-diagnostic-state`
  - `diagnose-non-finite`
- Keep `4` as the default value for the canonical lane.
- Treat `2` and `1` as first-class bounded-proof overrides.
- Surface the effective value in:
  - step semantics
  - status/report payloads
  - replay bundles
  - launch metadata
- Keep the change compatible with the exact-capture and bounded-replay surfaces
  already used for `1401`, `1406`, and `1417`.

## Deliverables

- [ ] One committed runtime override exists for `gradient_accumulation_steps`.
- [ ] Proof artifacts record the effective accumulation value.
- [ ] The training reference ledger records that reduced accumulation is the
  secondary ablation only after the structural mask-policy proof.

## Acceptance Criteria

- [ ] Focused parser/control-plane tests prove the override is accepted on all
  four committed training surfaces.
- [ ] Focused runtime/reporting tests prove the effective accumulation value is
  visible in machine-readable artifacts.
- [ ] Default behavior remains `4` when the override is omitted.

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
