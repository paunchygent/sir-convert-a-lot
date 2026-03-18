---
id: task-230-test-one-diagnosed-post-t219-micro-family-against-the-first-verified-layer16-sub-boundary
title: Test one diagnosed post-T219 micro-family against the first verified layer16 sub-boundary
type: task
status: in_progress
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-229-split-the-post-t219-layer16-handoff-seam-into-sub-boundary-probes.md
  - docs/backlog/tasks/task-217-run-the-first-fresh-start-governed-hemma-proof-for-the-talker-core-stabilization-lane.md
  - docs/reference/ref-task101-training-eval-pilot-progress-2026-03-15.md
labels:
  - qwen
  - finetuning
  - mechanism
  - stabilization
  - follow-on
---

PR-sized execution unit; may be linked to a story or standalone.

## Objective

Test one diagnosed pre-`input_layernorm` normalization-entry micro-family only
against the first verified post-`T219` layer-16 sub-boundary so the repo learns
whether one precise causal idea extends the finite window, instead of
launching another mixed stabilizer sweep.

## PR Scope

- Treat `T229` as closed truth:
  - truthful narrowed rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task229-20260318t064712z-a1`
  - target loss family:
    `sub_talker_loss`
  - pair and both single-row cases agreed on:
    `talker_core.layer_16.input_layernorm`
  - `T230` is therefore constrained to one pre-`input_layernorm`
    normalization-entry micro-family only
- Keep the ranked `T219` winner as the fixed baseline within this family:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
- Implement and compare only these two diagnosed variants on top of that
  baseline:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_pre_input_ln_rescale_1e3`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_pre_input_ln_rescale_1e2`
- Compare exactly:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_pre_input_ln_rescale_1e3`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_pre_input_ln_rescale_1e2`
- Reuse the Story 31 lab rather than building a separate proof stack.
- Keep all non-intervention factors fixed:
  - bundle root
  - selected rows
  - seed/shuffle
  - batch size and accumulation
  - assembly mode
  - mask policy
- Stop if the new family only relocates failure without improving the finite
  window or promotion margin.

## Implementation Status

- This task is now narrowed to one causal idea only:
  bounded rescaling of the residual stream immediately before
  `talker_core.layer_16.input_layernorm`.
- No residual-side, MLP-side, optimizer-side, or bundle-side changes are
  allowed in this task.
- Promotion into a bounded fresh-start proof is still governed by `T231`;
  `T230` only decides whether a local winner exists.

## Deliverables

- [ ] One diagnosed micro-family is registered in the Story 31 lab.
- [ ] One compact result matrix compares the fixed ranked-`T219` baseline
  against at most two normalization-entry micro-family variants.
- [ ] One explicit outcome states whether a local winner exists for promotion
  work or whether the lane remains negative.

## Acceptance Criteria

- [ ] The task tests one diagnosed causal idea only; it does not mix residual,
  normalization, optimizer, and bundle changes in the same family.
- [ ] The task compares no more than the fixed baseline plus two
  normalization-entry variants.
- [ ] The result explicitly distinguishes:
  - no winner
  - one local winner with a longer finite window
  - one local winner that earns bounded promotion consideration
- [ ] `T217` remains blocked unless this task produces a clear local winner.

## Validation

- [ ] `pdm run test-ml`
- [ ] `pdm run typecheck-ml`
- [ ] `pdm run validate-tasks`
- [ ] `pdm run validate-docs`
- [ ] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [ ] `pdm run qwen-story31-stability-lab run --skip-build --hook-profile talker_core_handoff_sub_boundary --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_pre_input_ln_rescale_1e3,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_pre_input_ln_rescale_1e2`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
