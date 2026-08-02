---
type: task
id: TASK-SIRCON-05-03-11
title: Add real in-training held-out eval loop to Qwen training
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
- "[ ] The patched Qwen trainer loads the held-out eval manifest into a real eval\n\
  \  dataset and dataloader instead of carrying it as metadata only."
- "[ ] The live training loop runs held-out eval at an explicit bounded cadence\n\
  \  during training, and performs a terminal catch-up eval when the latest\n  completed\
  \ optimizer step has not yet been evaluated."
- "[ ] Eval runs use `model.eval()` and `torch.no_grad()` and restore\n  `model.train()`\
  \ afterwards."
- '[ ] Live status heartbeats expose the eval phase and the latest held-out loss.'
- '[ ] Tracker artifacts include held-out eval loss keyed by optimizer step.'
- "[ ] Completed `report.json` and `status.json` persist latest and best eval\n  loss\
  \ truth and no longer claim\n  `upstream_trainer_uses_eval_manifest=False` for this\
  \ lane."
- "[ ] Focused tests prove that eval is real, periodic, and machine-readable\n  without\
  \ requiring a long Hemma run."
retired_ids:
- task-181-add-real-in-training-held-out-eval-loop-to-task-101-qwen-training
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

### Context

State the bounded implementation or proof need and the parent story behavior it
supports.

### Decision And Assumption Ledger

Every material implementation choice must already be closed by an accepted
source before scaffolding this task.

| ID  | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | ---- | ------ | ------------------- | ----------------------- | ------ |

### Story Contract Slice

Define the single-responsibility implementation or proof slice derived from the
parent story. Name the exact surfaces this task may change.

### Contract Inputs

- Accepted ADRs, references, runbooks, reviews, or prior backlog contracts that
  constrain this task.

### Plan

State the smallest implementation approach that satisfies the story slice and
acceptance criteria.

### Implementation Steps

List ordered steps small enough to execute and verify without inventing scope.

### Proof

- Selected proof mode and applicability basis.
- Focused pre-change command and expected result when required.
- The same focused post-change command and expected result.

### Validation

List the exact focused and repository gates required before closeout and retain
concise results after they run.

### Stop Conditions

- Missing authority, open material decision, scope expansion, or failed required
  proof that requires returning to planning.

### Lessons Learned

Retain only reusable findings or explicitly identified failed approaches.

### Notes

Record current task-local context that does not belong in the contract, ledger,
proof, or lessons learned.

### Plan Document Review

Record findings, evidence, permitted next step, and residual risk. The
`readiness_review` frontmatter mapping is the machine authority for gate status.

### Implementation Review

Record supplied proof, findings, permitted next step, validation not run, and
residual risk. The `closeout_review` frontmatter mapping is the machine authority
for gate status and approval evidence.

PR-sized execution unit; may be linked to a story or standalone.
### Objective
Turn the current Task 101 held-out eval contract from metadata-only truth into a real in-training evaluation loop that runs against `swedish_checkpoint_dev` inside the canonical detached Hemma Qwen lane.
### Why This Exists
Task 101 and Task 143 already require the held-out eval manifest to exist and be carried through launch, status, and report metadata. That contract is now too weak for the real pilot lane:
- the current trainer still only builds a train dataloader,
- no periodic held-out pass runs during training,
- no eval loss is available for checkpoint review,
- and operators would otherwise be asked to spend multi-hour training time
without any in-run convergence signal.
This task upgrades that contract to a real held-out loop instead of a demo or a reporting-only placeholder.
### PR Scope
- Extend the patched Qwen training runtime so it prepares a real eval dataset
and dataloader from `--eval-jsonl`.
- Add a real in-training eval phase at explicit bounded intervals, using
`model.eval()` and `torch.no_grad()` rather than fake post-hoc reporting.
- Compute and persist held-out eval loss during training.
- Mirror eval truth into live heartbeats, tracker payloads, terminal
`status.json`, and `report.json`.
- Keep the first slice bounded to held-out loss and eval cadence truth; do not
expand this task into generation-time MOS-style scoring or a broad metric suite.
### Non-Goals
- Do not invent a fake eval loop in reporting while the trainer stays train-only.
- Do not redesign the Qwen training objective in this task.
- Do not add broad speech-quality generation metrics in the same slice.
- Do not couple this task to GPU-saturation tuning; eval must be truthful even
if the stable lane remains under-saturated.
### Ordered Execution
1. Update Task 181, Story 26, and the runbook so the docs contract explicitly requires real in-training held-out evaluation. 1. Add eval runtime configuration, eval dataloader preparation, and eval phase support to the patched Qwen trainer path. 1. Persist eval truth into trackers, live progress, status, and terminal reports. 1. Add focused regression coverage for eval cadence, eval reporting, and completed/failed status truth. 1. Run local quality gates and docs gates before any Hemma relaunch.
### Deliverables
- [ ] Real eval dataset and dataloader preparation from `--eval-jsonl`.
- [ ] Real periodic held-out eval pass inside the canonical training loop.
- [ ] Live and terminal artifacts that persist eval loss truth.
- [ ] Focused tests for eval cadence, eval metrics, and report/status payloads.
- [ ] Updated story/runbook/task docs that no longer describe the lane as
train-only.
### Acceptance Criteria
- [ ] The patched Qwen trainer loads the held-out eval manifest into a real eval
dataset and dataloader instead of carrying it as metadata only.
- [ ] The live training loop runs held-out eval at an explicit bounded cadence
during training, and performs a terminal catch-up eval when the latest completed optimizer step has not yet been evaluated.
- [ ] Eval runs use `model.eval()` and `torch.no_grad()` and restore
`model.train()` afterwards.
- [ ] Live status heartbeats expose the eval phase and the latest held-out loss.
- [ ] Tracker artifacts include held-out eval loss keyed by optimizer step.
- [ ] Completed `report.json` and `status.json` persist latest and best eval
loss truth and no longer claim `upstream_trainer_uses_eval_manifest=False` for this lane.
- [ ] Focused tests prove that eval is real, periodic, and machine-readable
without requiring a long Hemma run.
### Validation
- [ ] `pdm run format-all`
- [ ] `pdm run lint-fix`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_train_loop.py tests/sir_convert_a_lot/ml/qwen/training/test_reporting.py tests/sir_convert_a_lot/ml/qwen/training/test_trainer.py tests/sir_convert_a_lot/ml/qwen/training/test_orchestrator.py -q`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
### Checklist
- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
