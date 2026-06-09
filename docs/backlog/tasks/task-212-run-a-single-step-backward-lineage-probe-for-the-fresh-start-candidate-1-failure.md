---
id: task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure
title: Run a single-step backward-lineage probe for the fresh-start Candidate 1 failure
type: task
status: done
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
  - docs/backlog/tasks/task-210-run-the-first-governed-hemma-proof-for-candidate-1-semantic-only-assembly.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
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

## Outcome

`T212` is complete with one truthful Hemma probe result:

- operational launch repairs:
  - `task212-20260317t140500z-lineage-a1` failed before probe execution
    because Docker could not bind-mount the `/srv/scratch/.../mini-bundle`
    path directly for this surface
  - `task212-20260317t141000z-lineage-a2` failed before probe execution
    because the in-container runner lacked the repo mount needed to import
    `scripts.sir_convert_a_lot.ml.qwen.training.backward_lineage_probe`
- truthful backward-lineage proof:
  - `task212-20260317t141500z-lineage-a3`
  - detached worker exit code: `0`
  - report artifact:
    `build/verification/qwen-backward-lineage/task212-20260317t141500z-lineage-a3/status.json`

What the truthful probe proved:

- all three branch orders failed on the exact row pair:
  - `main_loss`
  - `sub_talker_loss`
  - `combined_loss`
- both isolated rows also failed independently:
  - line `13` alone
  - line `4` alone
- the branch summaries were `both_rows` for every loss branch, so this is not
  a pair-only interaction defect
- `hidden_states` gradient stayed finite first
- `talker_hidden_states` gradient stayed finite where present
- the earliest instrumented non-finite backward hook then appeared at
  `input_embeddings`
- after `input_embeddings` became non-finite, the additive branches all
  inherited non-finite gradients:
  - `fused_auxiliary_embedding`
  - `input_codec_embedding`
  - `input_text_embedding`
  - `semantic_text_embeddings`
- the targeted RCA still reported:
  - first non-finite backward surface:
    `input_text_embedding.grad`
  - first poisoned parameter surface:
    `text_embedding.weight.grad`
- anomaly traces differed by branch:
  - `main_loss` and `combined_loss`:
    `MulBackward0`
  - `sub_talker_loss`:
    `MmBackward0`

Operator conclusion:

- `T212` explains why the fresh-start Candidate 1 lane still fails on step `1`
  more honestly than replay ever could
- the current failure is not row-pair-only and not replay-inherited-state-only
- the earliest instrumented non-finite appears at `input_embeddings`, after a
  still-finite `hidden_states` gradient
- the next clean move is to trace the first talker-core backward operation
  between `hidden_states` and `input_embeddings` before opening Candidate `3`

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

- [x] One committed backward-lineage probe surface exists with deterministic
  `prepare`, `launch`, and `status` commands.
- [x] One committed bounded bundle/helper exists for the exact row-pair probe.
- [x] One Hemma proof result records the branch-ordered outcome:
  `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation.
- [x] One operator-facing decision record states the earliest non-finite
  backward edge/tensor currently visible in the graph.

## Acceptance Criteria

- [x] The probe does not resume from any legacy Task 101 checkpoint.
- [x] The probe uses the exact `T211` fresh-start row pair first:
  manifest lines `13` and `4`.
- [x] The probe records the first non-finite backward edge/tensor, not only
  the first failed parameter gradient row set.
- [x] The branch order is exactly:
  `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation.
- [x] The runtime surface uses committed repo commands and detached Hemma
  execution rather than inline remote shell logic.
- [x] The result is recorded in the active task, `current.md`, and the Task 101
  reference ledger before any new long proof or restart discussion.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_qwen_backward_lineage_bundle.py -q`
- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_qwen_backward_lineage_probe.py -q`
- [x] `pdm run typecheck-all`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run qwen-backward-lineage prepare --proof-id <proof-id> --skip-build`
- [x] `pdm run qwen-backward-lineage launch --proof-id <proof-id>`
- [x] `pdm run qwen-backward-lineage status --proof-id <proof-id>`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
