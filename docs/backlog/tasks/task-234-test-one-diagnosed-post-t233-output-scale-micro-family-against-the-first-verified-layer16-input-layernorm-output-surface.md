---
id: task-234-test-one-diagnosed-post-t233-output-scale-micro-family-against-the-first-verified-layer16-input-layernorm-output-surface
title: Test one diagnosed post-T233 output-scale micro-family against the first verified layer16 input-layernorm output surface
type: task
status: proposed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-233-split-the-post-t230-layer16-input-layernorm-seam-into-normalization-internal-probes.md
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

Test one diagnosed post-normalization output-scale micro-family only against
the first verified `T233` internal surface so the repo learns whether bounded
attenuation of `layer_16.input_layernorm.output` extends the finite window,
instead of widening back into another mixed stabilizer sweep.

## PR Scope

- Treat `T233` as closed truth:
  - truthful narrowed rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task233-20260318t112544z-a1`
  - the pair and both single-row `sub_talker_loss` cases agreed on:
    `talker_core.layer_16.input_layernorm.output`
  - the broader nine-row matrix also first broke at that same output surface
  - `T234` is therefore constrained to one post-normalization output-scale
    micro-family only
- Keep the ranked baseline stabilizer fixed:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
- Implement and compare only these diagnosed variants on top of that baseline:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
- Compare exactly:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
- Reuse the Story 31 lab rather than building a separate proof stack.
- Use the broader `talker_core_boundary` hook profile so the task can detect
  whether the output-scale family clears the exact `input_layernorm.output`
  seam or merely moves failure immediately downstream into the next boundary.
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

- This task is not implemented yet.
- It must test one causal idea only:
  bounded attenuation of `talker_core.layer_16.input_layernorm.output`.
- No normalization-internal, residual-side, MLP-side, optimizer-side, or
  bundle-side changes are allowed in this task.
- Promotion into a bounded fresh-start proof remains governed by `T217`;
  `T234` only decides whether a local output-scale winner exists.

## Deliverables

- [ ] One diagnosed post-normalization output-scale micro-family is registered
  in the Story 31 lab.
- [ ] One compact result matrix compares the fixed baseline against at most two
  output-scale variants.
- [ ] One explicit outcome states whether a local winner exists for promotion
  work or whether the lane remains negative.

## Acceptance Criteria

- [ ] The task tests one diagnosed causal idea only; it does not mix output
  attenuation with normalization-internal, residual, optimizer, and bundle
  changes in the same family.
- [ ] The task compares no more than the fixed baseline plus two output-scale
  variants.
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
- [ ] `pdm run run-hemma -- pdm run qwen-story31-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-story31-stability-lab/task234-<timestamp>-a1 --skip-build --hook-profile talker_core_boundary --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`

## Checklist

- [ ] Implementation complete
- [ ] Validation complete
- [ ] Docs updated
