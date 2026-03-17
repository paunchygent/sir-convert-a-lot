---
id: task-213-trace-the-first-talker-core-backward-operation-after-input-embeddings-in-the-fresh-start-candidate-1-failure
title: Trace the first talker-core backward operation after input embeddings in the fresh-start Candidate 1 failure
type: task
status: done
priority: high
created: '2026-03-17'
last_updated: '2026-03-17'
related:
  - docs/backlog/stories/story-30-define-the-post-task-101-design-lane-after-the-final-story-29-stop-rule.md
  - docs/backlog/tasks/task-212-run-a-single-step-backward-lineage-probe-for-the-fresh-start-candidate-1-failure.md
  - docs/backlog/tasks/task-211-run-a-fresh-start-candidate-1-discriminant-proof-before-opening-candidate-3.md
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

Trace the first talker-core backward operation between still-finite
`hidden_states` gradients and newly non-finite `input_embeddings` gradients in
the fresh-start Candidate 1 failure, so the repo can identify the missing
talker-core puzzle piece before making any Candidate `3` implementation move.

## PR Scope

- Treat `T212` as closed truth:
  - the truthful fresh-start backward-lineage probe was
    `task212-20260317t141500z-lineage-a3`
  - both isolated rows failed independently
  - all three loss branches failed
  - `hidden_states` and `talker_hidden_states` gradients stayed finite first
  - `input_embeddings` was the earliest currently instrumented non-finite
    backward hook
- Build one committed talker-core probe surface that:
  - reuses the exact `T212` fresh-start row pair:
    manifest lines `13` and `4`
  - reuses the same probe order:
    `main_loss`, `sub_talker_loss`, `combined_loss`, then row isolation
  - instruments the talker-core path between `input_embeddings` and the first
    still-finite hidden-state surfaces
  - identifies the first talker-core backward op or tensor family that turns
    non-finite before the additive input branches inherit that corruption
- Keep the probe detached and committed on Hemma; do not debug through inline
  shell payloads or ad hoc notebooks.
- Do not reopen replay framing in this task.
- Do not open Candidate `3` implementation work until this talker-core trace
  either identifies the decisive missing piece or clearly proves the probe no
  longer yields additional causal signal.

## Deliverables

- [x] One committed talker-core backward probe surface exists for the exact
  fresh-start row pair from `T212`.
- [x] One truthful Hemma probe result identifies the earliest non-finite
  talker-core backward op or tensor family between `hidden_states` and
  `input_embeddings`.
- [x] One operator-facing decision record states whether Candidate `3` should
  now open immediately or whether another smaller causal split is still more
  truthful.

## Acceptance Criteria

- [x] The probe does not resume from any legacy Task 101 checkpoint.
- [x] The probe keeps the exact `T212` row pair and branch order unless a
  smaller probe is explicitly documented as more decisive.
- [x] The result localizes corruption more precisely than:
  `input_embeddings` non-finite / `input_text_embedding.grad` first RCA
  surface / `text_embedding.weight.grad` first parameter surface.
- [x] The runtime surface uses committed repo commands and detached Hemma
  execution rather than inline remote shell logic.
- [x] The result is recorded in the active task, `current.md`, and the Task
  101 reference ledger before any Candidate `3` implementation slice starts.

## Result

- Truthful probe:
  `task213-20260317t143810z-talkercore-a1`
- Artifact:
  `build/verification/qwen-story30-backward-lineage/task213-20260317t143810z-talkercore-a1/status.json`
- Pair `main_loss` and pair `combined_loss` first non-finite talker-core hook:
  `talker_core.layer_16.post_attention_layernorm`
- Pair `sub_talker_loss` first non-finite talker-core hook:
  `talker_core.layer_15.output`
- Isolated row `13` and isolated row `4`:
  - `main_loss` and `combined_loss` first localized at
    `talker_core.layer_16.output`
  - `sub_talker_loss` first localized at `talker_core.layer_15.output`
- Pair-main anomaly trace:
  `MulBackward0`
- Pair-sub anomaly trace:
  `MmBackward0`
- Pair-combined anomaly trace:
  `MulBackward0`
- Pair-main gradient magnitudes stayed finite while exploding across late
  talker layers:
  - `layer_27.output`: `1.07e-4`
  - `layer_26.output`: `2.34e3`
  - `layer_25.output`: `1.77e7`
  - `layer_24.output`: `1.04e11`
  - `layer_23.output`: `6.16e14`
  - `layer_22.output`: `1.73e18`
  - `layer_21.output`: `4.35e21`
  - `layer_20.output`: `1.22e25`
  - `layer_19.output`: `2.35e28`
  - `layer_18.output`: `6.75e31`
  - `layer_17.output`: `3.09e35`
  - `layer_16.output`: `3.19e38`
  - `layer_16.post_attention_layernorm`: first non-finite (`2048` NaNs)

## Decision

Do not open Candidate `3` immediately.

`T213` yielded materially stronger causal signal inside the talker core, so the
next truthful move is one smaller split around the localized layer
`16` / layer `15` MLP-residual boundary. That next owner is `T214`.

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
