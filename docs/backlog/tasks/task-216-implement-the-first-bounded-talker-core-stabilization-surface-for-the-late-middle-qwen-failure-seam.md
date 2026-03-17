---
id: task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam
title: Implement the first bounded talker-core stabilization surface for the late-middle Qwen failure seam
type: task
status: done
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - stabilization
  - talker-core
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Implement the first bounded talker-core stabilization surface that directly
targets the late-middle failure seam exposed by `T214`, so the repo can test a
working fresh-start training recipe instead of collecting another proof-only
RCA slice.

This task is the implementation owner for the lightweight Story 31
exploration vehicle, not a one-off proof wrapper.

## PR Scope

- Treat `T214` as fixed truth:
  - pair `main_loss` / `combined_loss` first break at
    `talker_core.layer_16.mlp.gated_product`
  - pair `sub_talker_loss` first breaks at `talker_core.layer_15.output`
  - replay and text-span leakage are no longer the leading explanations
- Preserve the current clean baseline:
  - no-projection fine-tune graph
  - semantic-only text assembly from `T207-T209`
  - same canonical frozen Task 101 bundle contract
- Build one lightweight Story 31 exploration surface that can run short matrix
  cells quickly against the real failing family.
- Add one explicit bounded stabilization surface in that exploration lane that
  is local to the late-middle talker-core seam and can be enabled without
  rewriting the whole decoder contract.
- Reuse existing surfaces instead of building a new proof stack:
  - mini-bundle truth from `story30_freshstart_bundle.py` and
    `story30_backward_lineage_bundle.py`
  - forward/backward kernel from `backward_lineage_probe.py`
  - hook plumbing from `story30_backward_lineage_hooks.py`
  - layer targeting from `sft_12hz_talker_core_trace.py`
- Emit one compact machine-readable results table per matrix run under a single
  output root, not one full proof package per experiment.
- Keep the first intervention honest:
  - do not reframe it as an optimizer-only cushioning change
  - do not reopen replay rescue work
  - do not mix Candidate `3` into this first surface
- Expose the new stabilization posture through committed runtime/config
  metadata so local gates and the later promoted proof can record it exactly.

## Deliverables

- [x] One committed Story 31 exploration surface exists for rapid local or
  short Hemma-shared experiments.
- [x] One committed first bounded talker-core stabilization surface exists for
  the late-middle seam highlighted by `T214`.
- [x] One compact results artifact format exists for the experiment matrix.
- [x] One operator-facing doc update explains the exact first stabilization
  posture and why the new surface is faster than proof-per-slice iteration.

## Acceptance Criteria

- [x] The change preserves semantic-only text assembly and the no-projection
  training contract.
- [x] The intervention is bounded to the late-middle talker-core seam rather
  than broad optimizer or dataset churn.
- [x] The exploration surface can vary branch, row selection, and one bounded
  stabilization variant without minting a new proof wrapper for each cell.
- [x] The resulting surface is usable by a local finiteness gate and a later
  short fresh-start Hemma proof without ad hoc shell logic.
- [x] The task does not claim restart readiness on its own.

## Validation

- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

## Outcome

- Added the first bounded talker-core stabilization surface in
  `sft_12hz_talker_core_stabilization.py` with the initial Story 31 variants:
  `off`, `layer16_gated_fp32`, and `layer16_gated_fp32_clamp_1e4`.
- Wired the shared forward path to apply the stabilization patch during the
  talker forward pass without changing the semantic-only text contract or the
  no-projection graph.
- Added the lightweight Story 31 exploration surface:
  `pdm run qwen-story31-stability-lab run`
- The lab reuses the exact failing-row mini-bundle plus the existing
  backward-lineage probe and writes one compact matrix artifact set under a
  single output root:
  - `results.json`
  - `results.md`
  - `variant-reports/<variant>.json`
- Operator guidance for the new exploration surface now lives in the Qwen
  runbook and repo finetuning skill so short Hemma-shared experiments do not
  need ad hoc shell packaging.
