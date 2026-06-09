---
id: task-228-close-the-failed-t219-layer16-handoff-family-with-one-ranked-failure-matrix
title: Close the failed T219 layer16 handoff family with one ranked failure matrix
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-219-implement-the-third-bounded-story31-layer16-handoff-candidate-for-the-shifted-seams.md
  - docs/backlog/tasks/task-215-add-the-smallest-signal-local-finiteness-gate-for-the-first-talker-core-stabilization-lane.md
  - docs/backlog/tasks/task-218-implement-the-second-bounded-story31-late-middle-attenuation-candidate-for-the-layer16-layer15-seams.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-qwen-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - stabilization
  - follow-on
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

If the `T219` layer-16 handoff family fails to earn promotion, close that
family truthfully before opening any new probe or fresh-start lane.

This task is the first contingent post-`T219` session. It exists to prevent
the repo from inferring too much from an unranked negative family and to fix
one clean handoff from `T219` into the next mechanism question.

## PR Scope

- Activate only if `T219` completes without a promoted winner.
- Re-run or summarize the exact `T219` family under one locked Story 32 state
  vector:
  - same bundle root
  - same row selection policy
  - same seed/shuffle posture
  - same assembly mode
  - same mask policy
  - same optimizer/accumulation posture
- Compare only:
  - `off`
  - the exact `T219` layer-16 handoff variants
- Record one ranked matrix using the existing Story 31 lab and gate:
  - earliest failing seam
  - first non-finite surface
  - surviving finite span or margin
  - whether failure relocates or remains monotonic with stronger handoff
    damping
- End with one explicit stop-rule decision:
  - candidate promoted -> return to the promotion ladder
  - no candidate promoted -> continue to `T229`
- Do not add new variants, reopen parity work, or widen into optimizer-regime
  experimentation.

## Outcome

`T228` is now completed using the recovered `T219` Hemma artifact root:

- output root:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task219-20260317t180700z-a1`
- surviving artifacts:
  - `results.json`
  - `results.md`
  - variant reports under `variant-reports/`
- evaluated family:
  - `off`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p25_layer15_out_0p5`

Truthful ranked closure of the family:

1. `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
   - best negative result
   - moved the pair `sub_talker_loss` seam downstream from
     `talker_core.layer_15.output` to
     `talker_core.layer_16.input_layernorm`
   - also moved both single-row `sub_talker_loss` cases to
     `talker_core.layer_16.input_layernorm`
   - pair `main_loss` / `combined_loss` still failed at
     `talker_core.layer_16.output`
1. `layer16_gated_fp32_rescale_1e3_layer16_out_0p25_layer15_out_0p5`
   - second-best negative result
   - pair `main_loss` / `combined_loss` also failed at
     `talker_core.layer_16.output`
   - single-row `sub_talker_loss` moved to
     `talker_core.layer_16.input_layernorm`
   - but the pair `sub_talker_loss` seam regressed to
     `talker_core.layer_15.output`
1. `off`
   - baseline negative family
   - pair `main_loss` / `combined_loss` first broke at
     `talker_core.layer_16.mlp.gated_product`
   - pair and single-row `sub_talker_loss` stayed at
     `talker_core.layer_15.output`

Interpretation:

- no variant kept the target family finite
- no variant earned promotion
- the `0p5` handoff variant is the strongest negative mechanism signal because
  it moved the widest share of the `sub_talker_loss` failures downstream
  without solving the family
- Story 31 should now continue to `T229`

Evidence limit:

- the recovered `T219` artifact set does not include a separate `gate.json`
  or scalar finite-window metric, so the ranking is based on earliest-failing
  seam movement across pair and single-row cases rather than an unrecorded
  numeric margin

## Deliverables

- [x] One compact `T219` family result matrix closes the handoff family under a
  single locked state vector.
- [x] One ranking table orders the failed variants by the recorded earliest
  seam movement, with the available evidence limit stated explicitly.
- [x] One explicit operator decision states whether the lane returns to
  promotion or moves to `T229`.

## Acceptance Criteria

- [x] The task activates only after `T219` closes without promotion.
- [x] The matrix compares only the exact `T219` variants plus `off`.
- [x] The result distinguishes "failure moved" from "failure stayed in place"
  rather than collapsing all negatives into one bucket.
- [x] If no winner is promoted, the task explicitly hands the lane to `T229`
  and keeps `T217` blocked.

## Validation

- [x] `pdm run run-hemma -- cat /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task219-20260317t180700z-a1/results.json`
- [x] `pdm run run-hemma -- cat /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task219-20260317t180700z-a1/results.md`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
