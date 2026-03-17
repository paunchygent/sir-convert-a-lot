---
id: 'task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane'
title: 'Run the first fresh-start governed Hemma proof for the talker-core stabilization lane'
type: 'task'
status: 'proposed'
priority: 'high'
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-216-implement-the-first-bounded-talker-core-stabilization-surface-for-the-late-middle-qwen-failure-seam.md
  - docs/backlog/tasks/task-199-launch-the-first-clean-base-restart-after-the-bounded-stability-gate.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - stabilization
  - hemma
  - proof
---
PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run the first short governed fresh-start Hemma proof for the talker-core
stabilization lane so we can decide whether the repo has recovered a viable
clean-start bundle-learning recipe or must escalate to a stronger architecture
shift.

This task must only run for the first Story 31 candidate that earns promotion
from the exploration lane.

## PR Scope

- Treat `T216` and `T215` as prerequisites:
  - the bounded talker-core stabilization surface exists
  - the smallest-signal local finiteness gate is green
- Reuse existing governed surfaces wherever possible:
  - mini-bundle truth from the Story 30 fresh-start lane
  - scratch-headroom and detached status helpers from the existing proof
    surfaces
  - `qwen-train launch/status` rather than a bespoke remote shell flow
- Launch from `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, not from any replay checkpoint.
- Reuse the governed fresh-start operator posture from `T211` where possible:
  - canonical frozen Task 101 mini-bundle
  - detached Hemma execution
  - short bounded run
- Keep this proof purposefully narrow:
  - establish whether early fresh-start learning stays finite on the stabilized
  lane
  - do not authorize a full restart from this task alone
- Do not run this task for a candidate that has not crossed the local
  promotion gate.
- Record the exact stabilization posture and result in operator artifacts and
  the Task 101 reference ledger.

## Deliverables

- [ ] One committed fresh-start Hemma proof package exists for the talker-core
  stabilization lane.
- [ ] One truthful Hemma result states whether the stabilized lane survives the
  early fresh-start window.
- [ ] One operator-facing decision record states whether a larger clean-start
  proof is now justified or whether the repo must escalate again.

## Acceptance Criteria

- [ ] The proof does not reuse replay checkpoints or inherited-state rescue
  framing.
- [ ] The proof is only launched for a promoted exploration winner.
- [ ] The exact stabilization posture is recorded in proof metadata.
- [ ] The result is written into `current.md` and the Task 101 reference ledger
  before any broader restart decision.
- [ ] `T199` remains blocked unless this proof provides an explicit positive
  basis for a larger clean-start proof lane.

## Validation

- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run <governed proof surface> prepare`
- [ ] `pdm run <governed proof surface> launch`
- [ ] `pdm run <governed proof surface> status`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
