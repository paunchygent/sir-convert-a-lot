---
id: task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure
title: Run a single-step backward-lineage probe for the fresh-start Candidate 1 failure
type: task
status: in_progress
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
  - docs/runbooks/runbook-qwen3-swedish-finetuning-on-hemma-and-colab.md
labels:
  - qwen
  - finetuning
  - candidate-1
  - rca
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Run one committed single-step backward-lineage probe on Hemma against the
exact fresh-start Candidate 1 failing row pair from `T211` so the repo can
identify the first non-finite backward edge/tensor inside the graph instead of
continuing to reason from replay or parameter-symptom surfaces.

## PR Scope

- Treat `T211` as closed truth:
  - the fresh-start Candidate 1 probe failed at optimizer step `1`
  - the first poisoned parameter surface was `text_embedding.weight.grad`
  - forward tensors and losses stayed finite
  - replay-amassed inherited state is no longer the leading explanation
- Reuse the exact fresh-start failing microbatch provenance from `T211`:
  - manifest line `13`
  - manifest line `4`
- Build one committed probe surface that:
  - starts from `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
  - uses the current Candidate 1 semantic-only assembly lane from `T207-T209`
  - materializes only the required bounded train rows under Hemma scratch
  - runs one forward/backward without an optimizer step
  - captures the first non-finite backward edge/tensor with JSON-safe output
- Probe the loss branches in this exact order:
  - `main_loss`
  - `sub_talker_loss`
  - `combined_loss`
  - then row isolation:
    - line `13` alone
    - line `4` alone
    - lines `13 + 4` together
- Record whether the failure is:
  - main-loss-local
  - sub-talker-local
  - combined-only
  - row-local
  - batch-interaction-only
- Keep the surface committed and detached/operator-governed on Hemma; do not
  debug through inline remote shell payloads.
- Do not turn this task into another replay or restart authorization lane.

## Deliverables

- [ ] One committed backward-lineage probe surface exists with deterministic
  `prepare`, `launch`, and `status` commands.
- [ ] One committed bounded bundle/helper exists for the exact row-pair probe.
- [ ] One Hemma proof result records the branch-ordered outcome:
  `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation.
- [ ] One operator-facing decision record states the earliest non-finite
  backward edge/tensor currently visible in the graph.

## Acceptance Criteria

- [ ] The probe does not resume from any legacy Task 101 checkpoint.
- [ ] The probe uses the exact `T211` fresh-start row pair first:
  manifest lines `13` and `4`.
- [ ] The probe records the first non-finite backward edge/tensor, not only
  the first failed parameter gradient row set.
- [ ] The branch order is exactly:
  `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation.
- [ ] The runtime surface uses committed repo commands and detached Hemma
  execution rather than inline remote shell logic.
- [ ] The result is recorded in the active task, `current.md`, and the Task 101
  reference ledger before any new long proof or restart discussion.

## Validation

- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story30_backward_lineage_bundle.py -q`
- [ ] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_story30_backward_lineage_probe.py -q`
- [ ] `pdm run typecheck-all`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-story30-backward-lineage prepare --proof-id <proof-id> --skip-build`
- [ ] `pdm run qwen-story30-backward-lineage launch --proof-id <proof-id>`
- [ ] `pdm run qwen-story30-backward-lineage status --proof-id <proof-id>`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
