---
id: task-237-test-one-post-t236-micro-family-against-the-first-verified-dominant-sub-talker-outlier-seam
title: Test one post-T236 micro-family against the first verified dominant sub-talker outlier seam
type: task
status: completed
priority: high
created: '2026-03-18'
last_updated: '2026-03-18'
related:
  - docs/backlog/stories/story-31-recover-a-stable-fresh-start-task-101-bundle-learning-recipe-through-talker-core-stabilization.md
  - docs/backlog/tasks/task-236-resolve-the-post-t235-line4-row-local-outlier-before-claiming-a-generic-layer15-output-seam.md
  - docs/backlog/tasks/task-240-split-the-post-t237-downstream-convergence-seam-beneath-layer15-output-before-any-promotion-discussion.md
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

Test one micro-family only against the first verified dominant seam produced
by `T236`, now fixed to the row-local upstream surface
`talker_core.layer_16.input_layernorm.output`, so Story 31 can keep drilling
toward a real fix without widening back into another multi-cause stabilizer
sweep.

## PR Scope

- Treat `T236` as the gating diagnosis:
  - truthful row-local resolution:
    `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task236-20260318t145434z-a1`
  - resolved classification:
    `genuine_row_local_seam_difference`
  - verified dominant seam for the next task:
    `talker_core.layer_16.input_layernorm.output`
- Keep the Story 32 state vector fixed:
  - same canonical bundle root
  - same selected rows `13,4`
  - same `text_span_only` mask policy
  - same Story 31 lab surface
  - same strongest T234 member:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
- Compare baseline plus at most two strength levels in one micro-family only.
- Target only the exact verified row-local seam:
  `talker_core.layer_16.input_layernorm.output`
- Do not mix in optimizer, bundle, sampler, or recovery changes.
- Stop if the family only relocates failure without extending the finite
  window.

## Interpretation Contract

- If one member clearly extends the finite window without merely moving the
  first failure to an adjacent seam, that member becomes the only candidate
  eligible for a later diagnosis-only downstream convergence split.
- If the family fails or only relocates failure without convergence, close it
  negative and keep Story 31 in mechanism.
- `T217` remains blocked unless a later promotion gate is actually earned.

## Implementation Status

- Implemented as one bounded fp32-output-cap micro-family at the exact T236
  seam:
  - baseline:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5`
  - candidates:
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
    and
    `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e2`
- Landed code surfaces:
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_stabilization.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_stabilization_specs.py`
  - `scripts/devops/qwen_finetuning_patches/sft_12hz_talker_core_stabilization_input_layernorm.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_micro_family_assessment.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_stability_lab_contracts.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_stability_lab_runner.py`
  - `scripts/sir_convert_a_lot/ml/qwen/training/qwen_stability_lab_markdown.py`

## Result

- Truthful bounded rerun:
  `/srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task237-20260318t154708z-a1`
- Resolved family classification:
  `converged_downstream`
- Winning candidate:
  `layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3`
- Dominant surface:
  `talker_core.layer_15.output`
- Under the winner:
  - `pair-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-13-sub-talker-loss` first broke at `talker_core.layer_15.output`
  - `line-4-sub-talker-loss` also moved downstream to
    `talker_core.layer_15.output`
- Interpretation:
  - `T237` closed the upstream row-local disagreement
  - Story 31 stays in `mechanism`
  - the next truthful step is diagnosis-only downstream seam splitting, not
    promotion and not recovery
  - `T240` is the immediate next task

## Deliverables

- [x] One diagnosed post-`T236` micro-family is implemented and compared.
- [x] One compact result matrix records baseline plus at most two strengths.
- [x] One explicit outcome records whether the family stayed upstream, regressed,
  or converged downstream.

## Acceptance Criteria

- [x] The task tests one diagnosed causal idea only.
- [x] The task compares no more than baseline plus two strengths.
- [x] The output distinguishes a real local winner from a simple failure
  relocation or regression.

## Validation

- [x] `pdm run pytest-root tests/sir_convert_a_lot/ml/qwen/training/test_talker_core_stabilization.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_micro_family_assessment.py tests/sir_convert_a_lot/ml/qwen/training/test_qwen_stability_lab.py -q`
- [x] `pdm run test-ml`
- [x] `pdm run typecheck-ml`
- [x] `pdm run typecheck-all`
- [x] `pdm run format-all`
- [x] `pdm run lint-fix`
- [x] `pdm run validate-tasks`
- [x] `pdm run validate-docs`
- [x] `pdm run index-tasks --root "$(pwd)/docs/backlog" --out "/tmp/sir_tasks_index.md" --fail-on-missing`
- [x] `pdm run run-hemma -- pdm run qwen-stability-lab run --output-root /srv/scratch/sir-convert-a-lot/build/verification/qwen-stability-lab/task237-20260318t154708z-a1 --skip-build --hook-profile talker_core_post_t235_row_local_outlier --stabilization-variants layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e3,layer16_gated_fp32_rescale_1e3_layer16_out_0p5_layer15_out_0p5_layer16_input_ln_output_0p5_layer16_input_ln_fp32_output_cap_1e2`

## Checklist

- [x] Implementation complete
- [x] Validation complete
- [x] Docs updated
