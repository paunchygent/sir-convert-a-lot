---
type: task
id: TASK-SIRCON-05-03-12
title: Add standalone eval and scheduled train-stop-resume control for Qwen training
repository: sir-convert-a-lot
owners:
- kind: service
  id: sir-convert-a-lot
created: '2026-08-02'
status: in_progress
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SIRCON-05-03
task_kind: story
acceptance_criteria:
- "[x] `qwen-train eval` accepts an explicit checkpoint plus held-out eval\n  material\
  \ and runs a real eval pass with `model.eval()` and `torch.no_grad()`\n  inside\
  \ the governed training image."
- "[x] Standalone eval writes deterministic machine-readable artifacts that\n  expose\
  \ at least latest eval loss, checkpoint path, eval manifest path, and\n  bundle/reference-input\
  \ posture."
- "[x] The schedule runner can intentionally stop a detached training run,\n  launch\
  \ standalone eval against the resulting durable checkpoint, and resume\n  training\
  \ from that checkpoint afterwards."
- "[x] Epoch-aware schedule boundaries are computed from canonical\n  `dataloader_length`\
  \ and durable checkpoint metadata rather than inferred from\n  raw row counts alone."
- "[x] Focused tests prove the schedule runner chooses the correct next boundary\n\
  \  and wires train/eval/resume calls in order without needing a long Hemma run."
retired_ids:
- task-182-add-standalone-eval-and-scheduled-train-stop-resume-control-for-task-101-qwen-training
---

## Context

## Decision And Assumption Ledger

## Story Contract Slice

## Contract Inputs

## Plan

## Implementation Steps

## Proof

## Validation

## Stop Conditions

## Lessons Learned

## Notes

## Plan Document Review

## Implementation Review

## Historical Source Content

PR-sized execution unit; may be linked to a story or standalone.

### Objective

Add a real standalone `qwen-train eval` command plus an epoch-aware schedule
runner that can drive `train -> stop -> eval -> resume` from durable
checkpoints without forcing a full pilot-bundle rebuild before each held-out
check.

### PR Scope

- Add a public `qwen-train eval` surface that loads one Task 101 checkpoint,
  runs a real held-out eval pass against explicit eval material, and persists
  machine-readable eval artifacts.
- Reuse the canonical Qwen training image and checkpoint contract rather than
  inventing a host-only or reporting-only eval path.
- Add one schedule runner that orchestrates detached training windows together
  with intentional stop, standalone eval, and resume.
- Make the schedule runner epoch-aware by reading canonical dataloader-length
  truth and durable checkpoint metadata instead of guessing epoch boundaries
  from row counts alone.
- Keep the first slice bounded to held-out loss and schedule control truth; do
  not expand into broad generation metrics or speculative throughput tuning.

### Non-Goals

- Do not require a full pilot-bundle rebuild just to run held-out eval on an
  existing checkpoint.
- Do not add a fake shell-script scheduler that depends on operator memory and
  produces no machine-readable evidence.
- Do not redesign the Qwen training objective in this task.
- Do not collapse the held-out eval contract back into train-manifest eval.

### Ordered Execution

1. Open the task/docs slice for standalone eval and scheduled control.
1. Add the public `qwen-train eval` surface and in-container standalone eval
   implementation.
1. Add schedule-runner orchestration that can launch or resume training,
   request a graceful stop at the next planned boundary, run standalone eval,
   and resume again.
1. Persist eval and schedule truth into deterministic status/report artifacts.
1. Add focused regression coverage for CLI parsing, checkpoint/eval path
   validation, epoch-boundary math, and schedule orchestration.
1. Run local quality gates, docs gates, and one bounded Hemma proof before any
   longer pilot spend.

### Deliverables

- [x] Public `qwen-train eval` command with deterministic artifact output.
- [x] In-container standalone eval entrypoint that restores a checkpoint and
  runs held-out loss truthfully.
- [x] Epoch-aware schedule runner for `train -> stop -> eval -> resume`.
- [x] Focused tests for standalone eval and schedule control.
- [x] Updated task/story/runbook docs describing the new control surface.

### Acceptance Criteria

- [x] `qwen-train eval` accepts an explicit checkpoint plus held-out eval
  material and runs a real eval pass with `model.eval()` and `torch.no_grad()`
  inside the governed training image.
- [x] Standalone eval writes deterministic machine-readable artifacts that
  expose at least latest eval loss, checkpoint path, eval manifest path, and
  bundle/reference-input posture.
- [x] The schedule runner can intentionally stop a detached training run,
  launch standalone eval against the resulting durable checkpoint, and resume
  training from that checkpoint afterwards.
- [x] Epoch-aware schedule boundaries are computed from canonical
  `dataloader_length` and durable checkpoint metadata rather than inferred from
  raw row counts alone.
- [x] Focused tests prove the schedule runner chooses the correct next boundary
  and wires train/eval/resume calls in order without needing a long Hemma run.

### Validation

- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run typecheck-all`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_eval_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_schedule_runner.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py -q`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

### Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated

### Follow-on Remediation

- [x] Remediate post-review schedule pointer truth, schedule-path fail-closed
  validation, and retention-`3` proof coverage in
  `docs/backlog/tasks/task-184-remediate-task-101-qwen-schedule-pointer-truth-schedule-path-fail-closed-validation-and-retention-3-checkpoint-proof-coverage.md`.

### Notes

- Local implementation and focused validation are complete.
- Hemma now has scratch-root held-out eval manifests that can drive the new
  standalone eval surface without forcing a full pilot-bundle rebuild.
- Remote standalone eval smoke passed on Hemma against the stable balanced
  launch root
  `/srv/scratch/sir-convert-a-lot/build/verification/task-175-throughput-proof-20260314d-balanced/20260314T195507Z`
  using held-out eval material from
  `/srv/scratch/sir-convert-a-lot/build/verification/task-152-task101-finalization-benchmark-20260312j/direct-encode-chunk64-span1/manifests/swedish_checkpoint_dev.prepared.jsonl`.
- The passing standalone eval wrote canonical machine-readable artifacts under
  `/srv/scratch/sir-convert-a-lot/build/verification/task-175-throughput-proof-20260314d-balanced/20260314T195507Z/evals/eval-20260315T082624Z`
  with `status=completed`, `eval_dataloader_length=3`, `eval_batches_completed=3`,
  and `eval_loss=6.681333859761556`.
- The first remote schedule smoke against a pre-Task-182 source launch failed
  closed as designed because `dataloader_length` was absent from the older
  launch artifacts.
- A second remote schedule smoke minted a fresh Task 182-compliant source
  launch on the compact Task 152 benchmark bundle and populated
  `dataloader_length=92`, `eval_dataloader_length=3`, and real in-training eval
  fields, but exposed a practical blocker: durable checkpoint finalization is
  extremely slow on Hemma, with per-step checkpoint materialization producing
  multi-gigabyte artifacts and keeping the launch in `checkpoint-save` long
  enough that an end-to-end schedule cycle is still pending.
