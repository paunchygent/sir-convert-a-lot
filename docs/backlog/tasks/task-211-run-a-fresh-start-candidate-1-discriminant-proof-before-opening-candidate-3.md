---
id: task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3
title: Run a fresh-start Candidate 1 discriminant proof before opening Candidate 3
type: task
status: done
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - candidate-1
  - proof
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run one short governed fresh-start Candidate 1 proof that separates inherited
checkpoint-state instability from architecture instability before the repo
opens the ordered Candidate 3 contingency.

## PR Scope

- Treat `T210` as closed negative evidence for the inherited `1406` rescue
  claim:
  - Candidate 1 did not stabilize the preserved lane when resumed from
    `state-step-00001406`
  - do not relaunch that same rescue proof
- Create a tiny fresh-start discriminant surface from
  `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, not from any legacy checkpoint.
- Keep the Candidate 1 local lane fixed:
  - semantic-only batch contract from `T207`
  - semantic-only train/eval assembly from `T208`
  - local gradient-membership proof from `T209`
- Materialize one real mini-bundle under Hemma scratch from the canonical
  frozen train bundle plus one non-executed launch placeholder eval row:
  - train slice: manifest lines `1..16` from `swedish_pilot_train`
  - eval slice: one launch-contract placeholder row written under
    `swedish_checkpoint_dev`
  - resolve the canonical dated Task 101 frozen bundle root automatically for
    train rows if the legacy undated placeholder path is absent on Hemma
  - source that eval placeholder from the same canonical frozen train bundle
    because the short probe makes no eval claim and the available held-out eval
    manifests do not carry `precomputed_ref_input_path`
- Use the standard detached `qwen-train launch/status` runtime, not an ad hoc
  shell workflow.
- Keep the probe intentionally short:
  - fresh start
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=1`
  - no governed eval claim from this task
  - no clean-restart authorization from this task
- If the fresh-start proof fails in the same numerical family, close Candidate
  1 as a fresh-start discriminant and stop attributing the failure primarily
  to replay-amassed state.
- If the fresh-start proof stays finite across the bounded short slice, record
  that inherited training history remains a live suspect and define the next
  clean-start Candidate 1 Hemma proof task.

## Deliverables

- [x] One committed fresh-start proof surface exists with deterministic
  `prepare`, `launch`, and `status` commands.
- [x] One committed mini-bundle materialization helper exists for the bounded
  discriminant slice.
- [x] One prepared proof package exists with the exact proof id and detached
  commands.
- [x] One operator-facing decision record states whether the result points to
  deeper architectural discovery rather than another replay-only explanation.

## Acceptance Criteria

- [x] The fresh-start proof does not resume from `state-step-00001406` or any
  other legacy checkpoint.
- [x] The bounded train slice is a truthful mini-bundle rooted in the canonical
  frozen train bundle, the launch placeholder eval row is explicitly marked as
  non-evidentiary for held-out eval, and the train slice includes the known
  problematic line-14 family.
- [x] The runtime surface uses detached Hemma execution and a committed repo
  command, not inline remote shell logic.
- [x] The proof records whether Candidate 1 still fails from a fresh start or
  only failed as an in-place rescue from inherited state.
- [x] `T199` remains blocked after this task unless a later explicit clean-start
  proof authorizes restart.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_qwen_freshstart_proof.py -q`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_qwen_freshstart_bundle.py -q`
- [x] `pdm run typecheck-all`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-freshstart-proof prepare --proof-id <proof-id> --skip-build`
- [x] `pdm run qwen-freshstart-proof launch --proof-id <proof-id>`
- [x] `pdm run qwen-freshstart-proof status --proof-id <proof-id>`

## Outcome

- Final proof id:
  `task211-20260317t130740z-freshstart-a4`
- Local proof root:
  `build/verification/qwen-freshstart-proof/task211-20260317t130740z-freshstart-a4`
- Terminal artifact:
  `build/verification/qwen-freshstart-proof/task211-20260317t130740z-freshstart-a4/status.json`
- Terminal Hemma result:
  - `status=exited`
  - `exit_code=1`
  - `current_optimizer_step=1`
  - `current_train_iteration=1`
  - `latest_checkpoint_found=false`
  - `eval_runs_completed=0`
- Exact failure family:
  - `trigger_reason=pre_clip_non_finite_gradients`
  - `first_non_finite_surface=text_embedding.weight.grad`
  - `optimizer_step_attempted=false`
  - `optimizer_step_completed=false`
  - `pre_step_parameter_probes.first_non_finite_surface=null`
  - `pre_step_optimizer_state_probes.first_non_finite_surface=null`
  - `pre_clip_gradient_probes.probes.text_embedding.weight.nan_count=92160`
- First failing microbatch provenance:
  - manifest line `13`
  - manifest line `4`
  - both from the fresh-start mini-bundle
- Strongest interpretation:
  - Candidate 1 failed on a fresh start, not only as an inherited-state rescue
  - replay-amassed state is no longer the primary explanation
  - the next discovery lane must isolate the first non-finite backward edge
    inside the graph rather than repeating replay proofs

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
