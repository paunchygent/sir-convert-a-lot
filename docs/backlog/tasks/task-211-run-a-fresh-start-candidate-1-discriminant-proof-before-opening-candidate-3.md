---
id: task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3
title: Run a fresh-start Candidate 1 discriminant proof before opening Candidate 3
type: task
status: in_progress
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
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
- Materialize one real mini-bundle under Hemma scratch from the canonical pilot
  bundle:
  - train slice: manifest lines `1..16` from `swedish_pilot_train`
  - eval slice: manifest line `1` from `swedish_checkpoint_dev`
- Use the standard detached `qwen-train launch/status` runtime, not an ad hoc
  shell workflow.
- Keep the probe intentionally short:
  - fresh start
  - `text_embedding_mask_policy=text_span_only`
  - `gradient_accumulation_steps=1`
  - no governed eval claim from this task
  - no clean-restart authorization from this task
- If the fresh-start proof fails in the same numerical family, close Candidate
  1 as a fresh-start discriminant and open Candidate 3 directly.
- If the fresh-start proof stays finite across the bounded short slice, record
  that inherited training history remains a live suspect and define the next
  clean-start Candidate 1 Hemma proof task.

## Deliverables

- [ ] One committed fresh-start proof surface exists with deterministic
  `prepare`, `launch`, and `status` commands.
- [ ] One committed mini-bundle materialization helper exists for the bounded
  discriminant slice.
- [ ] One prepared proof package exists with the exact proof id and detached
  commands.
- [ ] One operator-facing decision record states whether the result points to
  Candidate 3 directly or to a larger clean-start Candidate 1 proof.

## Acceptance Criteria

- [ ] The fresh-start proof does not resume from `state-step-00001406` or any
  other legacy checkpoint.
- [ ] The bounded train slice is a truthful mini-bundle rooted in the canonical
  pilot bundle and includes the known problematic line-14 family.
- [ ] The runtime surface uses detached Hemma execution and a committed repo
  command, not inline remote shell logic.
- [ ] The proof records whether Candidate 1 still fails from a fresh start or
  only failed as an in-place rescue from inherited state.
- [ ] `T199` remains blocked after this task unless a later explicit clean-start
  proof authorizes restart.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story30_freshstart_proof.py -q`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story30_freshstart_bundle.py -q`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-story30-freshstart-proof prepare --proof-id <proof-id> --skip-build`
- [ ] `pdm run qwen-story30-freshstart-proof launch --proof-id <proof-id>`
- [ ] `pdm run qwen-story30-freshstart-proof status --proof-id <proof-id>`

## Current Prepared Package

- Prepared proof id:
  `task211-20260317t121557z-freshstart-a1`
- Local proof root:
  `build/verification/qwen-story30-freshstart-proof/task211-20260317t121557z-freshstart-a1`
- Prepared command:
  `pdm run qwen-story30-freshstart-proof prepare --proof-id task211-20260317t121557z-freshstart-a1 --skip-build`
- Exact detached surface now ready:
  - launch:
    `pdm run qwen-story30-freshstart-proof launch --proof-id task211-20260317t121557z-freshstart-a1`
  - status:
    `pdm run qwen-story30-freshstart-proof status --proof-id task211-20260317t121557z-freshstart-a1`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
