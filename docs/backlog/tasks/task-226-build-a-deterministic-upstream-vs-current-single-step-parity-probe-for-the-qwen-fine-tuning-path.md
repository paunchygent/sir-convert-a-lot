---
id: task-226-build-a-deterministic-upstream-vs-current-single-step-parity-probe-for-the-qwen-fine-tuning-path
title: Build a deterministic upstream-vs-current single-step parity probe for the Qwen fine-tuning path
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-225-define-the-exact-step-1-instability-parity-contract-for-the-recreated-historical-control-failure-family.md
  - docs/backlog/tasks/task-221-recreate-the-documented-historical-task-101-control-contract-before-judging-the-t206-only-fresh-start-lane.md
  - docs/backlog/tasks/task-193-restore-the-upstream-qwen-fine-tune-graph-and-add-clip-boundary-forensics.md
  - docs/reference/ref-task101-live-qwen-training-pipeline-analysis-2026-03-13.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - parity
  - probe
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Build one deterministic local probe that runs the exact `T225` failure-family
input through the current patched path and the intended upstream-compatible
path, then records the first meaningful divergence from batch assembly through
the optimizer boundary.

This is a mechanism task, not a bundle-stability search and not a governed
proof.

## PR Scope

- Implement or extend one committed local parity surface that can compare:
  - current patched trainer/runtime behavior
  - intended upstream-compatible fine-tuning behavior
- Reuse existing repo-owned Qwen tracing and bounded-probe surfaces where
  possible instead of adding a new long-running proof wrapper.
- Capture deterministic, comparable artifacts at the checkpoints defined in
  `T225`.
- Keep the probe narrow:
  - one exact failure family
  - one exact local output root
  - no detached Hemma proof
  - no recovery recipe sweep
  - no optimizer-regime search beyond what the parity contract requires
- Emit one artifact set that lets the repo answer:
  - do the two paths diverge before the first non-finite stage?
  - if yes, where exactly?
  - if not, what mechanism question remains for `T219`?

## Implementation Notes

- The committed local mechanism surface is now:
  - `pdm run qwen-story31-parity-probe run`
- The surface persists one compact local artifact set under:
  - `build/verification/qwen-story31-parity-probe/`
  - `current-path.json`
  - `intended-path.json`
  - `results.json`
  - `results.md`
- The current path reuses the real `execute_train_iteration` window.
- The intended path is a repo-owned reconstructed shared-forward /
  optimizer-boundary window for the same exact `T225` microbatch family.
- Live operator execution on Hemma is now also complete:
  - host-venv execution first failed as an invalid parity setup because
    `flash_attn` was unavailable outside the canonical image
  - the committed device-transfer fix in `555624e` then reran the probe inside
    the `sir-convert-a-lot-qwen-finetune-hemma:task100` image against the real
    historical bundle under
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-parity-probe/task226-20260317t224307Z`
  - that live run resolved with:
    - `first_divergence_checkpoint = null`
    - `first_divergence_classification = no_meaningful_divergence_found`
    - `recommended_next_step = return_to_t219_if_no_higher_priority_runtime_bug_is_found`
- This task therefore closes both the committed reusable surface and the live
  historical-bundle parity decision that returns Story 31 to `T219`.

## Deliverables

- [x] One deterministic parity probe exists as a committed local surface.
- [x] One output artifact set compares current vs intended upstream-compatible
  behavior checkpoint by checkpoint.
- [x] One first-divergence summary states whether the current implementation
  diverges before the first non-finite stage.
- [x] Operator docs can point to this probe as the required pre-`T219`
  mechanism check.

## Acceptance Criteria

- [x] The probe uses the exact failure-family contract from `T225`.
- [x] The probe records the same checkpoint families for both compared paths.
- [x] The output is deterministic enough to rerun locally without turning into
  a broad bundle experiment.
- [x] The output clearly distinguishes:
  - no meaningful divergence found
  - first divergence found while tensors are still finite
  - first divergence found at the non-finite boundary
- [x] The task does not unblock `T217`; it only informs whether `T219` or
  remediation should come next.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story31_parity_probe.py -q`
- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-story31-parity-probe --help`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
