---
id: task-246-split-the-post-t245-fp32-scaled-layer15-output-result-from-the-final-emitted-tensor-before-any-new-stabilizer-family
title: Split the post-T245 fp32-scaled layer15 output result from the final emitted tensor before any new stabilizer family
type: task
status: pending
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-245-confirm-the-post-t244-winner-specific-layer15-output-attenuation-multiply-before-any-new-stabilizer-family.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - diagnostics
  - follow-on
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Split the post-`T245` converged `talker_core.layer_15.output` seam one level
deeper under the fixed fp32-multiply confirmation variant so Story 31 can
determine whether the first reproducible `sub_talker_loss` break is born:

- in the fp32-scaled layer-15 output result before the final emitted tensor is
  materialized, or
- only in the final emitted `talker_core.layer_15.output` tensor handed to the
  downstream consumer

before any new stabilizer family is considered.

## PR Scope

- Treat `T245` as closed truth:
  - truthful rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task245-20260318t202916z-a1`
  - resolved classification:
    `multiply_not_causal`
  - dominant surface:
    `talker_core.layer_15.output`
  - fixed confirmation variant only:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3_layer15_output_scale_fp32`
- Keep the full Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same fixed T245 confirmation variant only
  - no optimizer, sampler, recovery, or bundle changes
- Add one diagnosis-only hook profile or equivalent bounded trace corridor that
  splits the fixed T245 output path into the smallest meaningful post-multiply
  sub-boundaries.
- Constrain the corridor to:
  - the fp32-scaled layer-15 output result before the final emitted tensor is
    returned
  - the final emitted `talker_core.layer_15.output`
  - `talker_core.layer_16.input` as the downstream guard surface
- Interpret only the three normative `sub_talker_loss` rows:
  - `pair-sub-talker-loss`
  - `line-13-sub-talker-loss`
  - `line-4-sub-talker-loss`
- Treat `main_loss` and `combined_loss` as observational only.
- Do not add a new stabilizer family in this task.

## Interpretation Contract

- Classify `converged_fp32_scaled_output` if all three normative rows first
  break at the fp32-scaled layer-15 output result.
- Classify `converged_output_return` if all three normative rows first break
  at the final emitted `talker_core.layer_15.output`.
- Classify `converged_layer16_input_handoff` if all three normative rows first
  break at `talker_core.layer_16.input`.
- Classify `downstream_disagreement` if all three rows stay inside the
  committed corridor but do not agree on one earliest surface.
- Classify `nonlocal_regression` if any required row reverts upstream, skips
  outside the committed corridor, or stays finite.
- Keep `T217` blocked in every branch.

## Deliverables

- [ ] One diagnosis-only T246 split exists for the fixed T245 confirmation
  variant.
- [ ] One machine-readable assessment payload classifies the narrowed
  post-multiply `layer_15.output` seam.
- [ ] One truthful Hemma rerun records the next smallest localized output seam
  and the next diagnosis-only rule.

## Acceptance Criteria

- [ ] The task uses only the fixed T245 confirmation variant and does not
  compare alternate variants.
- [ ] The task keeps the full Story 32 state vector fixed apart from the
  narrowed post-multiply output trace corridor.
- [ ] The result ends with exactly one diagnosis classification and one next
  diagnosis rule.

## Validation

- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
