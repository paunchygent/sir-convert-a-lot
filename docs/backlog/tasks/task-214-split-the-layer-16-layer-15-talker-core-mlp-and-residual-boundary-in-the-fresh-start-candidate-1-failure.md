---
id: task-214-split-the-layer-16-layer-15-talker-core-mlp-and-residual-boundary-in-the-fresh-start-candidate-1-failure
title: Split the layer 16/layer 15 talker-core MLP and residual boundary in the fresh-start Candidate 1 failure
type: task
status: done
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-213-trace-the-first-talker-core-backward-operation-after-input-embeddings-in-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - candidate-1
  - rca
  - hemma
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Split the newly localized talker-core failure boundary from `T213` so the repo
can identify whether the decisive missing piece is the layer `16` MLP/residual
path, the layer `15` downstream residual/output path, or a smaller shared
talker-core defect before making any Candidate `3` implementation move.

## PR Scope

- Treat `T213` as closed truth:
  - truthful probe:
    `task213-20260317t143810z-talkercore-a1`
  - earliest talker-core non-finite hook for pair `main_loss` and
    `combined_loss`:
    `talker_core.layer_16.post_attention_layernorm`
  - earliest talker-core non-finite hook for pair `sub_talker_loss`:
    `talker_core.layer_15.output`
  - isolated row runs localized to `talker_core.layer_16.output` for
    `main_loss` and `combined_loss`, and to `talker_core.layer_15.output` for
    `sub_talker_loss`
  - pair-main gradient magnitudes stayed finite but exploded from
    `1.07e-4` at `layer_27.output` to `3.19e38` at `layer_16.output` before
    `layer_16.post_attention_layernorm` turned non-finite
- Build one committed finer-grained talker-core probe that:
  - keeps the exact fresh-start row pair from `T212/T213`
  - keeps the same branch order:
    `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation
  - instruments the layer `16` MLP/residual path and the immediately adjacent
    layer `15` output boundary
  - identifies whether the first non-finite backward op is introduced by:
    - the layer `16` gated MLP multiplication path
    - one of the layer `16` linear projections
    - the layer `16` residual add boundary
    - or the first layer `15` downstream output boundary
- Keep the probe detached and committed on Hemma; do not debug via inline
  shell payloads or notebooks.
- Do not open Candidate `3` implementation while this smaller causal split is
  still yielding new signal.

## Deliverables

- [x] One committed finer-grained talker-core probe exists for the exact
  `T212/T213` row pair and branch order.
- [x] One truthful Hemma probe result localizes the first non-finite boundary
  beyond:
  `layer_16.post_attention_layernorm` / `layer_16.output` / `layer_15.output`.
- [x] One operator-facing decision record states whether Candidate `3` should
  now open or whether a talker-core design lane should replace it as the
  truthful next move.

## Acceptance Criteria

- [x] The probe remains fresh-start only; it does not resume from any legacy
  Task 101 checkpoint.
- [x] The probe retains the exact row pair and branch order unless a smaller
  decisive split is explicitly documented.
- [x] The result localizes corruption more precisely than the `T213`
  talker-core boundary.
- [x] The runtime surface uses committed repo commands and detached Hemma
  execution.
- [x] The result is recorded in the active task, `current.md`, and the Task
  101 reference ledger before any Candidate `3` implementation slice starts.

## Result

- Truthful probe:
  `task214-20260317t151800z-boundary-a1`
- Artifact:
  `build/verification/qwen-story30-backward-lineage/task214-20260317t151800z-boundary-a1/status.json`
- Pair `main_loss` and `combined_loss` first non-finite hook:
  `talker_core.layer_16.mlp.gated_product`
- Pair `sub_talker_loss` first non-finite hook:
  `talker_core.layer_15.output`
- Pair-main / pair-combined retained still-finite gradients at:
  - `talker_core.layer_16.output`
  - `talker_core.layer_16.mlp.down_proj`
    with max abs about `3.19e38` and `3.26e38` before the first non-finite hook
    at `gated_product`
- Pair-main / pair-combined anomaly trace:
  `MulBackward0`
- Pair-sub anomaly trace:
  `MmBackward0`
- Isolated rows still failed independently:
  - isolated `main_loss` / `combined_loss` first localized at
    `talker_core.layer_16.output`
  - isolated `sub_talker_loss` first localized at
    `talker_core.layer_15.output`

## Decision

Do not open Candidate `3` as the immediate next move.

`T214` yielded a smaller causal split that changes the solution posture: the
next truthful lane is a solution-oriented talker-core stabilization story aimed
at stable fresh-start bundle learning, not another replay proof and not an
immediate text-embedding fallback.

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
