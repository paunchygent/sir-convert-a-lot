---
id: task-181-add-real-in-training-held-out-eval-loop-to-task-101-qwen-training
title: Add real in-training held-out eval loop to Qwen training
type: task
status: in_progress
priority: critical
created: '2026-03-15'
last_updated: '2026-03-15'
related:
  - docs/backlog/stories/story-26-drive-task-101-qwen-training-observability-throughput-and-gpu-saturation-on-hemma.md
  - docs/backlog/tasks/task-101-run-the-hemma-pilot-full-finetune-for-swedish-qwen3-tts-language-expansion.md
  - docs/backlog/tasks/task-143-harden-qwen-pilot-training-eval-and-bundle-preflight-contracts.md
  - docs/backlog/tasks/task-179-bound-the-rebuilt-bundle-task-101-non-finite-loss-window-before-retrying-saturation-proof.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - eval
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Turn the current Task 101 held-out eval contract from metadata-only truth into a
real in-training evaluation loop that runs against `swedish_checkpoint_dev`
inside the canonical detached Hemma Qwen lane.

## Why This Exists

Task 101 and Task 143 already require the held-out eval manifest to exist and be
carried through launch, status, and report metadata. That contract is now too
weak for the real pilot lane:

- the current trainer still only builds a train dataloader,
- no periodic held-out pass runs during training,
- no eval loss is available for checkpoint review,
- and operators would otherwise be asked to spend multi-hour training time
  without any in-run convergence signal.

This task upgrades that contract to a real held-out loop instead of a demo or a
reporting-only placeholder.

## PR Scope

- Extend the patched Qwen training runtime so it prepares a real eval dataset
  and dataloader from `--eval-jsonl`.
- Add a real in-training eval phase at explicit bounded intervals, using
  `model.eval()` and `torch.no_grad()` rather than fake post-hoc reporting.
- Compute and persist held-out eval loss during training.
- Mirror eval truth into live heartbeats, tracker payloads, terminal
  `status.json`, and `report.json`.
- Keep the first slice bounded to held-out loss and eval cadence truth; do not
  expand this task into generation-time MOS-style scoring or a broad metric
  suite.

## Non-Goals

- Do not invent a fake eval loop in reporting while the trainer stays train-only.
- Do not redesign the Qwen training objective in this task.
- Do not add broad speech-quality generation metrics in the same slice.
- Do not couple this task to GPU-saturation tuning; eval must be truthful even
  if the stable lane remains under-saturated.

## Ordered Execution

1. Update Task 181, Story 26, and the runbook so the docs contract explicitly
   requires real in-training held-out evaluation.
1. Add eval runtime configuration, eval dataloader preparation, and eval phase
   support to the patched Qwen trainer path.
1. Persist eval truth into trackers, live progress, status, and terminal
   reports.
1. Add focused regression coverage for eval cadence, eval reporting, and
   completed/failed status truth.
1. Run local quality gates and docs gates before any Hemma relaunch.

## Deliverables

- [ ] Real eval dataset and dataloader preparation from `--eval-jsonl`.
- [ ] Real periodic held-out eval pass inside the canonical training loop.
- [ ] Live and terminal artifacts that persist eval loss truth.
- [ ] Focused tests for eval cadence, eval metrics, and report/status payloads.
- [ ] Updated story/runbook/task docs that no longer describe the lane as
  train-only.

## Acceptance Criteria

- [ ] The patched Qwen trainer loads the held-out eval manifest into a real eval
  dataset and dataloader instead of carrying it as metadata only.
- [ ] The live training loop runs held-out eval at an explicit bounded cadence
  during training, and performs a terminal catch-up eval when the latest
  completed optimizer step has not yet been evaluated.
- [ ] Eval runs use `model.eval()` and `torch.no_grad()` and restore
  `model.train()` afterwards.
- [ ] Live status heartbeats expose the eval phase and the latest held-out loss.
- [ ] Tracker artifacts include held-out eval loss keyed by optimizer step.
- [ ] Completed `report.json` and `status.json` persist latest and best eval
  loss truth and no longer claim
  `upstream_trainer_uses_eval_manifest=False` for this lane.
- [ ] Focused tests prove that eval is real, periodic, and machine-readable
  without requiring a long Hemma run.

## Validation

- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
