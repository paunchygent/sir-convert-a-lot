---
id: task-234-test-one-diagnosed-post-t233-output-scale-micro-family-against-the-first-verified-layer16-input-layernorm-output-surface
title: Test one diagnosed post-T233 output-scale micro-family against the first verified layer16 input-layernorm output surface
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-233-split-the-post-t230-layer16-input-layernorm-seam-into-normalization-internal-probes.md
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

Test one diagnosed post-normalization output-scale micro-family only against
the first verified `T233` internal surface so the repo learns whether bounded
attenuation of `layer_16.input_layernorm.output` extends the finite window,
instead of widening back into another mixed stabilizer sweep.

## PR Scope

- Treat `T233` as closed truth:
  - truthful narrowed rerun:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task233-20260318t112544z-a1`
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

- Implemented in the bounded Story 31 stabilization surface by adding one
  output-scale family on top of the fixed ranked baseline:
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75`
  - `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
- Landed code surfaces:
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_stabilization.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_stabilization_specs.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_stabilization_input_layernorm.py`
- Result is now closed truth under:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task234-20260318t123644z-a1`
- Outcome:
  - no variant stayed finite
  - no variant earned promotion
  - the stronger `0p5` output-scale member was the strongest diagnostic member
    because it shifted `pair-sub-talker-loss` and `line-13-sub-talker-loss`
    downstream to `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` still first broke at
    `talker_core.layer_16.input_layernorm`
  - every `main_loss` and `combined_loss` case still first broke at
    `talker_core.layer_16.output`
- Interpretation:
  `T234` closes as no-promotion mechanism evidence and opens one next
  disagreement-resolution slice instead of authorizing recovery.

## Deliverables

- [x] One diagnosed post-normalization output-scale micro-family is registered
  in the Story 31 lab.
- [x] One compact result matrix compares the fixed baseline against at most two
  output-scale variants.
- [x] One explicit outcome states whether a local winner exists for promotion
  work or whether the lane remains negative.

## Acceptance Criteria

- [x] The task tests one diagnosed causal idea only; it does not mix output
  attenuation with normalization-internal, residual, optimizer, and bundle
  changes in the same family.
- [x] The task compares no more than the fixed baseline plus two output-scale
  variants.
- [x] The result explicitly distinguishes:
  - no winner
  - one local winner with a longer finite window
  - one local winner that earns bounded promotion consideration
- [x] `T217` remains blocked unless this task produces a clear local winner.

## Validation

- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task234-20260318t123644z-a1 --skip-build --hook-profile talker_core_boundary --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p75,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
