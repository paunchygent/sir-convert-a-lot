---
id: task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly
title: Run the first governed Hemma proof for Candidate 1 semantic-only assembly
type: task
status: completed
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-206-prove-the-true-task-101-text-token-span-contract-and-set-the-final-post-fix-restart-rule.md
  - docs/backlog/tasks/task-207-implement-semantic-only-batch-contract-for-task-101-text-embedding-assembly.md
  - docs/backlog/tasks/task-208-implement-semantic-only-train-step-assembly-for-task-101-text-embeddings.md
  - docs/backlog/tasks/task-209-add-local-gradient-membership-proof-for-semantic-only-text-embedding-assembly.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - proof
  - hemma
  - candidate-1
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first governed Hemma proof for Story 30 Candidate 1 after the local
semantic-only assembly gate from `T209`, and decide whether Candidate 1
authorizes the first clean restart or fails as an inherited-state rescue lane.

## PR Scope

- Use the existing detached proof surface; do not invent a new ad hoc replay
  command if `qwen-t198-proof` already satisfies the governed proof contract.
- Use the canonical RCA checkpoint:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen3-tts-swedish-hemma-training/task194-20260316t-1405-rca-a1/diagnostic-run/checkpoints/state-step-00001406`
- Hold the preserved no-projection fine-tuning lane fixed.
- Hold the Candidate 1 local gate fixed:
  - semantic-only batch contract from `T207`
  - semantic-only train/eval assembly from `T208`
  - local gradient-membership proof from `T209`
- Use the best surviving bounded replay posture from the exhausted Story 29
  family:
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=1`
- Run exactly one detached bounded proof:
  - clear `1406 -> 1470`
  - launch detached standalone eval only if a truthful `1470` checkpoint is
    minted
- Do not launch a new clean restart in this task.
- Do not reopen the old accumulation ladder, the preferred `1500` gate, or
  any replay-only variant on the pre-Candidate-1 code path.
- If the proof still fails numerically before `1470`, stop Candidate 1 rescue
  churn on the inherited `1406` checkpoint state instead of retrying the same
  replay lane.

## Deliverables

- [x] One prepared Candidate 1 proof package exists for the detached Hemma
  run.
- [x] One bounded `1406 -> 1470` detached proof record exists for the
  semantic-only assembly lane.
- [x] No detached standalone eval record exists because no truthful `1470`
  checkpoint was minted.
- [x] One operator-facing decision record states that Candidate 1 failed as an
  inherited-state rescue lane and does not authorize `T199`.

## Acceptance Criteria

- [x] `T209` is treated as the required local gate before the Hemma proof is
  launched.
- [x] The bounded proof uses the canonical `1406` checkpoint, the
  semantic-only assembly code path, and accumulation `1`.
- [x] Detached standalone eval is launched only after a truthful `1470`
  checkpoint exists.
- [x] If the proof fails numerically before `1470`, the task records Candidate
  1 as failed for restart authorization on the inherited-state rescue lane and
  does not authorize a clean restart.
- [x] `T199` remains blocked unless this task records a successful `1470 + detached eval` result in the training reference ledger.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_semantic_text_embeddings.py -q`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-t198-proof prepare --proof-id <proof-id> --gradient-accumulation-steps 1 --skip-build`
- [ ] `pdm run qwen-t198-proof launch-fallback1470 --proof-id <proof-id>`
- [ ] `pdm run qwen-t198-proof status-fallback1470 --proof-id <proof-id>`
- [ ] `pdm run qwen-t198-proof launch-fallback-eval --proof-id <proof-id>` only
  after a truthful `1470` checkpoint exists
- [ ] `pdm run qwen-t198-proof status-fallback-eval --proof-id <proof-id>` only
  when fallback eval was launched

## Current Prepared Package

- Prepared proof id:
  `task210-20260317t104600z-candidate1-a1`
- Local proof root:
  `build/verification/qwen-t198-proof/task210-20260317t104600z-candidate1-a1`
- Prepared command:
  `pdm run qwen-t198-proof prepare --proof-id task210-20260317t104600z-candidate1-a1 --gradient-accumulation-steps 1 --skip-build`
- Exact detached launch surface now ready:
  - bounded replay:
    `pdm run qwen-t198-proof launch-fallback1470 --proof-id task210-20260317t104600z-candidate1-a1`
  - bounded replay status:
    `pdm run qwen-t198-proof status-fallback1470 --proof-id task210-20260317t104600z-candidate1-a1`
  - detached fallback eval launch, only after truthful `1470`:
    `pdm run qwen-t198-proof launch-fallback-eval --proof-id task210-20260317t104600z-candidate1-a1`
  - detached fallback eval status:
    `pdm run qwen-t198-proof status-fallback-eval --proof-id task210-20260317t104600z-candidate1-a1`

## Outcome

- Hemma replay launched from the canonical inherited-state checkpoint:
  `state-step-00001406`
- The bounded proof failed immediately at optimizer step `1407`
- Failure family stayed the same:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - first bad backward surface: `input_text_embedding.grad`
  - first poisoned parameter surface: `text_embedding.weight.grad`
- Parameters and optimizer state remained finite before the attempted step
- No truthful new checkpoint was minted
- Detached standalone eval was correctly not launched
- Decision:
  - Candidate 1 failed as an inherited-state rescue lane
  - the next honest discriminant is a fresh-start Candidate 1 proof, not a
    relaunch of the same `1406` rescue replay

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
